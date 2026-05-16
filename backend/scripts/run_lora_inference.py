"""
Quick inference script to sanity-check the Qwen SMS LoRA adapter.

Example:
    python backend/scripts/run_lora_inference.py \
        --adapter_dir backend/models/qwen_sms_lora \
        --eval_jsonl backend/data/llm_train.jsonl \
        --num_samples 5 \
        --max_new_tokens 256 \
        --temperature 0.1
"""

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

from datasets import load_dataset
from peft import PeftModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

PROMPT_TEMPLATE = (
    "{instruction}\n\nInput:\n{input}\n\nJSON:"
)


def load_samples(path: Path, num_samples: Optional[int], seed: int):
    dataset = load_dataset("json", data_files=str(path))["train"]
    if num_samples:
        dataset = dataset.shuffle(seed=seed)
        dataset = dataset.select(range(min(num_samples, len(dataset))))
    return dataset


def build_prompt(record: dict) -> str:
    instruction = (record.get("instruction") or "").strip()
    input_text = (record.get("input") or "").strip()
    return PROMPT_TEMPLATE.format(instruction=instruction, input=input_text)


def generate(model, tokenizer, prompt: str, max_new_tokens: int, temperature: float, top_p: float,
             repetition_penalty: float) -> str:
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    do_sample = temperature > 0
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            repetition_penalty=repetition_penalty,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    completion_ids = outputs[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(completion_ids, skip_special_tokens=True).strip()


def write_results(records: Iterable[dict], output_path: Path):
    if not output_path:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Run LoRA adapter inference on sample prompts.")
    parser.add_argument("--adapter_dir", type=Path, required=True, help="Directory with saved LoRA adapter.")
    parser.add_argument("--model_name", type=str, default="Qwen/Qwen2.5-1.5B-Instruct",
                        help="Base model to load before applying the adapter.")
    parser.add_argument("--eval_jsonl", type=Path, required=True,
                        help="JSONL file with records containing instruction/input/output fields.")
    parser.add_argument("--num_samples", type=int, default=5, help="Number of random samples to evaluate.")
    parser.add_argument("--max_new_tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--repetition_penalty", type=float, default=1.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output_jsonl", type=Path, default=None,
                        help="Optional path to save model outputs alongside ground truth.")
    return parser.parse_args()


def main():
    args = parse_args()

    dataset = load_samples(args.eval_jsonl, args.num_samples, args.seed)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        load_in_4bit=True,
        device_map="auto",
    )
    model = PeftModel.from_pretrained(model, args.adapter_dir)
    model.eval()

    results = []
    for idx, record in enumerate(dataset):
        prompt = build_prompt(record)
        prediction = generate(
            model,
            tokenizer,
            prompt,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            repetition_penalty=args.repetition_penalty,
        )
        target = record.get("output")
        if isinstance(target, str):
            expected = target
        else:
            expected = json.dumps(target, ensure_ascii=False)

        print("=" * 80)
        print(f"Sample #{idx + 1}")
        print("Instruction:", record.get("instruction"))
        print("Input:", record.get("input"))
        print("Model output:", prediction)
        print("Ground truth:", expected)

        results.append(
            {
                "instruction": record.get("instruction"),
                "input": record.get("input"),
                "model_output": prediction,
                "ground_truth": target,
            }
        )

    if args.output_jsonl:
        write_results(results, args.output_jsonl)
        print(f"\nSaved outputs to {args.output_jsonl}")


if __name__ == "__main__":
    main()


