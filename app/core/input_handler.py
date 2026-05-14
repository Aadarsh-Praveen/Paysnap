"""
input_handler.py
Routes all input types to correct parser.
Returns PaystubData in all cases.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "app_config.yaml"
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)


@dataclass
class DeductionItem:
    name: str
    amount: float
    raw_text: str = ""


@dataclass
class PaystubData:
    regular_hours: Optional[float] = None
    overtime_hours: Optional[float] = None
    total_hours: Optional[float] = None
    hourly_rate: Optional[float] = None
    overtime_rate: Optional[float] = None
    gross_pay: Optional[float] = None
    net_pay: Optional[float] = None
    deductions: list = field(default_factory=list)
    employer_name: Optional[str] = None
    pay_period_start: Optional[str] = None
    pay_period_end: Optional[str] = None
    state: Optional[str] = None
    confidence: float = 0.0
    input_type: str = "unknown"
    needs_review: bool = True


class InputHandler:
    def __init__(self):
        self.image_types = set(CONFIG["input"]["accepted_image_types"])
        self.confidence_threshold = CONFIG["input"]["ocr_confidence_threshold"]

    def handle(self, file_path: str) -> PaystubData:
        path = Path(file_path)
        ext = path.suffix.lower()
        print(f"Handling: {path.name} ({ext})")

        if ext in self.image_types:
            return self._handle_image(file_path)
        elif ext == ".pdf":
            return self._handle_pdf(file_path)
        elif ext == ".docx":
            return self._handle_docx(file_path)
        elif ext == ".xlsx":
            return self._handle_xlsx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _handle_image(self, file_path):
        try:
            from app.core.image_parser import ImageParser
            data = ImageParser().parse(file_path)
            data.input_type = "image"
            data.needs_review = True
            return data
        except Exception as e:
            print(f"Image parse error: {e}")
            import traceback
            traceback.print_exc()
            # Return empty paystub — worker fills in manually
            from app.core.input_handler import PaystubData
            return PaystubData(confidence=0.0, needs_review=True, input_type="image")

    def _handle_pdf(self, file_path):
        from app.core.pdf_parser import PDFParser
        data = PDFParser().parse(file_path)
        data.input_type = "pdf"
        return data

    def _handle_docx(self, file_path):
        from app.core.doc_parser import DocParser
        data = DocParser().parse_docx(file_path)
        data.input_type = "docx"
        return data

    def _handle_xlsx(self, file_path):
        from app.core.doc_parser import DocParser
        data = DocParser().parse_xlsx(file_path)
        data.input_type = "xlsx"
        return data