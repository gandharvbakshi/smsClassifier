"""
Sample 100 LLM-labeled phishing messages and re-check them with LLaMA 3.1 via Ollama.

The script:
  1. Loads `classification_results_with_phishing_verified.csv` (falls back to
     `classification_results_with_phishing.csv` if needed).
  2. Selects 100 rows where the existing `is_phishing` label is True.
  3. Sends the messages to `llama3.1:latest` in batches of 10 using a strict
     JSON-only prompt.
  4. Prints the percentage that LLaMA also marks as phishing and writes full
     details to `llama_recheck_phishing_sample.csv`.

Usage (run from project root):

    python sample_phishing_llama_verification.py

Make sure Ollama is running and the `llama3.1:latest` model is pulled locally.
"""

import json
import os
import random
import time
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests

PRIMARY_SOURCE = "classification_results_with_phishing_verified.csv"
FALLBACK_SOURCE = "classification_results_with_phishing.csv"
OUTPUT_FILE = "llama_recheck_phishing_sample.csv"

MODEL_ID = "llama3.1:latest"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
SAMPLE_SIZE = 100
CHUNK_SIZE = 10
RANDOM_SEED = 42


PROMPT_TEMPLATE = """You are a precise SMS phishing detector.
For each message you receive:
- Decide if the message is phishing (true) or not phishing (false).
- Respond ONLY with JSON, no commentary.

Definitions:
- phishing (true): Messages that try to steal money or information, urge the user to click suspicious links, login on unknown domains, share OTP/PIN/card details, call unfamiliar numbers, or promise unrealistic rewards.
- not phishing (false): Legitimate transaction notifications, delivery updates without suspicious content, personal conversations, or anything clearly safe and informational.

High-risk indicators include URLs, urgent login/verification requests, instructions to share OTP/PIN, or promises of rewards.
Safe indicators include explicit safety warnings (“do not share OTP”), personal or conversational tone, and absence of suspicious links or demands.

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


def load_source_dataframe() -> pd.DataFrame:
    if os.path.exists(PRIMARY_SOURCE):
        df = pd.read_csv(PRIMARY_SOURCE)
        if df["is_phishing"].notna().any():
            return df
    df = pd.read_csv(FALLBACK_SOURCE)
    return df


def prepare_sample(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_phishing_original"] = df["is_phishing"].apply(to_bool)
    positives = df[df["is_phishing_original"] == True]
    if positives.empty:
        raise ValueError("No phishing-positive rows found in the source dataset.")
    sample_size = min(SAMPLE_SIZE, len(positives))
    random_state = random.Random(RANDOM_SEED)
    indices = list(positives.index)
    random_state.shuffle(indices)
    selected = positives.loc[indices[:sample_size]].copy()
    selected["original_index"] = selected["original_index"].astype(str)
    if "sms_text" not in selected.columns:
        # If the column is named differently (e.g., 'sender'/'body'), fall back to best guess.
        text_col = "sms_text"
        if "body" in selected.columns:
            selected[text_col] = selected["body"].astype(str)
        elif "sender" in selected.columns:
            selected[text_col] = selected["sender"].astype(str)
        else:
            raise ValueError("Could not locate SMS text column in dataset.")
    else:
        selected["sms_text"] = selected["sms_text"].astype(str)
    return selected.reset_index(drop=True)


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
    """
    Heuristically extract JSON objects from the model response, regardless of formatting.
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
    ]

    if "```" in content:
        for block in content.split("```"):
            cleaned = strip_fence(block)
            if cleaned:
                candidate_strings.append(cleaned)
                candidate_strings.append(cleaned.replace('\\"', '"'))
                candidate_strings.append(cleaned.replace("'", '"'))

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


def compute_summary(merged: pd.DataFrame) -> Dict[str, Any]:
    merged["is_phishing_llama_bool"] = merged["is_phishing_llama"].astype(str).str.lower().map({"true": True, "false": False})
    true_count = merged["is_phishing_llama_bool"].sum()
    total = len(merged)
    return {
        "total_samples": total,
        "llama_true_count": int(true_count),
        "percentage_true": round((true_count / total) * 100, 2) if total else 0.0,
        "elapsed_seconds": merged["elapsed_seconds"].iloc[0] if "elapsed_seconds" in merged.columns else None,
    }


def main() -> None:
    df = load_source_dataframe()
    sample = prepare_sample(df)

    predictions, elapsed = classify(sample)
    merged = sample.merge(predictions, on="original_index", how="left")
    merged["elapsed_seconds"] = elapsed

    summary = compute_summary(merged)

    merged[
        [
            "original_index",
            "sms_text",
            "is_phishing_original",
            "is_phishing_llama_bool",
            "is_phishing_llama",
            "raw_response",
        ]
    ].to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Analyzed {summary['total_samples']} phishing-positive messages.")
    print(f"LLaMA marked {summary['llama_true_count']} as phishing ({summary['percentage_true']}%).")
    if summary["elapsed_seconds"] is not None:
        print(f"Total time: {summary['elapsed_seconds']:.2f}s (avg {summary['elapsed_seconds']/summary['total_samples']:.3f}s per message)")
    print(f"Detailed predictions written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


