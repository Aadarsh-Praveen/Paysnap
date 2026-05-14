"""
gemma_client.py
Lazy-loads Ollama connection — only connects when first needed.
Supports 11 languages natively via Gemma 4.
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
    MULTILINGUAL_EXPLANATION_PROMPT,
    LANGUAGE_INSTRUCTIONS,
    LEGAL_AID_PHRASES,
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

    # ─────────────────────────────────────────────
    # EXTRACTION METHODS
    # These read paystub documents
    # Same regardless of language
    # ─────────────────────────────────────────────

    def extract_paystub_fields(self, raw_text: str) -> PaystubData:
        """Extract fields from raw text (PDF/Word)."""
        self._ensure_ollama()
        prompt = EXTRACTION_FROM_TEXT_PROMPT.format(text=raw_text)
        response = self._call_text(prompt)
        return self._parse_extraction(response)

    def extract_paystub_from_image(
        self,
        image_path: str,
        ocr_text: str = ""
    ) -> PaystubData:
        """Extract fields from paystub photo using Gemma 4 vision."""
        self._ensure_ollama()
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        prompt = EXTRACTION_FROM_IMAGE_PROMPT.format(ocr_hint=ocr_text)
        response = self._call_vision(prompt, image_b64)
        return self._parse_extraction(response)

    # ─────────────────────────────────────────────
    # EXPLANATION METHODS
    # These generate output in the worker's language
    # Gemma 4 natively speaks all 11 languages
    # The math and law never change — only the language
    # ─────────────────────────────────────────────

    def generate_explanation(
        self,
        violation_report,
        language: str = "es"
    ) -> str:
        """
        Generates violation explanation in the worker's language.

        Supported languages:
        es=Spanish, zh=Mandarin, pt=Portuguese, ht=Haitian Creole,
        vi=Vietnamese, ko=Korean, tl=Filipino, hi=Hindi,
        ar=Arabic, ru=Russian, en=English

        The math and statute citations are always the same.
        Only the explanation language changes.
        """
        self._ensure_ollama()

        # Get language-specific instructions
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(
            language,
            LANGUAGE_INSTRUCTIONS["es"]  # Default to Spanish
        )

        legal_aid_phrase = LEGAL_AID_PHRASES.get(
            language,
            LEGAL_AID_PHRASES["es"]
        )

        # Serialize the violation report
        report_json = self._serialize_report(violation_report)

        # Build the multilingual prompt
        prompt = MULTILINGUAL_EXPLANATION_PROMPT.format(
            language_instruction=lang_instruction,
            state=violation_report.state,
            language_code=language,
            report_json=report_json,
            legal_aid_phrase=legal_aid_phrase
        )

        return self._call_text(prompt)

    def generate_spanish_explanation(self, violation_report) -> str:
        """
        Backward compatible method.
        Calls generate_explanation with Spanish.
        Used by existing code that hasn't been updated yet.
        """
        return self.generate_explanation(violation_report, language="es")

    def answer_followup(
        self,
        question: str,
        context: str,
        language: str = "es"
    ) -> str:
        """Answer worker follow-up questions in their language."""
        self._ensure_ollama()

        # Build language-aware followup prompt
        lang_instruction = LANGUAGE_INSTRUCTIONS.get(
            language,
            LANGUAGE_INSTRUCTIONS["es"]
        )

        prompt = (
            f"You are PaySnap, a payroll assistant.\n\n"
            f"Language instruction: {lang_instruction}\n\n"
            f"Previous analysis context:\n{context}\n\n"
            f"Worker question: {question}\n\n"
            f"Answer in the requested language. "
            f"If asked about legal action, recommend calling "
            f"1-866-487-9243. Do not invent legal information.\n\n"
            f"Answer:"
        )

        return self._call_text(prompt)

    # ─────────────────────────────────────────────
    # INTERNAL METHODS
    # ─────────────────────────────────────────────

    def _parse_extraction(self, response_text: str) -> PaystubData:
        """Parse Gemma's JSON extraction response into PaystubData."""
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
        """Call Ollama text model. Returns response string."""
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
        """Call Ollama vision model with image."""
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
        """
        Converts violation report to JSON for prompts.
        Language-neutral — always serializes in English keys.
        The explanation method handles language translation.
        """
        data = {
            "state": report.state,
            "has_violation": report.has_any_violation,
            "total_owed": report.total_money_owed,
            "overtime": {
                "has_violation": report.overtime.has_violation,
                "ot_hours_owed": report.overtime.ot_hours_owed,
                "ot_pay_owed": report.overtime.ot_pay_owed,
                "statute": report.overtime.statute,
                "statute_description": report.overtime.statute_description_en,
                "breakdown": report.overtime.calculation_breakdown
            },
            "illegal_deductions": [
                {
                    "name": r.deduction.name,
                    "amount": r.deduction.amount,
                    "reason": r.reason_en,
                    "statute": r.statute
                }
                for r in report.illegal_deductions
            ],
            "suspicious_deductions": [
                {
                    "name": r.deduction.name,
                    "amount": r.deduction.amount,
                    "requires_consent": r.requires_written_consent
                }
                for r in report.suspicious_deductions
            ],
            "legal_aid": report.legal_aid_contacts[:2]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except:
            return None