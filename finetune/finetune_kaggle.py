"""
finetune/finetune_kaggle.py
PaySnap — Gemma 4 Fine-tuning with Unsloth
Run on Kaggle GPU T4 x2

Dataset: Real DOL enforcement data + verified synthetic
Source:  data.dol.gov/datasets/10246 (public domain)
Model:   Gemma 4 E2B via Unsloth FastModel

Results:
  Training examples: 856
  Final loss:        0.009
  Validation loss:   0.071
  Runtime:           ~13 minutes on T4
"""

import os
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

import subprocess
subprocess.run(["pip", "install", "unsloth", "-q"])
subprocess.run(["pip", "install", "trl", "datasets", "-q"])

import torch
import json
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth import FastModel

print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# ── Load Dataset ──
# Upload to Kaggle as: paysnap-labor-law-dataset
# Source: data.dol.gov/datasets/10246 (US Government public domain)
train_data = []
with open("/kaggle/input/paysnap-labor-law-dataset/train.jsonl") as f:
    for line in f:
        if line.strip():
            train_data.append(json.loads(line))

eval_data = []
with open("/kaggle/input/paysnap-labor-law-dataset/eval.jsonl") as f:
    for line in f:
        if line.strip():
            eval_data.append(json.loads(line))

print(f"Train: {len(train_data)} examples")
print(f"Eval:  {len(eval_data)} examples")
print(f"Sample:\n{train_data[0]['text'][:300]}")

# ── Load Gemma 4 E2B with Unsloth ──
# Uses FastModel (not FastLanguageModel) for Gemma 4
# E2B = 2B active parameters, fits in 15GB VRAM with 4-bit
model, tokenizer = FastModel.from_pretrained(
    model_name="unsloth/gemma-4-E2B-it",
    max_seq_length=512,
    load_in_4bit=True,
    dtype=None,
    full_finetuning=False,
)
print("Model loaded")

# ── Apply LoRA ──
# Only trains 0.3% of parameters — 15M of 5B
# Makes fine-tuning possible on free GPU
model = FastModel.get_peft_model(
    model,
    r=8,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_alpha=8,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)
print("LoRA applied")

# ── Train ──
train_dataset = Dataset.from_list(train_data)
eval_dataset  = Dataset.from_list(eval_data)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    dataset_text_field="text",
    max_seq_length=512,
    args=TrainingArguments(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        warmup_steps=10,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        output_dir="paysnap_output",
        optim="adamw_8bit",
        seed=42,
        report_to="none",
        dataloader_pin_memory=False,
    ),
)

print("Starting training...")
stats = trainer.train()
print(f"Training complete!")
print(f"Final loss:      {stats.metrics['train_loss']:.4f}")
print(f"Runtime:         {stats.metrics['train_runtime']:.0f} seconds")

# ── Test Fine-tuned Model ──
FastModel.for_inference(model)

test_prompt = (
    "### Instruction:\n"
    "Analyze this paystub for labor violations.\n\n"
    "### Paystub Data:\n"
    '{"state": "TX", "total_hours_worked": 52, '
    '"hours_shown_on_stub": 40, "overtime_hours_shown": 0, '
    '"hourly_rate": 23.0, "deductions": []}\n\n'
    "### Analysis:\n"
)

inputs = tokenizer(text=test_prompt, return_tensors="pt").to("cuda")
outputs = model.generate(
    **inputs,
    max_new_tokens=300,
    temperature=0.1,
    do_sample=True,
)
response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print("\nFine-tuned model response:")
print(response[len(test_prompt):])

# ── Save Model ──
model.save_pretrained("paysnap-gemma4-lora")
tokenizer.save_pretrained("paysnap-gemma4-lora")
print("\nModel saved to paysnap-gemma4-lora/")

# ── Push to HuggingFace ──
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login

try:
    secrets = UserSecretsClient()
    hf_token = secrets.get_secret("HF_TOKEN")
    login(token=hf_token)
    model.push_to_hub("Aadarsh-Praveen/paysnap-gemma4-lora")
    tokenizer.push_to_hub("Aadarsh-Praveen/paysnap-gemma4-lora")
    print("Model pushed to HuggingFace!")
    print("URL: https://huggingface.co/Aadarsh-Praveen/paysnap-gemma4-lora")
except Exception as e:
    print(f"HF push skipped: {e}")
    print("Model saved locally to paysnap-gemma4-lora/")