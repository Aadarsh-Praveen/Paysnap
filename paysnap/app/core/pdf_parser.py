"""
pdf_parser.py
Extracts text from PDF paystubs using PyMuPDF.
Digital PDFs = 99% accurate, no OCR needed.
"""

import fitz  # PyMuPDF
from pathlib import Path
from app.core.input_handler import PaystubData
from app.model.gemma_client import GemmaClient


class PDFParser:
    def __init__(self):
        self.gemma = GemmaClient()

    def parse(self, file_path: str) -> PaystubData:
        print(f"Parsing PDF: {file_path}")
        raw_text = self._extract_text(file_path)

        if not raw_text.strip():
            print("Scanned PDF detected — falling back to OCR")
            return self._fallback_to_ocr(file_path)

        structured = self.gemma.extract_paystub_fields(raw_text)
        structured.confidence = 0.95
        return structured

    def _extract_text(self, file_path: str) -> str:
        doc = fitz.open(file_path)
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                pages.append(f"--- Page {i+1} ---\n{text}")
        doc.close()
        return "\n".join(pages)

    def _fallback_to_ocr(self, file_path: str) -> PaystubData:
        doc = fitz.open(file_path)
        page = doc[0]
        mat = fitz.Matrix(200/72, 200/72)
        pix = page.get_pixmap(matrix=mat)
        img_path = "/tmp/paysnap_pdf_page.png"
        pix.save(img_path)
        doc.close()

        from app.core.image_parser import ImageParser
        result = ImageParser().parse(img_path)
        result.confidence = min(result.confidence, 0.80)
        return result