"""
FastAPI service that exposes the ensemble classification logic to Android clients.

The service combines:
  - LightGBM models (trained offline) for `is_otp` and `is_phishing`
  - Groq's `llama-3.1-8b-instant` for OTP intent classification when an OTP is detected

Run locally for testing:
    uvicorn backend.scripts.android_backend_server:app --host 0.0.0.0 --port 8001 --reload
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pickle
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from scipy.sparse import csr_matrix, hstack

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sms_backend_server")
LOG_MESSAGE_BODY = os.getenv("LOG_RAW_MESSAGES", "").lower() in {"1", "true", "yes"}

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT_DIR / "trained_models"

VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.pkl"
LGB_ISOTP_PATH = MODEL_DIR / "model_isotp_lgb.pkl"
LGB_PHISH_PATH = MODEL_DIR / "model_phishing_lgb.pkl"

OTP_THRESHOLD = float(os.getenv("OTP_THRESHOLD", "0.5"))
PHISH_THRESHOLD = float(os.getenv("PHISH_THRESHOLD", "0.5"))
GROQ_MODEL = os.getenv("GROQ_INTENT_MODEL", "llama-3.1-8b-instant")
GROQ_TIMEOUT = float(os.getenv("GROQ_TIMEOUT", "45"))

# Intent metadata reused from synthetic evaluation script
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


class ClassifyRequest(BaseModel):
    text: str = Field(..., description="SMS text body")
    sender: Optional[str] = Field(None, description="Alphanumeric sender id or phone number")


class ClassifyResponse(BaseModel):
    isOtp: bool
    otpIntent: str
    isPhishing: bool
    phishScore: float
    reasons: List[str]


class HealthResponse(BaseModel):
    status: str
    modelsLoaded: bool
    groqModel: str


@dataclass
class GroqIntentResult:
    intent: str
    latency_ms: float
    raw_response: Dict[str, Any]


def _load_pickle(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}")
    with open(path, "rb") as handle:
        return pickle.load(handle)


VECTORIZER = _load_pickle(VECTORIZER_PATH, "TF-IDF vectorizer")
LGB_ISOTP = _load_pickle(LGB_ISOTP_PATH, "LightGBM is_otp model")
LGB_PHISH = _load_pickle(LGB_PHISH_PATH, "LightGBM phishing model")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is required to start the backend server.")

REQUEST_SESSION = requests.Session()

app = FastAPI(title="SMS Ensemble Backend", version="0.1.0")
api_router = APIRouter(prefix="/api")


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


def normalize_intent(intent: Optional[str], is_otp: bool) -> str:
    if not is_otp:
        return "NOT_OTP"
    if not intent:
        return "NOT_OTP"
    candidate = intent.strip().upper().replace(" ", "_")
    candidate = INTENT_ALIASES.get(candidate, candidate)
    return candidate if candidate in INTENT_LABELS else "NOT_OTP"


def build_messages(sender: Optional[str], sms_text: str) -> List[Dict[str, str]]:
    sender_str = sender.strip() if sender else "UNKNOWN"
    sms_str = sms_text.replace("\r\n", "\n").strip()
    user_content = USER_TEMPLATE.format(sender=sender_str, sms=sms_str)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def call_groq(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    response = REQUEST_SESSION.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 256,
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


def classify_intent_with_groq(text: str, sender: Optional[str]) -> GroqIntentResult:
    messages = build_messages(sender or "UNKNOWN", text)
    start = time.time()
    raw_response = call_groq(messages)
    parsed = extract_prediction(raw_response)
    latency_ms = (time.time() - start) * 1000
    if not parsed:
        raise ValueError("Groq response missing valid JSON content.")
    is_otp_flag = normalize_bool(parsed.get("is_otp", True))
    intent = normalize_intent(parsed.get("otp_intent"), is_otp_flag)
    return GroqIntentResult(intent=intent, latency_ms=latency_ms, raw_response=raw_response)


@api_router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        modelsLoaded=all([VECTORIZER, LGB_ISOTP, LGB_PHISH]),
        groqModel=GROQ_MODEL,
    )


@api_router.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest) -> ClassifyResponse:
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Request text must not be empty.")

    feature_matrix = build_feature_matrix(request.text, request.sender)
    dense_features = feature_matrix.toarray()

    isotp_probs = LGB_ISOTP.predict_proba(dense_features)[0]
    isotp_prob = float(isotp_probs[1])
    is_otp = isotp_prob >= OTP_THRESHOLD

    phish_probs = LGB_PHISH.predict_proba(dense_features)[0]
    phish_prob = float(phish_probs[1])
    is_phishing = phish_prob >= PHISH_THRESHOLD

    reasons = [
        f"is_otp LightGBM prob={isotp_prob:.3f} (threshold={OTP_THRESHOLD})",
        f"is_phishing LightGBM prob={phish_prob:.3f} (threshold={PHISH_THRESHOLD})",
    ]

    otp_intent = "NOT_OTP"
    if is_otp:
        try:
            groq_result = classify_intent_with_groq(request.text, request.sender)
            otp_intent = groq_result.intent
            reasons.append(f"Groq intent={otp_intent} ({groq_result.latency_ms:.0f} ms)")
            if otp_intent == "BANK_OR_CARD_TXN_OTP":
                reasons.append("Bank/card OTP – approve only if you just initiated the transaction. Never share this code.")
            elif otp_intent in {"FINANCIAL_LOGIN_OTP", "APP_ACCOUNT_CHANGE_OTP", "UPI_TXN_OR_PIN_OTP"}:
                reasons.append("Sensitive account OTP – only enter inside your trusted app/site. Do not share with anyone.")
            elif otp_intent in {"DELIVERY_OR_SERVICE_OTP"}:
                reasons.append("Delivery OTP – share only with the delivery agent in person.")
        except Exception as exc:  # noqa: BLE001
            reasons.append(f"Groq intent failed: {exc}")
    else:
        reasons.append("Intent skipped because message classified as NOT_OTP")

    logger.info(
        "classified message",
        extra={
            "text": request.text if LOG_MESSAGE_BODY else request.text[:32] + ("…" if len(request.text) > 32 else ""),
            "sender": request.sender,
            "is_otp_true": is_otp,
            "is_phishing": is_phishing,
            "otp_intent": otp_intent,
            "phish_prob": phish_prob,
            "isotp_prob": isotp_prob,
        },
    )

    return ClassifyResponse(
        isOtp=is_otp,
        otpIntent=otp_intent,
        isPhishing=is_phishing,
        phishScore=phish_prob,
        reasons=reasons,
    )


app.include_router(api_router)


@app.get("/")
def index():
    return {"status": "ok", "docs": "/docs"}


