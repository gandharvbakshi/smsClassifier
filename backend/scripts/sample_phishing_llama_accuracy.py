"""
Sample 500 rows from classification_results_with_phishing_llm.csv and evaluate
them with local LLaMA 3.1 (Ollama) to estimate phishing label agreement.

The script:
  - Randomly samples 500 rows (or all rows if fewer than 500) using a fixed seed.
  - Calls LLaMA 3.1 in batches of 10 messages with a JSON-only prompt.
  - Compares the new predictions against the original `is_phishing` column.
  - Prints accuracy, confusion counts, and writes detailed results to
    sample_phishing_llama_accuracy_results.csv plus a summary CSV.

Usage:
    python sample_phishing_llama_accuracy.py
"""

import json
import os
import random
import time
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests

SOURCE_FILE = "classification_results_with_phishing_llm.csv"
OUTPUT_DETAIL_FILE = "sample_phishing_llama_accuracy_results.csv"
OUTPUT_SUMMARY_FILE = "sample_phishing_llama_accuracy_summary.csv"

MODEL_ID = "llama3.1:latest"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
SAMPLE_SIZE = 500
CHUNK_SIZE = 10
RANDOM_SEED = 1337


PROMPT_TEMPLATE = """You are a precise SMS phishing detector.
For each message you receive:
- Decide if the message is phishing (true) or not phishing (false).
- Respond ONLY with JSON, no commentary.

Definitions:
- phishing (true): Messages that try to steal information or money, ask the user to click suspicious links, login on unknown domains, share OTP/PIN/card details, call unfamiliar numbers, or promise unrealistic rewards.
- not phishing (false): Legitimate transaction notifications, delivery updates without suspicious content, personal conversations, or anything clearly safe and informational.

Return ONLY JSON in the form:
[
  {{"id": "<original_index>", "is_phishing": true/false}},
  ...
]

Messages:
{messages}
"""


def to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    value_str = str(value).strip().lower()
    return value_str in {"true", "1", "yes"}


def load_sample() -> pd.DataFrame:
    df = pd.read_csv(SOURCE_FILE)
    sample_size = min(SAMPLE_SIZE, len(df))
    rng = random.Random(RANDOM_SEED)
    indices = list(df.index)
    rng.shuffle(indices)
    sample = df.loc[indices[:sample_size]].copy().reset_index(drop=True)
    sample["original_index"] = sample["original_index"].astype(str)
    sample["sms_text"] = sample["sms_text"].astype(str)
    sample["is_phishing_original"] = sample["is_phishing"].apply(to_bool)
    return sample


def build_prompt(chunk: pd.DataFrame) -> str:
    messages = []
    for row in chunk.itertuples(index=False):
        sms_clean = row.sms_text.replace("\\", " ").replace('"', '\\"')
        messages.append(f'{{"id": "{row.original_index}", "sms": "{sms_clean}"}}')
    messages_block = "[\n" + ",\n".join(messages) + "\n]"
    return PROMPT_TEMPLATE.format(messages=messages_block)


def call_ollama(prompt: str) -> str:
    url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {"model": MODEL_ID, "prompt": prompt, "stream": False}
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def parse_predictions(content: str) -> List[Dict[str, Any]]:
    def strip_fence(block: str) -> str:
        candidate = block.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            newline = candidate.find("\n")
            if newline != -1:
                candidate = candidate[newline + 1 :]
            candidate = candidate.strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
        return candidate

    def try_parse(text: str) -> List[Any]:
        decoder = json.JSONDecoder()
        idx = 0
        length = len(text)
        items: List[Any] = []
        while idx < length:
            try:
                obj, next_idx = decoder.raw_decode(text, idx)
                items.append(obj)
                idx = next_idx
            except json.JSONDecodeError:
                idx += 1
        return items

    base = strip_fence(content.strip())
    candidate_strings = [
        base,
        base.replace('\\"', '"'),
        base.replace("'", '"'),
        base.replace("\\'", "'"),
    ]

    if "```" in content:
        blocks = [strip_fence(block) for block in content.split("```") if block.strip()]
        for block in blocks:
            candidate_strings.extend(
                [
                    block,
                    block.replace('\\"', '"'),
                    block.replace("'", '"'),
                ]
            )

    seen = set()
    structures: List[Any] = []
    for candidate_text in candidate_strings:
        candidate_text = candidate_text.strip()
        if not candidate_text or candidate_text in seen:
            continue
        seen.add(candidate_text)
        structures.extend(try_parse(candidate_text))

    if not structures:
        raise ValueError(f"Unable to parse JSON predictions from: {content[:200]}...")

    results: List[Dict[str, Any]] = []
    for obj in structures:
        if isinstance(obj, list):
            results.extend([item for item in obj if isinstance(item, dict)])
        elif isinstance(obj, dict):
            if "results" in obj and isinstance(obj["results"], list):
                results.extend([item for item in obj["results"] if isinstance(item, dict)])
            elif "is_phishing" in obj or "id" in obj:
                results.append(obj)

    if not results:
        raise ValueError(f"No prediction objects found in: {content[:200]}...")

    for idx, item in enumerate(results):
        if "id" not in item:
            item["id"] = f"row_{idx}"
    return results


