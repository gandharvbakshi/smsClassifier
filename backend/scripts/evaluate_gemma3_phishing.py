"""
Evaluate multiple Ollama models on the phishing ground-truth set.

- Input: phishing_ground_truth_100.csv (columns: sms_text, is_phishing, etc.)
- Models: Gemma3:1b and LLaMA 3.1 (latest) served by Ollama on localhost.
- Output: prints accuracy/confusion for each model and writes detailed
          predictions to evaluate_phishing_ollama_results.csv

Usage:
    python evaluate_gemma3_phishing.py

(Ensure Ollama is running and both models are pulled.)
"""

import json
import os
from typing import Any, Dict, List, Tuple
import time

import pandas as pd
import requests

GROUND_TRUTH_FILE = "phishing_ground_truth_100.csv"
OUTPUT_FILE = "evaluate_phishing_ollama_results.csv"
MODELS = [
    {"name": "Gemma3 1B", "id": "gemma3:1b"},
    {"name": "Gemma3 12B", "id": "gemma3:12b"},
    {"name": "LLaMA 3.1 Latest", "id": "llama3.1:latest"},
]
CHUNK_SIZE = 10
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


PROMPT_TEMPLATE = """You are a precise phishing detector for SMS messages.
For each message you receive:
- Decide if the message is phishing (true) or not phishing (false).
- Respond ONLY with JSON, no commentary.

Definitions:
- phishing (true): Messages that try to steal information or money, ask the user to click suspicious links, login on unknown domains, share OTP/PIN/card details, call strange numbers, or promise unrealistic rewards.
- not phishing (false): Routine alerts (transaction notices, delivery updates, OTP reminders that include clear safety language), personal conversations, legitimate reminders, and anything without suspicious elements.

High-risk indicators:
- URLs/domains (http://, https://, .com, .in, shortened links).
- Urgent requests to login, verify, update, reply, call, or share credentials/PIN/OTP.
- Promises of prizes, rewards, cashback, lotteries, free upgrades.
- Unknown phone numbers asking for action.

Safe indicators:
- Standard bank alerts that explicitly say “do not share OTP/PIN”.
- Delivery updates with no suspicious links.
- Clear instructions that no action is required.
- Personal or conversational messages.

Examples:
1. SMS: "Claim your free reward now at http://bit.ly/win-5000"
   Output: {{\\"is_phishing\\": true}}
2. SMS: "HDFC Bank: Rs.345.32 debited from A/C XX1245 on 14 Feb. Avl bal Rs. 45,932. Do not share OTP with anyone."
   Output: {{\\"is_phishing\\": false}}

Now classify the following messages. Respond ONLY with a JSON array where each element matches:
{{\\"id\\": \\"<original_index>\\", \\"is_phishing\\": true/false}}

Messages:
{messages}
"""


