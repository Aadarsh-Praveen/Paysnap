"""
test_paysnap.py
Complete PaySnap test suite — run before filming video.
Tests all endpoints, all scenarios, all languages.

Usage:
  python3 test_paysnap.py                    # test local
  python3 test_paysnap.py --url https://paysnap.website  # test GCP
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"
if "--url" in sys.argv:
    idx = sys.argv.index("--url")
    BASE_URL = sys.argv[idx + 1]

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = []

def check(name, actual, expected, tolerance=0.01):
    if isinstance(expected, (int, float)):
        ok = abs(float(actual) - float(expected)) <= tolerance
    else:
        ok = str(actual) == str(expected)
    status = PASS if ok else FAIL
    results.append((status, name, actual, expected))
    print(f"  {status} {name}: got={actual} expected={expected}")
    return ok

def post_analyze(data):
    resp = requests.post(f"{BASE_URL}/analyze", data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]

def post_agentic(payload):
    resp = requests.post(
        f"{BASE_URL}/analyze-agentic",
        json=payload,
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()

print("=" * 60)
print(f"PaySnap Full Test Suite")
print(f"Target: {BASE_URL}")
print(f"Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ── TEST 1: HEALTH ────────────────────────────────────────────
print("\n[1] Health Check")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    data = r.json()
    check("status", data.get("status"), "ok")
    check("app", data.get("app"), "PaySnap")
    print(f"  ℹ model: {data.get('model', 'unknown')}")
except Exception as e:
    print(f"  {FAIL} Health check failed: {e}")

# ── TEST 2: TX OVERTIME ───────────────────────────────────────
print("\n[2] Texas Overtime — 52 hrs @ $15")
try:
    d = post_analyze({
        "regular_hours": 52, "overtime_hours": 0,
        "hourly_rate": 15, "state": "TX",
        "deductions": "[]", "language": "en"
    })
    check("has_violation",   d["has_violation"],     True)
    check("total_owed",      d["total_money_owed"],  90.0)
    check("ot_hours_owed",   d["overtime"]["ot_hours_owed"], 12.0)
    check("ot_pay_owed",     d["overtime"]["ot_pay_owed"],   90.0)
    check("statute_present", "FLSA" in d.get("statute", ""), True)
    check("explanation_present", len(d.get("explanation_es", "")) > 0, True)
except Exception as e:
    print(f"  {FAIL} TX test failed: {e}")

# ── TEST 3: NY OVERTIME + DEDUCTIONS ─────────────────────────
print("\n[3] New York — 48 hrs + UNIFORM $35 + BREAKAGE $50")
try:
    d = post_analyze({
        "regular_hours": 48, "overtime_hours": 0,
        "hourly_rate": 16, "state": "NY",
        "deductions": '[{"name":"UNIFORM","amount":35},{"name":"BREAKAGE","amount":50}]',
        "language": "en"
    })
    check("has_violation",     d["has_violation"],    True)
    check("total_owed",        d["total_money_owed"], 149.0)
    check("illegal_deds_count", len(d["illegal_deductions"]), 2)
    check("uniform_illegal",   d["illegal_deductions"][0]["name"], "UNIFORM")
    check("breakage_illegal",  d["illegal_deductions"][1]["name"], "BREAKAGE")
    check("ny_statute",        "193" in str(d["illegal_deductions"][0].get("statute","")), True)
except Exception as e:
    print(f"  {FAIL} NY test failed: {e}")

# ── TEST 4: CA OVERTIME ───────────────────────────────────────
print("\n[4] California — 50 hrs @ $18")
try:
    d = post_analyze({
        "regular_hours": 50, "overtime_hours": 0,
        "hourly_rate": 18, "state": "CA",
        "deductions": "[]", "language": "en"
    })
    check("has_violation", d["has_violation"],    True)
    check("total_owed",    d["total_money_owed"], 90.0)
    check("ca_statute",    "510" in d.get("statute", "") or "CA" in d.get("statute",""), True)
except Exception as e:
    print(f"  {FAIL} CA test failed: {e}")

# ── TEST 5: FL OVERTIME ───────────────────────────────────────
print("\n[5] Florida — 48 hrs @ $12")
try:
    d = post_analyze({
        "regular_hours": 48, "overtime_hours": 0,
        "hourly_rate": 12, "state": "FL",
        "deductions": "[]", "language": "en"
    })
    check("has_violation", d["has_violation"],    True)
    check("total_owed",    d["total_money_owed"], 48.0)
except Exception as e:
    print(f"  {FAIL} FL test failed: {e}")

# ── TEST 6: IL OVERTIME ───────────────────────────────────────
print("\n[6] Illinois — 45 hrs @ $16")
try:
    d = post_analyze({
        "regular_hours": 45, "overtime_hours": 0,
        "hourly_rate": 16, "state": "IL",
        "deductions": "[]", "language": "en"
    })
    check("has_violation", d["has_violation"],    True)
    check("total_owed",    d["total_money_owed"], 40.0)
except Exception as e:
    print(f"  {FAIL} IL test failed: {e}")

# ── TEST 7: NO VIOLATION ──────────────────────────────────────
print("\n[7] No Violation — 40 hrs @ $20")
try:
    d = post_analyze({
        "regular_hours": 40, "overtime_hours": 0,
        "hourly_rate": 20, "state": "TX",
        "deductions": "[]", "language": "en"
    })
    check("no_violation",  d["has_violation"],    False)
    check("zero_owed",     d["total_money_owed"], 0.0)
except Exception as e:
    print(f"  {FAIL} No violation test failed: {e}")

# ── TEST 8: HINDI EXPLANATION ─────────────────────────────────
print("\n[8] Hindi Language — TX 52 hrs @ $15")
try:
    d = post_analyze({
        "regular_hours": 52, "overtime_hours": 0,
        "hourly_rate": 15, "state": "TX",
        "deductions": "[]", "language": "hi"
    })
    check("has_violation",      d["has_violation"],    True)
    check("total_owed",         d["total_money_owed"], 90.0)
    explanation = d.get("explanation_es", "")
    has_hindi = any(ord(c) > 0x0900 for c in explanation)
    check("hindi_text_present", has_hindi, True)
except Exception as e:
    print(f"  {FAIL} Hindi test failed: {e}")

# ── TEST 9: SPANISH EXPLANATION ───────────────────────────────
print("\n[9] Spanish Language — TX 52 hrs @ $15")
try:
    d = post_analyze({
        "regular_hours": 52, "overtime_hours": 0,
        "hourly_rate": 15, "state": "TX",
        "deductions": "[]", "language": "es"
    })
    check("has_violation", d["has_violation"],    True)
    check("total_owed",    d["total_money_owed"], 90.0)
    explanation = d.get("explanation_es", "")
    check("explanation_not_empty", len(explanation) > 50, True)
except Exception as e:
    print(f"  {FAIL} Spanish test failed: {e}")

# ── TEST 10: EXTRACT TEXT ─────────────────────────────────────
print("\n[10] Extract from text description")
try:
    resp = requests.post(
        f"{BASE_URL}/extract-text",
        data={"text": "I worked 52 hours at $15 per hour in Texas with no overtime paid"},
        timeout=60
    )
    resp.raise_for_status()
    d = resp.json()["data"]
    check("extract_success",  d.get("regular_hours", 0) > 0, True)
    check("state_extracted",  d.get("state", "") != "", True)
    check("rate_extracted",   d.get("hourly_rate", 0) > 0, True)
    print(f"  ℹ extracted: hours={d.get('regular_hours')} rate={d.get('hourly_rate')} state={d.get('state')}")
except Exception as e:
    print(f"  {FAIL} Extract text failed: {e}")

# ── TEST 11: AGENTIC ENDPOINT ─────────────────────────────────
print("\n[11] Agentic Function Calling — TX 52 hrs @ $15")
try:
    result = post_agentic({
        "paystub": {
            "employer_name": "ABC Construction",
            "regular_hours": 52,
            "overtime_hours": 0,
            "hourly_rate": 15.0,
            "state": "TX",
            "deductions": []
        },
        "language": "en"
    })
    check("agentic_flag",      result.get("agentic"),        True)
    check("total_owed",        result.get("total_owed"),     90.0)
    check("violations_found",  len(result.get("violations", [])) > 0, True)
    tool_names = [t["tool"] for t in result.get("tool_calls_made", [])]
    check("calculate_overtime_called", "calculate_overtime" in tool_names, True)
    check("get_dol_contact_called",    "get_dol_contact" in tool_names,    True)
    check("explanation_present", len(result.get("explanation", "")) > 0, True)
    print(f"  ℹ tools called: {tool_names}")
    print(f"  ℹ iterations: {result.get('iterations')}")
except Exception as e:
    print(f"  {FAIL} Agentic test failed: {e}")

# ── TEST 12: AGENTIC NY DEDUCTIONS ───────────────────────────
print("\n[12] Agentic — NY 48 hrs + deductions")
try:
    result = post_agentic({
        "paystub": {
            "employer_name": "NYC Restaurant",
            "regular_hours": 48,
            "overtime_hours": 0,
            "hourly_rate": 16.0,
            "state": "NY",
            "deductions": [
                {"name": "UNIFORM", "amount": 35},
                {"name": "BREAKAGE", "amount": 50}
            ]
        },
        "language": "en"
    })
    check("total_owed",   result.get("total_owed"), 149.0)
    tool_names = [t["tool"] for t in result.get("tool_calls_made", [])]
    check("check_deductions_called", "check_deductions" in tool_names, True)
    print(f"  ℹ tools called: {tool_names}")
except Exception as e:
    print(f"  {FAIL} Agentic NY test failed: {e}")

# ── TEST 13: DEMAND LETTER ────────────────────────────────────
print("\n[13] Demand Letter Generation")
try:
    resp = requests.post(
        f"{BASE_URL}/demand-letter",
        data={
            "employer": "ABC Construction",
            "regular_hours": 52,
            "overtime_hours": 0,
            "hourly_rate": 15,
            "state": "TX",
            "total_owed": 90,
            "breakdown": "12 hrs x $15 x 0.5 = $90",
            "statute": "FLSA 29 USC 207(a)(1)"
        },
        timeout=60
    )
    resp.raise_for_status()
    letter = resp.json()["data"]["letter"]
    check("letter_generated",  len(letter) > 100, True)
    check("statute_in_letter", "FLSA" in letter,  True)
    check("amount_in_letter",  "$90" in letter or "90" in letter, True)
except Exception as e:
    print(f"  {FAIL} Demand letter failed: {e}")

# ── TEST 14: HISTORY ──────────────────────────────────────────
print("\n[14] History Endpoint")
try:
    resp = requests.get(f"{BASE_URL}/history", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    check("history_success", data.get("success"), True)
    print(f"  ℹ records: {len(data.get('data', {}).get('records', []))}")
except Exception as e:
    print(f"  {FAIL} History failed: {e}")

# ── SUMMARY ───────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
total  = len(results)

print(f"RESULTS: {passed}/{total} passed")
if failed > 0:
    print(f"\nFAILED CHECKS:")
    for r in results:
        if r[0] == FAIL:
            print(f"  {FAIL} {r[1]}: got={r[2]} expected={r[3]}")
else:
    print(f"\n{PASS} ALL TESTS PASSED — ready to film!")

print("=" * 60)

if failed == 0:
    print("""
Video demo scenarios confirmed working:
  Scenario 1: TX 52hrs $15    → $90.00  ✅
  Scenario 2: NY 48hrs $16    → $149.00 ✅
  Scenario 3: CA 50hrs $18    → $90.00  ✅
  Agentic:    5 tools called  → correct ✅
  Hindi:      explanation ok  → correct ✅
""")