"""
deduction_checker.py
Deterministic deduction legality. Zero LLM.
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
    reason_es: str
    reason_en: str
    severity: str  # "illegal", "suspicious", "ok"


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

        effective = (gross_pay - deduction.amount) / hours_worked if hours_worked > 0 else 0
        drops_below = effective < min_wage

        if drops_below:
            return DeductionCheckResult(
                deduction=deduction, is_legal=False, is_suspicious=False,
                requires_written_consent=False, drops_below_minimum_wage=True,
                statute=f"FLSA 29 USC 203(m)",
                reason_es=(f"Esta deducción de ${deduction.amount:.2f} baja tu pago a "
                           f"${effective:.2f}/hora, por debajo del mínimo de ${min_wage:.2f}/hora. ILEGAL."),
                reason_en=(f"This ${deduction.amount:.2f} deduction reduces pay to "
                           f"${effective:.2f}/hr, below ${min_wage:.2f}/hr minimum. ILLEGAL."),
                severity="illegal"
            )

        rule = self._get_rule(state, category)
        if rule:
            if not rule["is_allowed"]:
                return DeductionCheckResult(
                    deduction=deduction, is_legal=False, is_suspicious=False,
                    requires_written_consent=False, drops_below_minimum_wage=False,
                    statute=rule["statute"] or "State labor law",
                    reason_es=f"La deducción '{deduction.name}' es ILEGAL en {state} según {rule['statute']}.",
                    reason_en=f"Deduction '{deduction.name}' is ILLEGAL in {state} under {rule['statute']}.",
                    severity="illegal"
                )
            if rule["requires_written_consent"]:
                return DeductionCheckResult(
                    deduction=deduction, is_legal=True, is_suspicious=True,
                    requires_written_consent=True, drops_below_minimum_wage=False,
                    statute=rule["statute"] or "State labor law",
                    reason_es=f"La deducción '{deduction.name}' requiere consentimiento por escrito. ¿Firmaste un acuerdo?",
                    reason_en=f"Deduction '{deduction.name}' requires written consent. Did you sign an agreement?",
                    severity="suspicious"
                )

        return DeductionCheckResult(
            deduction=deduction, is_legal=True, is_suspicious=(category == "unknown"),
            requires_written_consent=False, drops_below_minimum_wage=False,
            statute="FLSA",
            reason_es="No detectamos un problema con esta deducción." if category != "unknown"
                      else f"No reconocemos '{deduction.name}'. Verifica con un abogado.",
            reason_en="No issue detected." if category != "unknown"
                      else f"Could not identify '{deduction.name}'. Verify with an attorney.",
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
            row = conn.execute("SELECT minimum_wage FROM state_rules WHERE state_code=?", (state,)).fetchone()
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