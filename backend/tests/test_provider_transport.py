from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
from typing import Any, Callable
from unittest import TestCase

import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.classification.provider_transport import (  # noqa: E402
    GroqTransport,
    GroqTransportConfig,
    ProviderCooldownError,
)


class MutableClock:
    def __init__(self, start: float = 0.0) -> None:
        self._value = start
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._value

    def advance(self, delta: float) -> None:
        with self._lock:
            self._value += delta


class FakeResponse:
    def __init__(self, status_code: int, payload: Any, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.closed = False

    def json(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def close(self) -> None:
        self.closed = True


class QueueSession:
    def __init__(self, responses: list[Any], clock: MutableClock, *, advance_seconds: float = 0.05) -> None:
        self._responses = queue.Queue()
        for item in responses:
            self._responses.put(item)
        self._clock = clock
        self._advance_seconds = advance_seconds
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: tuple[float, float]) -> Any:
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        item = self._responses.get_nowait()
        self._clock.advance(self._advance_seconds)
        if isinstance(item, BaseException):
            raise item
        return item


class BlockingSession:
    def __init__(self, response: FakeResponse, clock: MutableClock) -> None:
        self._response = response
        self._clock = clock
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: tuple[float, float]) -> FakeResponse:
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        self.entered.set()
        self.release.wait(timeout=2.0)
        self._clock.advance(0.05)
        return self._response


def _make_transport(
    *,
    session: Any,
    clock: MutableClock,
    connect_timeout: float = 1.0,
    read_timeout: float = 6.0,
    cooldown_seconds: float = 2.0,
    inflight_ttl_seconds: float = 7.5,
    max_inflight_requests: int = 8,
    log_sink: list[tuple[str, dict[str, Any]]] | None = None,
) -> GroqTransport:
    events = log_sink if log_sink is not None else []

    def _log(event: str, payload: dict[str, Any]) -> None:
        events.append((event, payload))

    return GroqTransport(
        api_key="test-key",
        model="llama-3.1-8b-instant",
        session=session,
        config=GroqTransportConfig(
            connect_timeout_seconds=connect_timeout,
            read_timeout_seconds=read_timeout,
            cooldown_seconds=cooldown_seconds,
            inflight_ttl_seconds=inflight_ttl_seconds,
            max_inflight_requests=max_inflight_requests,
        ),
        clock=clock.now,
        log_callback=_log,
    )


