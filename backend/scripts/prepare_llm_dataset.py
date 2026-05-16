"""
Prepare supervised fine-tuning data for the SMS LLM.

Reads the main training CSV, normalizes columns, and writes a JSONL file with
instruction/input/output records suitable for LoRA/QLoRA training.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DEFAULT_INPUT = DATA_DIR / "classification_results_with_phishing_llm_balanced_with_sender.csv"
DEFAULT_OUTPUT = DATA_DIR / "llm_train.jsonl"

INSTRUCTION = (
    "You are an SMS security assistant. Read the sender and SMS body, "
    "then respond ONLY with JSON that matches this schema:\n"
    "{\"is_otp\": <true|false>, \"otp_intent\": \"...\", "
    "\"is_phishing\": <true|false>, \"reason\": \"...\"}\n"
    "Use the canonical intent labels from training data."
)


def build_reason(row: pd.Series) -> str:
    reasons = []
    text_lower = row["sms_text"].lower()
    if row["predicted_is_otp"]:
        reasons.append("Detected OTP keywords")
    else:
        if "otp" not in text_lower and "code" not in text_lower:
            reasons.append("No OTP keywords present")
    if row["is_phishing_original"]:
        if any(word in text_lower for word in ["urgent", "suspend", "verify", "http", "bit.ly", "click"]):
            reasons.append("Suspicious urgency or link")
        else:
            reasons.append("Message pattern matches phishing cluster")
    else:
        reasons.append("Message matches non-phishing distribution")
    if not reasons:
        reasons.append("General classification based on training data")
    return "; ".join(reasons)


def normalize_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False, "1": True, "0": False})
        .astype(bool)
    )


def prepare_dataset(args):
    df = pd.read_csv(args.train_csv)
    expected = [
        "sms_text",
        "sender",
        "predicted_is_otp",
        "predicted_otp_intent",
        "is_phishing_original",
    ]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {args.train_csv}: {missing}")

    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    df["sender"] = df["sender"].fillna("").astype(str)
    df["predicted_is_otp"] = normalize_bool(df["predicted_is_otp"])
    df["is_phishing_original"] = normalize_bool(df["is_phishing_original"])
    df.loc[~df["predicted_is_otp"], "predicted_otp_intent"] = "NOT_OTP"
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)

    if args.max_rows:
        df = df.sample(n=min(args.max_rows, len(df)), random_state=2025)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            record = {
                "instruction": INSTRUCTION,
                "input": f"Sender: {row['sender'] or 'UNKNOWN'}\nText: {row['sms_text']}",
                "output": {
                    "is_otp": bool(row["predicted_is_otp"]),
                    "otp_intent": row["predicted_otp_intent"],
                    "is_phishing": bool(row["is_phishing_original"]),
                    "reason": build_reason(row),
                },
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(df)} records to {args.output_jsonl}")


def parse_args():
    parser = argparse.ArgumentParser(description="Create JSONL for LLM fine-tuning.")
    parser.add_argument("--train_csv", type=Path, default=DEFAULT_INPUT, help="Training CSV path.")
    parser.add_argument("--output_jsonl", type=Path, default=DEFAULT_OUTPUT, help="Destination JSONL file.")
    parser.add_argument("--max_rows", type=int, default=None, help="Optional limit for debugging.")
    return parser.parse_args()


if __name__ == "__main__":
    prepare_dataset(parse_args())

