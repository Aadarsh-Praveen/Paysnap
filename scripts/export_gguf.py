"""
scripts/export_gguf.py

Exports PaySnap fine-tuned model to GGUF format.
Enables llama.cpp and Cactus mobile deployment.

Run on Google Colab with T4 GPU:
  1. Upload this file to Colab
  2. Add HF_TOKEN to Colab secrets
  3. Run: python export_gguf.py

Output:
  HuggingFace: Aadarsh-Praveen/paysnap-gemma4-gguf
  File: gemma-4-e2b-it.Q4_K_M.gguf (3.4GB)
  Vision: gemma-4-e2b-it.F16-mmproj.gguf (986MB)

Enables:
  - llama.cpp: run on any CPU laptop
  - Cactus:    run on iPhone + Android
  - Ollama:    import via Modelfile
"""

import subprocess
subprocess.run(["pip", "install", "unsloth", "-q"])

import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# ── HuggingFace Login ──
try:
    # Colab secrets
    from google.colab import userdata
    hf_token = userdata.get('HF_TOKEN')
except:
    # Direct token (replace with yours)
    hf_token = "YOUR_HF_TOKEN_HERE"

from huggingface_hub import login
login(token=hf_token)
print("Logged in to HuggingFace")

# ── Load Fine-tuned Model ──
from unsloth import FastModel

print("Loading PaySnap fine-tuned model...")
model, tokenizer = FastModel.from_pretrained(
    model_name="Aadarsh-Praveen/paysnap-gemma4-lora",
    max_seq_length=512,
    load_in_4bit=True,
    dtype=torch.float16,
    device_map={"": 0},
    token=hf_token,
)
print("Model loaded")

# ── Quick Test ──
FastModel.for_inference(model)

test_prompt = (
    "### Instruction:\n"
    "Analyze this paystub for labor violations.\n\n"
    "### Paystub Data:\n"
    '{"state": "TX", "total_hours_worked": 52, '
    '"hours_shown_on_stub": 40, "hourly_rate": 23.0}\n\n'
    "### Analysis:\n"
)

inputs = tokenizer(text=test_prompt, return_tensors="pt").to("cuda")
outputs = model.generate(
    **inputs, max_new_tokens=150, temperature=0.1, do_sample=True
)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print("\nModel test:")
print(response[len(test_prompt):])

# ── Export to GGUF ──
print("\nExporting to GGUF format")

model.push_to_hub_gguf(
    "Aadarsh-Praveen/paysnap-gemma4-gguf",
    tokenizer,
    quantization_method="q4_k_m",
    token=hf_token
)

print("\nDone!")
print("GGUF: https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-gguf")
print("File: gemma-4-e2b-it.Q4_K_M.gguf")
print("Runs: Mac · Linux · Windows · Android · iPhone via Cactus")