class ProviderTransportTests(TestCase):
    def test_success_returns_raw_json_and_logs_safe_metrics(self) -> None:
        clock = MutableClock(100.0)
        response = FakeResponse(
            200,
            {"choices": [{"message": {"content": '{"ok":true}'}}]},
            headers={
                "x-ratelimit-remaining-requests": "12",
                "x-ratelimit-reset-requests": "3.5",
                "x-ratelimit-limit-requests": "inf",
            },
        )
        events: list[tuple[str, dict[str, Any]]] = []
        session = QueueSession([response], clock)
        transport = _make_transport(session=session, clock=clock, log_sink=events)

        result = transport.post_chat_completions([{"role": "user", "content": "hi"}])

        self.assertEqual(result, {"choices": [{"message": {"content": '{"ok":true}'}}]})
        self.assertEqual(session.calls[0]["timeout"], (1.0, 6.0))
        self.assertTrue(response.closed)
        self.assertEqual(len(events), 1)
        event, payload = events[0]
        self.assertEqual(event, "groq_transport_response")
        self.assertEqual(payload["status_code"], 200)
        self.assertGreater(payload["elapsed_ms"], 0.0)
        self.assertEqual(payload["rate_limit_remaining_requests"], 12.0)
        self.assertEqual(payload["rate_limit_reset_requests"], 3.5)
        self.assertNotIn("rate_limit_limit_requests", payload)
        self.assertNotIn("messages", payload)
        self.assertNotIn("Authorization", payload)

    def test_429_sets_cooldown_and_expires_after_retry_after(self) -> None:
        clock = MutableClock(200.0)
        first = FakeResponse(429, {"detail": "rate limited"}, headers={"Retry-After": "2"})
        second = FakeResponse(200, {"choices": [{"message": {"content": '{"ok":true}'}}]})
        session = QueueSession([first, second], clock)
        transport = _make_transport(session=session, clock=clock, cooldown_seconds=8.0)

        with self.assertRaises(requests.HTTPError):
            transport.post_chat_completions([{"role": "user", "content": "same"}])
        self.assertTrue(first.closed)
        self.assertEqual(len(session.calls), 1)

        with self.assertRaises(ProviderCooldownError):
            transport.post_chat_completions([{"role": "user", "content": "same"}])
        self.assertEqual(len(session.calls), 1)

        clock.advance(2.1)
        result = transport.post_chat_completions([{"role": "user", "content": "same"}])
        self.assertEqual(result, {"choices": [{"message": {"content": '{"ok":true}'}}]})
        self.assertEqual(len(session.calls), 2)
        self.assertTrue(second.closed)

    def test_timeout_cleanup_allows_retry_without_stall(self) -> None:
        clock = MutableClock(300.0)

        class TimeoutSession:
            def __init__(self) -> None:
                self.calls: list[dict[str, Any]] = []

            def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: tuple[float, float]) -> Any:
                self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
                clock.advance(0.1)
                raise requests.Timeout("provider timed out")

        session = TimeoutSession()
        transport = _make_transport(session=session, clock=clock)

        with self.assertRaises(requests.Timeout):
            transport.post_chat_completions([{"role": "user", "content": "timeout"}])
        with self.assertRaises(requests.Timeout):
            transport.post_chat_completions([{"role": "user", "content": "timeout"}])

        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0]["timeout"], (1.0, 6.0))

    def test_identical_inflight_requests_share_one_network_call(self) -> None:
        clock = MutableClock(400.0)
        response = FakeResponse(200, {"choices": [{"message": {"content": '{"ok":true}'}}]})
        session = BlockingSession(response, clock)
        transport = _make_transport(session=session, clock=clock)
        payload = [{"role": "user", "content": "coalesce me"}]
        results: list[Any] = [None, None]
        errors: list[BaseException | None] = [None, None]

        def _run(index: int) -> None:
            try:
                results[index] = transport.post_chat_completions(payload)
            except BaseException as exc:  # noqa: BLE001
                errors[index] = exc

        first = threading.Thread(target=_run, args=(0,))
        first.start()
        self.assertTrue(session.entered.wait(timeout=2.0))

        attached = threading.Event()
        original_wait = transport._wait_for_inflight

        def wait_for_leader(key, inflight):
            attached.set()
            return original_wait(key, inflight)

        transport._wait_for_inflight = wait_for_leader
        second = threading.Thread(target=_run, args=(1,))
        second.start()
        self.assertTrue(attached.wait(timeout=2.0))
        self.assertEqual(len(session.calls), 1)
        session.release.set()
        first.join(timeout=2.0)
        second.join(timeout=2.0)

        self.assertIsNone(errors[0])
        self.assertIsNone(errors[1])
        self.assertEqual(results[0], {"choices": [{"message": {"content": '{"ok":true}'}}]})
        self.assertEqual(results[1], {"choices": [{"message": {"content": '{"ok":true}'}}]})
        self.assertEqual(len(session.calls), 1)
        self.assertTrue(response.closed)

    def test_exception_clears_inflight_state(self) -> None:
        clock = MutableClock(500.0)

        class BoomSession:
            def __init__(self) -> None:
                self.calls: list[dict[str, Any]] = []

            def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: tuple[float, float]) -> Any:
                self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
                clock.advance(0.1)
                raise RuntimeError("boom")

        session = BoomSession()
        transport = _make_transport(session=session, clock=clock)

        with self.assertRaises(RuntimeError):
            transport.post_chat_completions([{"role": "user", "content": "boom"}])
        with self.assertRaises(RuntimeError):
            transport.post_chat_completions([{"role": "user", "content": "boom"}])

        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    import unittest

    unittest.main()
