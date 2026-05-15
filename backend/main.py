"""
backend/main.py
FastAPI server for PaySnap.
Uses our fine-tuned Gemma 4 via Ollama (local, offline).
Run: uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import shutil
import tempfile
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.input_handler import InputHandler, PaystubData, DeductionItem
from app.analysis.violation_engine import ViolationEngine
from app.model.gemma_client import GemmaClient
from app.output.evidence_vault import EvidenceVault

app = FastAPI(title="PaySnap API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

handler = InputHandler()
engine  = ViolationEngine()
gemma   = GemmaClient()
vault   = EvidenceVault()

# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "app": "PaySnap", "model": "paysnap (fine-tuned Gemma 4)"}


# ─────────────────────────────────────────────
# EXTRACT FROM FILE (image/PDF)
# Gemma 4 vision reads the paystub
# ─────────────────────────────────────────────

@app.post("/extract")
async def extract_from_file(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        extracted = handler.handle(tmp.name)
        os.unlink(tmp.name)

        return {
            "success": True,
            "data": {
                "employer_name":  extracted.employer_name or "",
                "regular_hours":  float(extracted.regular_hours  or 0),
                "overtime_hours": float(extracted.overtime_hours or 0),
                "hourly_rate":    float(extracted.hourly_rate    or 0),
                "gross_pay":      float(extracted.gross_pay      or 0),
                "state":          extracted.state or "TX",
                "deductions": [
                    {"name": d.name, "amount": d.amount}
                    for d in extracted.deductions
                ],
                "confidence": extracted.confidence
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})


# ─────────────────────────────────────────────
# EXTRACT FROM TEXT / VOICE
# Gemma 4 understands natural language in any language
# ─────────────────────────────────────────────

@app.post("/extract-text")
async def extract_from_text(text: str = Form(...)):
    try:
        prompt = f"""Extract paystub data from this worker description.
Return ONLY valid JSON, nothing else:
{{
  "employer_name": "",
  "regular_hours": 0,
  "overtime_hours": 0,
  "hourly_rate": 0.0,
  "state": "TX",
  "deductions": []
}}

Rules:
- regular_hours = total hours worked if no overtime mentioned separately
- state: must be one of TX, CA, NY, FL, IL only
- deductions format: [{{"name": "TOOLS", "amount": 75.0}}]
- employer_name: extract company name if mentioned, else empty string
- If a field is not mentioned, use 0 or empty string
- Do NOT include any text outside the JSON

Worker description: {text}

