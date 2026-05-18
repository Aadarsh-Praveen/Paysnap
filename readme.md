# PaySnap — AI Wage Theft Detector

> Fine-tuned Gemma 4 E2B on 365,393 real DOL enforcement cases. Workers upload a paystub → Gemma 4 reads it with vision → detects violations with deterministic math → explains rights in their language using native function calling.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-paysnap.vercel.app-f97316?style=flat-square)](https://paysnap.vercel.app)
[![Model](https://img.shields.io/badge/HuggingFace-paysnap--gemma4--gguf-yellow?style=flat-square)](https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-gguf)
[![Dataset](https://img.shields.io/badge/Kaggle-DOL%20Dataset-20BEFF?style=flat-square)](https://kaggle.com/datasets/aadarshpraveen/paysnap-labor-law-dataset)
[![Notebook](https://img.shields.io/badge/Kaggle-Fine--tuning%20Notebook-20BEFF?style=flat-square)](https://kaggle.com/code/aadarshpraveen/paysnap-gemma4-finetuning)

---

## What PaySnap Does

A construction worker in Texas worked 52 hours at $15/hour. His paystub shows zero overtime. He is owed $90. He will never know — until PaySnap.

**Worker uploads paystub → PaySnap detects violation → explains in their language → connects to DOL.**

Supports 11 languages: English · Español · हिन्दी · 中文 · Tiếng Việt · 한국어 · Português · العربية · Русский · Filipino · Kreyòl

---

## How We Used Gemma 4

### 1. Fine-tuning on Real DOL Data

We fine-tuned Gemma 4 E2B using Unsloth on **365,393 real DOL Wage and Hour Division enforcement cases** — the largest public wage enforcement dataset in the US.

| Detail | Value |
|--------|-------|
| Base model | Gemma 4 E2B |
| Method | LoRA via Unsloth on Kaggle T4 GPU |
| Training cases | 365,393 real DOL enforcement records |
| Training loss | 0.009 |
| LoRA weights | [Aadarsh-Praveen/paysnap-gemma4-lora](https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-lora) |
| GGUF (Q4_K_M) | [Aadarsh-Praveen/paysnap-gemma4-gguf](https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-gguf) |

### 2. Native Function Calling — Agentic Architecture

Gemma 4 uses **native function calling** to autonomously decide which tools to run. This is not a hardcoded pipeline — Gemma 4 reasons about what to check.

**Tools available to Gemma 4:**
- `calculate_overtime(hours, rate, state)` — FLSA + state overtime rules
- `check_minimum_wage(rate, state, hours)` — federal + state minimum wage
- `check_deductions(name, amount, state)` — state-specific deduction laws
- `get_applicable_statutes(violation_type, state)` — exact statute citations
- `get_dol_contact(state, language)` — DOL hotline + state offices

**Live example — NY worker, 2 deductions:**
```
Gemma 4 called: calculate_overtime()       → $64 overtime owed
Gemma 4 called: check_deductions(UNIFORM)  → illegal in NY, $35 back
Gemma 4 called: check_deductions(BREAKAGE) → illegal in NY, $50 back
Gemma 4 called: get_dol_contact()          → 1-866-487-9243
Total: $149 owed — explanation in Spanish 
```

Gemma 4 decided to check deductions because it saw them on the paystub.

### 3. Multimodal Vision

Gemma 4 reads paystub images via llama.cpp (OpenAI-compatible vision API). Workers photograph their paystub — Gemma 4 extracts employer, hours, rate, and deductions from the image.

> **Note:** Gemma 4 vision crashes on NVIDIA GPUs in Ollama due to a CUDA bug. We built a separate llama.cpp server on port 8080 for vision — routing text to Ollama and images to llama.cpp.

### 4. Multilingual Explanation

After tool calls complete, Gemma 4 generates worker-friendly explanations in 11 languages with exact statute citations and the DOL hotline in every response.

---

## Evaluation

LLM-as-Judge evaluation (Zheng et al. 2023) using base Gemma 4 E2B as impartial judge — 15 domain-specific DOL enforcement scenarios.

| Model | Score (/10) |
|-------|------------|
| Base Gemma 4 E2B | 8.12 |
| PaySnap Fine-tuned | 9.07 |
| **Improvement** | **+11.7%** |

All 5 dimensions improved:

| Dimension | Δ |
|-----------|---|
| Legal Accuracy | +1.73 |
| Statute Quality | +1.33 |
| Actionability | +0.73 |
| Dollar Accuracy | +0.67 |
| Worker Clarity | +0.27 |

Category highlights: DOL Violation Pattern +4.2, Wrong OT Rate Detection +1.8, DOL Hotline Knowledge +1.7.

Keyword evaluation (25 tests): +15% overall. Statute citations: 9/25 → 24/25 (+167%).

Full evaluation results: [`evaluation_results/`](./evaluation_results/)

---

## Architecture

```
Worker Input (photo / voice / text / form)
         ↓
Gemma 4 Vision via llama.cpp (port 8080)
         ↓ structured JSON extraction
FastAPI Backend (/analyze-agentic endpoint)
         ↓
Gemma 4 + 5 Tools (native function calling)
  Gemma 4 decides → calls calculate_overtime()
  Gemma 4 decides → calls check_deductions()
  Gemma 4 decides → calls get_dol_contact()
         ↓
Python executes tools deterministically
Results returned to Gemma 4
         ↓
Gemma 4 generates explanation in worker's language
         ↓
Worker: violation + $ owed + statute + DOL contact
```

**Key design principle:** Math is always deterministic Python. Gemma 4 decides what to check and explains results — tools handle computation. This guarantees 100% calculation accuracy.

**Stack:** Gemma 4 E2B · Unsloth · Ollama · llama.cpp · FastAPI · React · GCP (NVIDIA L4) · Vercel

---

## What It Detects

| Violation | States | Statute |
|-----------|--------|---------|
| Overtime (weekly) | All | FLSA 29 USC 207(a)(1) |
| Daily overtime | CA | California Labor Code §510 |
| Minimum wage | All | FLSA 29 USC 206 |
| Tool deductions | CA, NY, IL | CA §221, NY §193, IL 820 ILCS |
| Uniform deductions | CA, NY | CA §221, NY §193 |
| Breakage deductions | CA, NY, IL | CA §221, NY §193, IL 820 ILCS |
| Cash register shortages | CA, NY, IL | CA §221, NY §193 |
| Worker misclassification | All | DOL economic reality test |
| Retaliation | All | FLSA §15(a)(3) |

---

## States Supported

| State | Min Wage | Key Law |
|-------|----------|---------|
| Texas | $7.25 | FLSA federal |
| California | $16.50 | CA Labor Code §510 |
| New York | $16.00 | NY Labor Law §193 |
| Florida | $13.00 | FLSA + FL Constitution Art. X §24 |
| Illinois | $14.00 | 820 ILCS 105/4a |

---

## Running Locally

```bash
# 1. Install Ollama — https://ollama.ai
ollama pull gemma4:e2b

# 2. Download fine-tuned GGUF
mkdir -p ~/paysnap-gguf
# Download from: huggingface.co/Aadarsh-Praveen/paysnap-gemma4-gguf

# 3. Create Ollama model
ollama create paysnap -f Modelfile

# 4. Install dependencies
pip install -r requirements.txt

# 5. Build the law database
python data/build_db.py

# 6. Start llama.cpp vision server (port 8080)
./llama-server -m ~/paysnap-gguf/gemma-4-e2b-it.Q4_K_M.gguf \
  --mmproj ~/paysnap-gguf/gemma-4-e2b-it.F16-mmproj.gguf \
  --port 8080

# 7. Start backend
uvicorn backend.main:app --reload --port 8000

# 8. Start frontend
cd frontend && npm install && npm run dev

# 9. Open http://localhost:5174
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/extract` | POST | Gemma 4 vision reads paystub image |
| `/extract-text` | POST | Gemma 4 understands natural language |
| `/analyze` | POST | Deterministic math + Gemma 4 explanation |
| `/analyze-agentic` | POST | **Gemma 4 native function calling** |
| `/demand-letter` | POST | Formal demand letter generation |
| `/translate-ui` | POST | Translate all 65 UI strings |
| `/history` | GET | Evidence vault |
| `/export` | GET | Download evidence as .txt |

---

## Project Structure

```
paysnap/
├── app/
│   ├── analysis/
│   │   ├── overtime_calculator.py   # FLSA math — zero LLM
│   │   ├── deduction_checker.py     # State-specific deduction rules
│   │   └── violation_engine.py      # Combines all checks
│   ├── core/
│   │   ├── image_parser.py          # llama.cpp vision integration
│   │   └── input_handler.py         # Multi-modal input handling
│   ├── model/
│   │   ├── gemma_client.py          # Hybrid Ollama + llama.cpp client
│   │   ├── agentic_analyzer.py      # Native function calling loop
│   │   ├── tools.py                 # 5 tools Gemma 4 can call
│   │   ├── prompts.py               # Multilingual prompt templates
│   │   └── router.py                # Intelligent model routing
│   └── output/
│       ├── demand_letter.py         # Formal letter generator
│       └── evidence_vault.py        # Local evidence storage
├── backend/
│   └── main.py                      # FastAPI server — all endpoints
├── data/
│   ├── states/                      # TX CA NY FL IL labor law JSON
│   ├── build_db.py                  # Builds SQLite from JSON
│   └── labor_law.db                 # Generated — run build_db.py
├── evaluation_results/              # LLM-as-Judge evaluation JSON + charts
├── scripts/
│   ├── evaluate_models.py           # Keyword-based evaluation
│   ├── evaluate_paysnap_final.py    # Final LLM-as-Judge evaluation
│   └── test_agentic.py              # Agentic function calling tests
├── frontend/
│   └── src/
│       ├── App.jsx                  # Language picker + routing
│       ├── pages/                   # Analyze, History, Rights
│       └── data/languages.js        # 11 language definitions
└── tests/
    └── test_paysnap.py              # Full test suite — 14 tests
```

---

## Tests

```bash
# Full test suite
python3 tests/test_paysnap.py

# Test production
python3 tests/test_paysnap.py --url https://paysnap.website
```

Tests cover: health, TX/NY/CA/FL/IL overtime, deductions, Hindi/Spanish explanation, text extraction, agentic function calling, demand letter, history.

---

## Special Tracks

| Track | Implementation |
|-------|---------------|
| **Unsloth** | Fine-tuned Gemma 4 E2B with Unsloth on Kaggle. Loss 0.009. Published to HuggingFace. |
| **Ollama** | Backend uses Ollama to serve fine-tuned GGUF for text generation and translation. |
| **llama.cpp** | Built with CUDA on GCP VM for vision inference. Fixes Gemma 4 NVIDIA CUDA vision bug. Runs at 63 t/s on Apple Silicon. |

---

## Infrastructure

| Component | Details |
|-----------|---------|
| Cloud API | GCP VM — NVIDIA L4 GPU (g2-standard-4), us-east1-b |
| Frontend | Vercel — paysnap.vercel.app |
| Model serving | Ollama (text) + llama.cpp (vision, port 8080) |
| Database | SQLite — 365,393 DOL cases + state labor laws |
| SSL | Let's Encrypt — paysnap.website |

---

## Privacy

- No account or signup required
- No analytics or tracking
- Sensitive paystub data can stay on-device via llama.cpp
- Local evidence vault

---

## Links

| Resource | URL |
|----------|-----|
| Live Demo | https://paysnap.vercel.app |
| API | https://paysnap.website |
| Fine-tuned GGUF | https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-gguf |
| LoRA Weights | https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-lora |
| Training Notebook | https://kaggle.com/code/aadarshpraveen/paysnap-gemma4-finetuning |
| Dataset | https://kaggle.com/datasets/aadarshpraveen/paysnap-labor-law-dataset |
| HuggingFace Space | https://huggingface.co/spaces/Aadarsh-Praveen/paysnap |

---

## Data Sources

- U.S. Department of Labor WHD Enforcement: https://data.dol.gov/datasets/10246
- FLSA: https://www.law.cornell.edu/uscode/text/29/207
- CA Labor Code: https://leginfo.legislature.ca.gov
- NY Labor Law: https://dol.ny.gov
- Texas Payday Law: https://www.twc.texas.gov
- Illinois Wage Payment: https://labor.illinois.gov

---

## License

Apache 2.0

---

*PaySnap — your paystub, your rights.*