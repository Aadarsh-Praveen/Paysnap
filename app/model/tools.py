"""
app/model/tools.py

Native Gemma 4 function calling tools for wage theft detection.
Gemma 4 decides which tools to call based on paystub data.
Each tool wraps our deterministic Python math engine.
"""

from typing import Any
import sys
import os

# ── TOOL SCHEMAS (passed to Gemma 4) ─────────────────────────
PAYSNAP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_overtime",
            "description": (
                "Calculate unpaid overtime owed to a worker under FLSA "
                "and state law. Use this when the paystub shows hours "
                "worked over 40/week or when overtime hours appear underpaid."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hours_worked": {
                        "type": "number",
                        "description": "Total hours worked in the pay period"
                    },
                    "hourly_rate": {
                        "type": "number",
                        "description": "Worker's regular hourly rate in USD"
                    },
                    "overtime_hours_paid": {
                        "type": "number",
                        "description": "Overtime hours already paid (0 if none shown on paystub)"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code (TX, CA, NY, FL, IL)"
                    }
                },
                "required": ["hours_worked", "hourly_rate", "state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_minimum_wage",
            "description": (
                "Check if a worker was paid below minimum wage. "
                "Use this when the hourly rate seems low or when "
                "total pay divided by hours is below minimum wage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hourly_rate": {
                        "type": "number",
                        "description": "Worker's actual hourly rate paid"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code"
                    },
                    "hours_worked": {
                        "type": "number",
                        "description": "Total hours worked"
                    }
                },
                "required": ["hourly_rate", "state", "hours_worked"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_deductions",
            "description": (
                "Check if a paycheck deduction is legal in the worker's state. "
                "Use this when the paystub shows deductions for tools, uniforms, "
                "equipment, breakage, or other items that may be illegal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "deduction_name": {
                        "type": "string",
                        "description": "Name of the deduction (e.g. TOOLS, UNIFORM, BREAKAGE)"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount deducted in USD"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code"
                    },
                    "hourly_rate": {
                        "type": "number",
                        "description": "Worker's hourly rate (to check if deduction drops below minimum wage)"
                    },
                    "hours_worked": {
                        "type": "number",
                        "description": "Hours worked in the period"
                    }
                },
                "required": ["deduction_name", "amount", "state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_applicable_statutes",
            "description": (
                "Get the exact FLSA and state law statutes that apply "
                "to a specific violation type. Always call this after "
                "identifying a violation to get precise legal citations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "violation_type": {
                        "type": "string",
                        "description": "Type of violation: overtime, minimum_wage, illegal_deduction, retaliation"
                    },
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code"
                    }
                },
                "required": ["violation_type", "state"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dol_contact",
            "description": (
                "Get DOL contact information for a worker to report violations. "
                "Always call this at the end of analysis to give the worker "
                "actionable next steps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code for state-specific contacts"
                    },
                    "language": {
                        "type": "string",
                        "description": "Worker's language code (en, es, hi, zh, vi, etc.)"
                    }
                },
                "required": ["state"]
            }
        }
    }
]


# ── TOOL EXECUTION ENGINE ─────────────────────────────────────
# These functions are called when Gemma 4 requests a tool call.
# They wrap our deterministic Python math — 100% accurate.

STATE_RULES = {
    "TX": {"min_wage": 7.25,  "ot_threshold": 40, "ot_multiplier": 1.5,
           "daily_ot": False, "daily_threshold": None},
    "CA": {"min_wage": 16.50, "ot_threshold": 40, "ot_multiplier": 1.5,
           "daily_ot": True,  "daily_threshold": 8, "daily_double": 12},
    "NY": {"min_wage": 16.00, "ot_threshold": 40, "ot_multiplier": 1.5,
           "daily_ot": False, "daily_threshold": None},
    "FL": {"min_wage": 13.00, "ot_threshold": 40, "ot_multiplier": 1.5,
           "daily_ot": False, "daily_threshold": None},
    "IL": {"min_wage": 14.00, "ot_threshold": 40, "ot_multiplier": 1.5,
           "daily_ot": False, "daily_threshold": None},
}