def classify(df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    predictions: List[Dict[str, Any]] = []
    start_time = time.time()
    for start_idx in range(0, len(df), CHUNK_SIZE):
        chunk = df.iloc[start_idx : start_idx + CHUNK_SIZE]
        prompt = build_prompt(chunk)
        raw_response = call_ollama(prompt)
        parsed = parse_predictions(raw_response)
        for item in parsed:
            predictions.append(
                {
                    "original_index": item.get("id"),
                    "is_phishing_llama": item.get("is_phishing"),
                    "raw_response": raw_response,
                }
            )
    elapsed = time.time() - start_time
    return pd.DataFrame(predictions), elapsed


def compute_metrics(merged: pd.DataFrame) -> Dict[str, Any]:
    merged["is_phishing_llama_bool"] = merged["is_phishing_llama"].astype(str).str.lower().map({"true": True, "false": False})
    accuracy = (merged["is_phishing_llama_bool"] == merged["is_phishing_original"]).mean() * 100 if len(merged) else 0.0
    tp = ((merged["is_phishing_llama_bool"] == True) & (merged["is_phishing_original"] == True)).sum()
    tn = ((merged["is_phishing_llama_bool"] == False) & (merged["is_phishing_original"] == False)).sum()
    fp = ((merged["is_phishing_llama_bool"] == True) & (merged["is_phishing_original"] == False)).sum()
    fn = ((merged["is_phishing_llama_bool"] == False) & (merged["is_phishing_original"] == True)).sum()
    return {
        "total_samples": len(merged),
        "accuracy": round(accuracy, 2),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
    }


def main() -> None:
    sample = load_sample()
    predictions, elapsed = classify(sample)
    merged = sample.merge(predictions, on="original_index", how="left")
    merged["elapsed_seconds"] = elapsed

    summary = compute_metrics(merged)

    merged[
        [
            "original_index",
            "sms_text",
            "is_phishing_original",
            "is_phishing_llama_bool",
            "is_phishing_llama",
            "raw_response",
        ]
    ].to_csv(OUTPUT_DETAIL_FILE, index=False, encoding="utf-8-sig")

    summary_df = pd.DataFrame([summary])
    summary_df["avg_seconds_per_row"] = round(elapsed / summary["total_samples"], 3) if summary["total_samples"] else None
    summary_df.to_csv(OUTPUT_SUMMARY_FILE, index=False, encoding="utf-8-sig")

    print(f"Processed {summary['total_samples']} sampled rows.")
    print(f"Accuracy vs original labels: {summary['accuracy']}%")
    print(f"TP: {summary['true_positives']} | TN: {summary['true_negatives']} | FP: {summary['false_positives']} | FN: {summary['false_negatives']}")
    print(f"Total time: {elapsed:.2f}s (avg {summary_df['avg_seconds_per_row'].iloc[0]:.3f}s per row)")
    print(f"Details saved to {OUTPUT_DETAIL_FILE} and summary to {OUTPUT_SUMMARY_FILE}")


if __name__ == "__main__":
    main()


