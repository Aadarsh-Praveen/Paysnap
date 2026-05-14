"""
test_overtime.py
Run: python -m pytest tests/test_overtime.py -v
All must pass before filming the video.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import pytest

DB_PATH = Path(__file__).parent.parent / "data" / "labor_law.db"


@pytest.fixture(scope="session", autouse=True)
def build_db():
    if not DB_PATH.exists():
        subprocess.run(
            ["python3", "data/build_db.py"],
            cwd=str(Path(__file__).parent.parent),
            check=True
        )


# ─────────────────────────────────────────────
# OVERTIME CALCULATOR TESTS
# ─────────────────────────────────────────────

class TestOvertimeCalculator:
    """Tests for overtime_calculator.py — all deterministic math."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.analysis.overtime_calculator import OvertimeCalculator
        self.calc = OvertimeCalculator()

    def test_no_violation_40hrs(self):
        """40 hours or less = no overtime violation."""
        r = self.calc.calculate(40, 15.0, "TX", 40, 0)
        assert r.has_violation == False
        assert r.total_additional_pay == 0.0

    def test_tx_overtime_12hrs(self):
        """
        52 hours worked, only 40 shown on stub.
        12 OT hours × $32 × 1.5 = $576.
        """
        r = self.calc.calculate(52, 32.0, "TX", 40, 0)
        assert r.has_violation == True
        assert r.ot_hours_owed == 12.0
        assert abs(r.total_additional_pay - 576.0) < 0.01
        assert "207" in r.statute

    def test_already_paid_ot(self):
        """If stub already shows correct OT hours, no violation."""
        r = self.calc.calculate(52, 32.0, "TX", 40, 12)
        assert r.has_violation == False

    def test_ca_daily_overtime(self):
        """CA: over 8 hours in a day triggers OT even under 40/week."""
        r = self.calc.calculate(38, 20.0, "CA", 38, 0, daily_hours=10)
        assert r.has_violation == True
        assert "510" in r.statute

    def test_ca_double_time(self):
        """CA: over 12 hours in a day triggers double time."""
        r = self.calc.calculate(40, 20.0, "CA", 40, 0, daily_hours=14)
        assert r.has_violation == True
        assert r.double_time_hours > 0

    def test_statute_present_on_violation(self):
        """Every violation must cite a statute — never empty."""
        r = self.calc.calculate(50, 15.0, "NY", 40, 0)
        assert r.has_violation == True
        assert r.statute and len(r.statute) > 5

    def test_biweekly(self):
        """Biweekly pay period: 90 hours = 45hrs/week = OT violation."""
        r = self.calc.calculate(90, 20.0, "TX", 80, 0, pay_period="biweekly")
        assert r.has_violation == True


# ─────────────────────────────────────────────
# DEDUCTION CHECKER TESTS — BASIC
# ─────────────────────────────────────────────