def load_ground_truth(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "sms_text" not in df.columns or "is_phishing" not in df.columns:
        raise ValueError("Ground truth file must contain 'sms_text' and 'is_phishing' columns.")
    df["is_phishing_truth"] = df["is_phishing"].astype(bool)
    df["original_index"] = df["original_index"].astype(str)
    return df


def build_prompt(chunk: pd.DataFrame) -> str:
    messages = []
    for row in chunk.itertuples(index=False):
        sms_clean = str(row.sms_text).replace("\\", " ").replace('"', '\\"')
        messages.append(f'{{"id": "{row.original_index}", "sms": "{sms_clean}"}}')
    messages_block = "[\n" + ",\n".join(messages) + "\n]"
    return PROMPT_TEMPLATE.format(messages=messages_block)


def call_ollama(model_id: str, prompt: str) -> str:
    url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {"model": model_id, "prompt": prompt, "stream": False}
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def parse_predictions(content: str) -> List[Dict[str, Any]]:
    """
    Attempt to recover JSON predictions from potentially messy LLM output.
    Handles arrays, newline-delimited objects, and fenced code blocks.
    """

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
        structures = []
        while idx < length:
            try:
                obj, next_idx = decoder.raw_decode(text, idx)
                structures.append(obj)
                idx = next_idx
            except json.JSONDecodeError:
                idx += 1
        return structures

    # Build candidate strings by progressively normalising the content.
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

    seen_texts = set()
    candidates: List[Any] = []
    for candidate_text in candidate_strings:
        candidate_text = candidate_text.strip()
        if not candidate_text or candidate_text in seen_texts:
            continue
        seen_texts.add(candidate_text)
        extracted = try_parse(candidate_text)
        if not extracted:
            continue
        candidates.extend(extracted)

    # Post-process structures into prediction dicts.
    results: List[Dict[str, Any]] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            results.extend([item for item in candidate if isinstance(item, dict)])
        elif isinstance(candidate, dict):
            if "results" in candidate and isinstance(candidate["results"], list):
                results.extend([item for item in candidate["results"] if isinstance(item, dict)])
            elif "is_phishing" in candidate or "id" in candidate:
                results.append(candidate)

    if not results:
        raise ValueError(f"Could not parse JSON predictions from: {content[:200]}...")

    for idx, item in enumerate(results):
        if "id" not in item:
            item["id"] = f"row_{idx}"
    return results


def classify(df: pd.DataFrame, model_id: str, model_name: str) -> Tuple[pd.DataFrame, float]:
    predictions: List[Dict[str, Any]] = []
    total = len(df)
    start_time = time.time()
    for start in range(0, total, CHUNK_SIZE):
        chunk = df.iloc[start : start + CHUNK_SIZE]
        prompt = build_prompt(chunk)
        raw_response = call_ollama(model_id, prompt)
        parsed = parse_predictions(raw_response)
        for item in parsed:
            predictions.append(
                {
                    "original_index": item.get("id"),
                    "predicted_is_phishing": item.get("is_phishing"),
                    "model_id": model_id,
                    "model_name": model_name,
                    "raw_response": raw_response,
                }
            )
    elapsed = time.time() - start_time
    return pd.DataFrame(predictions), elapsed


def compute_metrics(merged: pd.DataFrame) -> Tuple[float, int, int, int, int]:
    merged["pred_bool"] = merged["predicted_is_phishing"].astype(str).str.lower().map({"true": True, "false": False})
    merged["correct"] = merged["pred_bool"] == merged["is_phishing_truth"]
    accuracy = merged["correct"].mean() * 100 if len(merged) else 0.0
    tp = ((merged["pred_bool"] == True) & (merged["is_phishing_truth"] == True)).sum()
    tn = ((merged["pred_bool"] == False) & (merged["is_phishing_truth"] == False)).sum()
    fp = ((merged["pred_bool"] == True) & (merged["is_phishing_truth"] == False)).sum()
    fn = ((merged["pred_bool"] == False) & (merged["is_phishing_truth"] == True)).sum()
    return accuracy, tp, tn, fp, fn


def main() -> None:
    ground_truth = load_ground_truth(GROUND_TRUTH_FILE)
    all_results: List[pd.DataFrame] = []

    for model in MODELS:
        model_id = model["id"]
        model_name = model["name"]
        print(f"Running model: {model_name} ({model_id}) on {len(ground_truth)} messages...")

        predictions, elapsed = classify(ground_truth, model_id, model_name)
        merged = ground_truth.merge(predictions, on="original_index", how="left")
        merged["model_id"] = model_id
        merged["model_name"] = model_name
        merged["elapsed_seconds"] = elapsed
        all_results.append(merged)

        accuracy, tp, tn, fp, fn = compute_metrics(merged)
        print(f"{model_name} Accuracy: {accuracy:.2f}%")
        print(f"TP: {tp} | TN: {tn} | FP: {fp} | FN: {fn}")
        print(f"Total time: {elapsed:.2f}s | Avg per row: {elapsed / len(ground_truth):.3f}s")

        mismatches = merged[merged["correct"] == False]
        if not mismatches.empty:
            print("\nSample disagreements (up to 5):")
            print(
                mismatches[
                    ["original_index", "sms_text", "is_phishing_truth", "predicted_is_phishing"]
                ]
                .head(5)
                .to_string(index=False)
            )
        print("-" * 60)

    results_df = pd.concat(all_results, ignore_index=True)
    results_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    summary_records = []
    for model in MODELS:
        model_data = results_df[results_df["model_id"] == model["id"]]
        accuracy, tp, tn, fp, fn = compute_metrics(model_data)
        summary_records.append(
            {
                "model_name": model["name"],
                "model_id": model["id"],
                "accuracy": round(accuracy, 2),
                "avg_seconds_per_row": round(merged["elapsed_seconds"].iloc[0] / len(ground_truth), 3),
                "true_positives": tp,
                "true_negatives": tn,
                "false_positives": fp,
                "false_negatives": fn,
            }
        )

    summary_df = pd.DataFrame(summary_records)
    print("\nComparison Summary:")
    print(summary_df.to_string(index=False))

    summary_df.to_csv("evaluate_phishing_ollama_summary.csv", index=False, encoding="utf-8-sig")



if __name__ == "__main__":
    main()