STATUTES = {
    "overtime": {
        "federal": "FLSA 29 USC 207(a)(1)",
        "CA": "California Labor Code §510",
        "NY": "New York Labor Law §160",
        "IL": "820 ILCS 105/4a",
        "FL": "FLSA 29 USC 207(a)(1)",
        "TX": "FLSA 29 USC 207(a)(1)",
    },
    "minimum_wage": {
        "federal": "FLSA 29 USC 206",
        "CA": "California Labor Code §1182.12",
        "NY": "New York Labor Law §652",
        "IL": "820 ILCS 105/4",
        "FL": "Florida Constitution Art. X §24",
        "TX": "FLSA 29 USC 206",
    },
    "illegal_deduction": {
        "federal": "FLSA 29 USC 206 (deductions cannot drop below minimum wage)",
        "CA": "California Labor Code §221",
        "NY": "New York Labor Law §193",
        "IL": "820 ILCS 115/9",
        "FL": "FLSA 29 USC 206",
        "TX": "FLSA 29 USC 206",
    },
    "retaliation": {
        "federal": "FLSA §15(a)(3)",
        "CA": "California Labor Code §98.6",
        "NY": "New York Labor Law §215",
        "IL": "820 ILCS 105/11",
        "FL": "FLSA §15(a)(3)",
        "TX": "FLSA §15(a)(3)",
    }
}

ILLEGAL_DEDUCTION_TYPES = {
    "CA": ["TOOLS", "EQUIPMENT", "UNIFORM", "BREAKAGE", "SHORTAGE",
           "CASH_REGISTER", "DAMAGE", "SAFETY", "TRAINING"],
    "NY": ["TOOLS", "EQUIPMENT", "UNIFORM", "BREAKAGE", "SHORTAGE",
           "CASH_REGISTER", "DAMAGE"],
    "IL": ["TOOLS", "BREAKAGE", "SHORTAGE", "CASH_REGISTER", "DAMAGE"],
    "FL": [],  # Only illegal if drops below minimum wage
    "TX": [],  # Only illegal if drops below minimum wage
}

