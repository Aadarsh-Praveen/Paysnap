# PaySnap — Unsloth Fine-tuning Notebook
# Run on Kaggle with GPU T4 x2

# Install
!pip install unsloth
!pip install torch transformers datasets

from unsloth import FastLanguageModel
import torch
from datasets import Dataset
import json

# ── Load Gemma 4 ──
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="google/gemma-4-4b-it",
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=None,
)

# ── Apply LoRA ──
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

# ── Training Data ──
# Paystub scenarios → correct Spanish explanation
training_data = [
    {
        "instruction": "Analiza este recibo de pago y explica en español simple.",
        "input": json.dumps({
            "state": "TX",
            "total_hours": 52,
            "hourly_rate": 23.00,
            "hours_shown": 40,
            "ot_shown": 0,
            "deductions": [{"name": "TOOLS", "amount": 75.00}]
        }),
        "output": (
            "Esta semana trabajaste 52 horas, pero tu recibo solo muestra 40 horas regulares. "
            "Según la Ley Federal de Normas Laborales (FLSA 29 USC 207(a)(1)), "
            "las horas que trabajas de más de 40 por semana deben pagarse al 1.5 veces "
            "tu tarifa normal. En tu caso, trabajaste 12 horas extras que no se pagaron. "
            "Esas 12 horas a $34.50 por hora (1.5 x $23.00) significan que podría "
            "corresponderle $414.00. "
            "Además, la deducción de $75.00 por herramientas (TOOLS) puede requerir "
            "tu consentimiento por escrito según la ley de Texas. "
            "Para más información llame al 1-866-487-9243."
        )
    },
    {
        "instruction": "Analiza este recibo de pago y explica en español simple.",
        "input": json.dumps({
            "state": "CA",
            "total_hours": 45,
            "hourly_rate": 18.00,
            "hours_shown": 45,
            "ot_shown": 5,
            "daily_hours": 10,
            "deductions": []
        }),
        "output": (
            "En California, la ley es diferente a la ley federal. "
            "Según el Código Laboral de California §510, si trabajas más de "
            "8 horas en un día, esas horas adicionales deben pagarse al 1.5 veces "
            "tu tarifa normal. Si trabajaste 10 horas en un día, las últimas 2 horas "
            "son tiempo extra diario. "
            "Tu tarifa normal es $18.00 por hora, así que el tiempo extra es $27.00 "
            "por hora. Podría corresponderle pago adicional por las horas extras diarias. "
            "Para verificar llame al Comisionado Laboral de California: 1-844-522-6734."
        )
    },
    {
        "instruction": "Analiza este recibo de pago y explica en español simple.",
        "input": json.dumps({
            "state": "NY",
            "total_hours": 40,
            "hourly_rate": 14.00,
            "hours_shown": 40,
            "ot_shown": 0,
            "deductions": [
                {"name": "UNIFORM", "amount": 50.00},
                {"name": "FEDERAL TAX", "amount": 89.50}
            ]
        }),
        "output": (
            "Revisamos tu recibo de pago de Nueva York. "
            "Las horas parecen correctas — 40 horas regulares sin tiempo extra. "
            "Sin embargo, encontramos un posible problema con una deducción: "
            "La deducción de $50.00 por uniforme (UNIFORM) es ILEGAL en Nueva York "
            "según la Ley Laboral de NY §193. Los empleadores en Nueva York no pueden "
            "cobrar por uniformes. "
            "La deducción de impuestos federales es normal y legal. "
            "Para reportar la deducción ilegal de uniforme llame al: 1-888-469-7365 "
            "(Departamento de Trabajo de Nueva York, servicio en español)."
        )
    },
    {
        "instruction": "Analiza este recibo de pago y explica en español simple.",
        "input": json.dumps({
            "state": "TX",
            "total_hours": 40,
            "hourly_rate": 7.50,
            "hours_shown": 40,
            "ot_shown": 0,
            "deductions": [{"name": "TOOLS", "amount": 75.00}]
        }),
        "output": (
            "Encontramos un problema serio en tu recibo. "
            "Tu tarifa es $7.50 por hora, que está apenas por encima del mínimo "
            "federal de $7.25 por hora. "
            "Sin embargo, la deducción de $75.00 por herramientas baja tu pago "
            "efectivo a aproximadamente $5.63 por hora — por DEBAJO del salario "
            "mínimo federal. "
            "Esto es ILEGAL según la Ley Federal (FLSA 29 USC 203(m)). "
            "Ninguna deducción puede bajar tu salario por debajo del mínimo. "
            "Podría corresponderle recuperar los $75.00. "
            "Llame inmediatamente al 1-866-487-9243 (DOL, gratis, español)."
        )
    },
    {
        "instruction": "Analiza este recibo de pago y explica en español simple.",
        "input": json.dumps({
            "state": "FL",
            "total_hours": 38,
            "hourly_rate": 13.50,
            "hours_shown": 38,
            "ot_shown": 0,
            "deductions": [
                {"name": "FEDERAL TAX", "amount": 95.00},
                {"name": "MEDICARE", "amount": 19.50},
                {"name": "SOCIAL SECURITY", "amount": 83.00}
            ]
        }),
        "output": (
            "Revisamos tu recibo de Florida. "
            "Trabajaste 38 horas esta semana — menos de 40, así que no hay "
            "tiempo extra requerido por ley. "
            "Tu tarifa de $13.50 por hora está por encima del mínimo de Florida "
            "de $13.00 por hora. "
            "Las deducciones de impuestos federales, Medicare y Seguro Social "
            "son deducciones normales y legales que todos los empleadores deben hacer. "
            "No detectamos problemas en este recibo. "
            "Si tienes dudas, puede llamar al 1-866-487-9243."
        )
    },
]

# ── Format Dataset ──
def format_prompt(example):
    return {
        "text": (
            f"### Instrucción:\n{example['instruction']}\n\n"
            f"### Datos del recibo:\n{example['input']}\n\n"
            f"### Explicación:\n{example['output']}"
        )
    }

dataset = Dataset.from_list(training_data)
dataset = dataset.map(format_prompt)

# ── Train ──
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        output_dir="paysnap_model",
        optim="adamw_8bit",
        seed=42,
    ),
)

trainer.train()

# ── Save ──
model.save_pretrained("paysnap-gemma4-lora")
tokenizer.save_pretrained("paysnap-gemma4-lora")
print("Model saved!")

# ── Push to HuggingFace (optional) ──
# model.push_to_hub("YOUR_USERNAME/paysnap-gemma4-lora")