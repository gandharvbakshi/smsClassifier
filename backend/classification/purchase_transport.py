from __future__ import annotations

import contextvars
import math
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

import httplib2
from google_auth_httplib2 import AuthorizedHttp

BuildFn = Callable[..., Any]
CredentialsFactory = Callable[[], Any]
Clock = Callable[[], float]

_ANDROID_PUBLISHER_DEADLINE = contextvars.ContextVar("android_publisher_deadline", default=None)


def _clean_timeout(value: object, default: float) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(timeout) or timeout <= 0:
        return default
    return timeout


@dataclass(frozen=True)
class AndroidPublisherTransportConfig:
    request_timeout_seconds: float = 2.0
    request_deadline_seconds: float = 5.0
    refresh_status_codes: tuple[int, ...] = (401,)
    max_refresh_attempts: int = 0
    service_name: str = "androidpublisher"
    service_version: str = "v3"
    cache_discovery: bool = False
    static_discovery: bool = True


class _DeadlineHttp:
    def __init__(
        self,
        *,
        request_timeout_seconds: float,
        request_deadline_seconds: float,
        clock: Clock = time.monotonic,
    ) -> None:
        self._request_timeout_seconds = self._require_positive_timeout(request_timeout_seconds, "request_timeout_seconds")
        self._request_deadline_seconds = self._require_positive_timeout(request_deadline_seconds, "request_deadline_seconds")
        self._clock = clock

    @staticmethod
    def _require_positive_timeout(value: float, label: str) -> float:
        timeout = float(value)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError(f"{label} must be a finite positive number")
        return timeout

    def request(
        self,
        uri: str,
        method: str = "GET",
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
        redirections: int = httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type: Any = None,
        **kwargs: Any,
    ) -> tuple[Any, Any]:
        deadline = _ANDROID_PUBLISHER_DEADLINE.get()
        token = None
        if deadline is None:
            token = _ANDROID_PUBLISHER_DEADLINE.set(self._clock() + self._request_deadline_seconds)
            deadline = _ANDROID_PUBLISHER_DEADLINE.get()
        http = None
        try:
            remaining = float(deadline) - self._clock()
            if remaining <= 0:
                raise TimeoutError("Android Publisher request deadline exceeded")

            timeout = min(self._request_timeout_seconds, remaining)
            explicit_timeout = kwargs.pop("timeout", None)
            if explicit_timeout is not None:
                timeout = min(timeout, _clean_timeout(explicit_timeout, timeout))

            http = httplib2.Http(timeout=timeout)
            return http.request(
                uri,
                method=method,
                body=body,
                headers=headers,
                redirections=redirections,
                connection_type=connection_type,
                **kwargs,
            )
        finally:
            if http is not None and hasattr(http, "close"):
                http.close()
            if token is not None:
                _ANDROID_PUBLISHER_DEADLINE.reset(token)

    def close(self) -> None:
        return None


class _BoundedAuthorizedHttp(AuthorizedHttp):
    def __init__(
        self,
        credentials: Any,
        *,
        config: AndroidPublisherTransportConfig,
        clock: Clock = time.monotonic,
    ) -> None:
        self._clock = clock
        self._request_deadline_seconds = config.request_deadline_seconds
        super().__init__(
            credentials,
            http=_DeadlineHttp(
                request_timeout_seconds=config.request_timeout_seconds,
                request_deadline_seconds=config.request_deadline_seconds,
                clock=clock,
            ),
            refresh_status_codes=config.refresh_status_codes,
            max_refresh_attempts=config.max_refresh_attempts,
        )

    def request(
        self,
        uri: str,
        method: str = "GET",
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
        redirections: int = httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type: Any = None,
        **kwargs: Any,
    ) -> tuple[Any, Any]:
        token = None
        if _ANDROID_PUBLISHER_DEADLINE.get() is None:
            token = _ANDROID_PUBLISHER_DEADLINE.set(self._clock() + self._request_deadline_seconds)
        try:
            return super().request(
                uri,
                method=method,
                body=body,
                headers=headers,
                redirections=redirections,
                connection_type=connection_type,
                **kwargs,
            )
        finally:
            if token is not None:
                _ANDROID_PUBLISHER_DEADLINE.reset(token)


class AndroidPublisherTransport:
    def __init__(
        self,
        *,
        credentials_factory: CredentialsFactory,
        build_fn: BuildFn,
        config: AndroidPublisherTransportConfig | None = None,
        clock: Clock = time.monotonic,
    ) -> None:
        self._credentials_factory = credentials_factory
        self._build_fn = build_fn
        self._config = config or AndroidPublisherTransportConfig()
        self._clock = clock
        self._local = threading.local()

    def service(self) -> Any:
        service = getattr(self._local, "service", None)
        if service is None:
            credentials = self._credentials_factory()
            service = self._build_service(credentials)
            self._local.service = service
        return service

    def _build_service(self, credentials: Any) -> Any:
        authed_http = _BoundedAuthorizedHttp(credentials, config=self._config, clock=self._clock)
        return self._build_fn(
            self._config.service_name,
            self._config.service_version,
            http=authed_http,
            credentials=None,
            cache_discovery=self._config.cache_discovery,
            static_discovery=self._config.static_discovery,
        )