DOL_CONTACTS = {
    "federal": {
        "phone":       "1-866-487-9243",
        "description": "DOL Wage and Hour Division — free, confidential, 200+ languages",
        "url":         "https://www.dol.gov/agencies/whd",
    },
    "CA": {
        "phone":       "1-844-522-6734",
        "description": "California Labor Commissioner",
        "url":         "https://www.dir.ca.gov/dlse/",
    },
    "NY": {
        "phone":       "1-888-469-7365",
        "description": "New York State Department of Labor",
        "url":         "https://dol.ny.gov",
    },
    "IL": {
        "phone":       "1-312-793-2804",
        "description": "Illinois Department of Labor",
        "url":         "https://labor.illinois.gov",
    },
    "FL": {
        "phone":       "1-866-487-9243",
        "description": "DOL Wage and Hour Division",
        "url":         "https://www.dol.gov/agencies/whd",
    },
    "TX": {
        "phone":       "1-866-487-9243",
        "description": "DOL Wage and Hour Division",
        "url":         "https://www.dol.gov/agencies/whd",
    },
}


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """
    Execute a tool call from Gemma 4.
    Returns result dict that gets sent back to Gemma 4.
    """
    handlers = {
        "calculate_overtime":    _calculate_overtime,
        "check_minimum_wage":    _check_minimum_wage,
        "check_deductions":      _check_deductions,
        "get_applicable_statutes": _get_statutes,
        "get_dol_contact":       _get_dol_contact,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return handler(**arguments)
    except Exception as e:
        return {"error": str(e)}


def _calculate_overtime(
    hours_worked: float,
    hourly_rate: float,
    state: str,
    overtime_hours_paid: float = 0
) -> dict:
    rules = STATE_RULES.get(state.upper(), STATE_RULES["TX"])
    threshold = rules["ot_threshold"]
    multiplier = rules["ot_multiplier"]

    total_ot_hours = max(0, hours_worked - threshold)
    additional_ot  = max(0, total_ot_hours - overtime_hours_paid)
    ot_premium     = round(additional_ot * hourly_rate * 0.5, 2)

    has_violation = additional_ot > 0
    statute = STATUTES["overtime"].get(state.upper(),
              STATUTES["overtime"]["federal"])

    result = {
        "has_violation":        has_violation,
        "hours_worked":         hours_worked,
        "overtime_threshold":   threshold,
        "total_ot_hours":       total_ot_hours,
        "ot_hours_already_paid": overtime_hours_paid,
        "additional_ot_hours":  additional_ot,
        "hourly_rate":          hourly_rate,
        "ot_rate":              round(hourly_rate * multiplier, 2),
        "ot_premium_owed":      ot_premium,
        "statute":              statute,
        "calculation":          f"{additional_ot} hrs × ${hourly_rate} × 0.5 = ${ot_premium}"
    }

    # California daily overtime
    if state.upper() == "CA" and rules.get("daily_ot"):
        result["note"] = (
            "California also has daily overtime: 1.5x after 8 hrs/day, "
            "2x after 12 hrs/day (Labor Code §510). "
            "Daily OT may add to amount owed."
        )
    return result


def _check_minimum_wage(
    hourly_rate: float,
    state: str,
    hours_worked: float
) -> dict:
    rules    = STATE_RULES.get(state.upper(), STATE_RULES["TX"])
    min_wage = rules["min_wage"]
    federal  = 7.25
    effective_min = max(min_wage, federal)

    has_violation  = hourly_rate < effective_min
    amount_owed    = round(max(0, (effective_min - hourly_rate) * hours_worked), 2)
    statute        = STATUTES["minimum_wage"].get(
                     state.upper(), STATUTES["minimum_wage"]["federal"])

    return {
        "has_violation":     has_violation,
        "hourly_rate_paid":  hourly_rate,
        "minimum_wage":      effective_min,
        "federal_minimum":   federal,
        "state_minimum":     min_wage,
        "hours_worked":      hours_worked,
        "amount_owed":       amount_owed,
        "statute":           statute,
        "calculation":       (
            f"(${effective_min} - ${hourly_rate}) × {hours_worked} hrs = ${amount_owed}"
            if has_violation else "No violation — rate above minimum wage"
        )
    }


def _check_deductions(
    deduction_name: str,
    amount: float,
    state: str,
    hourly_rate: float = 0,
    hours_worked: float = 0
) -> dict:
    state_upper  = state.upper()
    illegal_list = ILLEGAL_DEDUCTION_TYPES.get(state_upper, [])
    deduction_upper = deduction_name.upper()

    # Check if deduction type is categorically illegal in this state
    is_categorically_illegal = any(
        illegal in deduction_upper for illegal in illegal_list
    )

    # Check if deduction drops pay below minimum wage
    drops_below_min = False
    if hourly_rate > 0 and hours_worked > 0:
        rules    = STATE_RULES.get(state_upper, STATE_RULES["TX"])
        min_wage = max(rules["min_wage"], 7.25)
        gross    = hourly_rate * hours_worked
        net      = gross - amount
        effective_rate = net / hours_worked if hours_worked > 0 else 0
        drops_below_min = effective_rate < min_wage

    has_violation = is_categorically_illegal or drops_below_min
    statute = STATUTES["illegal_deduction"].get(
              state_upper, STATUTES["illegal_deduction"]["federal"])

    return {
        "has_violation":             has_violation,
        "deduction_name":            deduction_name,
        "amount":                    amount,
        "state":                     state,
        "is_categorically_illegal":  is_categorically_illegal,
        "drops_below_minimum_wage":  drops_below_min,
        "amount_must_be_returned":   amount if has_violation else 0,
        "statute":                   statute if has_violation else "No violation",
        "reason": (
            f"Deductions for {deduction_name} are prohibited in {state} "
            f"under {statute}" if is_categorically_illegal
            else (
                "Deduction drops effective hourly rate below minimum wage"
                if drops_below_min
                else f"Deduction appears legal in {state}"
            )
        )
    }


def _get_statutes(violation_type: str, state: str) -> dict:
    vtype       = violation_type.lower().replace(" ", "_")
    state_upper = state.upper()
    statutes    = STATUTES.get(vtype, {})

    return {
        "violation_type":  violation_type,
        "state":           state,
        "federal_statute": statutes.get("federal", "FLSA"),
        "state_statute":   statutes.get(state_upper, statutes.get("federal", "FLSA")),
        "statute_of_limitations": (
            "2 years (regular) or 3 years (willful) — FLSA 29 USC 255(a)"
        ),
        "liquidated_damages": (
            "Equal amount in liquidated damages available — FLSA 29 USC 216(b)"
        )
    }


def _get_dol_contact(state: str, language: str = "en") -> dict:
    state_upper  = state.upper()
    federal      = DOL_CONTACTS["federal"]
    state_office = DOL_CONTACTS.get(state_upper, federal)

    return {
        "federal_hotline":    federal["phone"],
        "federal_description": federal["description"],
        "state_office":       state_office.get("phone", federal["phone"]),
        "state_description":  state_office.get("description", federal["description"]),
        "note":               "Free, confidential, available in 200+ languages. "
                              "FLSA protects ALL workers regardless of immigration status.",
        "online":             "https://www.dol.gov/agencies/whd/contact/complaints",
        "language_note":      (
            "Interpreters available — you can report in your language"
            if language != "en" else "Available in English and 200+ languages"
        )
    }