"""
Evaluate Groq's llama-3.1-8b-instant model on the verified synthetic test set.

Example usage:
    python backend/scripts/eval_groq_llama_on_synthetic.py --limit 50 --verbose

Requirements:
    - GROQ_API_KEY available in the environment or .env file
    - pandas, requests, scikit-learn, python-dotenv installed
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT_DIR / "data" / "synthetic_test_set_200_verified.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "model_comparison_results"
DEFAULT_MODEL = "llama-3.1-8b-instant"

INTENT_LABELS = [
    "NOT_OTP",
    "APP_ACCOUNT_CHANGE_OTP",
    "APP_LOGIN_OTP",
    "BANK_OR_CARD_TXN_OTP",
    "DELIVERY_OR_SERVICE_OTP",
    "FINANCIAL_LOGIN_OTP",
    "GENERIC_APP_ACTION_OTP",
    "KYC_OR_ESIGN_OTP",
    "UPI_TXN_OR_PIN_OTP",
]

INTENT_ALIASES = {
    "GENERIC_APP_OTP": "GENERIC_APP_ACTION_OTP",
    "APP_ACTION_OTP": "GENERIC_APP_ACTION_OTP",
    "APP_ACCOUNT_OTP": "APP_ACCOUNT_CHANGE_OTP",
    "ACCOUNT_CHANGE_OTP": "APP_ACCOUNT_CHANGE_OTP",
    "UPI_OTP": "UPI_TXN_OR_PIN_OTP",
    "UPI_PIN_OTP": "UPI_TXN_OR_PIN_OTP",
    "KYC_OTP": "KYC_OR_ESIGN_OTP",
    "ESIGN_OTP": "KYC_OR_ESIGN_OTP",
    "BANK_CARD_OTP": "BANK_OR_CARD_TXN_OTP",
    "CARD_TRANSACTION_OTP": "BANK_OR_CARD_TXN_OTP",
    "FINANCIAL_APP_LOGIN_OTP": "FINANCIAL_LOGIN_OTP",
    "DELIVERY_OTP": "DELIVERY_OR_SERVICE_OTP",
}

SYSTEM_PROMPT = (
    "You are an SMS security classifier. For each message you must decide:\n"
    "1) does it contain a numeric One-Time Password (OTP)?\n"
    "2) what high-level OTP intent applies?\n"
    "3) is it a phishing attempt?\n\n"
    "Allowed intents:\n"
    "  - NOT_OTP (no usable OTP code present)\n"
    "  - APP_ACCOUNT_CHANGE_OTP (OTP for changing account details)\n"
    "  - APP_LOGIN_OTP (non-financial app login)\n"
    "  - BANK_OR_CARD_TXN_OTP (bank/card transaction approval)\n"
    "  - DELIVERY_OR_SERVICE_OTP (delivery/service verification)\n"
    "  - FINANCIAL_LOGIN_OTP (banking or trading login)\n"
    "  - GENERIC_APP_ACTION_OTP (generic in-app actions)\n"
    "  - KYC_OR_ESIGN_OTP (KYC/e-sign/document signing)\n"
    "  - UPI_TXN_OR_PIN_OTP (UPI transfers, PIN or device binding)\n\n"
    "Rules:\n"
    "- If no numeric OTP appears, set is_otp=false and otp_intent=NOT_OTP.\n"
    "- If is_otp=false you MUST return otp_intent=NOT_OTP.\n"
    "- Respond ONLY with JSON: "
    '{"is_otp": <true|false>, "otp_intent": "<label>", "is_phishing": <true|false>}.\n'
    "- No Markdown, prose, or additional keys."
)

USER_TEMPLATE = (
    "Sender: {sender}\n"
    "SMS: {sms}\n"
    "Return the JSON now."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Groq llama-3.1-8b-instant on the synthetic test set.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Groq model name to invoke.")
    parser.add_argument("--synthetic_csv", type=Path, default=DEFAULT_DATASET, help="Path to synthetic test CSV.")
    parser.add_argument("--output_json", type=Path, default=DEFAULT_OUTPUT_DIR / "groq_llama_synthetic_metrics.json")
    parser.add_argument(
        "--output_predictions",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "groq_llama_synthetic_predictions.csv",
    )
    parser.add_argument("--limit", type=int, help="Limit the evaluation to the first N rows.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between API calls.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max_tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def normalize_intent(intent: Optional[str], is_otp: bool) -> str:
    if not is_otp:
        return "NOT_OTP"
    if not intent:
        return "NOT_OTP"
    candidate = intent.strip().upper().replace(" ", "_")
    candidate = INTENT_ALIASES.get(candidate, candidate)
    return candidate if candidate in INTENT_LABELS else "NOT_OTP"


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)
    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    if "sender" not in df.columns:
        df["sender"] = ""
    df["sender"] = df["sender"].astype(str).fillna("")
    df["true_is_otp"] = df["predicted_is_otp"].apply(normalize_bool)
    df["true_is_phishing"] = df["is_phishing_original"].apply(normalize_bool)
    df["true_intent"] = df["predicted_otp_intent"].astype(str).fillna("NOT_OTP").str.upper()
    df.loc[~df["true_is_otp"], "true_intent"] = "NOT_OTP"
    return df


def build_messages(sender: str, sms_text: str) -> List[Dict[str, str]]:
    sender_str = sender.strip() or "UNKNOWN"
    sms_str = sms_text.replace("\r\n", "\n").strip()
    user_content = USER_TEMPLATE.format(sender=sender_str, sms=sms_str)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def call_groq(
    session: requests.Session,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    response = session.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def extract_prediction(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def compute_binary_metrics(y_true: List[bool], y_pred: List[bool]) -> Dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }


def compute_intent_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
    }


def evaluate(args: argparse.Namespace, api_key: str) -> None:
    df = load_dataset(args.synthetic_csv)
    if args.limit:
        df = df.head(args.limit).copy()
    total_rows = len(df)
    if total_rows == 0:
        raise ValueError("Synthetic dataset is empty.")

    session = requests.Session()

    pred_is_otp: List[bool] = []
    pred_is_phishing: List[bool] = []
    pred_intents: List[str] = []
    latencies: List[float] = []
    records: List[Dict[str, Any]] = []
    failures = 0

    for idx, row in df.iterrows():
        messages = build_messages(row["sender"], row["sms_text"])
        start = time.time()
        error: Optional[str] = None
        raw_response: Optional[Dict[str, Any]] = None

        try:
            raw_response = call_groq(
                session=session,
                api_key=api_key,
                model=args.model,
                messages=messages,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
            parsed = extract_prediction(raw_response)
            if not parsed:
                raise ValueError("Failed to parse JSON response.")
        except Exception as exc:  # noqa: BLE001 - need to capture any failure to mark record
            failures += 1
            error = str(exc)
            parsed = {"is_otp": False, "otp_intent": "NOT_OTP", "is_phishing": False}

        latency = time.time() - start
        latencies.append(latency)

        is_otp_pred = normalize_bool(parsed.get("is_otp"))
        intent_pred = normalize_intent(parsed.get("otp_intent"), is_otp_pred)
        is_phishing_pred = normalize_bool(parsed.get("is_phishing"))

        pred_is_otp.append(is_otp_pred)
        pred_is_phishing.append(is_phishing_pred)
        pred_intents.append(intent_pred)

        records.append(
            {
                "original_index": row.get("original_index"),
                "sender": row["sender"],
                "sms_text": row["sms_text"],
                "true_is_otp": row["true_is_otp"],
                "pred_is_otp": is_otp_pred,
                "true_otp_intent": row["true_intent"],
                "pred_otp_intent": intent_pred,
                "true_is_phishing": row["true_is_phishing"],
                "pred_is_phishing": is_phishing_pred,
                "raw_response": json.dumps(raw_response) if raw_response else None,
                "latency_ms": round(latency * 1000, 2),
                "error": error,
            }
        )

        if args.verbose:
            print(
                f"[{len(pred_is_otp)}/{total_rows}] "
                f"is_otp={is_otp_pred} intent={intent_pred} phishing={is_phishing_pred} "
                f"latency={latency:.2f}s {'ERROR: ' + error if error else ''}"
            )

        if args.sleep:
            time.sleep(args.sleep)

    metrics = {
        "model": args.model,
        "dataset": str(args.synthetic_csv),
        "rows_evaluated": total_rows,
        "failures": failures,
        "avg_latency_ms": (sum(latencies) / len(latencies)) * 1000 if latencies else 0.0,
        "is_otp": compute_binary_metrics(df["true_is_otp"].tolist(), pred_is_otp),
        "is_phishing": compute_binary_metrics(df["true_is_phishing"].tolist(), pred_is_phishing),
        "otp_intent": compute_intent_metrics(df["true_intent"].tolist(), pred_intents),
    }

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_predictions.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    pd.DataFrame.from_records(records).to_csv(args.output_predictions, index=False)

    print(json.dumps(metrics, indent=2))
    print(f"\nMetrics saved to {args.output_json}")
    print(f"Predictions saved to {args.output_predictions}")


def main() -> None:
    load_dotenv()
    args = parse_args()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not found. Add it to your environment or .env file.")
    evaluate(args, api_key)


if __name__ == "__main__":
    main()


