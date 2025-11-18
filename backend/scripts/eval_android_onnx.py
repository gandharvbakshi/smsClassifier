"""
Evaluate the ONNX models packaged for the Android app on the synthetic test set.

Example:
    python backend/scripts/eval_android_onnx.py \
        --assets_dir android_sms_classifier/app/src/main/assets \
        --synthetic_csv backend/data/synthetic_test_set_200_verified.csv \
        --vectorizer backend/trained_models/tfidf_vectorizer.pkl \
        --label_encoder backend/trained_models/label_encoder_intent.pkl
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
from pathlib import Path
from typing import Dict

import numpy as np
import onnxruntime as ort
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.metrics import accuracy_score, f1_score

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_ASSETS = PROJECT_ROOT / "android_sms_classifier" / "app" / "src" / "main" / "assets"
DEFAULT_SYNTHETIC = BACKEND_DIR / "data" / "synthetic_test_set_200_verified.csv"
DEFAULT_VECTORIZER = PROJECT_ROOT / "trained_models" / "tfidf_vectorizer.pkl"
DEFAULT_LABEL_ENCODER = PROJECT_ROOT / "trained_models" / "label_encoder_intent.pkl"

PATTERNS: Dict[str, str] = {
    "has_digits": r"\d",
    "has_otp_word": r"\botp\b",
    "has_do_not_share": r"do not share|never share",
    "has_url": r"https?://|www\.",
    "has_request": r"\blogin\b|\bverify\b|\bupdate\b|\bclick\b|\bcall\b|\bshare\b",
    "mentions_bank_safe": r"bank never asks|otp is secret|do not disclose",
    "icici_sms_block": r"sms block 7007",
    "has_reward": r"reward|win|cashback|lottery|prize|gift",
    "has_financial_context": r"\b(trading|investment|portfolio|demat|mutual fund|stocks|NSE|BSE|Zerodha|Groww|Upstox|broker|equity|Angel One|Kotak Securities|ICICI Direct|HDFC Securities)\b",
    "has_app_context": r"\b(social|entertainment|streaming|gaming|shopping|app login|account login)\b",
    "has_delivery_context": r"\b(delivery|deliver|courier|package|order|shipment|tracking|OTP.*delivery|share.*code.*delivery)\b",
    "has_upi_context": r"\b(UPI|unified payments|PIN|device.*link|link.*device|bind.*device)\b",
    "has_kyc_context": r"\b(KYC|know your customer|e-sign|esign|document.*sign|verification.*document)\b",
    "has_account_change": r"\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|update.*contact)\b",
    "has_otp_phrase": r"\b(one time password|OTP|verification code|authentication code|this is your.*code|your.*code is|give.*code|share.*code|delivery code)\b",
    "has_amount_pattern": r"\b(INR|Rs\.?|₹)\s*\d+[.,]?\d*\b",
    "has_card_mask": r"\b(XX\d+|xxxx\d+|card.*XX|account.*XX)\b",
    "has_urgent_language": r"\b(urgent|immediately|act now|expires.*soon|limited time|verify now)\b",
    "has_suspicious_link": r"\b(bit\.ly|tinyurl|short\.link|click.*here|verify.*link)\b",
}

SENDER_PATTERNS = [
    r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY)\b",
    r"\b(SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART)\b",
    r"\b(NETFLIX|SPOTIFY|INSTAGRAM|FACEBOOK|TWITTER)\b",
    r"^\d{10,12}$",
]


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    df["sender"] = df.get("sender", "").astype(str).fillna("")
    df["predicted_is_otp"] = df["predicted_is_otp"].astype(str).str.lower().map({"true": True, "false": False})
    df["is_phishing_original"] = df["is_phishing_original"].astype(str).str.lower().map({"true": True, "false": False})
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)
    return df


def build_heuristic_features(text_series: pd.Series, sender_series: pd.Series) -> csr_matrix:
    rows = []
    for idx, text in enumerate(text_series):
        feature_row = [
            bool(re.search(pattern, text, flags=re.IGNORECASE))
            for pattern in PATTERNS.values()
        ]
        sender = str(sender_series.iloc[idx]).upper()
        feature_row.extend(bool(re.search(sp, sender)) for sp in SENDER_PATTERNS)
        rows.append(feature_row)
    return csr_matrix(np.array(rows, dtype=np.float32))


def load_onnx_sessions(assets_dir: Path):
    assets_dir = assets_dir.resolve()
    sessions = {
        "phishing": ort.InferenceSession(str(assets_dir / "model_phishing.onnx")),
        "isotp": ort.InferenceSession(str(assets_dir / "model_isotp.onnx")),
        "intent": ort.InferenceSession(str(assets_dir / "model_intent.onnx")),
    }
    return sessions


def run_binary(session: ort.InferenceSession, batch: np.ndarray):
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: batch})
    labels = outputs[0].astype(int).ravel()
    probabilities = np.asarray(outputs[1])
    if probabilities.ndim == 2:
        probs = probabilities[:, 1]
    else:
        probs = probabilities.ravel()
    return labels, probs


def run_intent(session: ort.InferenceSession, batch: np.ndarray):
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: batch})
    labels = outputs[0].astype(int).ravel()
    probabilities = np.asarray(outputs[1])
    return labels, probabilities


def evaluate(args):
    df = load_dataset(args.synthetic_csv)
    with open(args.vectorizer, "rb") as f:
        vectorizer = pickle.load(f)
    with open(args.label_encoder, "rb") as f:
        label_encoder = pickle.load(f)

    X_tfidf = vectorizer.transform(df["sms_text"])
    X_heur = build_heuristic_features(df["sms_text"], df["sender"])
    X_full = hstack([X_tfidf, X_heur])
    batch = X_full.astype(np.float32).toarray()

    sessions = load_onnx_sessions(args.assets_dir)
    phish_pred, _ = run_binary(sessions["phishing"], batch)
    isotp_pred, _ = run_binary(sessions["isotp"], batch)
    intent_pred, _ = run_intent(sessions["intent"], batch)

    gold_phish = df["is_phishing_original"].astype(int).values
    gold_isotp = df["predicted_is_otp"].astype(int).values
    gold_intent = label_encoder.transform(df["predicted_otp_intent"])

    metrics = {
        "is_phishing": {
            "accuracy": accuracy_score(gold_phish, phish_pred),
            "f1": f1_score(gold_phish, phish_pred),
        },
        "is_otp": {
            "accuracy": accuracy_score(gold_isotp, isotp_pred),
            "f1": f1_score(gold_isotp, isotp_pred),
        },
        "otp_intent": {
            "accuracy": accuracy_score(gold_intent, intent_pred),
            "f1_macro": f1_score(gold_intent, intent_pred, average="macro"),
        },
    }

    print(json.dumps(metrics, indent=2))
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Android ONNX models on synthetic dataset.")
    parser.add_argument("--assets_dir", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--synthetic_csv", type=Path, default=DEFAULT_SYNTHETIC)
    parser.add_argument("--vectorizer", type=Path, default=DEFAULT_VECTORIZER)
    parser.add_argument("--label_encoder", type=Path, default=DEFAULT_LABEL_ENCODER)
    parser.add_argument("--output_json", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    evaluate(parse_args())


