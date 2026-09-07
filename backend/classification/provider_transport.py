from __future__ import annotations

import email.utils
import hashlib
import math
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional

import requests

JsonDict = Dict[str, Any]
StructuredLogCallback = Callable[[str, Dict[str, Any]], None]


def _clean_float(value: object, default: float) -> float:
    try:
        cleaned = float(value)
    except (TypeError, ValueError):
        return default
    return cleaned if cleaned >= 0 else default


def _parse_numeric_header(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = float(raw)
    except ValueError:
        return None
    return parsed if parsed >= 0 and math.isfinite(parsed) else None


def _parse_retry_after_seconds(value: Optional[str]) -> Optional[float]:
    parsed = _parse_numeric_header(value)
    if parsed is not None:
        return parsed
    if not value:
        return None
    try:
        retry_after_dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if retry_after_dt.tzinfo is None:
        retry_after_dt = retry_after_dt.replace(tzinfo=timezone.utc)
    delta_seconds = (retry_after_dt - datetime.now(timezone.utc)).total_seconds()
    return delta_seconds if delta_seconds > 0 else 0.0


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _extract_numeric_headers(headers: Mapping[str, str]) -> Dict[str, float]:
    safe_keys = {
        "x-ratelimit-limit-requests": "rate_limit_limit_requests",
        "x-ratelimit-remaining-requests": "rate_limit_remaining_requests",
        "x-ratelimit-reset-requests": "rate_limit_reset_requests",
        "x-ratelimit-limit-tokens": "rate_limit_limit_tokens",
        "x-ratelimit-remaining-tokens": "rate_limit_remaining_tokens",
        "x-ratelimit-reset-tokens": "rate_limit_reset_tokens",
    }
    metrics: Dict[str, float] = {}
    for header_name, metric_name in safe_keys.items():
        parsed = _parse_numeric_header(headers.get(header_name))
        if parsed is not None:
            metrics[metric_name] = parsed
    return metrics


@dataclass(frozen=True)
class GroqTransportConfig:
    connect_timeout_seconds: float = 1.5
    read_timeout_seconds: float = 6.0
    cooldown_seconds: float = 8.0
    inflight_ttl_seconds: float = 15.0
    max_inflight_requests: int = 128


@dataclass
class _InflightRequest:
    event: threading.Event
    deadline: float
    result: Optional[JsonDict] = None
    error: Optional[BaseException] = None
    waiters: int = 0


class ProviderCooldownError(requests.HTTPError):
    def __init__(self, retry_after_seconds: float) -> None:
        retry_after_seconds = _clean_float(retry_after_seconds, 0.0)
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Groq provider cooldown active for {retry_after_seconds:.3f}s")


class GroqTransport:
    """Thread-safe Groq transport with bounded in-flight request coalescing."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        session: Optional[requests.Session] = None,
        config: GroqTransportConfig | None = None,
        clock: Callable[[], float] = time.monotonic,
        log_callback: Optional[StructuredLogCallback] = None,
        base_url: str = "https://api.groq.com/openai/v1/chat/completions",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._session = session
        self._config = config or GroqTransportConfig()
        self._clock = clock
        self._log_callback = log_callback
        self._base_url = base_url
        self._local = threading.local()
        self._lock = threading.Lock()
        self._cooldown_until = 0.0
        self._inflight: Dict[str, _InflightRequest] = {}

    def post_chat_completions(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 256,
        response_format: Optional[dict[str, str]] = None,
    ) -> JsonDict:
        payload: JsonDict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format or {"type": "json_object"},
        }
        request_key = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

        while True:
            now = self._clock()
            cooldown_payload: Optional[Dict[str, Any]] = None
            with self._lock:
                self._prune_inflight_locked(now)
                cooldown_remaining = self._cooldown_until - now
                if cooldown_remaining > 0:
                    cooldown_payload = {
                        "status_code": 429,
                        "elapsed_ms": 0.0,
                        "retry_after_seconds": cooldown_remaining,
                        "cooldown_remaining_seconds": cooldown_remaining,
                    }
                else:
                    inflight = self._inflight.get(request_key)
                    if inflight is None:
                        if len(self._inflight) >= self._config.max_inflight_requests:
                            raise RuntimeError("Groq transport in-flight limit exceeded")
                        inflight = _InflightRequest(
                            event=threading.Event(),
                            deadline=now + self._config.inflight_ttl_seconds,
                        )
                        self._inflight[request_key] = inflight
                        leader = True
                    else:
                        inflight.waiters += 1
                        leader = False

            if cooldown_payload is not None:
                self._emit("groq_transport_cooldown", cooldown_payload)
                raise ProviderCooldownError(cooldown_remaining)

            if not leader:
                if self._wait_for_inflight(request_key, inflight):
                    if inflight.error is not None:
                        raise inflight.error
                    return inflight.result or {}
                continue

            started = self._clock()
            status_code = 0
            retry_after_seconds = 0.0
            elapsed_ms = 0.0
            headers: Mapping[str, str] = {}
            result: Optional[JsonDict] = None
            error: Optional[BaseException] = None
            response = None
            try:
                response = self._get_session().post(
                    self._base_url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=(self._config.connect_timeout_seconds, self._config.read_timeout_seconds),
                )
                elapsed_ms = (self._clock() - started) * 1000.0
                status_code = int(getattr(response, "status_code", 0) or 0)
                headers = getattr(response, "headers", {}) or {}
                safe_headers = _extract_numeric_headers(headers)
                if status_code == 429:
                    retry_after_seconds = _parse_retry_after_seconds(headers.get("Retry-After"))
                    if retry_after_seconds is None:
                        retry_after_seconds = self._config.cooldown_seconds
                    self._set_cooldown(self._clock() + retry_after_seconds)
                self._emit(
                    "groq_transport_response",
                    {
                        "status_code": status_code,
                        "elapsed_ms": elapsed_ms,
                        "retry_after_seconds": retry_after_seconds if status_code == 429 else 0.0,
                        "cooldown_remaining_seconds": max(self._cooldown_until - self._clock(), 0.0),
                        "coalesced_waiters": inflight.waiters,
                        **safe_headers,
                    },
                )
                response.raise_for_status()
                try:
                    result = response.json()
                except ValueError as exc:
                    error = ValueError("Groq response missing valid JSON content.")
                    raise error from exc
            except BaseException as exc:  # noqa: BLE001
                error = exc if error is None else error
                elapsed_ms = max(elapsed_ms, (self._clock() - started) * 1000.0)
                if not isinstance(error, ProviderCooldownError):
                    self._emit(
                        "groq_transport_error",
                        {
                            "status_code": status_code,
                            "elapsed_ms": elapsed_ms,
                            "retry_after_seconds": retry_after_seconds,
                            "cooldown_remaining_seconds": max(self._cooldown_until - self._clock(), 0.0),
                            "coalesced_waiters": inflight.waiters,
                        },
                    )
                with self._lock:
                    inflight.error = error
                    inflight.event.set()
                    if self._inflight.get(request_key) is inflight:
                        self._inflight.pop(request_key, None)
                raise
            else:
                with self._lock:
                    inflight.result = result
                    inflight.event.set()
                    if self._inflight.get(request_key) is inflight:
                        self._inflight.pop(request_key, None)
                return result or {}
            finally:
                if response is not None and hasattr(response, "close"):
                    try:
                        response.close()
                    except Exception:  # noqa: BLE001
                        pass

    def _get_session(self) -> requests.Session:
        if self._session is not None:
            return self._session
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session

    def _set_cooldown(self, cooldown_until: float) -> None:
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, cooldown_until)

    def _prune_inflight_locked(self, now: float) -> None:
        expired = [key for key, inflight in self._inflight.items() if inflight.event.is_set()]
        for key in expired:
            self._inflight.pop(key, None)

    def _wait_for_inflight(self, request_key: str, inflight: _InflightRequest) -> bool:
        remaining = min(
            max(inflight.deadline - self._clock(), 0.0),
            self._config.connect_timeout_seconds + self._config.read_timeout_seconds,
        )
        if remaining <= 0:
            raise TimeoutError("Groq duplicate request timed out waiting for an in-flight request.")
        if inflight.event.wait(timeout=remaining):
            return True
        raise TimeoutError("Groq duplicate request timed out waiting for an in-flight request.")

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        if self._log_callback is not None:
            self._log_callback(event, payload)
