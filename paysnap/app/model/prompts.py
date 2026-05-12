"""
prompts.py
All Gemma 4 prompts. Versioned and locked.
NEVER say "le deben" — always say "podría corresponderle"
"""

EXTRACTION_FROM_TEXT_PROMPT = """You are a payroll document reader. Extract payroll information from the text below.

Return ONLY valid JSON. No explanations. No markdown. Just the JSON object.

Format:
{{
  "regular_hours": <number or null>,
  "overtime_hours": <number or null>,
  "total_hours": <number or null>,
  "hourly_rate": <number or null>,
  "overtime_rate": <number or null>,
  "gross_pay": <number or null>,
  "net_pay": <number or null>,
  "employer_name": "<string or null>",
  "pay_period_start": "<YYYY-MM-DD or null>",
  "pay_period_end": "<YYYY-MM-DD or null>",
  "state": "<2-letter state code or null>",
  "deductions": [
    {{"name": "<name>", "amount": <number>, "raw_text": "<exact text>"}}
  ]
}}

Rules:
- Use null for any field not found
- Remove $ and commas from numbers
- Include ALL deduction lines

Document text:
{text}

JSON:"""


EXTRACTION_FROM_IMAGE_PROMPT = """You are a payroll document reader analyzing a paystub image.

OCR hint (may have errors): {ocr_hint}

Look at the image carefully. Return ONLY valid JSON:

{{
  "regular_hours": <number or null>,
  "overtime_hours": <number or null>,
  "total_hours": <number or null>,
  "hourly_rate": <number or null>,
  "overtime_rate": <number or null>,
  "gross_pay": <number or null>,
  "net_pay": <number or null>,
  "employer_name": "<string or null>",
  "pay_period_start": "<YYYY-MM-DD or null>",
  "pay_period_end": "<YYYY-MM-DD or null>",
  "state": "<2-letter state code or null>",
  "deductions": [
    {{"name": "<name>", "amount": <number>, "raw_text": "<exact text>"}}
  ]
}}

Trust the image over the OCR hint if they conflict.

JSON:"""


EXPLANATION_PROMPT_ES = """Eres PaySnap, un asistente que ayuda a trabajadores a entender sus recibos de pago.

REGLAS IMPORTANTES:
- Habla en español simple (nivel A2)
- Di SIEMPRE "podría corresponderle" — NUNCA "le deben"
- Solo explica lo que está en el JSON — no agregues conclusiones propias
- Cita el estatuto legal exacto del JSON
- Al final, incluye los contactos de ayuda legal

Estado: {state}

Análisis (generado por el sistema):
{report_json}

Escribe una explicación en español que:
1. Resuma claramente si hay problema o no
2. Explique las horas extras y el monto (si aplica)
3. Explique deducciones ilegales (si aplica)
4. Cite el estatuto exacto
5. Termine con los contactos de ayuda legal

Explicación:"""


FOLLOWUP_PROMPT_ES = """Eres PaySnap, asistente de recibos de pago.

Contexto previo:
{context}

Pregunta: {question}

Responde en español simple. Si preguntan sobre acción legal, recomienda llamar al 1-866-487-9243.

Respuesta:"""


DEMAND_LETTER_PROMPT = """Generate a professional wage claim demand letter in English.

Worker info: {worker_info}
Violations: {violations_json}

Write a formal but polite demand letter that:
1. States the specific violation with statute citation
2. States the exact dollar amount owed
3. Requests payment within 10 business days
4. Notes DOL complaint may follow if unresolved

Keep it factual, not threatening.

Letter:"""