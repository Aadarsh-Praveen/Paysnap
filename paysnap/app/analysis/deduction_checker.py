"""
deduction_checker.py
Deterministic deduction legality. Zero LLM.
All strings in English — translation handled by backend layer.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from app.core.input_handler import DeductionItem

DB_PATH = Path(__file__).parent.parent.parent / "data" / "labor_law.db"


@dataclass
class DeductionCheckResult:
    deduction: DeductionItem
    is_legal: bool
    is_suspicious: bool
    requires_written_consent: bool
    drops_below_minimum_wage: bool
    statute: str
    reason_es: str   # kept for backward compatibility — now always English
    reason_en: str   # canonical English reason
    severity: str    # "illegal", "suspicious", "ok"


class DeductionChecker:
    KEYWORDS = {
        "tools": ["tools", "tool", "equipment", "herramientas", "equipo"],
        "uniforms": ["uniform", "uniforms", "clothing", "vest", "uniforme", "ropa"],
        "meals": ["meal", "meals", "food", "lunch", "comida", "almuerzo"],
        "health_insurance": ["health", "medical", "insurance", "dental", "vision", "salud", "seguro"],
        "retirement_401k": ["401k", "401(k)", "retirement", "ira", "retiro"],
        "union_dues": ["union", "dues", "sindical", "sindicato"],
        "federal_taxes": ["federal tax", "federal income", "fit"],
        "state_taxes": ["state tax", "state income", "sit"],
        "social_security": ["social security", "ss", "fica", "seguro social"],
        "medicare": ["medicare"],
        "cash_register_shortages": ["shortage", "cash short", "faltante"],
        "breakage": ["breakage", "broken", "damage", "daño", "rotura"],
        "business_expenses": ["gas", "mileage", "phone", "supplies"],
    }

    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def check_all(self, deductions, hourly_rate, hours_worked, state):
        gross = hourly_rate * hours_worked
        return [
            self.check_single(d, hourly_rate, hours_worked, gross, state)
            for d in deductions
        ]

    def check_single(self, deduction, hourly_rate, hours_worked, gross_pay, state):
        category = self._categorize(deduction.name)
        min_wage = self._get_min_wage(state)
        rule = self._get_rule(state, category)

        # ─────────────────────────────────────────
        # CHECK 3 RUNS FIRST AND ALWAYS
        # Minimum wage check is independent of
        # deduction type — runs no matter what
        # ─────────────────────────────────────────
        drops_below = False
        effective_hourly = 0.0

        if hours_worked > 0 and gross_pay > 0:
            effective_hourly = (gross_pay - deduction.amount) / hours_worked
            drops_below = effective_hourly < min_wage

        if drops_below:
            reason = (
                f"This ${deduction.amount:.2f} deduction "
                f"reduces your effective pay to "
                f"${effective_hourly:.2f}/hr. "
                f"Minimum wage in {state} is ${min_wage:.2f}/hr. "
                f"This is ILLEGAL under federal law "
                f"regardless of deduction type."
            )
            return DeductionCheckResult(
                deduction=deduction,
                is_legal=False,
                is_suspicious=False,
                requires_written_consent=False,
                drops_below_minimum_wage=True,
                statute="FLSA 29 USC 203(m)",
                reason_es=reason,
                reason_en=reason,
                severity="illegal"
            )

        # ─────────────────────────────────────────
        # CHECK 1: Is deduction TYPE illegal
        # in this state regardless of wage?
        # ─────────────────────────────────────────
        if rule and not rule["is_allowed"]:
            reason = (
                f"'{deduction.name}' deduction is ILLEGAL "
                f"in {state} regardless of wage level. "
                f"Under {rule['statute']}, employers cannot "
                f"make this deduction."
            )
            return DeductionCheckResult(
                deduction=deduction,
                is_legal=False,
                is_suspicious=False,
                requires_written_consent=False,
                drops_below_minimum_wage=False,
                statute=rule["statute"] or "State labor law",
                reason_es=reason,
                reason_en=reason,
                severity="illegal"
            )

        # ─────────────────────────────────────────
        # CHECK 2: Requires written consent?
        # Only reaches here if not below min wage
        # and not categorically illegal
        # ─────────────────────────────────────────
        if rule and rule["requires_written_consent"]:
            reason = (
                f"'{deduction.name}' requires your written "
                f"consent. If you did not sign an agreement, "
                f"it may be illegal."
            )
            return DeductionCheckResult(
                deduction=deduction,
                is_legal=True,
                is_suspicious=True,
                requires_written_consent=True,
                drops_below_minimum_wage=False,
                statute=rule["statute"] or "State labor law",
                reason_es=reason,
                reason_en=reason,
                severity="suspicious"
            )

        # ─────────────────────────────────────────
        # No violation found
        # ─────────────────────────────────────────
        if category != "unknown":
            reason = "No issue detected with this deduction."
        else:
            reason = (
                f"Could not identify '{deduction.name}'. "
                f"Verify with a labor attorney."
            )

        return DeductionCheckResult(
            deduction=deduction,
            is_legal=True,
            is_suspicious=(category == "unknown"),
            requires_written_consent=False,
            drops_below_minimum_wage=False,
            statute="FLSA",
            reason_es=reason,
            reason_en=reason,
            severity="ok" if category != "unknown" else "suspicious"
        )

    def _categorize(self, name: str) -> str:
        name_lower = name.lower()
        for cat, keywords in self.KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return cat
        return "unknown"

    def _get_min_wage(self, state: str) -> float:
        try:
            conn = self._get_db()
            row = conn.execute(
                "SELECT minimum_wage FROM state_rules WHERE state_code=?",
                (state,)
            ).fetchone()
            conn.close()
            return row["minimum_wage"] if row else 7.25
        except:
            return 7.25

    def _get_rule(self, state: str, category: str):
        try:
            conn = self._get_db()
            row = conn.execute(
                "SELECT * FROM deduction_rules WHERE state_code=? AND deduction_type=?",
                (state, category)
            ).fetchone()
            conn.close()
            return dict(row) if row else None
        except:
            return None