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
- employer_name: extract company name if mentioned

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


# Language-specific instructions for Gemma 4
LANGUAGE_INSTRUCTIONS = {
    "es": "Responde completamente en español simple (nivel A2). Di 'podría corresponderle' nunca 'le deben'.",
    "zh": "请用简单的中文回答。说'可能欠您'而不是'他们欠您'。",
    "pt": "Responda completamente em português simples. Diga 'pode ter direito a' nunca 'eles devem'.",
    "ht": "Reponn nan kreyòl ayisyen senp. Di 'ou ka gen dwa a' pa 'yo dwe ou'.",
    "vi": "Trả lời hoàn toàn bằng tiếng Việt đơn giản. Nói 'có thể bạn được trả' không phải 'họ nợ bạn'.",
    "ko": "간단한 한국어로 답하세요. '받을 수 있습니다'라고 하고 '빚졌습니다'라고 하지 마세요.",
    "tl": "Sagutin sa simpleng Filipino. Sabihing 'maaaring may karapatang' hindi 'utang nila'.",
    "hi": "सरल हिंदी में जवाब दें। 'आपको मिल सकता है' कहें, 'वे आपका बकाया है' नहीं।",
    "ar": "أجب باللغة العربية البسيطة. قل 'قد تستحق' وليس 'يدينون لك'.",
    "ru": "Отвечайте на простом русском языке. Говорите 'возможно причитается' не 'они должны'.",
    "en": "Respond in plain English. Say 'you may be owed' never 'they owe you'.",
}

# Legal aid contact phrases by language
LEGAL_AID_PHRASES = {
    "es": "Para ayuda legal gratuita, llame al",
    "zh": "如需免费法律援助，请致电",
    "pt": "Para ajuda jurídica gratuita, ligue para",
    "ht": "Pou èd legal gratis, rele",
    "vi": "Để được hỗ trợ pháp lý miễn phí, hãy gọi",
    "ko": "무료 법률 지원을 받으려면 전화하세요",
    "tl": "Para sa libreng tulong legal, tumawag sa",
    "hi": "मुफ्त कानूनी सहायता के लिए, कॉल करें",
    "ar": "للحصول على مساعدة قانونية مجانية، اتصل بـ",
    "ru": "Для бесплатной юридической помощи позвоните",
    "en": "For free legal help, call",
}

MULTILINGUAL_EXPLANATION_PROMPT = """You are PaySnap, a payroll analysis assistant helping workers understand wage violations.

Language instruction: {language_instruction}

CRITICAL RULES:
1. Respond ONLY in the requested language — every word
2. ALWAYS include the EXACT dollar amount from the JSON (total_owed field)
3. ALWAYS show the math: hours × rate = amount
4. ALWAYS cite the exact statute (e.g. FLSA 29 USC 207(a)(1))
5. Say worker "may be owed" — never say employer "owes"
6. Use simple language a worker with basic education can understand
7. END with the DOL phone number: 1-866-487-9243
8. Keep response under 300 words
9. DO NOT ask clarifying questions — explain what is in the data

State: {state}
Language: {language_code}

Violation analysis (calculated by deterministic system):
{report_json}

Legal aid phrase in {language_code}: "{legal_aid_phrase}"
DOL phone: 1-866-487-9243

Structure your response as:
1. What violation was found (1-2 sentences)
2. The math calculation showing exact dollar amount
3. Which law applies (statute number)
4. How to get help (DOL phone number)

Write explanation now:"""


FOLLOWUP_PROMPT_ES = """Eres PaySnap, asistente de recibos de pago.

Contexto previo:
{context}

Pregunta: {question}

Responde en español simple. Si preguntan sobre acción legal, recomienda llamar al 1-866-487-9243.
Da respuestas cortas y directas. No hagas preguntas de vuelta.

Respuesta:"""


DEMAND_LETTER_PROMPT = """Generate a professional wage claim demand letter in English.

Worker info: {worker_info}
Violations: {violations_json}

Write a formal but polite demand letter that:
1. States the specific violation with exact statute citation
2. Shows the exact dollar calculation
3. Demands payment within 10 business days
4. Notes DOL complaint will follow if unresolved
5. Has [DATE] and [WORKER NAME] placeholders

Keep it factual and professional.

Letter:"""


# ── EXTRACTION FROM NATURAL LANGUAGE (voice/text input) ──
EXTRACTION_FROM_NATURAL_LANGUAGE = """You are a payroll data extractor. 
Extract wage information from the worker's description below.

Return ONLY valid JSON — no text, no explanation:
{{
  "employer_name": "<string or empty>",
  "regular_hours": <number or 0>,
  "overtime_hours": <number or 0>,
  "hourly_rate": <number or 0.0>,
  "state": "<TX|CA|NY|FL|IL>",
  "deductions": [
    {{"name": "<name>", "amount": <number>}}
  ]
}}

Rules:
- regular_hours = total hours worked (include overtime in total)
- overtime_hours = hours SHOWN as overtime on paystub (often 0)
- state: must be TX, CA, NY, FL, or IL only — guess from context
- deductions: list any money taken out of pay
- employer_name: company name if mentioned, else empty string
- If not mentioned, use 0 or empty string

Worker description:
{text}

JSON:"""