JSON:"""

        result = gemma._call_text(prompt)
        clean  = result.strip()

        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()

        start = clean.find("{")
        end   = clean.rfind("}") + 1

        if start >= 0 and end > start:
            data = json.loads(clean[start:end])
            return {
                "success": True,
                "data": {
                    "employer_name":  str(data.get("employer_name", "")),
                    "regular_hours":  float(data.get("regular_hours", 0)),
                    "overtime_hours": float(data.get("overtime_hours", 0)),
                    "hourly_rate":    float(data.get("hourly_rate", 0)),
                    "state":          str(data.get("state", "TX")),
                    "deductions":     data.get("deductions", []),
                }
            }
        return {"success": False, "error": "Could not parse response"}

    except Exception as e:
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})


# ─────────────────────────────────────────────
# ANALYZE PAYSTUB
# Math is deterministic — Gemma only explains
# ─────────────────────────────────────────────

@app.post("/analyze")
async def analyze_paystub(
    employer:       str   = Form(""),
    regular_hours:  float = Form(0),
    overtime_hours: float = Form(0),
    hourly_rate:    float = Form(0),
    state:          str   = Form("TX"),
    deductions:     str   = Form(""),
    language:       str   = Form("en"),
):
    try:
        # Parse deductions
        ded_list = []
        if deductions:
            try:
                for d in json.loads(deductions):
                    ded_list.append(DeductionItem(
                        name=d["name"], amount=float(d["amount"])
                    ))
            except:
                pass

        paystub = PaystubData(
            employer_name=employer or "Unknown",
            regular_hours=regular_hours,
            overtime_hours=overtime_hours,
            total_hours=regular_hours + overtime_hours,
            hourly_rate=hourly_rate,
            gross_pay=regular_hours * hourly_rate,
            deductions=ded_list,
            state=state
        )

        use_state = state if state in ["TX","CA","NY","FL","IL"] else "TX"
        report = engine.analyze(paystub, use_state)

        # Gemma 4 explains in worker's language
        explanation = gemma.generate_explanation(report, language=language)

        vault.save_record(paystub, report)

        # Build illegal deductions — translate reason to worker's language
        illegal_deds = []
        for r in report.illegal_deductions:
            reason = r.reason_es
            if language not in ["es", "en"]:
                try:
                    reason = gemma._call_text(
                        f"Translate this sentence to {language}. "
                        f"Return ONLY the translated sentence:\n{r.reason_es}"
                    )
                except:
                    pass
            illegal_deds.append({
                "name":    r.deduction.name,
                "amount":  r.deduction.amount,
                "reason_es": reason,
                "statute": r.statute
            })

        # Build legal aid — translate note to worker's language
        legal_aid_note = "Free · Bilingual · Regardless of immigration status"
        if language not in ["es", "en"]:
            try:
                legal_aid_note = gemma._call_text(
                    f"Translate this phrase to {language}. "
                    f"Return ONLY the translation:\n"
                    f"Free, bilingual, regardless of immigration status"
                )
            except:
                pass

        legal_aid = []
        for c in report.legal_aid_contacts[:2]:
            contact = dict(c)
            # Use English name for all languages
            if contact.get("organization_name_en"):
                contact["organization_name_es"] = contact["organization_name_en"]
            elif contact.get("organization_name"):
                contact["organization_name_es"] = contact["organization_name"]
            contact["phone_note_es"] = legal_aid_note
            legal_aid.append(contact)

        return {
            "success": True,
            "data": {
                "has_violation":      report.has_any_violation,
                "total_money_owed":   report.total_money_owed,
                "explanation_es":     explanation,
                "breakdown":          report.overtime.calculation_breakdown,
                "statute":            report.overtime.statute,
                "overtime": {
                    "has_violation":  report.overtime.has_violation,
                    "ot_hours_owed":  report.overtime.ot_hours_owed,
                    "ot_pay_owed":    report.overtime.ot_pay_owed,
                },
                "illegal_deductions": illegal_deds,
                "legal_aid":          legal_aid,
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})


# ─────────────────────────────────────────────
# DEMAND LETTER
# Always in English — legal document for employer
# ─────────────────────────────────────────────

@app.post("/demand-letter")
async def generate_demand_letter(
    employer:       str   = Form(""),
    regular_hours:  float = Form(0),
    overtime_hours: float = Form(0),
    hourly_rate:    float = Form(0),
    state:          str   = Form("TX"),
    deductions:     str   = Form(""),
    total_owed:     float = Form(0),
    breakdown:      str   = Form(""),
    statute:        str   = Form("FLSA 29 USC 207(a)(1)")
):
    try:
        prompt = f"""Write a professional wage claim demand letter in English.

Employer: {employer}
State: {state}
Hours worked: {regular_hours + overtime_hours}
Hourly rate: ${hourly_rate:.2f}
Amount owed: ${total_owed:.2f}
Statute violated: {statute}

Math proof:
{breakdown}

Write a complete formal demand letter that:
1. Has [DATE] at top for worker to fill in
2. States the violation clearly with exact statute
3. Shows the exact math calculation
4. Demands payment within 10 business days
5. States DOL complaint will follow if ignored
6. Has space for worker name and signature
7. Is professional and factual

