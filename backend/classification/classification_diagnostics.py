"""Privacy-safe classification diagnostics helpers.

This module keeps diagnostics structured without exposing raw SMS content or
plaintext identifiers. It is intentionally self-contained so backend callers
can build Cloud Logging-friendly payloads without modifying the main server.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Optional

ANONYMOUS_SUBJECT_KEY = "anonymous"
GROQ_MODEL_COST_RATES = {
    "llama-3.1-8b-instant": (50_000, 80_000),
    "openai/gpt-oss-20b": (75_000, 300_000),
}


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _subject_components(
    install_id: Optional[str] = None,
    firebase_uid: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> str:
    install_id = _clean(install_id)
    firebase_uid = _clean(firebase_uid)
    client_ip = _clean(client_ip)

    if firebase_uid:
        return f"firebaseUid={firebase_uid}"
    if install_id:
        return f"installId={install_id}"
    if client_ip:
        return f"ip={client_ip}"
    return ""


def subject_kind(
    install_id: Optional[str] = None,
    firebase_uid: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> str:
    if _clean(firebase_uid):
        return "firebase_uid"
    if _clean(install_id):
        return "install_id"
    if _clean(client_ip):
        return "ip"
    return "anonymous"


def build_subject_key(
    secret: Optional[str],
    install_id: Optional[str] = None,
    firebase_uid: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> str:
    """Return an HMAC subject key or an anonymous marker.

    The helper refuses to weak-hash when the secret or subject is missing.
    """

    secret = _clean(secret)
    subject = _subject_components(install_id, firebase_uid, client_ip)
    if not secret or not subject:
        return ANONYMOUS_SUBJECT_KEY
    digest = hmac.new(
        secret.encode("utf-8"),
        subject.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


@dataclass(frozen=True)
class GroqCostRates:
    """Per-million token rates expressed in micros."""

    prompt_per_million_micros: int = 0
    completion_per_million_micros: int = 0


def _cost_micros_for_tokens(tokens: Optional[int], rate_per_million_micros: int) -> int:
    tokens = int(tokens or 0)
    if tokens <= 0 or rate_per_million_micros <= 0:
        return 0
    amount = (Decimal(tokens) * Decimal(rate_per_million_micros)) / Decimal("1000000")
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def groq_cost_micros(
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    rates: GroqCostRates,
) -> Dict[str, int]:
    prompt_cost = _cost_micros_for_tokens(prompt_tokens, rates.prompt_per_million_micros)
    completion_cost = _cost_micros_for_tokens(completion_tokens, rates.completion_per_million_micros)
    return {
        "groq_prompt_cost_micros": prompt_cost,
        "groq_completion_cost_micros": completion_cost,
        "groq_total_cost_micros": prompt_cost + completion_cost,
    }


def _default_cost_rates(model_name: Optional[str] = None) -> GroqCostRates:
    def _env_int(name: str) -> int:
        raw = os.getenv(name, "").strip()
        if not raw:
            return 0
        try:
            return int(raw)
        except ValueError:
            return 0

    default_prompt, default_completion = GROQ_MODEL_COST_RATES.get(
        _clean(model_name),
        (0, 0),
    )
    return GroqCostRates(
        prompt_per_million_micros=(
            _env_int("GROQ_PROMPT_COST_PER_MILLION_MICROS") or default_prompt
        ),
        completion_per_million_micros=(
            _env_int("GROQ_COMPLETION_COST_PER_MILLION_MICROS") or default_completion
        ),
    )


def build_classification_diagnostics(
    *,
    subject_secret: Optional[str],
    install_id: Optional[str] = None,
    firebase_uid: Optional[str] = None,
    client_ip: Optional[str] = None,
    model_version: Optional[str] = None,
    model_path: Optional[os.PathLike[str] | str] = None,
    model_source: Optional[str] = None,
    classification_path: Optional[str] = None,
    intent_source: Optional[str] = None,
    total_latency_ms: Optional[float] = None,
    intent_confidence: Optional[float] = None,
    intent_abstained: bool = False,
    intent_shadow: bool = False,
    groq_prompt_tokens: Optional[int] = None,
    groq_completion_tokens: Optional[int] = None,
    groq_model: Optional[str] = None,
    groq_cost_rates: Optional[GroqCostRates] = None,
) -> Dict[str, Any]:
    """Build a Cloud Logging-friendly diagnostics payload.

    The payload is intentionally limited to privacy-safe metadata. It excludes
    raw SMS text, sender strings, plaintext subject IDs, URLs, and reasons.
    """

    rates = groq_cost_rates or _default_cost_rates(groq_model)
    subject_key = build_subject_key(
        subject_secret,
        install_id=install_id,
        firebase_uid=firebase_uid,
        client_ip=client_ip,
    )
    costs = groq_cost_micros(groq_prompt_tokens, groq_completion_tokens, rates)
    return {
        "subject_key": subject_key,
        "subject_kind": (
            "anonymous"
            if subject_key == ANONYMOUS_SUBJECT_KEY
            else subject_kind(install_id, firebase_uid, client_ip)
        ),
        "model_version": _clean(model_version) or None,
        "model_path": str(model_path) if model_path is not None else None,
        "model_source": _clean(model_source) or None,
        "classification_path": _clean(classification_path) or None,
        "intent_source": _clean(intent_source) or None,
        "total_latency_ms": total_latency_ms,
        "intent_confidence": intent_confidence,
        "intent_abstained": bool(intent_abstained),
        "intent_shadow": bool(intent_shadow),
        "groq_prompt_tokens": int(groq_prompt_tokens or 0),
        "groq_completion_tokens": int(groq_completion_tokens or 0),
        "groq_model": _clean(groq_model) or None,
        **costs,
    }


def build_cloud_logging_payload(**kwargs: Any) -> Dict[str, Any]:
    """Alias for diagnostics payload construction.

    This keeps the call site explicit when the returned dict is destined for
    structured logging.
    """

    return build_classification_diagnostics(**kwargs)
