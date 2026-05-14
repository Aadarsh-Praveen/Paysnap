"""
demand_letter.py
Generates formal English demand letter for employer.
Uses Gemma 4 to write the letter based on violation report.
"""

from pathlib import Path
import tempfile


def generate_letter(violation_report, paystub) -> str:
    """
    Generates a professional demand letter.
    Returns the letter as a string.
    """
    if not violation_report.has_any_violation:
        return "No violations found — no demand letter needed."

    # Build violation summary for prompt
    violations = []

    if violation_report.overtime.has_violation:
        violations.append(
            f"- Unpaid overtime: {violation_report.overtime.ot_hours_owed:.1f} hours "
            f"x ${violation_report.overtime.ot_hours_owed * paystub.hourly_rate * 0.5:.2f} "
            f"= ${violation_report.overtime.ot_pay_owed:.2f} owed\n"
            f"  Statute: {violation_report.overtime.statute}"
        )

    for d in violation_report.illegal_deductions:
        violations.append(
            f"- Illegal deduction '{d.deduction.name}': "
            f"${d.deduction.amount:.2f}\n"
            f"  Statute: {d.statute}"
        )

    violations_text = "\n".join(violations)
    total = violation_report.total_money_owed

    prompt = f"""Write a professional wage claim demand letter in English.

Employer: {paystub.employer_name or 'Employer'}
State: {violation_report.state}
Total hours worked: {paystub.total_hours}
Hourly rate: ${paystub.hourly_rate:.2f}
Total amount owed: ${total:.2f}

Violations found:
{violations_text}

Math verification:
{violation_report.overtime.calculation_breakdown}

Write a formal demand letter that:
1. Has today's date at the top
2. Addresses the employer formally
3. States each violation with exact statute citation
4. Shows the math clearly
5. States the total amount owed: ${total:.2f}
6. Requests payment within 10 business days
7. States that failure to respond will result in 
   a DOL Wage and Hour Division complaint
8. Is firm but professional — not threatening
9. Ends with space for worker signature

Write the complete letter now:"""

    return prompt


def save_letter_to_file(letter_text: str) -> str:
    """Saves letter to temp file for download."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
        prefix="paysnap_demand_letter_"
    )
    tmp.write(letter_text)
    tmp.close()
    return tmp.name