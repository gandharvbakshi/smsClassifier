"""
Evaluate a fine-tuned LLM on the synthetic test set without contaminating training.

Example:
    python backend/scripts/eval_llm_on_synthetic.py \
        --model_path backend/models/qwen_sms_lora \
        --base_model Qwen/Qwen2.5-1.5B-Instruct
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from peft import PeftModel, PeftConfig
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "synthetic_test_set_200_verified.csv"

PROMPT = (
    "You are an SMS security assistant. Respond ONLY with JSON matching "
    "{{\"is_otp\": <true|false>, \"otp_intent\": \"...\", \"is_phishing\": <true|false>, \"reason\": \"...\"}}.\n"
    "Input:\n{input}\n\nJSON:"
)


def load_model(model_path: Path, base_model: str | None):
    if (model_path / "adapter_config.json").exists():
        # LoRA adapter directory
        base = base_model or PeftConfig.from_pretrained(model_path).base_model_name_or_path
        tokenizer = AutoTokenizer.from_pretrained(base, use_fast=False)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            base,
            torch_dtype="auto",
            device_map="auto",
        )
        model = PeftModel.from_pretrained(model, model_path)
    else:
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto",
        )
    model.eval()
    return model, tokenizer


def extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    snippet = match.group(0)
    try:
        snippet = snippet.replace("True", "true").replace("False", "false")
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def normalize_outputs(obj: dict) -> tuple[bool, str, bool]:
    is_otp = bool(obj.get("is_otp"))
    otp_intent = str(obj.get("otp_intent", "NOT_OTP"))
    is_phishing = bool(obj.get("is_phishing"))
    return is_otp, otp_intent, is_phishing


def evaluate(args):
    df = pd.read_csv(args.synthetic_csv)
    df["sender"] = df["sender"].fillna("").astype(str)

    model, tokenizer = load_model(args.model_path, args.base_model)

    preds_otp, preds_phish, preds_intent = [], [], []
    gold_otp = df["predicted_is_otp"].astype(str).str.lower().map({"true": True, "false": False})
    gold_phish = df["is_phishing_original"].astype(str).str.lower().map({"true": True, "false": False})
    gold_intent = df["predicted_otp_intent"].astype(str)

    failures = 0
    for _, row in df.iterrows():
        prompt = PROMPT.format(input=f"Sender: {row['sender'] or 'UNKNOWN'}\nText: {row['sms_text']}")
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=192,
                do_sample=False,
                temperature=0.0,
            )
        decoded = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        parsed = extract_json(decoded)
        if not parsed:
            failures += 1
            preds_otp.append(False)
            preds_phish.append(False)
            preds_intent.append("NOT_OTP")
            continue
        is_otp, intent, is_phish = normalize_outputs(parsed)
        preds_otp.append(is_otp)
        preds_phish.append(is_phish)
        preds_intent.append(intent)

    metrics = {
        "is_otp": {
            "accuracy": accuracy_score(gold_otp, preds_otp),
            "f1": f1_score(gold_otp, preds_otp),
        },
        "is_phishing": {
            "accuracy": accuracy_score(gold_phish, preds_phish),
            "f1": f1_score(gold_phish, preds_phish),
        },
    }

    intent_acc = accuracy_score(gold_intent, preds_intent)
    intent_macro_f1 = f1_score(gold_intent, preds_intent, average="macro")
    metrics["otp_intent"] = {
        "accuracy": intent_acc,
        "f1_macro": intent_macro_f1,
    }

    print(json.dumps(metrics, indent=2))
    if failures:
        print(f"Warning: failed to parse JSON for {failures} messages.")
    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate LLM on synthetic dataset.")
    parser.add_argument("--model_path", type=Path, required=True, help="Fine-tuned model or adapter directory.")
    parser.add_argument("--base_model", type=str, default=None, help="Base model (if model_path is LoRA).")
    parser.add_argument("--synthetic_csv", type=Path, default=DATA_PATH)
    parser.add_argument("--output_json", type=Path, default=ROOT_DIR / "model_comparison_results" / "llm_synthetic_eval.json")
    return parser.parse_args()


if __name__ == "__main__":
    import torch

    evaluate(parse_args())

