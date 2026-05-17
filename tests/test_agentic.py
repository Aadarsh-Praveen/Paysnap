"""
test_agentic.py
Test Gemma 4 native function calling for wage theft detection.

Run: python3 test_agentic.py
     (with Ollama running and paysnap model loaded)
"""

import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "paysnap"

# Import our tools
import sys
sys.path.insert(0, ".")
from app.model.tools import PAYSNAP_TOOLS, execute_tool


def test_agentic_analysis(test_case: dict):
    """Run a full agentic analysis and show tool calls."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*60}")

    paystub = test_case["paystub"]
    language = test_case.get("language", "en")

    # Format paystub for Gemma 4
    paystub_text = f"""PAYSTUB DATA:
Employer: {paystub.get('employer', 'Unknown')}
State: {paystub.get('state', 'TX')}
Hours worked: {paystub.get('hours_worked', 40)}
Overtime hours shown: {paystub.get('overtime_hours_paid', 0)}
Hourly rate: ${paystub.get('hourly_rate', 15)}/hr
Deductions: {json.dumps(paystub.get('deductions', []))}

Analyze this paystub for wage violations using the available tools.
Provide final explanation in {'English' if language == 'en' else language}."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are PaySnap, an AI wage theft detector. "
                "Use the available tools to analyze paystubs for violations. "
                "Always call calculate_overtime if hours > 40. "
                "Always call check_deductions for any deductions. "
                "Always end with get_dol_contact."
            )
        },
        {"role": "user", "content": paystub_text}
    ]

    tool_calls_made = []
    iterations = 0

    while iterations < 10:
        iterations += 1
        print(f"\n[Iteration {iterations}] Calling Gemma 4...")

        resp = requests.post(
            OLLAMA_URL,
            json={
                "model":    MODEL,
                "messages": messages,
                "tools":    PAYSNAP_TOOLS,
                "stream":   False,
                "options":  {"temperature": 0.1, "num_predict": 1000}
            },
            timeout=120
        )
        resp.raise_for_status()
        data    = resp.json()
        message = data.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            print(f"\n✅ Gemma 4 final response:")
            print(message.get("content", "")[:500])
            break

        # Execute tools
        print(f"  Gemma 4 requested {len(tool_calls)} tool call(s):")
        tool_results = []

        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args = func.get("arguments", {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except: args = {}

            print(f"  → {name}({json.dumps(args)})")
            result = execute_tool(name, args)
            print(f"    Result: {json.dumps(result)[:150]}...")

            tool_calls_made.append({"tool": name, "args": args, "result": result})
            tool_results.append(result)

        # Add to conversation
        messages.append({
            "role": "assistant",
            "content": message.get("content", ""),
            "tool_calls": tool_calls
        })
        for result in tool_results:
            messages.append({
                "role": "tool",
                "content": json.dumps(result)
            })

    print(f"\n📊 Summary:")
    print(f"  Tool calls made: {len(tool_calls_made)}")
    print(f"  Tools used: {[tc['tool'] for tc in tool_calls_made]}")

    violations = [tc for tc in tool_calls_made if tc["result"].get("has_violation")]
    total_owed = sum(
        tc["result"].get("ot_premium_owed", 0) +
        tc["result"].get("amount_owed", 0) +
        tc["result"].get("amount_must_be_returned", 0)
        for tc in violations
    )
    print(f"  Violations found: {len(violations)}")
    print(f"  Total owed: ${total_owed:.2f}")
    return tool_calls_made


# ── TEST CASES ────────────────────────────────────────────────
TEST_CASES = [
    {
        "name": "Texas overtime + tool deduction",
        "paystub": {
            "employer": "ABC Construction",
            "state": "TX",
            "hours_worked": 52,
            "overtime_hours_paid": 0,
            "hourly_rate": 15.00,
            "deductions": [{"name": "TOOLS", "amount": 75}]
        },
        "language": "en"
    },
    {
        "name": "New York deductions",
        "paystub": {
            "employer": "NYC Restaurant",
            "state": "NY",
            "hours_worked": 48,
            "overtime_hours_paid": 0,
            "hourly_rate": 16.00,
            "deductions": [
                {"name": "UNIFORM", "amount": 35},
                {"name": "BREAKAGE", "amount": 50}
            ]
        },
        "language": "en"
    },
    {
        "name": "California worker — Hindi",
        "paystub": {
            "employer": "LA Hotel",
            "state": "CA",
            "hours_worked": 50,
            "overtime_hours_paid": 0,
            "hourly_rate": 18.00,
            "deductions": []
        },
        "language": "hi"
    },
]


if __name__ == "__main__":
    print("PaySnap Agentic Function Calling Test")
    print("Testing Gemma 4 native tool use...")
    print()

    for i, test in enumerate(TEST_CASES):
        try:
            result = test_agentic_analysis(test)
            print(f"\n✅ Test {i+1} passed — {len(result)} tool calls made")
        except Exception as e:
            print(f"\n❌ Test {i+1} failed: {e}")

    print("\n" + "="*60)
    print("All tests complete!")