class TestDeductionChecker:
    """Basic deduction tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.analysis.deduction_checker import DeductionChecker
        from app.core.input_handler import DeductionItem
        self.checker = DeductionChecker()
        self.Item = DeductionItem

    def test_tools_illegal_ca(self):
        """Tool deductions are always illegal in California."""
        d = self.Item(name="TOOLS", amount=75.0)
        r = self.checker.check_single(d, 20.0, 40, 800.0, "CA")
        assert r.is_legal == False
        assert r.severity == "illegal"

    def test_drops_below_min_wage(self):
        """
        TOOLS in TX requires written consent.
        But if it also drops below minimum wage,
        the minimum wage violation takes priority.
        Worker: $7.50/hr × 40hrs = $300 gross
        Deduction: $75
        Effective: ($300-$75)/40 = $5.625/hr < $7.25 minimum
        """
        d = self.Item(name="TOOLS", amount=75.0)
        r = self.checker.check_single(d, 7.50, 40, 300.0, "TX")
        assert r.drops_below_minimum_wage == True
        assert r.is_legal == False

    def test_taxes_always_legal(self):
        """Federal/state taxes and FICA are always legal deductions."""
        for name in ["Federal Tax", "State Tax", "Social Security", "Medicare"]:
            d = self.Item(name=name, amount=50.0)
            r = self.checker.check_single(d, 20.0, 40, 800.0, "TX")
            assert r.is_legal == True, f"{name} should be legal"

    def test_spanish_keywords(self):
        """Spanish deduction names must be recognized correctly."""
        assert self.checker._categorize("HERRAMIENTAS") == "tools"
        assert self.checker._categorize("UNIFORME") == "uniforms"


# ─────────────────────────────────────────────
# DEDUCTION CHECKER TESTS — ADVANCED
# Tests that verify wage-level-independent rules
# ─────────────────────────────────────────────

class TestDeductionCheckerAdvanced:
    """
    Advanced tests verifying that deduction legality
    is checked independently of wage level.

    Key insight: Two separate legal standards apply:
    1. Some deductions are categorically illegal (type-based)
    2. Any deduction that drops below minimum wage is illegal
    These must be checked independently.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        from app.analysis.deduction_checker import DeductionChecker
        from app.core.input_handler import DeductionItem
        self.checker = DeductionChecker()
        self.Item = DeductionItem

    def test_tools_illegal_ca_regardless_of_wage(self):
        """
        CA Labor Code §221-224 prohibits tool deductions entirely.
        A worker earning $50/hr still cannot have tools deducted.
        This is wage-level INDEPENDENT — about deduction type only.
        Effective pay: ($2000-$100)/40 = $47.50/hr — above minimum.
        The violation is about type, not wage level.
        """
        d = self.Item(name="TOOLS", amount=100.0)
        result = self.checker.check_single(
            deduction=d,
            hourly_rate=50.00,
            hours_worked=40,
            gross_pay=2000.00,
            state="CA"
        )
        assert result.is_legal == False
        assert result.severity == "illegal"
        assert result.drops_below_minimum_wage == False
        assert "illegal" in result.reason_es.lower()
        
    def test_tools_require_consent_tx_high_earner(self):
        """
        TX high earner: tool deductions need written consent.
        Effective: ($2000-$100)/40 = $47.50 — above $7.25 minimum.
        Not a minimum wage issue — a consent issue.
        """
        d = self.Item(name="TOOLS", amount=100.0)
        result = self.checker.check_single(
            deduction=d,
            hourly_rate=50.00,
            hours_worked=40,
            gross_pay=2000.00,
            state="TX"
        )
        assert result.requires_written_consent == True
        assert result.drops_below_minimum_wage == False

    def test_uniform_illegal_ny_regardless_of_wage(self):
        """
        NY Labor Law §193 prohibits uniform deductions.
        Illegal even for workers earning $25/hr.
        Effective: ($1000-$50)/40 = $23.75 — above $16.00 minimum.
        Violation is type-based, not wage-based.
        """
        d = self.Item(name="UNIFORM", amount=50.0)
        result = self.checker.check_single(
            deduction=d,
            hourly_rate=25.00,
            hours_worked=40,
            gross_pay=1000.00,
            state="NY"
        )
        assert result.is_legal == False
        assert result.severity == "illegal"
        assert result.drops_below_minimum_wage == False

    def test_health_insurance_always_legal(self):
        """
        Health insurance is a legal deduction type in all states.
        This test uses $30/hr — well above all state minimums:
        CA: $16.50, NY: $16.00, IL: $14.00, FL: $13.00, TX: $7.25
        Effective: ($1200-$120)/40 = $27/hr — above all minimums.
        Should be legal in all 5 states.
        """
        d = self.Item(name="HEALTH INSURANCE", amount=120.0)

        for state in ["TX", "CA", "NY", "FL", "IL"]:
            result = self.checker.check_single(
                deduction=d,
                hourly_rate=30.00,
                hours_worked=40,
                gross_pay=1200.00,
                state=state
            )
            assert result.is_legal == True, \
                f"Health insurance should be legal in {state} for $30/hr worker"
            assert result.drops_below_minimum_wage == False, \
                f"$27/hr effective should not drop below minimum in {state}"

    def test_minimum_wage_check_independent_of_deduction_type(self):
        """
        Even a normally-allowed deduction becomes illegal
        if it drops the worker below minimum wage.

        Health insurance is normally legal in TX.
        But: $300 gross - $200 deduction = $100 / 40hrs = $2.50/hr
        $2.50 < $7.25 TX minimum wage → ILLEGAL

        The minimum wage check overrides the type check.
        """
        d = self.Item(name="HEALTH INSURANCE", amount=200.0)
        result = self.checker.check_single(
            deduction=d,
            hourly_rate=7.50,
            hours_worked=40,
            gross_pay=300.00,
            state="TX"
        )
        assert result.drops_below_minimum_wage == True
        assert result.is_legal == False

    def test_il_breakage_illegal_regardless_of_wage(self):
        """
        Illinois 820 ILCS 115/9 prohibits breakage deductions.
        Illegal even for high earners.
        """
        d = self.Item(name="BREAKAGE", amount=50.0)
        result = self.checker.check_single(
            deduction=d,
            hourly_rate=40.00,
            hours_worked=40,
            gross_pay=1600.00,
            state="IL"
        )
        assert result.is_legal == False
        assert result.severity == "illegal"

    def test_fl_minimum_wage_2025(self):
        """
        Florida minimum wage is $13.00 in 2025.
        A deduction that drops below $13.00 is illegal.
        Worker: $14/hr × 40 = $560 gross
        Deduction: $100
        Effective: $460/40 = $11.50 < $13.00 → ILLEGAL
        """
        d = self.Item(name="SUPPLIES", amount=100.0)
        result = self.checker.check_single(
            deduction=d,
            hourly_rate=14.00,
            hours_worked=40,
            gross_pay=560.00,
            state="FL"
        )
        assert result.drops_below_minimum_wage == True
        assert result.is_legal == False