Letter:"""

        letter = gemma._call_text(prompt)
        return {"success": True, "data": {"letter": letter}}

    except Exception as e:
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})


# ─────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────

@app.get("/history")
def get_history(language: str = "en"):
    try:
        records = vault.get_all()
        summary = vault.get_summary()
        return {
            "success": True,
            "data": {
                "records": records[:20],
                "summary": summary
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

@app.get("/export")
def export_evidence():
    try:
        text = vault.export_text()
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False,
            encoding="utf-8", prefix="paysnap_evidence_"
        )
        tmp.write(text)
        tmp.close()
        return FileResponse(
            tmp.name,
            media_type="text/plain",
            filename="paysnap_evidence.txt"
        )
    except Exception as e:
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})


# ─────────────────────────────────────────────
# TRANSLATE UI
# Gemma 4 translates all UI strings
# Batched to avoid timeout
# ─────────────────────────────────────────────

@app.post("/translate-ui")
async def translate_ui(
    language:      str = Form("es"),
    language_name: str = Form("Spanish")
):
    try:
        all_strings = {
            # Core
            "tagline":    "Your paystub. Your rights. On your phone.",
            "disclaimer": "PaySnap helps you understand your paystub. Not legal advice. Your data never leaves your device.",
            "tab_analyze": "Analyze",
            "tab_history": "History",
            "tab_rights":  "Rights",
            "step1": "Step 1",
            "step2": "Step 2",
            "step3": "Step 3",

            # Input options — Ask PaySnap screen
            "ask_paysnap":  "Ask PaySnap",
            "ask_sub":      "Upload, speak, or type — Gemma 4 does the rest",
            "speak_title":  "Speak your situation",
            "speak_sub":    "Talk in Hindi, Spanish, or any language",
            "describe_title": "Describe your situation",
            "describe_sub":   "I worked 52 hours at $23 per hour in Texas",
            "describe_hint":  "Type in your language. Gemma 4 extracts details automatically.",
            "describe_placeholder": "I worked 52 hours this week in Texas at $23 per hour",
            "describe_btn": "Let Gemma 4 Analyze",
            "manual_title": "Fill form manually",
            "manual_sub":   "Enter hours, rate, and deductions directly",

            # Navigation
            "back":          "Back",
            "change_input":  "Change Input Method",
            "example":       "Example",
            "analyze_another": "Analyze Another Paystub",

            # Voice screen
            "listening":      "Listening, tap to stop",
            "tap_mic":        "Tap microphone to speak",
            "transcript":     "TRANSCRIPT",
            "start_speaking": "Start Speaking",
            "use_this":       "Use This",
            "stop_analyze":   "Stop and Analyze",

            # Upload
            "upload_title":   "Upload Paystub",
            "upload_sub":     "Photo, PDF, or image — Gemma 4 reads it automatically",
            "upload_tap":     "Tap here to upload your paystub",
            "upload_formats": "Photo, PDF, Word, Excel",
            "upload_change":  "Tap to change",
            "upload_success": "Data extracted! Please verify below.",
            "upload_error":   "Could not read file. Please fill manually.",
            "read_btn":       "Read paystub automatically",
            "reading":        "Reading with Gemma 4...",

            # Form
            "form_title":        "Verify or enter your data",
            "form_sub":          "If you uploaded a file, check the data is correct",
            "employer_label":    "Employer name",
            "employer_placeholder": "ABC Construction LLC",
            "reg_hours":         "Regular hours",
            "ot_hours":          "Overtime hours on stub",
            "rate":              "Hourly rate",
            "state_label":       "State",
            "deductions_label":  "Paystub deductions",
            "ded_placeholder":   "e.g. TOOLS",
            "amount_placeholder":"75.00",
            "analyze_btn":       "Analyze my paystub",
            "analyzing":         "Analyzing with Gemma 4...",

            # Results
            "violation_found":    "potentially owed",
            "no_violation":       "No issues detected in this paystub",
            "explanation_title":  "Explanation",
            "math_title":         "Math breakdown",
            "illegal_ded_title":  "Illegal deductions detected",
            "legal_aid_title":    "Free legal help",
            "legal_aid_note":     "Free, bilingual, regardless of immigration status",
            "letter_title":       "Demand letter",
            "letter_btn":         "Generate formal letter to employer",
            "letter_loading":     "Generating letter...",

            # History
            "history_title":   "Your paystub history",
            "history_sub":     "Saved locally on your device, encrypted",
            "history_summary": "{count} paystubs analyzed, {violations} violations found, {total} total potential",
            "refresh_btn":     "Refresh",
            "export_btn":      "Export for attorney",
            "no_history":      "No paystubs analyzed yet. Upload your first paystub to begin.",

            # Rights
            "rights_title":  "Your Rights",
            "rights_sub":    "Regardless of immigration status",
            "wages_title":   "Minimum wages 2025",
            "report_title":  "Report a violation",
            "report_free":   "Free, bilingual, regardless of immigration status",
            "privacy_title": "Your privacy in PaySnap",
            "privacy_1":     "Zero cloud data, everything on your device",
            "privacy_2":     "No account or password required",
            "privacy_3":     "No telemetry or tracking",
            "privacy_4":     "History encrypted locally",
            "right_1_title": "Minimum wage",
            "right_1_desc":  "Your employer MUST pay at least the state minimum wage",
            "right_2_title": "Overtime",
            "right_2_desc":  "Over 40 hours per week equals 1.5 times your regular rate",
            "right_3_title": "No retaliation",
            "right_3_desc":  "Illegal to fire you for reporting wage violations",
            "right_4_title": "Federal FLSA Law",
            "right_4_desc":  "Protects all workers in the United States",
        }

        def batch_dict(d, size=10):
            items = list(d.items())
            return [dict(items[i:i+size]) for i in range(0, len(items), size)]

        def normalize_keys(result: dict, original_batch: dict) -> dict:
            normalized = {}
            result_lower = {k.lower().strip(): v for k, v in result.items()}
            for orig_key in original_batch.keys():
                if orig_key in result:
                    normalized[orig_key] = result[orig_key]
                elif orig_key.lower() in result_lower:
                    normalized[orig_key] = result_lower[orig_key.lower()]
                else:
                    orig_clean = orig_key.replace("_", " ").lower()
                    found = False
                    for rk, rv in result.items():
                        if rk.replace("_", " ").lower() == orig_clean:
                            normalized[orig_key] = rv
                            found = True
                            break
                    if not found:
                        normalized[orig_key] = original_batch[orig_key]
                        print(f"  Key not found: {orig_key} — keeping English")
            return normalized

        def translate_batch(batch: dict) -> dict:
            batch_json = json.dumps(batch, ensure_ascii=False, indent=2)
            prompt = f"""You are a professional translator. Translate the JSON values below into {language_name}.

