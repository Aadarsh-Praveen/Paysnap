"""
app/model/gemma_client.py
Hybrid client:
  TEXT:   Ollama (port 11434) → our fine-tuned paysnap model
  VISION: llama.cpp (port 8080) → same model + mmproj (fixes NVIDIA CUDA bug)
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
)
from app.core.input_handler import PaystubData, DeductionItem

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "app_config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

OLLAMA_BASE  = CONFIG["ollama"]["base_url"]
TEXT_MODEL   = CONFIG["ollama"]["text_model"]
TIMEOUT      = CONFIG["ollama"]["timeout_seconds"]
MAX_TOKENS   = CONFIG["ollama"]["max_tokens"]

# llama.cpp vision server (fixes Gemma 4 CUDA vision bug on NVIDIA)
LLAMA_BASE = "http://127.0.0.1:8080"


class GemmaClient:
    def __init__(self):
        self._ollama_checked = False

    def _ensure_ollama(self):
        if self._ollama_checked:
            return
        try:
            resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
            if resp.status_code == 200:
                print("Ollama connected")
        except:
            print("WARNING: Ollama not running")
        self._ollama_checked = True

    # ─── PUBLIC METHODS ───────────────────────────────────────

    def extract_paystub_fields(self, raw_text: str) -> PaystubData:
        self._ensure_ollama()
        prompt = EXTRACTION_FROM_TEXT_PROMPT.format(text=raw_text)
        response = self._call_text(prompt)
        return self._parse_extraction(response)

    def extract_paystub_from_image(
        self, image_path: str, ocr_text: str = ""
    ) -> PaystubData:
        """Use llama.cpp vision server — fixes NVIDIA CUDA bug with Gemma 4."""
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = (
            "Extract paystub data from this image. "
            "Return ONLY valid JSON:\n"
            '{"employer_name":"","regular_hours":0,"overtime_hours":0,'
            '"hourly_rate":0.0,"state":"TX","deductions":[]}\n\n'
            "Rules:\n"
            "- state: TX, CA, NY, FL, or IL only\n"
            "- deductions: [{\"name\":\"TOOLS\",\"amount\":75.0}]\n"
            "- Return ONLY JSON, no explanation\n\nJSON:"
        )

        response = self._call_vision_llama(prompt, image_b64)
        return self._parse_extraction(response)

    def generate_explanation(
        self, violation_report, language: str = "es"
    ) -> str:
        self._ensure_ollama()
        lang_instr   = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["es"])
        legal_phrase = LEGAL_AID_PHRASES.get(language, LEGAL_AID_PHRASES["es"])
        report_json  = self._serialize_report(violation_report)
        prompt = MULTILINGUAL_EXPLANATION_PROMPT.format(
            language_instruction=lang_instr,
            state=violation_report.state,
            language_code=language,
            report_json=report_json,
            legal_aid_phrase=legal_phrase
        )
        return self._call_text(prompt)

    def generate_spanish_explanation(self, violation_report) -> str:
        return self.generate_explanation(violation_report, language="es")

    def answer_followup(self, question: str, context: str, language: str = "es") -> str:
        self._ensure_ollama()
        lang_instr = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["es"])
        prompt = (
            f"You are PaySnap.\n\n"
            f"Language: {lang_instr}\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer in the requested language.\n\nAnswer:"
        )
        return self._call_text(prompt)

    # ─── OLLAMA TEXT ──────────────────────────────────────────

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
                        "temperature": 0.1,
                    }
                },
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            print(f"Ollama text error: {e}")
            return "DOL: 1-866-487-9243 (free, confidential)"

    # ─── LLAMA.CPP VISION ────────────────────────────────────

    def _call_vision_llama(self, prompt: str, image_b64: str) -> str:
        """
        Call llama.cpp server for vision tasks.
        Uses OpenAI-compatible API with image_url format.
        Fixes Gemma 4 NVIDIA CUDA crash that affects Ollama.
        """
        try:
            resp = requests.post(
                f"{LLAMA_BASE}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "paysnap-vision",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }],
                    "max_tokens": 500,
                    "temperature": 0.0,
                    "stream": False,
                },
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"llama.cpp vision error: {e}")
            return "{}"

    # ─── HELPERS ──────────────────────────────────────────────

    def _parse_extraction(self, response_text: str) -> PaystubData:
        try:
            clean = response_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            start = clean.find("{")
            end   = clean.rfind("}") + 1
            if start >= 0 and end > start:
                clean = clean[start:end]

            data = json.loads(clean)
            deductions = [
                DeductionItem(
                    name=str(d.get("name", "Unknown")),
                    amount=float(d.get("amount", 0)),
                    raw_text=str(d.get("raw_text", ""))
                )
                for d in data.get("deductions", []) if isinstance(d, dict)
            ]
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

    def _serialize_report(self, report) -> str:
        return json.dumps({
            "state": report.state,
            "has_violation": report.has_any_violation,
            "total_owed": report.total_money_owed,
            "overtime": {
                "has_violation": report.overtime.has_violation,
                "ot_hours_owed": report.overtime.ot_hours_owed,
                "ot_pay_owed":   report.overtime.ot_pay_owed,
                "statute":       report.overtime.statute,
                "breakdown":     report.overtime.calculation_breakdown,
            },
            "illegal_deductions": [
                {
                    "name":    r.deduction.name,
                    "amount":  r.deduction.amount,
                    "reason":  r.reason_en,
                    "statute": r.statute,
                }
                for r in report.illegal_deductions
            ],
            "legal_aid": report.legal_aid_contacts[:2]
        }, ensure_ascii=False, indent=2)

    def _safe_float(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except:
            return None