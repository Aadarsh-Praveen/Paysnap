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
        subprocess.run(["python3", "data/build_db.py"],
                      cwd=str(Path(__file__).parent.parent), check=True)


class TestOvertimeCalculator:
    @pytest.fixture(autouse=True)
    def setup(self):
        from app.analysis.overtime_calculator import OvertimeCalculator
        self.calc = OvertimeCalculator()

    def test_no_violation_40hrs(self):
        r = self.calc.calculate(40, 15.0, "TX", 40, 0)
        assert r.has_violation == False
        assert r.total_additional_pay == 0.0

    def test_tx_overtime_12hrs(self):
        r = self.calc.calculate(52, 32.0, "TX", 40, 0)
        assert r.has_violation == True
        assert r.ot_hours_owed == 12.0
        assert abs(r.total_additional_pay - 576.0) < 0.01
        assert "207" in r.statute

    def test_already_paid_ot(self):
        r = self.calc.calculate(52, 32.0, "TX", 40, 12)
        assert r.has_violation == False

    def test_ca_daily_overtime(self):
        r = self.calc.calculate(38, 20.0, "CA", 38, 0, daily_hours=10)
        assert r.has_violation == True
        assert "510" in r.statute

    def test_ca_double_time(self):
        r = self.calc.calculate(40, 20.0, "CA", 40, 0, daily_hours=14)
        assert r.has_violation == True
        assert r.double_time_hours > 0

    def test_statute_present_on_violation(self):
        r = self.calc.calculate(50, 15.0, "NY", 40, 0)
        assert r.has_violation == True
        assert r.statute and len(r.statute) > 5

    def test_biweekly(self):
        r = self.calc.calculate(90, 20.0, "TX", 80, 0, pay_period="biweekly")
        assert r.has_violation == True


class TestDeductionChecker:
    @pytest.fixture(autouse=True)
    def setup(self):
        from app.analysis.deduction_checker import DeductionChecker
        from app.core.input_handler import DeductionItem
        self.checker = DeductionChecker()
        self.Item = DeductionItem

    def test_tools_illegal_ca(self):
        d = self.Item(name="TOOLS", amount=75.0)
        r = self.checker.check_single(d, 20.0, 40, 800.0, "CA")
        assert r.is_legal == False
        assert r.severity == "illegal"

    def test_drops_below_min_wage(self):
        d = self.Item(name="TOOLS", amount=75.0)
        r = self.checker.check_single(d, 7.50, 40, 300.0, "TX")
        assert r.drops_below_minimum_wage == True
        assert r.is_legal == False

    def test_taxes_always_legal(self):
        for name in ["Federal Tax", "State Tax", "Social Security", "Medicare"]:
            d = self.Item(name=name, amount=50.0)
            r = self.checker.check_single(d, 20.0, 40, 800.0, "TX")
            assert r.is_legal == True, f"{name} should be legal"

    def test_spanish_keywords(self):
        assert self.checker._categorize("HERRAMIENTAS") == "tools"
        assert self.checker._categorize("UNIFORME") == "uniforms"