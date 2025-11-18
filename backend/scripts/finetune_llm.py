"""
LoRA fine-tuning script for small instruction-tuned LLMs on the SMS dataset.

Example:
    pip install -r requirements (transformers>=4.39, peft, bitsandbytes, datasets, accelerate)
    python backend/scripts/finetune_llm.py \
        --train_jsonl backend/data/llm_train.jsonl \
        --model_name Qwen/Qwen2.5-1.5B-Instruct \
        --output_dir backend/models/qwen_sms_lora
"""

import argparse
import json
from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig, get_peft_model
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

PROMPT_TEMPLATE = (
    "{instruction}\n\nInput:\n{input}\n\nJSON:"
)


def load_jsonl(path: Path):
    return load_dataset("json", data_files=str(path))["train"]


def format_record(record):
    output = record["output"]
    formatted = PROMPT_TEMPLATE.format(
        instruction=record["instruction"],
        input=record["input"],
    )
    return {"text": formatted + " " + output}


def tokenize_function(tokenizer, max_length):
    def _tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_length,
        )

    return _tokenize


def bf16_supported() -> bool:
    if not torch.cuda.is_available():
        return False
    if hasattr(torch.cuda, "is_bf16_supported"):
        return torch.cuda.is_bf16_supported()
    major, _ = torch.cuda.get_device_capability()
    return major >= 8


def train(args):
    if args.bf16 and not bf16_supported():
        print("bf16 requested but unsupported; falling back to fp16.")
        args.bf16 = False

    dataset = load_jsonl(args.train_jsonl)
    dataset = dataset.map(
        lambda r: {
            "text": PROMPT_TEMPLATE.format(instruction=r["instruction"], input=r["input"])
            + " "
            + json.dumps(r["output"], ensure_ascii=False)
        },
        remove_columns=dataset.column_names,
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenized = dataset.map(
        tokenize_function(tokenizer, args.max_length),
        batched=True,
        remove_columns=["text"],
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        load_in_4bit=True,
        device_map="auto",
    )

    lora_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=0.03,
        logging_steps=50,
        save_steps=500,
        bf16=args.bf16,
        fp16=not args.bf16,
        report_to="none",
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=data_collator,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"LoRA adapter saved to {args.output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for SMS LLM.")
    parser.add_argument("--train_jsonl", type=Path, required=True, help="SFT dataset JSONL.")
    parser.add_argument("--model_name", type=str, default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output_dir", type=Path, default=Path("backend/models/qwen_sms_lora"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--grad_accum", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--max_length", type=int, default=512)
    parser.add_argument("--lora_rank", type=int, default=8)
    parser.add_argument("--lora_alpha", type=int, default=16)
    parser.add_argument("--bf16", action="store_true", help="Enable bfloat16 training if hardware supports it.")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())

