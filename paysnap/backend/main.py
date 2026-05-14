"""
backend/main.py
FastAPI server — replaces Gradio entirely.
All existing Python logic stays the same.
Run: uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import shutil
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.input_handler import InputHandler, PaystubData, DeductionItem
from app.analysis.violation_engine import ViolationEngine
from app.model.gemma_client import GemmaClient
from app.output.evidence_vault import EvidenceVault

app = FastAPI(title="PaySnap API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

handler = InputHandler()
engine = ViolationEngine()
gemma = GemmaClient()
vault = EvidenceVault()


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "app": "PaySnap"}


@app.post("/extract")
async def extract_from_file(file: UploadFile = File(...)):
    """
    Upload a paystub file (photo/PDF/Word/Excel).
    Gemma 4 reads it and returns extracted fields.
    Worker verifies before analysis runs.
    """
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
                "employer_name": extracted.employer_name or "",
                "regular_hours": float(extracted.regular_hours or 0),
                "overtime_hours": float(extracted.overtime_hours or 0),
                "hourly_rate": float(extracted.hourly_rate or 0),
                "gross_pay": float(extracted.gross_pay or 0),
                "state": extracted.state or "TX",
                "deductions": [
                    {"name": d.name, "amount": d.amount}
                    for d in extracted.deductions
                ],
                "confidence": extracted.confidence
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/analyze")
async def analyze_paystub(
    employer: str = Form(""),
    regular_hours: float = Form(0),
    overtime_hours: float = Form(0),
    hourly_rate: float = Form(0),
    state: str = Form("TX"),
    deductions: str = Form(""),
    language: str = Form("es"),
):
    """
    Analyze paystub data for violations.
    Returns explanation in worker's language + math breakdown + legal aid.
    The math is always deterministic — Gemma only explains, never decides.
    """
    try:
        import json

        # Parse deductions from JSON string
        ded_list = []
        if deductions:
            try:
                ded_data = json.loads(deductions)
                for d in ded_data:
                    ded_list.append(DeductionItem(
                        name=d["name"],
                        amount=float(d["amount"])
                    ))
            except:
                pass

        # Build paystub from worker-confirmed data
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

        # Run deterministic analysis
        use_state = state if state in ["TX", "CA", "NY", "FL", "IL"] else "TX"
        report = engine.analyze(paystub, use_state)

        # Generate explanation in worker's language via Gemma 4
        explanation = gemma.generate_explanation(report, language=language)

        # Save to encrypted local vault
        vault.save_record(paystub, report)

        # Build illegal deductions list
        # Translate reason if not Spanish
        illegal_deds = []
        for r in report.illegal_deductions:
            reason = r.reason_es
            if language not in ["es", "en"]:
                try:
                    reason = gemma._call_text(
                        f"Translate this one sentence to {language}. "
                        f"Return only the translated sentence, nothing else: "
                        f"{r.reason_es}"
                    )
                except:
                    pass  # Keep Spanish if translation fails
            illegal_deds.append({
                "name": r.deduction.name,
                "amount": r.deduction.amount,
                "reason_es": reason,
                "statute": r.statute
            })

        # Translate legal aid phone notes if not Spanish
        legal_aid = []
        for c in report.legal_aid_contacts[:2]:
            contact = dict(c)
            if language != "es":
                # Use English organization name for non-Spanish languages
                if contact.get("organization_name_en"):
                    contact["organization_name_es"] = contact["organization_name_en"]
                elif contact.get("organization_name"):
                    contact["organization_name_es"] = contact["organization_name"]
                # Use English phone note
                if contact.get("phone_note_en"):
                    contact["phone_note_es"] = contact["phone_note_en"]
            legal_aid.append(contact)

        return {
            "success": True,
            "data": {
                "has_violation": report.has_any_violation,
                "total_money_owed": report.total_money_owed,
                "explanation_es": explanation,
                "breakdown": report.overtime.calculation_breakdown,
                "statute": report.overtime.statute,
                "overtime": {
                    "has_violation": report.overtime.has_violation,
                    "ot_hours_owed": report.overtime.ot_hours_owed,
                    "ot_pay_owed": report.overtime.ot_pay_owed,
                },
                "illegal_deductions": illegal_deds,
                "legal_aid": legal_aid
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/demand-letter")
async def generate_demand_letter(
    employer: str = Form(""),
    regular_hours: float = Form(0),
    overtime_hours: float = Form(0),
    hourly_rate: float = Form(0),
    state: str = Form("TX"),
    deductions: str = Form(""),
    total_owed: float = Form(0),
    breakdown: str = Form(""),
    statute: str = Form("FLSA 29 USC 207(a)(1)")
):
    """
    Generates formal English demand letter.
    Always in English — this is a legal document for the employer.
    """
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
2. States the violation clearly with statute
3. Shows the exact math
4. Demands payment within 10 business days
5. States DOL complaint will follow if ignored
6. Has space for worker name and signature
7. Is professional and factual

Letter:"""

        letter = gemma._call_text(prompt)

        return {
            "success": True,
            "data": {"letter": letter}
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/history")
def get_history(language: str = "es"):
    try:
        records = vault.get_all()
        summary = vault.get_summary()

        if language not in ["es", "en"] and summary.get("message_es"):
            try:
                summary["message_es"] = gemma._call_text(
                    f"Translate this one sentence to {language}. "
                    f"Return only the translated sentence, nothing else: "
                    f"{summary['message_es']}"
                )
            except:
                pass

        return {
            "success": True,
            "data": {
                "records": records[:20],
                "summary": summary
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/export")
def export_evidence():
    """Exports evidence vault as downloadable text file for legal aid."""
    try:
        text = vault.export_text()
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False,
            encoding="utf-8", prefix="paysnap_evidencia_"
        )
        tmp.write(text)
        tmp.close()
        return FileResponse(
            tmp.name,
            media_type="text/plain",
            filename="paysnap_evidencia.txt"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/translate-ui")
async def translate_ui(
    language: str = Form("es"),
    language_name: str = Form("Spanish")
):
    """
    Translates all UI strings into requested language.
    Splits into batches of 10 to avoid Ollama timeout.
    Keys are normalized to match exactly what frontend expects.
    Adding a new language requires zero changes here.
    """
    try:
        import json

        all_strings = {
            "tagline": "Your paystub. Your rights. On your phone.",
            "disclaimer": "PaySnap helps you understand your paystub. Not legal advice. Your data never leaves your device.",
            "tab_analyze": "Analyze",
            "tab_history": "History",
            "tab_rights": "Rights",
            "step1": "Step 1",
            "step2": "Step 2",
            "step3": "Step 3",
            "upload_title": "Upload your paystub",
            "upload_sub": "Accepts photo, PDF, Word or Excel",
            "upload_tap": "Tap here to upload your paystub",
            "upload_formats": "Photo · PDF · Word · Excel",
            "upload_change": "Tap to change",
            "read_btn": "Read paystub automatically",
            "reading": "Reading with Gemma 4...",
            "form_title": "Verify or enter your data",
            "form_sub": "If you uploaded a file check the data is correct",
            "employer_label": "Employer name",
            "employer_placeholder": "ABC Construction LLC",
            "reg_hours": "Regular hours",
            "ot_hours": "Overtime hours on stub",
            "rate": "Hourly rate ($)",
            "state_label": "State",
            "deductions_label": "Paystub deductions",
            "ded_placeholder": "e.g. TOOLS",
            "amount_placeholder": "75.00",
            "analyze_btn": "Analyze my paystub",
            "analyzing": "Analyzing with Gemma 4...",
            "violation_found": "potentially owed",
            "no_violation": "No issues detected in this paystub",
            "explanation_title": "Explanation",
            "math_title": "Math breakdown",
            "illegal_ded_title": "Illegal deductions detected",
            "legal_aid_title": "Free legal help",
            "letter_title": "Demand letter",
            "letter_btn": "Generate formal letter to employer",
            "letter_loading": "Generating letter...",
            "history_title": "Your paystub history",
            "history_sub": "Saved locally on your device encrypted",
            "refresh_btn": "Refresh",
            "export_btn": "Export for attorney",
            "no_history": "No paystubs analyzed yet. Upload your first paystub to begin.",
            "rights_title": "Your Rights",
            "rights_sub": "Regardless of immigration status:",
            "wages_title": "Minimum wages 2025",
            "report_title": "Report a violation",
            "report_free": "Free Bilingual Regardless of immigration status",
            "privacy_title": "Your privacy in PaySnap",
            "privacy_1": "Zero cloud data everything on your device",
            "privacy_2": "No account or password required",
            "privacy_3": "No telemetry or tracking",
            "privacy_4": "History encrypted locally",
            "right_1_title": "Minimum wage",
            "right_1_desc": "Your employer MUST pay at least the state minimum wage",
            "right_2_title": "Overtime",
            "right_2_desc": "Over 40 hours per week equals 1.5x your regular rate",
            "right_3_title": "No retaliation",
            "right_3_desc": "Illegal to fire you for reporting wage violations",
            "right_4_title": "Federal FLSA Law",
            "right_4_desc": "Protects all workers in the United States",
        }

        def batch_dict(d, size=10):
            items = list(d.items())
            return [dict(items[i:i+size]) for i in range(0, len(items), size)]

        def normalize_keys(result: dict, original_batch: dict) -> dict:
            """
            Forces returned keys to match original keys exactly.
            Gemma sometimes changes casing, adds spaces, or renames keys.
            """
            normalized = {}
            result_lower = {k.lower().strip(): v for k, v in result.items()}

            for orig_key in original_batch.keys():
                if orig_key in result:
                    normalized[orig_key] = result[orig_key]
                elif orig_key.lower() in result_lower:
                    normalized[orig_key] = result_lower[orig_key.lower()]
                else:
                    orig_no_underscore = orig_key.replace("_", " ").lower()
                    found = False
                    for rk, rv in result.items():
                        if rk.replace("_", " ").lower() == orig_no_underscore:
                            normalized[orig_key] = rv
                            found = True
                            break
                    if not found:
                        normalized[orig_key] = original_batch[orig_key]
                        print(f"  Key not found: {orig_key} — using English")

            return normalized

        def translate_batch(batch: dict) -> dict:
            batch_json = json.dumps(batch, ensure_ascii=False, indent=2)

            prompt = f"""You are a translator. Translate the JSON values below into {language_name} ({language}).

CRITICAL RULES:
1. Return ONLY a valid JSON object
2. Keep ALL keys EXACTLY as they appear — do not change key names at all
3. Only translate the string values
4. Keep these words exactly as-is in values: PaySnap, Gemma 4, FLSA, PDF, Word, Excel
5. Keep $ signs and numbers unchanged
6. Do not add any explanation, markdown, or extra text
7. The output must be valid JSON that can be parsed with json.loads()

Input JSON:
{batch_json}

Output (translated JSON only):"""

            response = gemma._call_text(prompt)

            clean = response.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start >= 0 and end > start:
                clean = clean[start:end]

            result = json.loads(clean)
            return normalize_keys(result, batch)

        # Translate in batches
        batches = batch_dict(all_strings, size=10)
        translated = {}

        for i, batch in enumerate(batches):
            print(f"Translating batch {i+1}/{len(batches)} to {language_name}...")
            try:
                result = translate_batch(batch)
                print(f"  Keys: {list(result.keys())}")
                print(f"  Sample: {list(result.items())[:2]}")
                translated.update(result)
            except Exception as batch_error:
                print(f"  Batch {i+1} failed: {batch_error} — using English")
                translated.update(batch)

        print(f"Translation complete: {len(translated)} strings")
        print(f"Sample: {dict(list(translated.items())[:3])}")

        return {
            "success": True,
            "data": {
                "translations": translated,
                "language": language,
                "language_name": language_name
            }
        }

    except Exception as e:
        print(f"Translation error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )