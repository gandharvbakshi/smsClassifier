import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from googleapiclient.discovery import build

from backend.classification.purchase_transport import (
    AndroidPublisherTransport,
    AndroidPublisherTransportConfig,
    _DeadlineHttp,
)


class FakeCredentials:
    def __init__(self, label: str, events: list[tuple[str, str, str, dict[str, str]]]) -> None:
        self.label = label
        self._events = events

    def before_request(self, request, method, uri, headers):
        self._events.append(("before_request", self.label, uri, dict(headers)))
        headers["Authorization"] = f"Bearer {self.label}"


def test_transport_caches_service_per_thread():
    credentials_created = []
    build_calls = []

    def credentials_factory():
        label = f"cred-{len(credentials_created)}"
        credential = object()
        credentials_created.append((label, credential))
        return credential

    def build_fn(service_name, version, **kwargs):
        build_calls.append((service_name, version, kwargs))
        return object()

    transport = AndroidPublisherTransport(
        credentials_factory=credentials_factory,
        build_fn=build_fn,
    )

    first = transport.service()
    second = transport.service()

    assert first is second
    assert len(credentials_created) == 1
    assert len(build_calls) == 1
    assert build_calls[0][0:2] == ("androidpublisher", "v3")
    assert build_calls[0][2]["cache_discovery"] is False
    assert build_calls[0][2]["static_discovery"] is True


def test_transport_uses_distinct_service_instances_across_threads():
    build_calls = []
    credential_lock = threading.Lock()
    credential_counter = 0

    def credentials_factory():
        nonlocal credential_counter
        with credential_lock:
            credential_counter += 1
            return f"credential-{credential_counter}"

    def build_fn(service_name, version, **kwargs):
        build_calls.append((threading.get_ident(), kwargs["http"].credentials))
        return kwargs["http"]

    transport = AndroidPublisherTransport(
        credentials_factory=credentials_factory,
        build_fn=build_fn,
    )

    results: list[tuple[int, object]] = []
    barrier = threading.Barrier(2)

    def run():
        barrier.wait()
        service = transport.service()
        results.append((threading.get_ident(), service))

    left = threading.Thread(target=run)
    right = threading.Thread(target=run)
    left.start()
    right.start()
    left.join()
    right.join()

    assert len(results) == 2
    assert len(build_calls) == 2
    assert build_calls[0][1] != build_calls[1][1]
    assert results[0][1] is not results[1][1]


def test_bounded_http_uses_remaining_budget_and_explicit_timeout(monkeypatch):
    requests = []

    class FakeHttp:
        def __init__(self, timeout=None, **kwargs):
            requests.append(("init", timeout))

        def request(self, uri, method="GET", body=None, headers=None, redirections=None, connection_type=None, **kwargs):
            requests.append(
                (
                    "request",
                    uri,
                    method,
                    body,
                    dict(headers or {}),
                    redirections,
                    connection_type,
                    dict(kwargs),
                )
            )
            return SimpleNamespace(status=200), b"{}"

    monkeypatch.setattr("backend.classification.purchase_transport.httplib2.Http", FakeHttp)

    events = []
    credential = FakeCredentials("credential-a", events)
    transport = AndroidPublisherTransport(
        credentials_factory=lambda: credential,
        build_fn=lambda *_args, **kwargs: kwargs["http"],
        config=AndroidPublisherTransportConfig(request_timeout_seconds=2.0, request_deadline_seconds=5.0),
        clock=lambda: 100.0,
    )

    http = transport.service()
    response, content = http.request(
        "https://example.com/purchases/verify?token=secret",
        method="POST",
        body="payload",
        headers={"X-Test": "1"},
        timeout=9.0,
    )

    assert response.status == 200
    assert content == b"{}"
    assert requests[0] == ("init", 2.0)
    assert requests[1][0] == "request"
    assert requests[1][1] == "https://example.com/purchases/verify?token=secret"
    assert requests[1][2] == "POST"
    assert requests[1][3] == "payload"
    assert requests[1][4]["Authorization"] == "Bearer credential-a"
    assert requests[1][5] == 5
    assert requests[1][7] == {}
    assert events[0][0] == "before_request"


def test_bounded_http_deadline_is_sanitized_and_blocks_request(monkeypatch):
    http_calls = []

    class FakeHttp:
        def __init__(self, timeout=None, **kwargs):
            http_calls.append(("init", timeout))

        def request(self, *args, **kwargs):
            http_calls.append(("request", args, kwargs))
            return SimpleNamespace(status=200), b"{}"

    monkeypatch.setattr("backend.classification.purchase_transport.httplib2.Http", FakeHttp)

    clock_values = iter([100.0, 100.2])

    transport = AndroidPublisherTransport(
        credentials_factory=lambda: FakeCredentials("credential-b", []),
        build_fn=lambda *_args, **kwargs: kwargs["http"],
        config=AndroidPublisherTransportConfig(request_timeout_seconds=2.0, request_deadline_seconds=0.1),
        clock=lambda: next(clock_values),
    )

    http = transport.service()
    with pytest.raises(TimeoutError) as excinfo:
        http.request("https://example.com/private/token", body="secret-body")

    assert "deadline" in str(excinfo.value).lower()
    assert "secret-body" not in str(excinfo.value)
    assert "private/token" not in str(excinfo.value)
    assert http_calls == []


def test_real_discovery_build_uses_the_bounded_transport(monkeypatch):
    requests = []

    class FakeHttp:
        def __init__(self, timeout=None, **kwargs):
            self.timeout = timeout

        def request(self, uri, method="GET", body=None, headers=None, redirections=None, connection_type=None, **kwargs):
            requests.append(
                (
                    uri,
                    method,
                    self.timeout,
                    dict(headers or {}),
                    dict(kwargs),
                )
            )
            return SimpleNamespace(status=200, reason="OK"), b'{"purchaseState":0}'

    monkeypatch.setattr("backend.classification.purchase_transport.httplib2.Http", FakeHttp)

    transport = AndroidPublisherTransport(
        credentials_factory=lambda: FakeCredentials("credential-c", []),
        build_fn=build,
        config=AndroidPublisherTransportConfig(request_timeout_seconds=2.0, request_deadline_seconds=5.0),
        clock=lambda: 100.0,
    )

    service = transport.service()
    result = service.purchases().products().get(
        packageName="com.example.app",
        productId="pro_lifetime",
        token="synthetic-token",
    ).execute(num_retries=0)

    assert result["purchaseState"] == 0
    assert len(requests) == 1
    assert "androidpublisher" in requests[0][0]
