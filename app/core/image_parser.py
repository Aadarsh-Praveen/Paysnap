"""
image_parser.py
Handles photos and screenshots via Gemma 4 vision.
PaddleOCR is optional — falls back to Gemma vision only.
"""

import base64
from pathlib import Path
from PIL import Image
from app.core.input_handler import PaystubData
from app.model.gemma_client import GemmaClient


class ImageParser:
    def __init__(self):
        self.gemma = GemmaClient()
        self._ocr = None
        self._ocr_loaded = False

    def _load_ocr(self):
        """Try to load PaddleOCR — skip if it fails."""
        if self._ocr_loaded:
            return
        try:
            from paddleocr import PaddleOCR
            # Try new API first (PaddleOCR 3.x)
            try:
                self._ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)
            except TypeError:
                # Fall back to old API
                self._ocr = PaddleOCR(use_angle_cls=True, lang="en",
                                       use_gpu=False, show_log=False)
            print("PaddleOCR loaded successfully")
        except Exception as e:
            print(f"PaddleOCR not available: {e} — using Gemma vision only")
            self._ocr = None
        self._ocr_loaded = True

    def parse(self, file_path: str) -> PaystubData:
        print(f"Parsing image: {file_path}")

        # Step 1: Pre-process image
        processed = self._preprocess(file_path)

        # Step 2: Try OCR for text hint
        ocr_text = self._run_ocr(processed)

        # Step 3: Gemma 4 vision reads the image
        structured = self.gemma.extract_paystub_from_image(processed, ocr_text)
        structured.confidence = 0.85
        return structured

    def _preprocess(self, file_path: str) -> str:
        """Improve image quality for better reading."""
        try:
            img = Image.open(file_path)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            w, h = img.size
            if w < 1000 or h < 1000:
                scale = max(1000/w, 1000/h)
                img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
            out = f"/tmp/paysnap_processed_{Path(file_path).stem}.jpg"
            img.save(out, "JPEG", quality=95)
            return out
        except Exception as e:
            print(f"Preprocess failed: {e} — using original")
            return file_path

    def _run_ocr(self, image_path: str) -> str:
        """
        Run PaddleOCR to get text hint for Gemma.
        Returns empty string if OCR fails — Gemma handles it alone.
        """
        self._load_ocr()
        if self._ocr is None:
            return ""
        try:
            result = self._ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return ""
            lines = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                    lines.append(text)
            extracted = "\n".join(lines)
            print(f"OCR extracted {len(lines)} lines")
            return extracted
        except Exception as e:
            print(f"OCR failed: {e} — Gemma will read image directly")
            return ""