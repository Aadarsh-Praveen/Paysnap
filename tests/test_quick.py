import sys
sys.path.insert(0, '.')

from app.analysis.deduction_checker import DeductionChecker
from app.core.input_handler import DeductionItem

checker = DeductionChecker()

print("TEST 1: CA tools — high earner still illegal")
d = DeductionItem(name="TOOLS", amount=100.0)
r = checker.check_single(d, 50.00, 40, 2000.00, "CA")
print(f"  Is legal: {r.is_legal}")
print(f"  Severity: {r.severity}")
print(f"  Reason: {r.reason_es}")
print()

print("TEST 2: TX tools — needs written consent")
r2 = checker.check_single(d, 50.00, 40, 2000.00, "TX")
print(f"  Is legal: {r2.is_legal}")
print(f"  Requires consent: {r2.requires_written_consent}")
print(f"  Severity: {r2.severity}")
print()

print("TEST 3: Low earner drops below minimum wage")
d2 = DeductionItem(name="SUPPLIES", amount=75.0)
r3 = checker.check_single(d2, 7.50, 40, 300.00, "TX")
print(f"  Is legal: {r3.is_legal}")
print(f"  Drops below min wage: {r3.drops_below_minimum_wage}")
print(f"  Reason: {r3.reason_es}")
print()

print("TEST 4: TX health insurance — legal")
d3 = DeductionItem(name="HEALTH INSURANCE", amount=120.0)
r4 = checker.check_single(d3, 32.00, 40, 1280.00, "TX")
print(f"  Is legal: {r4.is_legal}")
print(f"  Severity: {r4.severity}")
print()

print("TEST 5: NY uniform — illegal regardless of wage")
d5 = DeductionItem(name="UNIFORM", amount=50.0)
r5 = checker.check_single(d5, 25.00, 40, 1000.00, "NY")
print(f"  Is legal: {r5.is_legal}")
print(f"  Severity: {r5.severity}")
print()

print("ALL TESTS COMPLETE")