"""HTTP(S) URL extraction and Google Web Risk lookup helpers.

The module is deliberately fail-closed for link interaction and fail-open for
the classification endpoint: lookup failures become ``UNAVAILABLE`` verdicts
instead of request failures. Raw URLs are never logged here.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urlsplit, urlunsplit


logger = logging.getLogger(__name__)

_TRAILING_PUNCTUATION = ".,;:!?)]}'\""
_URL_CANDIDATE_PATTERN = re.compile(
    r"""
    (?:
        https?://[^\s<>\[\]{}]+
        |
        www\.[^\s<>\[\]{}]+
        |
        (?<![@\w])
        (?:[^\W_](?:[^\W_]|-){0,62}\.)+
        (?:[^\W_\d](?:[^\W_]|-){1,62}|xn--[a-z0-9-]{2,59})
        (?::\d{1,5})?
        (?:[/?#][^\s<>\[\]{}]*)?
    )
    (?![\w@:/?#.-])
    """,
    re.IGNORECASE | re.VERBOSE,
)

MALICIOUS = "MALICIOUS"
NO_MATCH = "NO_MATCH"
UNAVAILABLE = "UNAVAILABLE"
INVALID = "INVALID"
NOT_CHECKED = "NOT_CHECKED"


@dataclass(frozen=True)
class UrlCandidate:
    url: str
    host: str


@dataclass(frozen=True)
class UrlVerdict:
    url: str
    host: str
    status: str
    threat_types: tuple[str, ...] = ()
    checked_at_epoch_ms: Optional[int] = None
    latency_ms: float = 0.0

    def to_api_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return {
            "url": payload["url"],
            "host": payload["host"],
            "status": payload["status"],
            "threatTypes": list(payload["threat_types"]),
            "checkedAtEpochMs": payload["checked_at_epoch_ms"],
            "latencyMs": payload["latency_ms"],
        }


def _canonicalize_http_url(raw: str) -> Optional[UrlCandidate]:
    cleaned = (raw or "").strip().rstrip(_TRAILING_PUNCTUATION)
    if not cleaned:
        return None
    if not re.match(r"(?i)^https?://", cleaned):
        cleaned = f"https://{cleaned}"
    try:
        parsed = urlsplit(cleaned)
        if parsed.scheme.lower() not in {"http", "https"}:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        host = (parsed.hostname or "").strip(".")
        if not host or "." not in host:
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass
        ascii_host = host.encode("idna").decode("ascii").lower()
        if len(ascii_host) > 253 or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            for label in ascii_host.split(".")
        ):
            return None
        try:
            port = parsed.port
        except ValueError:
            return None
        if port is not None and port < 1:
            return None
        netloc = ascii_host
        if port is not None:
            netloc = f"{netloc}:{port}"
        path = parsed.path or ""
        canonical = urlunsplit(
            (parsed.scheme.lower(), netloc, path, parsed.query, "")
        )
        return UrlCandidate(url=canonical, host=ascii_host)
    except (UnicodeError, ValueError):
        return None


def extract_url_candidates(text: str) -> List[UrlCandidate]:
    """Return unique, validated HTTP(S) URLs in display order."""

    candidates: List[UrlCandidate] = []
    seen: set[str] = set()
    for match in _URL_CANDIDATE_PATTERN.finditer(text or ""):
        prefix = (text or "")[max(0, match.start() - 24) : match.start()]
        if re.search(r"[a-z][a-z0-9+.-]*://$", prefix, re.IGNORECASE):
            continue
        candidate = _canonicalize_http_url(match.group(0))
        if candidate is None or candidate.url in seen:
            continue
        seen.add(candidate.url)
        candidates.append(candidate)
    return candidates


def redact_url_references(
    text: str,
    replacement: Callable[[str], str],
) -> str:
    """Redact each validated URL token while preserving surrounding text."""

    source = text or ""
    replacements: List[tuple[int, int, str]] = []
    for match in _URL_CANDIDATE_PATTERN.finditer(source):
        prefix = source[max(0, match.start() - 24) : match.start()]
        if re.search(r"[a-z][a-z0-9+.-]*://$", prefix, re.IGNORECASE):
            continue
        if _canonicalize_http_url(match.group(0)) is None:
            continue
        replacements.append(
            (match.start(), match.end(), replacement(match.group(0)))
        )

    redacted = source
    for start, end, token in reversed(replacements):
        redacted = f"{redacted[:start]}{token}{redacted[end:]}"
    return redacted


def extract_url_hosts(text: str) -> List[str]:
    return [candidate.host for candidate in extract_url_candidates(text)]


def has_url_reference(text: str) -> bool:
    return bool(extract_url_candidates(text))


class UrlReputationChecker:
    """Bounded Google Web Risk lookups with short positive-result caching."""

    def __init__(
        self,
        *,
        mode: str = "off",
        timeout_seconds: float = 0.5,
        max_urls: int = 3,
        client_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        normalized_mode = mode.strip().lower()
        self.mode = normalized_mode if normalized_mode in {"off", "shadow", "enforce"} else "off"
        self.timeout_seconds = max(0.05, min(float(timeout_seconds), 3.0))
        self.max_urls = max(1, min(int(max_urls), 10))
        self._client_factory = client_factory or self._default_client_factory
        self._client: Any = None
        self._client_lock = threading.Lock()
        self._positive_cache: Dict[str, tuple[float, UrlVerdict]] = {}
        self._cache_lock = threading.Lock()

    @classmethod
    def from_env(cls) -> "UrlReputationChecker":
        return cls(
            mode=os.getenv("WEB_RISK_MODE", "off"),
            timeout_seconds=float(os.getenv("WEB_RISK_TIMEOUT_SECONDS", "0.5")),
            max_urls=int(os.getenv("WEB_RISK_MAX_URLS", "3")),
        )

    @property
    def policy_enforced(self) -> bool:
        return self.mode == "enforce"

    @staticmethod
    def _default_client_factory() -> Any:
        from google.cloud import webrisk_v1  # type: ignore

        return webrisk_v1.WebRiskServiceClient()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is None:
                self._client = self._client_factory()
        return self._client

    def _cached_positive(self, candidate: UrlCandidate) -> Optional[UrlVerdict]:
        now = time.time()
        with self._cache_lock:
            cached = self._positive_cache.get(candidate.url)
            if cached is None:
                return None
            expires_at, verdict = cached
            if expires_at <= now:
                self._positive_cache.pop(candidate.url, None)
                return None
            return verdict

    def _remember_positive(self, verdict: UrlVerdict, ttl_seconds: float = 300.0) -> None:
        with self._cache_lock:
            self._positive_cache[verdict.url] = (
                time.time() + max(30.0, min(ttl_seconds, 3600.0)),
                verdict,
            )

    def _lookup_one(self, candidate: UrlCandidate) -> UrlVerdict:
        cached = self._cached_positive(candidate)
        if cached is not None:
            return cached

        started = time.perf_counter()
        checked_at = int(time.time() * 1000)
        try:
            response = self._get_client().search_uris(
                request={
                    "uri": candidate.url,
                    "threat_types": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                    ],
                },
                timeout=self.timeout_seconds,
                retry=None,
            )
            threat_types = tuple(
                sorted(
                    {
                        getattr(threat_type, "name", str(threat_type))
                        for threat_type in getattr(
                            getattr(response, "threat", None),
                            "threat_types",
                            (),
                        )
                    }
                )
            )
            verdict = UrlVerdict(
                url=candidate.url,
                host=candidate.host,
                status=MALICIOUS if threat_types else NO_MATCH,
                threat_types=threat_types,
                checked_at_epoch_ms=checked_at,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
            )
            if verdict.status == MALICIOUS:
                self._remember_positive(verdict)
            return verdict
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Web Risk lookup unavailable (%s); URL omitted from logs",
                type(exc).__name__,
            )
            return UrlVerdict(
                url=candidate.url,
                host=candidate.host,
                status=UNAVAILABLE,
                checked_at_epoch_ms=checked_at,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
            )

    def check_text(self, text: str) -> List[UrlVerdict]:
        candidates = extract_url_candidates(text)
        if not candidates:
            return []
        if self.mode == "off":
            return [
                UrlVerdict(url=item.url, host=item.host, status=NOT_CHECKED)
                for item in candidates
            ]

        selected = candidates[: self.max_urls]
        verdict_by_url: Dict[str, UrlVerdict] = {}
        with ThreadPoolExecutor(max_workers=len(selected)) as executor:
            futures = {
                executor.submit(self._lookup_one, candidate): candidate
                for candidate in selected
            }
            for future in as_completed(futures):
                candidate = futures[future]
                try:
                    verdict_by_url[candidate.url] = future.result()
                except Exception:  # pragma: no cover - _lookup_one is fail-open
                    verdict_by_url[candidate.url] = UrlVerdict(
                        url=candidate.url,
                        host=candidate.host,
                        status=UNAVAILABLE,
                    )

        verdicts = [verdict_by_url[item.url] for item in selected]
        verdicts.extend(
            UrlVerdict(url=item.url, host=item.host, status=NOT_CHECKED)
            for item in candidates[self.max_urls :]
        )
        return verdicts


def verdicts_to_api(verdicts: Iterable[UrlVerdict]) -> List[Dict[str, Any]]:
    return [verdict.to_api_dict() for verdict in verdicts]
