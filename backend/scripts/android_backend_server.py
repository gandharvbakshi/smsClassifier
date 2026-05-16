"""
FastAPI service that exposes the ensemble classification logic to Android clients.

The service combines:
  - LightGBM models (trained offline) for `is_otp` and `is_phishing`
  - Groq's `llama-3.1-8b-instant` for OTP intent when an OTP is detected but intent is unknown
  - Optional Groq second opinion for phishing via `GROQ_PHISHING_MODE` (`off` default, `veto`, `gray`)

Run locally for testing:
    uvicorn backend.scripts.android_backend_server:app --host 0.0.0.0 --port 8001 --reload
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import numpy as np
import pickle
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
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
# Optional second opinion for phishing (default off). Eval on merged jury sample (n=100):
# LightGBM baseline beat veto/gray on F1; Groq-only was much worse than ML.
GROQ_PHISHING_MODE = os.getenv("GROQ_PHISHING_MODE", "off").strip().lower()
PHISH_GRAY_LOW = float(os.getenv("PHISH_GRAY_LOW", "0.35"))
PHISH_GRAY_HIGH = float(os.getenv("PHISH_GRAY_HIGH", "0.72"))
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

URL_PATTERN = re.compile(r"https?://[^\s<>)\]]+|www\.[^\s<>)\]]+", re.IGNORECASE)
SHORT_URL_HOSTS = {
    "bit.ly",
    "bitly.com",
    "cutt.ly",
    "goo.gl",
    "is.gd",
    "lnkd.in",
    "rb.gy",
    "shorturl.at",
    "tinyurl.com",
    "t.co",
}
BRAND_TOKEN_PATTERN = re.compile(
    r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY|"
    r"SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART|NETFLIX|SPOTIFY|"
    r"INSTAGRAM|FACEBOOK|TWITTER|GODADDY|BSE|VI)\b",
    re.IGNORECASE,
)

LEGIT_CONTEXT_PATTERNS = [
    (
        "bank transaction / standing-instruction notice",
        0.15,
        re.compile(
            r"\b("
            r"debit(?:ed)?|credit(?:ed)?|transaction|txn|standing instruction|"
            r"auto[- ]debit|auto[- ]?pay|mandate|ecs|nach|account statement|statement|"
            r"emi|scheduled payment|payment received|processed|refund(?:ed)?"
            r"|payment (?:of )?(?:rs\.?\s*)?\d+(?:[.,]\d+)? (?:was )?successful|receipt"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "delivery / order confirmation",
        0.15,
        re.compile(
            r"\b("
            r"order (?:has )?(?:confirmed|placed|shipped|dispatched)|"
            r"received your .* order|shipment|tracking|"
            r"delivery(?: update| status)?|out for delivery|courier|package|delivered"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "bill / data alert",
        0.18,
        re.compile(
            r"\b("
            r"bill due|due date|invoice|recharge|data balance|data pack|plan validity|"
            r"validity|usage alert|postpaid|prepaid|mobile data|broadband|"
            r"electricity bill|gas bill|internet bill"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "brand unsubscribe / preference link",
        0.25,
        re.compile(r"\b(unsubscribe|opt[- ]?out|sms preferences?|email preferences?)\b", re.IGNORECASE),
    ),
    (
        "security education / investor awareness",
        0.20,
        re.compile(
            r"\b(beware|unsolicited tips|take informed decision|attention investors?|security education)\b",
            re.IGNORECASE,
        ),
    ),
]

LEGIT_OTP_PATTERNS = [
    re.compile(
        r"\b(otp|verification code|verify code|login code|sign in code|"
        r"one[- ]time password|authentication code|auth code|passcode|code\s*[:#]\s*\d{4,8})\b",
        re.IGNORECASE,
    )
]

DANGER_PATTERNS = [
    (
        "credential / password collection",
        re.compile(
            r"\b("
            r"cvv|card details|bank details|account details|login details|"
            r"share otp|send otp|enter otp|confirm credentials|verify credentials|"
            r"reset password|change password|re[- ]?enter (?:your )?(?:details|credentials|password)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "KYC / account-blocked urgency",
        re.compile(
            r"\b("
            r"kyc|account blocked|blocked account|account will be blocked|"
            r"account suspended|suspended|freeze|deactivate|limited access|"
            r"verify immediately|verify now|urgent action|expires soon|"
            r"within \d+\s*(hours?|days?)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "APK / install lure",
        re.compile(
            r"\b(apk|install app|download app|sideload|unknown sources|update app)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "UPI / payment trap",
        re.compile(
            r"\b("
            r"upi|unified payments|pay request|collect request|scan qr|request money|"
            r"send money|transfer money|payment link|refund link"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]

PAYMENT_TRAP_PATTERN = re.compile(
    r"\b(upi|pay request|pay now|transfer money|send money|request money|"
    r"collect request|scan qr|qr code|payment link|refund link)\b",
    re.IGNORECASE,
)
SHORT_URL_DANGER_PATTERN = re.compile(
    r"\b(login|verify|update|password|pin|cvv|kyc|install|apk|upi|payment|transfer|"
    r"send money|request money|collect request|urgent)\b",
    re.IGNORECASE,
)


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
class GroqSmsFullResult:
    intent: str
    is_phishing: bool
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


# ---------------------------------------------------------------------------
# Misclassification feedback ingestion
#
# Endpoint:   POST /api/feedback
# Schema:     mirrors `FeedbackRequest` in the Android app
#             (com.smsclassifier.app.feedback.FeedbackUploader.kt)
#
# Storage:    JSON Lines file. By default writes to
#             `${FEEDBACK_LOG_DIR}/feedback.jsonl` (default
#             `/tmp/sms_feedback`). On Cloud Run the local FS is ephemeral, so
#             for persistence either:
#               (a) mount a Cloud Storage volume and point FEEDBACK_LOG_DIR at
#                   it (`gcsfuse` mount or Cloud Run volume mount), or
#               (b) set FEEDBACK_GCS_BUCKET (and optionally
#                   FEEDBACK_GCS_PREFIX) to upload each row as a small object,
#                   or
#               (c) replace `_persist_feedback` with a BigQuery streaming
#                   insert.
#
# Privacy:    Body content is never logged in full at INFO. We log only its
#             length and a SHA-1 hash for dedup observability.
# ---------------------------------------------------------------------------

FEEDBACK_GCS_BUCKET = os.getenv("FEEDBACK_GCS_BUCKET")
FEEDBACK_GCS_PREFIX = os.getenv("FEEDBACK_GCS_PREFIX", "misclassification/")
FEEDBACK_LOG_DIR_RAW = os.getenv("FEEDBACK_LOG_DIR")
# When GCS is configured, the local JSONL file is just a debug fallback.
# When GCS is NOT configured, we still write a local JSONL for development.
# Default to /tmp on Cloud Run-style targets — that's wiped on restart, which
# is fine because if no GCS_BUCKET is set the operator hasn't asked for
# durability anyway.
FEEDBACK_LOG_DIR = Path(FEEDBACK_LOG_DIR_RAW) if FEEDBACK_LOG_DIR_RAW else Path("/tmp/sms_feedback")
try:
    FEEDBACK_LOG_DIR.mkdir(parents=True, exist_ok=True)
    FEEDBACK_LOG_FILE: Optional[Path] = FEEDBACK_LOG_DIR / "feedback.jsonl"
except Exception as _exc:  # noqa: BLE001
    logger.warning("Could not create feedback log dir %s: %s", FEEDBACK_LOG_DIR, _exc)
    FEEDBACK_LOG_FILE = None
FEEDBACK_BODY_MAX_LEN = int(os.getenv("FEEDBACK_BODY_MAX_LEN", "4000"))
FEEDBACK_REJECT_NON_OKHTTP = os.getenv("FEEDBACK_REJECT_NON_OKHTTP", "true").lower() in {"1", "true", "yes"}
FEEDBACK_LOCK = threading.Lock()

_GCS_CLIENT = None


def _gcs_client():
    global _GCS_CLIENT
    if _GCS_CLIENT is not None:
        return _GCS_CLIENT
    if not FEEDBACK_GCS_BUCKET:
        return None
    try:
        from google.cloud import storage  # type: ignore

        _GCS_CLIENT = storage.Client()
        return _GCS_CLIENT
    except Exception as exc:  # noqa: BLE001
        logger.warning("GCS client unavailable; feedback will only be written locally: %s", exc)
        return None


class FeedbackRequest(BaseModel):
    installId: str = Field(..., min_length=8, max_length=128)
    appVersionCode: int
    appVersionName: str
    sender: str = Field(..., max_length=256)
    body: str
    predictedIsOtp: Optional[bool] = None
    predictedOtpIntent: Optional[str] = None
    predictedIsPhishing: Optional[bool] = None
    predictedPhishScore: Optional[float] = None
    userCorrection: Optional[str] = None
    userNote: Optional[str] = None
    clientCreatedAt: int


class FeedbackResponse(BaseModel):
    ok: bool
    id: Optional[str] = None
    error: Optional[str] = None


def _persist_feedback(record: Dict[str, Any]) -> None:
    line = json.dumps(record, ensure_ascii=False)
    gcs_ok = False
    client = _gcs_client()
    if client is not None and FEEDBACK_GCS_BUCKET:
        try:
            bucket = client.bucket(FEEDBACK_GCS_BUCKET)
            blob_name = (
                f"{FEEDBACK_GCS_PREFIX.rstrip('/')}/"
                f"{record['received_at']}_{record['id']}.json"
            )
            bucket.blob(blob_name).upload_from_string(
                line, content_type="application/json"
            )
            gcs_ok = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("GCS upload of feedback row failed: %s", exc)
    # Always also write local file when no GCS, or when GCS upload failed,
    # so we don't silently drop the row.
    if FEEDBACK_LOG_FILE is not None and (not FEEDBACK_GCS_BUCKET or not gcs_ok):
        try:
            with FEEDBACK_LOCK:
                with open(FEEDBACK_LOG_FILE, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Local feedback append failed: %s", exc)


@api_router.post("/feedback", response_model=FeedbackResponse)
def post_feedback(request: FeedbackRequest, http_request: Request) -> FeedbackResponse:
    if FEEDBACK_REJECT_NON_OKHTTP:
        ua = http_request.headers.get("user-agent", "")
        if "okhttp" not in ua.lower():
            raise HTTPException(status_code=403, detail="Forbidden")
    body = request.body or ""
    if not body.strip():
        raise HTTPException(status_code=400, detail="body must not be empty")
    if len(body) > FEEDBACK_BODY_MAX_LEN:
        raise HTTPException(status_code=413, detail="body too long")
    received_at = int(time.time() * 1000)
    record_id = str(uuid.uuid4())
    body_hash = hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
    record = {
        "id": record_id,
        "received_at": received_at,
        "client_user_agent": http_request.headers.get("user-agent", "")[:200],
        "body_hash": body_hash,
        **request.model_dump(),
    }
    _persist_feedback(record)
    logger.info(
        "feedback stored",
        extra={
            "id": record_id,
            "install_id": request.installId,
            "app_version_code": request.appVersionCode,
            "predicted_is_otp": request.predictedIsOtp,
            "predicted_otp_intent": request.predictedOtpIntent,
            "predicted_is_phishing": request.predictedIsPhishing,
            "predicted_phish_score": request.predictedPhishScore,
            "body_len": len(body),
            "body_hash": body_hash,
        },
    )
    return FeedbackResponse(ok=True, id=record_id)


# ---------------------------------------------------------------------------
# User-data deletion
#
# Endpoint:   DELETE /api/users/me
# Contract:   mirrors DeleteAccountClient.kt in the Android app.
#             Idempotent — returns 204 even when no rows exist for the id.
# ---------------------------------------------------------------------------

def _delete_local_feedback(install_id: str) -> int:
    """Rewrite the local JSONL dropping rows whose installId matches.

    Uses an atomic tmp-file + os.replace so a partial write never corrupts
    the live file. Holds FEEDBACK_LOCK for the full read-rewrite cycle.
    Returns the number of rows deleted.
    """
    if FEEDBACK_LOG_FILE is None or not FEEDBACK_LOG_FILE.exists():
        return 0
    deleted = 0
    tmp_path = FEEDBACK_LOG_FILE.with_suffix(".tmp")
    with FEEDBACK_LOCK:
        kept: list[str] = []
        with open(FEEDBACK_LOG_FILE, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.rstrip("\n")
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    kept.append(raw)
                    continue
                if row.get("installId") == install_id:
                    deleted += 1
                else:
                    kept.append(raw)
        with open(tmp_path, "w", encoding="utf-8") as fh:
            for line in kept:
                fh.write(line + "\n")
        os.replace(str(tmp_path), str(FEEDBACK_LOG_FILE))
    return deleted


def _delete_gcs_feedback(install_id: str) -> int:
    """Delete GCS feedback blobs whose JSON body contains a matching installId.

    Each blob is a single-row JSON object written by _persist_feedback.
    Downloads, checks, and deletes matching blobs one at a time.
    If GCS is not configured or any call fails, logs a warning and returns 0
    without raising.
    """
    client = _gcs_client()
    if client is None or not FEEDBACK_GCS_BUCKET:
        return 0
    deleted = 0
    try:
        bucket = client.bucket(FEEDBACK_GCS_BUCKET)
        blobs = list(bucket.list_blobs(prefix=FEEDBACK_GCS_PREFIX))
        for blob in blobs:
            try:
                content = blob.download_as_text(encoding="utf-8")
                row = json.loads(content)
                if row.get("installId") == install_id:
                    blob.delete()
                    deleted += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("GCS blob deletion failed for %s: %s", blob.name, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("GCS feedback deletion listing failed: %s", exc)
    return deleted


@api_router.delete("/users/me", status_code=204)
def delete_user_me(
    installId: str,
    uid: Optional[str] = None,
    authorization: Optional[str] = Header(default=None),
) -> None:
    if not installId:
        raise HTTPException(status_code=400, detail="installId is required")
    raw_token = (authorization or "").strip()
    if raw_token.startswith("Bearer "):
        raw_token = raw_token[len("Bearer "):]
    if not raw_token or raw_token != installId:
        raise HTTPException(status_code=401, detail="bearer mismatch")

    local_count = _delete_local_feedback(installId)
    gcs_count = _delete_gcs_feedback(installId)

    logger.info(
        "user data deleted",
        extra={
            "installId": installId,
            "uid": uid,
            "rows_local": local_count,
            "rows_gcs": gcs_count,
        },
    )


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


def _extract_url_hosts(text: str) -> List[str]:
    hosts: List[str] = []
    for match in URL_PATTERN.finditer(text or ""):
        raw_url = match.group(0).rstrip(").,;:!?]")
        if raw_url.startswith("www."):
            raw_url = f"http://{raw_url}"
        parsed = urlparse(raw_url)
        host = (parsed.netloc or parsed.path).lower().strip(".")
        if host.startswith("www."):
            host = host[4:]
        if host:
            hosts.append(host)
    return hosts


def _extract_brand_tokens(text: str, sender: Optional[str]) -> List[str]:
    haystack = f"{sender or ''} {text or ''}"
    return sorted({match.group(1).upper() for match in BRAND_TOKEN_PATTERN.finditer(haystack)})


def _has_strong_phishing_danger_signal(text: str, sender: Optional[str]) -> List[str]:
    normalized = f"{sender or ''} {text or ''}"
    lowered = normalized.lower()
    signals: List[str] = []

    for label, pattern in DANGER_PATTERNS:
        if pattern.search(normalized):
            signals.append(label)

    hosts = _extract_url_hosts(text)
    brand_tokens = _extract_brand_tokens(text, sender)
    if hosts and brand_tokens:
        for host in hosts:
            if host in SHORT_URL_HOSTS:
                if SHORT_URL_DANGER_PATTERN.search(normalized):
                    signals.append("suspicious shortened link in dangerous context")
                continue
            if any(token.lower() in host for token in brand_tokens):
                continue
            if SHORT_URL_DANGER_PATTERN.search(normalized) or "login" in lowered or "verify" in lowered:
                signals.append(f"brand-domain mismatch ({host})")
                break

    if PAYMENT_TRAP_PATTERN.search(normalized) and re.search(r"\b(link|url|http|www)\b", lowered):
        signals.append("payment trap with link")

    return list(dict.fromkeys(signals))


def _detect_legit_low_risk_context(
    text: str,
    sender: Optional[str],
    is_otp: bool,
    otp_intent: str,
) -> Optional[Dict[str, Any]]:
    normalized = text or ""
    reasons: List[str] = []
    if is_otp and otp_intent in {"APP_LOGIN_OTP", "APP_ACCOUNT_CHANGE_OTP", "GENERIC_APP_ACTION_OTP", "DELIVERY_OR_SERVICE_OTP"}:
        if LEGIT_OTP_PATTERNS[0].search(normalized):
            reasons.append("app OTP verification")
            return {"label": "app OTP verification", "cap": 0.08, "reasons": reasons}

    for label, cap, pattern in LEGIT_CONTEXT_PATTERNS:
        if pattern.search(normalized):
            reasons.append(label)
            return {"label": label, "cap": cap, "reasons": reasons}

    return None


def _apply_phishing_policy(
    text: str,
    sender: Optional[str],
    is_otp: bool,
    otp_intent: str,
    raw_phish_prob: float,
    is_phishing_ml: bool,
) -> tuple[bool, float, List[str]]:
    danger_signals = _has_strong_phishing_danger_signal(text, sender)
    if danger_signals:
        if is_phishing_ml:
            return True, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"] + [
                f"phishing calibration skipped: {', '.join(danger_signals)}"
            ]
        boosted = max(raw_phish_prob, PHISH_THRESHOLD)
        return True, boosted, [f"raw phishScore={raw_phish_prob:.3f}"] + [
            f"phishing promoted by high-risk signals: {', '.join(danger_signals)}"
        ]

    if not is_phishing_ml:
        return False, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"]

    low_risk_context = _detect_legit_low_risk_context(text, sender, is_otp, otp_intent)
    if not low_risk_context:
        return True, raw_phish_prob, [f"raw phishScore={raw_phish_prob:.3f}"]

    calibrated_phish_prob = min(raw_phish_prob, float(low_risk_context["cap"]))
    if calibrated_phish_prob >= PHISH_THRESHOLD:
        return True, raw_phish_prob, [
            f"raw phishScore={raw_phish_prob:.3f}",
            f"legit context matched ({low_risk_context['label']}) but calibrated score stayed above threshold",
        ]

    return False, calibrated_phish_prob, [
        f"raw phishScore={raw_phish_prob:.3f}",
        (
            f"phishing downgraded by context calibration ({low_risk_context['label']}); "
            f"calibrated phishScore={calibrated_phish_prob:.3f}"
        ),
    ]


def heuristic_confident_veto(heuristic_result: Dict[str, Any]) -> bool:
    """Return True when heuristics explicitly block OTP classification."""
    if heuristic_result.get("isOtp"):
        return False
    if float(heuristic_result.get("confidence", 0.0) or 0.0) > 0.0:
        return False
    reasons = heuristic_result.get("reasons") or []
    return any(
        str(reason).lower().startswith("heuristic otp veto:")
        for reason in reasons
    )


def _should_suppress_otp_for_phishing(danger_signals: List[str]) -> bool:
    return any(
        signal.startswith("KYC / account-blocked urgency")
        or signal.startswith("brand-domain mismatch")
        for signal in danger_signals
    )


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


def call_groq_full_classification(text: str, sender: Optional[str]) -> GroqSmsFullResult:
    messages = build_messages(sender or "UNKNOWN", text)
    start = time.time()
    raw_response = call_groq(messages)
    parsed = extract_prediction(raw_response)
    latency_ms = (time.time() - start) * 1000
    if not parsed:
        raise ValueError("Groq response missing valid JSON content.")
    is_otp_flag = normalize_bool(parsed.get("is_otp", True))
    intent = normalize_intent(parsed.get("otp_intent"), is_otp_flag)
    is_phishing = normalize_bool(parsed.get("is_phishing", False))
    return GroqSmsFullResult(
        intent=intent,
        is_phishing=is_phishing,
        latency_ms=latency_ms,
        raw_response=raw_response,
    )


def call_groq_phishing_light(text: str, sender: Optional[str]) -> GroqSmsFullResult:
    """Smaller prompt when only a phishing verdict is needed (no intent labels)."""
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
    start = time.time()
    raw_response = call_groq(messages)
    parsed = extract_prediction(raw_response) or {}
    latency_ms = (time.time() - start) * 1000
    is_phishing = normalize_bool(parsed.get("is_phishing", False))
    return GroqSmsFullResult(
        intent="NOT_OTP",
        is_phishing=is_phishing,
        latency_ms=latency_ms,
        raw_response=raw_response,
    )


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

    reasons = []
    
    # Heuristics-first approach: Run heuristics before ML
    try:
        import sys
        from pathlib import Path
        # Add parent directory to path to import classification module
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from classification.heuristic_classifier import HeuristicOtpClassifier
        heuristic_result = HeuristicOtpClassifier.classify(request.text, request.sender)
    except ImportError as e:
        # Fallback if module not available
        logger.warning(f"Heuristic classifier not available: {e}")
        heuristic_result = {"isOtp": False, "confidence": 0.0, "suggestedIntent": None, "reasons": []}
    
    # Build feature matrix for ML (sparse; LightGBM accepts CSR)
    feature_matrix = build_feature_matrix(request.text, request.sender)

    phish_probs = LGB_PHISH.predict_proba(feature_matrix)[0]
    phish_prob = float(phish_probs[1])
    is_phishing_ml = phish_prob >= PHISH_THRESHOLD
    is_phishing = is_phishing_ml
    
    # OTP detection: Use heuristics if high confidence, otherwise use ML
    is_otp = False
    otp_intent = "NOT_OTP"
    isotp_prob = None  # Initialize to None, will be set if ML is used
    heuristic_veto = heuristic_confident_veto(heuristic_result)

    if heuristic_veto:
        reasons.extend(heuristic_result.get("reasons", []))
        reasons.append("Heuristic veto blocked ML is_otp override")
        reasons.append("Intent skipped because heuristic veto classified the message as NOT_OTP")
        logger.info("Heuristic OTP veto suppressed ML override")
    elif heuristic_result.get("isOtp") and heuristic_result.get("confidence", 0.0) > 0.8:
        # High confidence heuristic match - use it
        is_otp = True
        otp_intent = heuristic_result.get("suggestedIntent") or "NOT_OTP"
        reasons.extend(heuristic_result.get("reasons", []))
        reasons.append(f"OTP detected by heuristics (confidence: {heuristic_result.get('confidence', 0.0):.2f})")
        logger.info("Using heuristic classification (high confidence)")
    else:
        # Low confidence or no heuristic match - use ML
        reasons.append("Heuristics inconclusive; falling back to ML is_otp score")
        isotp_probs = LGB_ISOTP.predict_proba(feature_matrix)[0]
        isotp_prob = float(isotp_probs[1])
        is_otp = isotp_prob >= OTP_THRESHOLD
        reasons.append(f"is_otp LightGBM prob={isotp_prob:.3f} (threshold={OTP_THRESHOLD})")
        
        # If ML says no but heuristics suggest yes with medium confidence - trust heuristics
        if not is_otp and heuristic_result.get("isOtp") and heuristic_result.get("confidence", 0.0) > 0.5:
            is_otp = True
            otp_intent = heuristic_result.get("suggestedIntent") or "NOT_OTP"
            reasons.extend(heuristic_result.get("reasons", []))
            reasons.append(f"ML negative but heuristics positive (confidence: {heuristic_result.get('confidence', 0.0):.2f})")
            logger.info("Using heuristic classification (ML disagreed)")
    
    groq_full: Optional[GroqSmsFullResult] = None

    # Intent classification (only if OTP)
    if is_otp:
        # Use heuristic intent if available, otherwise use Groq
        if otp_intent == "NOT_OTP" or not otp_intent:
            try:
                groq_full = call_groq_full_classification(request.text, request.sender)
                otp_intent = groq_full.intent
                reasons.append(f"Groq intent={otp_intent} ({groq_full.latency_ms:.0f} ms)")
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"Groq intent failed: {exc}")
                # Fallback to heuristic intent if available
                if heuristic_result.get("suggestedIntent"):
                    otp_intent = heuristic_result.get("suggestedIntent")
        
        # Add security warnings based on intent
        if otp_intent == "BANK_OR_CARD_TXN_OTP":
            reasons.append("Bank/card OTP – approve only if you just initiated the transaction. Never share this code.")
        elif otp_intent in {"FINANCIAL_LOGIN_OTP", "APP_ACCOUNT_CHANGE_OTP", "UPI_TXN_OR_PIN_OTP"}:
            reasons.append("Sensitive account OTP – only enter inside your trusted app/site. Do not share with anyone.")
        elif otp_intent in {"DELIVERY_OR_SERVICE_OTP"}:
            reasons.append("Delivery OTP – share only with the delivery agent in person.")
    else:
        reasons.append("Intent skipped because message classified as NOT_OTP")

    is_phishing, final_phish_prob, phish_policy_reasons = _apply_phishing_policy(
        request.text,
        request.sender,
        is_otp,
        otp_intent,
        phish_prob,
        is_phishing_ml,
    )
    reasons.append(f"is_phishing LightGBM prob={phish_prob:.3f} (threshold={PHISH_THRESHOLD})")
    reasons.extend(phish_policy_reasons)

    phishing_danger_signals = _has_strong_phishing_danger_signal(request.text, request.sender)
    if is_phishing and is_otp and _should_suppress_otp_for_phishing(phishing_danger_signals):
        is_otp = False
        otp_intent = "NOT_OTP"
        reasons.append(
            "OTP suppressed because high-risk phishing signals indicate a credential-capture flow"
        )

    # Optional Groq phishing (off by default)
    if GROQ_PHISHING_MODE == "gray":
        in_band = PHISH_GRAY_LOW <= phish_prob < PHISH_GRAY_HIGH
        if in_band:
            try:
                if groq_full is not None:
                    is_phishing = groq_full.is_phishing
                    final_phish_prob = phish_prob if is_phishing else min(final_phish_prob, PHISH_GRAY_LOW)
                    reasons.append(f"Groq gray-band phishing={is_phishing} (from intent call)")
                else:
                    g2 = call_groq_phishing_light(request.text, request.sender)
                    is_phishing = g2.is_phishing
                    final_phish_prob = phish_prob if is_phishing else min(final_phish_prob, PHISH_GRAY_LOW)
                    reasons.append(f"Groq gray-band phishing={is_phishing} ({g2.latency_ms:.0f} ms)")
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"Groq phishing (gray) failed: {exc}; kept ML")
                is_phishing = is_phishing_ml
                final_phish_prob = phish_prob
    elif GROQ_PHISHING_MODE == "veto" and is_phishing_ml:
        try:
            if groq_full is not None:
                is_phishing = is_phishing_ml and groq_full.is_phishing
                final_phish_prob = phish_prob if is_phishing else min(final_phish_prob, PHISH_GRAY_LOW)
                reasons.append(f"Groq phishing veto groq_phish={groq_full.is_phishing}")
            else:
                g2 = call_groq_phishing_light(request.text, request.sender)
                is_phishing = is_phishing_ml and g2.is_phishing
                final_phish_prob = phish_prob if is_phishing else min(final_phish_prob, PHISH_GRAY_LOW)
                reasons.append(f"Groq phishing veto groq_phish={g2.is_phishing} ({g2.latency_ms:.0f} ms)")
        except Exception as exc:  # noqa: BLE001
            reasons.append(f"Groq phishing veto failed: {exc}; kept ML")
            is_phishing = is_phishing_ml
            final_phish_prob = phish_prob

    # Build log extra dict, conditionally include isotp_prob if it was computed
    log_extra = {
        "text": request.text if LOG_MESSAGE_BODY else request.text[:32] + ("…" if len(request.text) > 32 else ""),
        "sender": request.sender,
        "is_otp_true": is_otp,
        "is_phishing": is_phishing,
        "otp_intent": otp_intent,
        "phish_prob_raw": phish_prob,
        "phish_prob_final": final_phish_prob,
    }
    if isotp_prob is not None:
        log_extra["isotp_prob"] = isotp_prob
    
    logger.info("classified message", extra=log_extra)

    return ClassifyResponse(
        isOtp=is_otp,
        otpIntent=otp_intent,
        isPhishing=is_phishing,
        phishScore=final_phish_prob,
        reasons=reasons,
    )


app.include_router(api_router)


@app.get("/")
def index():
    return {"status": "ok", "docs": "/docs"}
