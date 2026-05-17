"""
app/model/agentic_analyzer.py

Agentic wage theft analyzer using Gemma 4 native function calling.
Gemma 4 decides which tools to call based on what it sees in the paystub.

Flow:
  1. Send paystub data + tools to Gemma 4
  2. Gemma 4 calls calculate_overtime if needed
  3. Gemma 4 calls check_minimum_wage if needed
  4. Gemma 4 calls check_deductions for each deduction
  5. Gemma 4 calls get_applicable_statutes for each violation
  6. Gemma 4 calls get_dol_contact for next steps
  7. Gemma 4 generates final explanation in worker's language
"""

import json
import requests
from typing import Optional
from app.model.tools import PAYSNAP_TOOLS, execute_tool

OLLAMA_URL = "http://localhost:11434/api/chat"
TEXT_MODEL = "paysnap"
MAX_ITERATIONS = 10  # prevent infinite loops


AGENTIC_SYSTEM_PROMPT = """You are PaySnap, an AI wage theft detector trained on 365,393 real DOL enforcement cases.

You have access to tools to analyze paystubs for wage violations.

ANALYSIS RULES:
1. Always call calculate_overtime if hours_worked > 40
2. Always call check_minimum_wage to verify the hourly rate
3. Call check_deductions for EVERY deduction on the paystub
4. After finding violations, call get_applicable_statutes for exact legal citations
5. Always end with get_dol_contact so the worker knows how to report

IMPORTANT:
- Use the worker's STATED hourly rate — never substitute minimum wage
- Be precise with calculations
- Always cite exact statutes
- Always provide the DOL hotline

After all tool calls are complete, provide a clear explanation in the worker's language."""


def analyze_paystub_agentic(
    paystub_data: dict,
    language: str = "en"
) -> dict:
    """
    Main agentic analysis function.
    Gemma 4 decides which tools to call based on paystub.

    Args:
        paystub_data: extracted paystub fields
        language: worker's language code

    Returns:
        {
          "violations": [...],
          "total_owed": float,
          "explanation": str,
          "tool_calls_made": [...],
          "statutes": [...],
          "dol_contact": {...}
        }
    """

    # Build initial message with paystub context
    paystub_summary = _format_paystub_for_gemma(paystub_data)
    language_instruction = _get_language_instruction(language)

    initial_message = f"""{paystub_summary}

{language_instruction}

Analyze this paystub for wage violations. Use the available tools to:
1. Check for overtime violations
2. Verify minimum wage compliance
3. Check any deductions for legality
4. Get exact statute citations for any violations found
5. Provide DOL contact information

After using all necessary tools, provide a clear explanation of findings."""

    messages = [
        {"role": "system", "content": AGENTIC_SYSTEM_PROMPT},
        {"role": "user",   "content": initial_message}
    ]

    tool_calls_log = []
    tool_results   = []
    iterations     = 0

    # ── AGENTIC LOOP ─────────────────────────────────────────
    while iterations < MAX_ITERATIONS:
        iterations += 1

        response = _call_gemma_with_tools(messages)
        if not response:
            break

        message = response.get("message", {})

        # Check if Gemma 4 wants to call tools
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            # No more tool calls — Gemma 4 is done
            final_explanation = message.get("content", "")
            break

        # Execute each tool Gemma 4 requested
        tool_results_this_round = []
        for tc in tool_calls:
            func      = tc.get("function", {})
            tool_name = func.get("name", "")
            arguments = func.get("arguments", {})

            # Handle string arguments (Ollama sometimes returns JSON string)
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    arguments = {}

            print(f"  Gemma 4 calling: {tool_name}({arguments})")

            # Execute the tool
            result = execute_tool(tool_name, arguments)

            tool_calls_log.append({
                "tool":      tool_name,
                "arguments": arguments,
                "result":    result
            })

            tool_results_this_round.append({
                "tool_name": tool_name,
                "result":    result
            })

        # Add assistant message with tool calls
        messages.append({
            "role":       "assistant",
            "content":    message.get("content", ""),
            "tool_calls": tool_calls
        })

        # Add tool results back to conversation
        for tr in tool_results_this_round:
            messages.append({
                "role":    "tool",
                "content": json.dumps(tr["result"], ensure_ascii=False)
            })

        tool_results.extend(tool_results_this_round)

    else:
        final_explanation = "Analysis complete. Please contact DOL: 1-866-487-9243"

    # ── COMPILE RESULTS ──────────────────────────────────────
    violations  = _extract_violations(tool_results)
    total_owed  = _calculate_total_owed(tool_results)
    statutes    = _extract_statutes(tool_results)
    dol_contact = _extract_dol_contact(tool_results)

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


