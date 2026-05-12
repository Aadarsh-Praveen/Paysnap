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

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
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
    Returns extracted fields for worker to verify.
    """
    try:
        # Save uploaded file to temp location
        suffix = os.path.splitext(file.filename)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        # Extract using existing pipeline
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
    deductions: str = Form(""),  # JSON string
):
    """
    Analyze paystub data for violations.
    Returns Spanish explanation + math breakdown + legal aid.
    """
    try:
        import json

        # Parse deductions
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

        use_state = state if state in ["TX", "CA", "NY", "FL", "IL"] else "TX"
        report = engine.analyze(paystub, use_state)
        explanation = gemma.generate_spanish_explanation(report)
        vault.save_record(paystub, report)

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
                "illegal_deductions": [
                    {
                        "name": r.deduction.name,
                        "amount": r.deduction.amount,
                        "reason_es": r.reason_es,
                        "statute": r.statute
                    }
                    for r in report.illegal_deductions
                ],
                "legal_aid": report.legal_aid_contacts[:2]
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
    """Generates formal English demand letter."""
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
def get_history():
    """Returns paystub analysis history."""
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
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/export")
def export_evidence():
    """Exports evidence vault as downloadable text file."""
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