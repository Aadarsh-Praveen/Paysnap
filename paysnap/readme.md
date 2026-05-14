# 💼 PaySnap — AI Wage Theft Detector

PaySnap helps non-English speaking workers understand their paystubs and detect wage theft. Upload a paystub photo → Gemma 4 reads it → explains your rights in your language. Runs completely offline. No data ever leaves your device.

## Live Demo

**[Try PaySnap →](https://huggingface.co/spaces/Aadarsh-Praveen/paysnap)**

Supports 11 languages: English · Español · 中文 · Português · Tiếng Việt · हिन्दी · 한국어 · Filipino · العربية · Русский · Kreyòl

## What It Detects

- **Overtime violations** — unpaid hours over 40/week (FLSA 29 USC 207)
- **Illegal deductions** — tools, uniforms, breakage (varies by state)
- **Minimum wage violations** — deductions that drop below minimum
- **State-specific violations** — CA daily overtime, NY/IL strict deduction rules

## States Supported

| State | Min Wage | Key Law |
|-------|----------|---------|
| Texas | $7.25 | FLSA federal |
| California | $16.50 | CA Labor Code §510 |
| New York | $16.00 | NY Labor Law §193 |
| Florida | $13.00 | FLSA + FL Constitution Art. X §24 |
| Illinois | $14.00 | 820 ILCS 105/4a |

## Architecture

```
Worker uploads paystub photo
        ↓
Gemma 4 vision (Ollama) reads paystub via OCR
        ↓
Deterministic calculator (SQLite) detects violations
        ↓
Fine-tuned Gemma 4 explains in worker's language
        ↓
Worker gets exact dollar amount + statute + free legal aid
```

**Key design principle:** Legal facts come from SQLite (verifiable, auditable). Gemma 4 only explains — never decides. This prevents hallucination of legal facts.

## AI Model

- **Base model:** Gemma 4 E2B by Google DeepMind
- **Fine-tuning:** Unsloth LoRA, trained on Kaggle T4 GPU
- **Training data:** 856 examples — 500 from real DOL enforcement cases + 356 synthetic
- **Final training loss:** 0.009 | Validation loss: 0.071
- **Model weights:** [Aadarsh-Praveen/paysnap-gemma4-lora](https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-lora)
- **Training notebook:** [kaggle.com/code/aadarshpraveen/paysnap-gemma4-finetuning](https://www.kaggle.com/code/aadarshpraveen/paysnap-gemma4-finetuning)

## Dataset

Training data combines two sources:

**Real DOL Enforcement Data (public domain)**
- Source: https://data.dol.gov/datasets/10246
- 365,393 WHD compliance actions loaded
- 141,522 cases in TX, CA, NY, FL, IL
- 65,811 confirmed FLSA violations
- 500 real cases used in training
- License: US Government public domain (17 USC §105)
- Citation: *U.S. Department of Labor, Wage and Hour Division. WHD Compliance Action Data. data.dol.gov/datasets/10246*

**Verified Synthetic Scenarios**
- 570 mathematically generated paystub scenarios
- All calculations verified against deterministic calculator
- 18/18 unit tests passing
- State law sourced from official government websites

Full processed dataset: https://www.kaggle.com/datasets/aadarshpraveen/paysnap-labor-law-dataset

## Running Locally

```bash
# 1. Install Ollama — https://ollama.ai
ollama pull gemma4

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build the law database
python data/build_db.py

# 4. Start backend
uvicorn backend.main:app --reload --port 8000

# 5. Start frontend
cd frontend && npm install && npm run dev

# 6. Open http://localhost:5174
```

## Project Structure

```
paysnap/
├── app/
│   ├── analysis/          # Deterministic violation detection
│   │   ├── overtime_calculator.py   # FLSA math, zero LLM
│   │   ├── deduction_checker.py     # 3-check deduction system
│   │   └── violation_engine.py      # Combines all checks
│   ├── core/              # Paystub parsing
│   │   ├── image_parser.py          # PaddleOCR + Gemma 4 vision
│   │   └── input_handler.py
│   ├── model/             # Gemma 4 integration via Ollama
│   │   ├── gemma_client.py
│   │   ├── prompts.py               # Multilingual prompt templates
│   │   └── router.py                # Intelligent model routing
│   └── output/
│       ├── demand_letter.py         # Formal letter generator
│       └── evidence_vault.py        # Encrypted local history
├── backend/               # FastAPI server
├── data/
│   ├── states/            # TX CA NY FL IL labor law JSON
│   ├── build_db.py        # Builds SQLite from JSON files
│   └── labor_law.db       # Generated — run build_db.py
├── finetune/
│   ├── dataset/
│   │   ├── build_dataset.py         # Builds from DOL data
│   │   └── processed/               # train/eval/test JSONL
│   └── finetune_kaggle.py           # Unsloth training script
├── frontend/              # React + Vite
│   └── src/
│       ├── App.jsx                  # Language picker + main app
│       ├── pages/                   # Analyze, History, Rights
│       ├── api/client.js            # FastAPI calls
│       └── data/languages.js        # 11 language definitions
└── tests/
    └── test_overtime.py             # 18 unit tests
```

## Tests

```bash
python -m pytest tests/test_overtime.py -v
# 18/18 passing
```

## Privacy

- Zero cloud — all analysis runs on device
- No account or signup required
- No analytics or tracking
- Encrypted local history (Fernet encryption)
- Works offline after Ollama install

## License

Apache 2.0

## Data Sources

- U.S. Department of Labor WHD: https://data.dol.gov/datasets/10246
- FLSA: https://www.law.cornell.edu/uscode/text/29/207
- CA Labor Code: https://leginfo.legislature.ca.gov
- NY Labor Law: https://dol.ny.gov
- Texas Payday Law: https://www.twc.texas.gov
- Illinois Wage Payment: https://labor.illinois.gov