def _call_gemma_with_tools(messages: list) -> Optional[dict]:
    """Call Gemma 4 via Ollama with tool support."""
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


def _format_paystub_for_gemma(data: dict) -> str:
    """Format paystub data clearly for Gemma 4."""
    lines = ["PAYSTUB DATA:"]

    if data.get("employer_name"):
        lines.append(f"Employer: {data['employer_name']}")
    if data.get("state"):
        lines.append(f"State: {data['state']}")
    if data.get("hours_worked") or data.get("regular_hours"):
        hours = data.get("hours_worked") or data.get("regular_hours", 0)
        lines.append(f"Hours worked: {hours}")
    if data.get("overtime_hours"):
        lines.append(f"Overtime hours shown on paystub: {data['overtime_hours']}")
    if data.get("hourly_rate"):
        lines.append(f"Hourly rate: ${data['hourly_rate']}/hr")
    if data.get("gross_pay"):
        lines.append(f"Gross pay: ${data['gross_pay']}")
    if data.get("deductions"):
        lines.append("Deductions:")
        for d in data["deductions"]:
            if isinstance(d, dict):
                lines.append(f"  - {d.get('name', 'Unknown')}: ${d.get('amount', 0)}")
            else:
                lines.append(f"  - {d}")

    return "\n".join(lines)


def _get_language_instruction(language: str) -> str:
    instructions = {
        "en": "Provide your final explanation in English.",
        "es": "Provide your final explanation in Spanish (Español).",
        "hi": "Provide your final explanation in Hindi (हिंदी).",
        "zh": "Provide your final explanation in Chinese (中文).",
        "vi": "Provide your final explanation in Vietnamese (Tiếng Việt).",
        "ko": "Provide your final explanation in Korean (한국어).",
        "pt": "Provide your final explanation in Portuguese (Português).",
        "ar": "Provide your final explanation in Arabic (العربية).",
        "ru": "Provide your final explanation in Russian (Русский).",
        "tl": "Provide your final explanation in Tagalog (Filipino).",
        "ht": "Provide your final explanation in Haitian Creole (Kreyòl ayisyen).",
    }
    return instructions.get(language, instructions["en"])


def _extract_violations(tool_results: list) -> list:
    violations = []
    for tr in tool_results:
        result = tr.get("result", {})
        tool   = tr.get("tool_name", "")

        if result.get("has_violation"):
            if tool == "calculate_overtime":
                violations.append({
                    "type":        "Overtime Violation",
                    "amount_owed": result.get("ot_premium_owed", 0),
                    "statute":     result.get("statute", "FLSA 29 USC 207(a)(1)"),
                    "detail":      result.get("calculation", ""),
                })
            elif tool == "check_minimum_wage":
                violations.append({
                    "type":        "Minimum Wage Violation",
                    "amount_owed": result.get("amount_owed", 0),
                    "statute":     result.get("statute", "FLSA 29 USC 206"),
                    "detail":      result.get("calculation", ""),
                })
            elif tool == "check_deductions":
                violations.append({
                    "type":        f"Illegal Deduction — {result.get('deduction_name', '')}",
                    "amount_owed": result.get("amount_must_be_returned", 0),
                    "statute":     result.get("statute", ""),
                    "detail":      result.get("reason", ""),
                })
    return violations


def _calculate_total_owed(tool_results: list) -> float:
    total = 0.0
    for tr in tool_results:
        result = tr.get("result", {})
        if result.get("has_violation"):
            total += result.get("ot_premium_owed", 0)
            total += result.get("amount_owed", 0)
            total += result.get("amount_must_be_returned", 0)
    return round(total, 2)


def _extract_statutes(tool_results: list) -> list:
    statutes = []
    for tr in tool_results:
        result = tr.get("result", {})
        tool   = tr.get("tool_name", "")

        if tool == "get_applicable_statutes":
            statutes.append({
                "federal": result.get("federal_statute"),
                "state":   result.get("state_statute"),
                "sol":     result.get("statute_of_limitations"),
                "damages": result.get("liquidated_damages"),
            })
        elif result.get("statute") and result.get("has_violation"):
            statutes.append({"citation": result["statute"]})

    return statutes


def _extract_dol_contact(tool_results: list) -> dict:
    for tr in tool_results:
        if tr.get("tool_name") == "get_dol_contact":
            return tr.get("result", {})
    # Default if Gemma 4 didn't call get_dol_contact
    return {
        "federal_hotline":    "1-866-487-9243",
        "federal_description": "DOL Wage and Hour Division — free, confidential",
        "note": "FLSA protects ALL workers regardless of immigration status."
    }