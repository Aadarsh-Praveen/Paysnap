"""
violation_engine.py
Combines all checks into one ViolationReport.
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from app.core.input_handler import PaystubData
from app.analysis.overtime_calculator import OvertimeCalculator, OvertimeResult
from app.analysis.deduction_checker import DeductionChecker, DeductionCheckResult

DB_PATH = Path(__file__).parent.parent.parent / "data" / "labor_law.db"


@dataclass
class ViolationReport:
    paystub: PaystubData
    state: str
    overtime: OvertimeResult
    deduction_results: list = field(default_factory=list)
    has_any_violation: bool = False
    total_money_owed: float = 0.0
    violation_count: int = 0
    illegal_deductions: list = field(default_factory=list)
    suspicious_deductions: list = field(default_factory=list)
    legal_aid_contacts: list = field(default_factory=list)


class ViolationEngine:
    def __init__(self):
        self.ot = OvertimeCalculator()
        self.ded = DeductionChecker()

    def analyze(self, paystub: PaystubData, state: str) -> ViolationReport:
        print(f"Analyzing: state={state}")

        total = paystub.total_hours or ((paystub.regular_hours or 0) + (paystub.overtime_hours or 0))

        ot_result = self.ot.calculate(
            total_hours=total,
            regular_rate=paystub.hourly_rate or 0,
            state=state,
            hours_shown_on_stub=paystub.regular_hours or 0,
            overtime_shown_on_stub=paystub.overtime_hours or 0,
        )

        ded_results = []
        if paystub.deductions and paystub.hourly_rate and total:
            ded_results = self.ded.check_all(paystub.deductions, paystub.hourly_rate, total, state)

        legal_aid = self._get_legal_aid(state)
        illegal = [r for r in ded_results if not r.is_legal]
        suspicious = [r for r in ded_results if r.is_suspicious and r.is_legal]
        total_illegal_amt = sum(r.deduction.amount for r in illegal)
        total_owed = ot_result.total_additional_pay + total_illegal_amt

        return ViolationReport(
            paystub=paystub, state=state, overtime=ot_result,
            deduction_results=ded_results,
            has_any_violation=ot_result.has_violation or len(illegal) > 0,
            total_money_owed=total_owed,
            violation_count=int(ot_result.has_violation) + len(illegal),
            illegal_deductions=illegal,
            suspicious_deductions=suspicious,
            legal_aid_contacts=legal_aid
        )

    def _get_legal_aid(self, state):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM legal_aid WHERE state_code=? AND serves_undocumented=1", (state,)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except:
            return [{"organization_name": "DOL Wage and Hour Division",
                     "phone": "1-866-487-9243",
                     "phone_note_es": "Free, bilingual service available"}]