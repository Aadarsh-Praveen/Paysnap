"""
app/model/agentic_analyzer.py

Agentic wage theft analyzer using Gemma 4 native function calling.
Gemma 4 decides which tools to call based on what it sees in the paystub.

Flow:
  1. Send paystub data + tools to Gemma 4
  2. Gemma 4 calls calculate_overtime if hours > 40
  3. Gemma 4 calls check_minimum_wage to verify rate
  4. Gemma 4 calls check_deductions for each deduction
  5. Gemma 4 calls get_applicable_statutes for violations found
  6. Gemma 4 calls get_dol_contact for worker next steps
  7. Gemma 4 generates final explanation in worker's language

This uses Gemma 4's NATIVE FUNCTION CALLING capability —
Gemma 4 autonomously decides what to check, not the backend.
"""

import json
import requests
from typing import Optional
from app.model.tools import PAYSNAP_TOOLS, execute_tool

OLLAMA_URL     = "http://localhost:11434/api/chat"
TEXT_MODEL     = "paysnap"
MAX_ITERATIONS = 10  # prevent infinite loops


AGENTIC_SYSTEM_PROMPT = """You are PaySnap, an AI wage theft detector trained on 365,393 real DOL enforcement cases.

You have access to tools to analyze paystubs for wage violations.

ANALYSIS RULES:
1. Always call calculate_overtime if hours_worked > 40
2. Always call check_minimum_wage to verify the hourly rate
3. Call check_deductions for EVERY deduction listed on the paystub
4. After finding violations, call get_applicable_statutes with
   violation_type = "overtime", "minimum_wage", or "illegal_deduction"
5. Always end by calling get_dol_contact so the worker knows how to report

CRITICAL FACTS — never override these in your explanation:
- Federal overtime rate is ALWAYS 1.5x (time and a half) — NOT double time
- Federal minimum wage is $7.25/hour (FLSA 29 USC 206)
- Always use the exact DOL phone number from the get_dol_contact tool result
- Texas DOL contact is the federal number: 1-866-487-9243

After all tool calls are complete, provide a clear and helpful
explanation in the worker's requested language. Include:
- Which violations were found and exact amounts owed
- The exact statute that was violated
- How to report (use DOL number from tool result)"""


