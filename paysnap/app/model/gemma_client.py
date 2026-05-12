"""
gemma_client.py
Lazy-loads Ollama connection — only connects when first needed.
This prevents the UI from freezing on startup.
"""

import json
import base64
import requests
from pathlib import Path
from typing import Optional
import yaml

from app.model.prompts import (
    EXTRACTION_FROM_TEXT_PROMPT,
    EXTRACTION_FROM_IMAGE_PROMPT,
    EXPLANATION_PROMPT_ES,
    FOLLOWUP_PROMPT_ES,
)
from app.core.input_handler import PaystubData, DeductionItem

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "app_config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

OLLAMA_BASE = CONFIG["ollama"]["base_url"]
VISION_MODEL = CONFIG["ollama"]["vision_model"]
TEXT_MODEL = CONFIG["ollama"]["text_model"]
TIMEOUT = CONFIG["ollama"]["timeout_seconds"]
MAX_TOKENS = CONFIG["ollama"]["max_tokens"]


class GemmaClient:
    def __init__(self):
        # DO NOT connect to Ollama here
        # Lazy load — only connect when first API call is made
        self._ollama_checked = False

    def _ensure_ollama(self):
        """Check Ollama only when first needed — not on startup."""
        if self._ollama_checked:
            return
        try:
            resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
            if resp.status_code == 200:
                print("Ollama connected")
        except requests.exceptions.ConnectionError:
            print("WARNING: Ollama not running. Start with: ollama serve")
        self._ollama_checked = True

    def extract_paystub_fields(self, raw_text: str) -> PaystubData:
        self._ensure_ollama()
        prompt = EXTRACTION_FROM_TEXT_PROMPT.format(text=raw_text)
        response = self._call_text(prompt)
        return self._parse_extraction(response)

    def extract_paystub_from_image(self, image_path: str, ocr_text: str = "") -> PaystubData:
        self._ensure_ollama()
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        prompt = EXTRACTION_FROM_IMAGE_PROMPT.format(ocr_hint=ocr_text)
        response = self._call_vision(prompt, image_b64)
        return self._parse_extraction(response)

    def generate_spanish_explanation(self, violation_report) -> str:
        self._ensure_ollama()
        report_json = self._serialize_report(violation_report)
        prompt = EXPLANATION_PROMPT_ES.format(
            report_json=report_json,
            state=violation_report.state
        )
        return self._call_text(prompt)

    def answer_followup(self, question: str, context: str) -> str:
        self._ensure_ollama()
        prompt = FOLLOWUP_PROMPT_ES.format(question=question, context=context)
        return self._call_text(prompt)

    def _parse_extraction(self, response_text: str) -> PaystubData:
        try:
            clean = response_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            data = json.loads(clean)
            deductions = []
            for d in data.get("deductions", []):
                if isinstance(d, dict):
                    deductions.append(DeductionItem(
                        name=str(d.get("name", "Unknown")),
                        amount=float(d.get("amount", 0)),
                        raw_text=str(d.get("raw_text", ""))
                    ))

            return PaystubData(
                regular_hours=self._safe_float(data.get("regular_hours")),
                overtime_hours=self._safe_float(data.get("overtime_hours")),
                total_hours=self._safe_float(data.get("total_hours")),
                hourly_rate=self._safe_float(data.get("hourly_rate")),
                overtime_rate=self._safe_float(data.get("overtime_rate")),
                gross_pay=self._safe_float(data.get("gross_pay")),
                net_pay=self._safe_float(data.get("net_pay")),
                deductions=deductions,
                employer_name=data.get("employer_name"),
                pay_period_start=data.get("pay_period_start"),
                pay_period_end=data.get("pay_period_end"),
                state=data.get("state"),
                confidence=0.85,
                needs_review=True
            )
        except Exception as e:
            print(f"Parse error: {e}")
            return PaystubData(confidence=0.3, needs_review=True)

    def _call_text(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": TEXT_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": MAX_TOKENS,
                        "temperature": 0.1
                    }
                },
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            print(f"Text model error: {e}")
            return "No pudimos procesar. Llama al 1-866-487-9243"

    def _call_vision(self, prompt: str, image_b64: str) -> str:
        try:
            resp = requests.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": VISION_MODEL,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {
                        "num_predict": MAX_TOKENS,
                        "temperature": 0.1
                    }
                },
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            print(f"Vision model error: {e}")
            return "{}"

    def _serialize_report(self, report) -> str:
        data = {
            "state": report.state,
            "has_violation": report.has_any_violation,
            "total_owed": report.total_money_owed,
            "overtime": {
                "has_violation": report.overtime.has_violation,
                "ot_hours_owed": report.overtime.ot_hours_owed,
                "ot_pay_owed": report.overtime.ot_pay_owed,
                "statute": report.overtime.statute,
                "statute_es": report.overtime.statute_description_es,
                "breakdown": report.overtime.calculation_breakdown
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
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _safe_float(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except:
            return None