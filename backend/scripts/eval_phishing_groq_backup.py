"""
Compare phishing accuracy: LightGBM alone vs Groq-assisted policies.

Standalone (no FastAPI import). One Groq call per row. Policies:
  baseline — is_phishing = (phish_prob >= threshold)
  veto     — if ML positive, require Groq is_phishing True (else clear)
  gray     — if prob in [low, high), use Groq decision; else baseline

  cd backend && python scripts/eval_phishing_groq_backup.py --limit 100
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from scipy.sparse import csr_matrix, hstack

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR.parent / "android_sms_classifier" / "app" / ".env")
load_dotenv(ROOT_DIR.parent / ".env")
load_dotenv(ROOT_DIR / ".env")

MODEL_DIR = ROOT_DIR / "trained_models"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.pkl"
LGB_PHISH_PATH = MODEL_DIR / "model_phishing_lgb.pkl"
GROQ_MODEL = os.getenv("GROQ_INTENT_MODEL", "llama-3.1-8b-instant")
GROQ_TIMEOUT = float(os.getenv("GROQ_TIMEOUT", "45"))
_SESSION = requests.Session()

TEXT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\d",
        r"\botp\b",
        r"do not share|never share",
        r"https?://|www\.",
        r"\blogin\b|\bverify\b|\bupdate\b|\bclick\b|\bcall\b|\bshare\b",
        r"bank never asks|otp is secret|do not disclose",
        r"sms block 7007",
        r"reward|win|cashback|lottery|prize|gift",
        r"\b(trading|investment|portfolio|demat|mutual fund|stocks|NSE|BSE|Zerodha|Groww|Upstox|broker|equity|Angel One|Kotak Securities|ICICI Direct|HDFC Securities)\b",
        r"\b(social|entertainment|streaming|gaming|shopping|app login|account login)\b",
        r"\b(delivery|deliver|courier|package|order|shipment|tracking|OTP.*delivery|share.*code.*delivery)\b",
        r"\b(UPI|unified payments|PIN|device.*link|link.*device|bind.*device)\b",
        r"\b(KYC|know your customer|e-sign|esign|document.*sign|verification.*document)\b",
        r"\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|update.*contact)\b",
        r"\b(one time password|OTP|verification code|authentication code|this is your.*code|your.*code is|give.*code|share.*code|delivery code)\b",
        r"\b(INR|Rs\.?|₹)\s*\d+[.,]?\d*\b",
        r"\b(XX\d+|xxxx\d+|card.*XX|account.*XX)\b",
        r"\b(urgent|immediately|act now|expires.*soon|limited time|verify now)\b",
        r"\b(bit\.ly|tinyurl|short\.link|click.*here|verify.*link)\b",
    ]
]

SENDER_PATTERNS = [
    re.compile(r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY)\b"),
    re.compile(r"\b(SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART)\b"),
    re.compile(r"\b(NETFLIX|SPOTIFY|INSTAGRAM|FACEBOOK|TWITTER)\b"),
    re.compile(r"^\d{10,12}$"),
]


def _load_pickle(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}")
    with open(path, "rb") as handle:
        return pickle.load(handle)


VECTORIZER = _load_pickle(VECTORIZER_PATH, "TF-IDF vectorizer")
LGB_PHISH = _load_pickle(LGB_PHISH_PATH, "LightGBM phishing model")


def extract_heuristic_features(text: str, sender: Optional[str]) -> np.ndarray:
    text = text or ""
    sender = sender or ""
    features = [1.0 if pattern.search(text) else 0.0 for pattern in TEXT_PATTERNS]
    sender_upper = sender.upper()
    features.extend(1.0 if pattern.search(sender_upper) else 0.0 for pattern in SENDER_PATTERNS)
    return np.asarray(features, dtype=np.float32)


def build_feature_matrix(text: str, sender: Optional[str]) -> csr_matrix:
    tfidf = VECTORIZER.transform([text])
    heuristics = extract_heuristic_features(text, sender).reshape(1, -1)
    heuristics_sparse = csr_matrix(heuristics)
    return hstack([tfidf, heuristics_sparse], format="csr")


def phish_prob_row(text: str, sender: Optional[str]) -> float:
    X = build_feature_matrix(text, sender)
    p = LGB_PHISH.predict_proba(X)[0]
    return float(p[1])


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def call_groq(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise EnvironmentError("GROQ_API_KEY required")
    response = _SESSION.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 128,
            "response_format": {"type": "json_object"},
        },
        timeout=GROQ_TIMEOUT,
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


def groq_phishing_only(text: str, sender: Optional[str]) -> Tuple[bool, float]:
    sender_str = (sender or "UNKNOWN").strip()
    sms_str = (text or "").replace("\r\n", "\n").strip()
    system = (
        "You classify SMS for phishing/scam (credential theft, fake bank links, "
        "malicious shortened URLs, impersonation). Legitimate bank marketing or "
        "security education from known banks is NOT phishing.\n"
        'Reply ONLY with JSON: {"is_phishing": <true|false>}. No other keys.'
    )
    user = f"Sender: {sender_str}\nSMS: {sms_str}\nReturn JSON now."
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    t0 = time.time()
    raw = call_groq(messages)
    lat = (time.time() - t0) * 1000
    parsed = extract_prediction(raw) or {}
    return normalize_bool(parsed.get("is_phishing", False)), lat


def coerce_label(v: Any) -> int:
    if isinstance(v, bool):
        return int(v)
    if pd.isna(v):
        return 0
    s = str(v).strip().lower()
    if s in {"true", "1", "yes"}:
        return 1
    if s in {"false", "0", "no", ""}:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def sample_df(df: pd.DataFrame, limit: int, seed: int) -> pd.DataFrame:
    pos = df[df["y"] == 1]
    neg = df[df["y"] == 0]
    half = limit // 2
    take_p = min(len(pos), half)
    take_n = min(len(neg), limit - take_p)
    if take_n < half:
        take_p = min(len(pos), limit - take_n)
    pos_s = pos.sample(n=take_p, random_state=seed) if take_p else pos.iloc[0:0]
    neg_s = neg.sample(n=take_n, random_state=seed + 1) if take_n else neg.iloc[0:0]
    return pd.concat([pos_s, neg_s], axis=0).sample(frac=1.0, random_state=seed + 2)


def metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    from sklearn.metrics import f1_score, precision_score, recall_score

    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=ROOT_DIR / "data" / "classification_training_merged_jury_may2026.csv")
    ap.add_argument("--limit", type=int, default=160)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--gray-low", type=float, default=0.35)
    ap.add_argument("--gray-high", type=float, default=0.72)
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("GROQ_API_KEY not set")

    df = pd.read_csv(args.csv, low_memory=False)
    col = "is_phishing_original" if "is_phishing_original" in df.columns else "is_phishing"
    if col not in df.columns:
        raise SystemExit(f"No phishing label column in {args.csv}")
    df = df.dropna(subset=["sms_text"])
    df["y"] = df[col].map(coerce_label)
    df["sender"] = df["sender"].astype(str) if "sender" in df.columns else ""
    sample = sample_df(df, args.limit, args.seed)

    y_true: List[int] = []
    ml_bin: List[int] = []
    veto_pred: List[int] = []
    gray_pred: List[int] = []
    groq_only: List[int] = []
    latencies: List[float] = []

    for _, row in sample.iterrows():
        text = str(row["sms_text"])
        sender = str(row.get("sender", "") or "")
        yt = int(row["y"])
        y_true.append(yt)
        p = phish_prob_row(text, sender)
        mlb = 1 if p >= args.threshold else 0
        ml_bin.append(mlb)

        g_phish, lat = groq_phishing_only(text, sender)
        latencies.append(lat)
        groq_only.append(1 if g_phish else 0)

        if mlb == 0:
            veto_pred.append(0)
        else:
            veto_pred.append(1 if g_phish else 0)

        if args.gray_low <= p < args.gray_high:
            gray_pred.append(1 if g_phish else 0)
        else:
            gray_pred.append(mlb)

        time.sleep(args.sleep)

    out = {
        "n": len(y_true),
        "threshold": args.threshold,
        "gray_band": [args.gray_low, args.gray_high],
        "baseline_ml": metrics(y_true, ml_bin),
        "groq_only": metrics(y_true, groq_only),
        "veto_ml_then_groq": metrics(y_true, veto_pred),
        "gray_band_groq": metrics(y_true, gray_pred),
        "avg_latency_ms_groq": float(np.mean(latencies)) if latencies else 0.0,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