def analyze_paystub_agentic(
    paystub_data: dict,
    language: str = "en"
) -> dict:
    """
    Main agentic analysis function.
    Gemma 4 decides which tools to call based on paystub.

    Args:
        paystub_data: extracted paystub fields dict
        language:     worker's language code (en, es, hi, zh, etc.)

    Returns:
        {
          "violations":      list of violation dicts,
          "total_owed":      float,
          "explanation":     str in worker's language,
          "tool_calls_made": list of {tool, arguments, result},
          "statutes":        list of statute dicts,
          "dol_contact":     dict with phone numbers,
          "iterations":      int
        }
    """

    paystub_summary  = _format_paystub_for_gemma(paystub_data)
    lang_instruction = _get_language_instruction(language)

    initial_message = f"""{paystub_summary}

{lang_instruction}

Analyze this paystub for wage violations using the available tools.
Use all necessary tools, then provide a clear explanation."""

    messages = [
        {"role": "system", "content": AGENTIC_SYSTEM_PROMPT},
        {"role": "user",   "content": initial_message}
    ]

    tool_calls_log  = []
    tool_results    = []
    final_explanation = ""
    iterations      = 0

    # ── AGENTIC LOOP ─────────────────────────────────────────
    while iterations < MAX_ITERATIONS:
        iterations += 1

        response = _call_gemma_with_tools(messages)
        if not response:
            break

        message    = response.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            # No more tool calls — get final explanation
            final_explanation = message.get("content", "").strip()

            # If Gemma 4 returned empty content request explanation explicitly
            if not final_explanation:
                print("  Explanation empty — requesting final summary...")
                messages.append({
                    "role":    "assistant",
                    "content": "",
                })
                messages.append({
                    "role": "user",
                    "content": (
                        f"Based on all the tool results above, provide a clear "
                        f"summary for the worker. Include:\n"
                        f"1. Which violations were found\n"
                        f"2. Exact dollar amounts owed\n"
                        f"3. Which statute was violated\n"
                        f"4. How to report (use DOL number from tool result)\n\n"
                        f"{lang_instruction}"
                    )
                })
                followup = _call_gemma_with_tools(messages)
                if followup:
                    final_explanation = (
                        followup.get("message", {})
                                .get("content", "")
                                .strip()
                    )
            break

        # ── EXECUTE TOOL CALLS ────────────────────────────────
        tool_results_this_round = []

        for tc in tool_calls:
            func      = tc.get("function", {})
            tool_name = func.get("name", "")
            arguments = func.get("arguments", {})

            # Ollama sometimes returns arguments as JSON string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    arguments = {}

            print(f"  Gemma 4 → {tool_name}({json.dumps(arguments)})")

            result = execute_tool(tool_name, arguments)
            print(f"    Result: {json.dumps(result)[:120]}...")

            tool_calls_log.append({
                "tool":      tool_name,
                "arguments": arguments,
                "result":    result
            })
            tool_results_this_round.append({
                "tool_name": tool_name,
                "result":    result
            })

        # Add assistant message with tool calls to conversation
        messages.append({
            "role":       "assistant",
            "content":    message.get("content", ""),
            "tool_calls": tool_calls
        })

        # Add each tool result back to conversation
        for tr in tool_results_this_round:
            messages.append({
                "role":    "tool",
                "content": json.dumps(tr["result"], ensure_ascii=False)
            })

        tool_results.extend(tool_results_this_round)

    # ── COMPILE RESULTS ──────────────────────────────────────
    violations  = _extract_violations(tool_calls_log)
    total_owed  = _calculate_total_owed(tool_calls_log)
    statutes    = _extract_statutes(tool_calls_log)
    dol_contact = _extract_dol_contact(tool_calls_log)

    return {
        "violations":       violations,
        "total_owed":       total_owed,
        "explanation":      final_explanation,
        "tool_calls_made":  tool_calls_log,
        "statutes":         statutes,
        "dol_contact":      dol_contact,
        "iterations":       iterations,
        "agentic":          True,
    }


# ── GEMMA 4 API CALL ─────────────────────────────────────────

def _call_gemma_with_tools(messages: list) -> Optional[dict]:
    """Call Gemma 4 via Ollama with native tool/function calling support."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model":    TEXT_MODEL,
                "messages": messages,
                "tools":    PAYSNAP_TOOLS,
                "stream":   False,
                "options":  {
                    "temperature": 0.1,
                    "num_predict": 2000,
                }
            },
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Gemma tool call error: {e}")
        return None


# ── FORMATTERS ───────────────────────────────────────────────

def _format_paystub_for_gemma(data: dict) -> str:
    """Format paystub data clearly so Gemma 4 can decide what to check."""
    lines = ["PAYSTUB DATA:"]

    if data.get("employer_name"):
        lines.append(f"Employer: {data['employer_name']}")

    state = data.get("state", "TX")
    lines.append(f"State: {state}")

    hours = (
        data.get("hours_worked")
        or (
            float(data.get("regular_hours") or 0)
          + float(data.get("overtime_hours") or 0)
        )
    )
    if hours:
        lines.append(f"Total hours worked: {hours}")

    ot_paid = data.get("overtime_hours", 0)
    if ot_paid:
        lines.append(f"Overtime hours shown on paystub: {ot_paid}")
    else:
        lines.append("Overtime hours shown on paystub: 0")

    rate = data.get("hourly_rate")
    if rate:
        lines.append(f"Hourly rate: ${rate}/hr")

    gross = data.get("gross_pay")
    if gross:
        lines.append(f"Gross pay shown: ${gross}")

    deductions = data.get("deductions", [])
    if deductions:
        lines.append("Deductions on paystub:")
        for d in deductions:
            if isinstance(d, dict):
                lines.append(
                    f"  - {d.get('name', 'Unknown')}: "
                    f"${d.get('amount', 0)}"
                )
    else:
        lines.append("Deductions: none")

    return "\n".join(lines)


def _get_language_instruction(language: str) -> str:
    """Return language instruction for Gemma 4's final explanation."""
    instructions = {
        "en": "Provide your final explanation in English.",
        "es": "Provide your final explanation in Spanish (Español).",
        "hi": "Provide your final explanation in Hindi (हिंदी में जवाब दें).",
        "zh": "Provide your final explanation in Chinese (用中文回答).",
        "vi": "Provide your final explanation in Vietnamese (Tiếng Việt).",
        "ko": "Provide your final explanation in Korean (한국어로 답변).",
        "pt": "Provide your final explanation in Portuguese (Português).",
        "ar": "Provide your final explanation in Arabic (الإجابة بالعربية).",
        "ru": "Provide your final explanation in Russian (Отвечайте по-русски).",
        "tl": "Provide your final explanation in Tagalog (Sagutin sa Tagalog).",
        "ht": "Provide your final explanation in Haitian Creole (Reponn an Kreyòl).",
    }
    return instructions.get(language, instructions["en"])