RULES — follow exactly:
1. Return ONLY a valid JSON object, nothing else
2. Keep ALL keys exactly as they are — never change key names
3. Translate only the string values
4. Keep unchanged in values: PaySnap, Gemma 4, FLSA, PDF, Word, Excel, DOL
5. Keep $ signs and numbers unchanged
6. No markdown, no explanation, no extra text
7. Output must be parseable by json.loads()

Input:
{batch_json}

{language_name} translation:"""

            response = gemma._call_text(prompt)
            clean = response.strip()

            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            start = clean.find("{")
            end   = clean.rfind("}") + 1
            if start >= 0 and end > start:
                clean = clean[start:end]

            result = json.loads(clean)
            return normalize_keys(result, batch)

        batches    = batch_dict(all_strings, size=10)
        translated = {}

        for i, batch in enumerate(batches):
            print(f"Translating batch {i+1}/{len(batches)} to {language_name}...")
            try:
                result = translate_batch(batch)
                translated.update(result)
                print(f"  ✅ {len(result)} keys translated")
            except Exception as batch_err:
                print(f"  ❌ Batch {i+1} failed: {batch_err} — using English")
                translated.update(batch)

        print(f"✅ Translation complete: {len(translated)} strings")

        return {
            "success": True,
            "data": {
                "translations":  translated,
                "language":      language,
                "language_name": language_name,
            }
        }

    except Exception as e:
        print(f"Translation error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500,
            content={"success": False, "error": str(e)})