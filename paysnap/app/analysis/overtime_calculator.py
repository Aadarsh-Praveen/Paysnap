"""
overtime_calculator.py
DETERMINISTIC overtime calculation. Zero LLM.
Database decides. AI explains.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "labor_law.db"


@dataclass
class OvertimeResult:
    total_hours: float
    regular_rate: float
    state: str
    regular_hours_paid: float
    ot_hours_owed: float
    ot_pay_owed: float
    double_time_hours: float
    double_time_pay: float
    total_additional_pay: float
    has_violation: bool
    statute: str
    statute_description_es: str
    statute_description_en: str
    calculation_breakdown: str


class OvertimeCalculator:
    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def calculate(self, total_hours, regular_rate, state,
                  hours_shown_on_stub, overtime_shown_on_stub=0.0,
                  daily_hours=None, pay_period="weekly"):

        rules = self._get_rules(state)
        if not rules:
            rules = self._get_rules("TX")

        weekly_hours = total_hours / 2 if pay_period == "biweekly" else total_hours
        threshold = rules["ot_weekly_threshold"]
        multiplier = rules["ot_multiplier"]

        ot_hours = max(0, weekly_hours - threshold)
        regular_hours = min(weekly_hours, threshold)
        ot_rate = regular_rate * multiplier
        ot_pay = ot_hours * ot_rate

        double_time_hours = 0.0
        double_time_pay = 0.0

        if rules["ot_daily_threshold"] and daily_hours:
            daily_threshold = rules["ot_daily_threshold"]
            double_threshold = rules["ot_double_threshold"]
            double_mult = rules["ot_double_multiplier"] or 2.0

            if daily_hours > double_threshold:
                double_time_hours = daily_hours - double_threshold
                double_time_pay = double_time_hours * (regular_rate * double_mult)
                ot_hours = double_threshold - daily_threshold
                ot_pay = ot_hours * ot_rate
            elif daily_hours > daily_threshold:
                ot_hours = daily_hours - daily_threshold
                ot_pay = ot_hours * ot_rate

        ot_difference = ot_hours - overtime_shown_on_stub
        additional = max(0, ot_difference * ot_rate)
        total_additional = additional + double_time_pay
        has_violation = total_additional > 0.01

        statute = rules["ot_statute"] or "FLSA 29 USC 207(a)(1)"

        breakdown = (
            f"Total hours: {total_hours}\n"
            f"Rate: ${regular_rate:.2f}/hr\n"
            f"OT threshold ({state}): {threshold} hrs/week\n"
            f"OT hours owed: {ot_hours:.1f}\n"
            f"OT rate: ${regular_rate:.2f} x {multiplier} = ${ot_rate:.2f}/hr\n"
            f"OT pay: {ot_hours:.1f} x ${ot_rate:.2f} = ${ot_pay:.2f}\n"
        )
        if double_time_hours > 0:
            breakdown += f"Double time: {double_time_hours:.1f} hrs = ${double_time_pay:.2f}\n"
        breakdown += f"TOTAL OWED: ${total_additional:.2f}"

        es_desc = self._statute_es(state, rules)
        en_desc = self._statute_en(state, rules)

        return OvertimeResult(
            total_hours=total_hours,
            regular_rate=regular_rate,
            state=state,
            regular_hours_paid=regular_hours,
            ot_hours_owed=ot_hours,
            ot_pay_owed=ot_pay,
            double_time_hours=double_time_hours,
            double_time_pay=double_time_pay,
            total_additional_pay=total_additional,
            has_violation=has_violation,
            statute=statute,
            statute_description_es=es_desc,
            statute_description_en=en_desc,
            calculation_breakdown=breakdown
        )

    def _get_rules(self, state):
        try:
            conn = self._get_db()
            row = conn.execute(
                "SELECT * FROM state_rules WHERE state_code=?", (state,)
            ).fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"DB error: {e}")
            return None

    def _statute_es(self, state, rules):
        t = rules.get("ot_weekly_threshold", 40)
        m = rules.get("ot_multiplier", 1.5)
        st = rules.get("ot_statute", "FLSA 29 USC 207")
        if state == "CA":
            return (f"Según el Código Laboral de California §510: más de 8 horas/día "
                    f"o más de {t} horas/semana = {m}x tu tarifa. Más de 12 horas/día = 2x.")
        return (f"Según la Ley Federal ({st}): más de {t} horas/semana "
                f"deben pagarse al {m}x tu tarifa normal.")

    def _statute_en(self, state, rules):
        t = rules.get("ot_weekly_threshold", 40)
        m = rules.get("ot_multiplier", 1.5)
        st = rules.get("ot_statute", "FLSA 29 USC 207")
        if state == "CA":
            return (f"Under CA Labor Code §510: over 8 hrs/day or {t} hrs/week "
                    f"= {m}x rate. Over 12 hrs/day = 2x.")
        return f"Under FLSA ({st}): over {t} hours/week must be paid at {m}x regular rate."