# ── RESULT EXTRACTORS ─────────────────────────────────────────

def _extract_violations(tool_calls_log: list) -> list:
    """Extract violation summaries from tool call results."""
    violations = []
    for tc in tool_calls_log:
        result    = tc.get("result", {})
        tool_name = tc.get("tool", "")

        if not result.get("has_violation"):
            continue

        if tool_name == "calculate_overtime":
            violations.append({
                "type":        "Overtime Violation",
                "amount_owed": result.get("ot_premium_owed", 0),
                "statute":     result.get("statute", "FLSA 29 USC 207(a)(1)"),
                "detail":      result.get("calculation", ""),
            })

        elif tool_name == "check_minimum_wage":
            violations.append({
                "type":        "Minimum Wage Violation",
                "amount_owed": result.get("amount_owed", 0),
                "statute":     result.get("statute", "FLSA 29 USC 206"),
                "detail":      result.get("calculation", ""),
            })

        elif tool_name == "check_deductions":
            violations.append({
                "type":        f"Illegal Deduction — {result.get('deduction_name', '')}",
                "amount_owed": result.get("amount_must_be_returned", 0),
                "statute":     result.get("statute", ""),
                "detail":      result.get("reason", ""),
            })

    return violations


def _calculate_total_owed(tool_calls_log: list) -> float:
    """Sum all amounts owed across all tool call results."""
    total = 0.0
    for tc in tool_calls_log:
        result = tc.get("result", {})
        if not result.get("has_violation"):
            continue
        total += float(result.get("ot_premium_owed", 0) or 0)
        total += float(result.get("amount_owed", 0) or 0)
        total += float(result.get("amount_must_be_returned", 0) or 0)
    return round(total, 2)


def _extract_statutes(tool_calls_log: list) -> list:
    """Extract statute citations from tool call results."""
    statutes = []
    seen     = set()

    for tc in tool_calls_log:
        result    = tc.get("result", {})
        tool_name = tc.get("tool", "")

        if tool_name == "get_applicable_statutes":
            statutes.append({
                "federal":  result.get("federal_statute"),
                "state":    result.get("state_statute"),
                "sol":      result.get("statute_of_limitations"),
                "damages":  result.get("liquidated_damages"),
            })

        elif result.get("has_violation") and result.get("statute"):
            citation = result["statute"]
            if citation not in seen and citation != "No violation":
                seen.add(citation)
                statutes.append({"citation": citation})

    return statutes


def _extract_dol_contact(tool_calls_log: list) -> dict:
    """Extract DOL contact info from get_dol_contact tool result."""
    for tc in tool_calls_log:
        if tc.get("tool") == "get_dol_contact":
            return tc.get("result", {})

    # Default if Gemma 4 didn't call get_dol_contact
    return {
        "federal_hotline":     "1-866-487-9243",
        "federal_description": "DOL Wage and Hour Division — free, confidential",
        "note":                "FLSA protects ALL workers regardless of immigration status.",
        "online":              "https://www.dol.gov/agencies/whd/contact/complaints",
    }