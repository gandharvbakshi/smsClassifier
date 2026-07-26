from __future__ import annotations

import logging
import time
import unittest
from types import SimpleNamespace

from backend.classification.url_reputation import (
    MALICIOUS,
    NO_MATCH,
    NOT_CHECKED,
    UNAVAILABLE,
    UrlReputationChecker,
    extract_url_candidates,
    redact_url_references,
)


class _ThreatType:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeClient:
    def __init__(
        self,
        results: dict[str, list[str] | Exception],
        delay_seconds: float = 0.0,
    ) -> None:
        self.results = results
        self.delay_seconds = delay_seconds
        self.calls: list[dict] = []

    def search_uris(self, *, request: dict, timeout: float, retry: object) -> object:
        self.calls.append(
            {"request": request, "timeout": timeout, "retry": retry}
        )
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        result = self.results.get(request["uri"], [])
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(
            threat=SimpleNamespace(
                threat_types=[_ThreatType(item) for item in result]
            )
        )


class UrlExtractionTests(unittest.TestCase):
    def test_extracts_http_www_bare_and_idn_urls_in_order(self) -> None:
        found = extract_url_candidates(
            "Open HTTP://Example.com/a, www.demo.co.in/pay and münich.example/ok."
        )

        self.assertEqual(
            [item.url for item in found],
            [
                "http://example.com/a",
                "https://www.demo.co.in/pay",
                "https://xn--mnich-kva.example/ok",
            ],
        )

    def test_rejects_email_userinfo_ip_local_and_non_http_lookalikes(self) -> None:
        found = extract_url_candidates(
            "a@example.com ftp://files.example http://user:pw@example.com "
            "http://127.0.0.1 http://localhost/a hxxp://bad.example"
        )

        self.assertEqual(found, [])

    def test_deduplicates_canonical_urls(self) -> None:
        found = extract_url_candidates(
            "example.com/pay and https://example.com/pay"
        )

        self.assertEqual([item.url for item in found], ["https://example.com/pay"])

    def test_preserves_bare_queries_short_ports_and_drops_fragments(self) -> None:
        found = extract_url_candidates(
            "example.com?token=abc example.org:8/pay?x=1 demo.example/path#section"
        )

        self.assertEqual(
            [item.url for item in found],
            [
                "https://example.com?token=abc",
                "https://example.org:8/pay?x=1",
                "https://demo.example/path",
            ],
        )

    def test_rejects_invalid_ports_and_one_character_tlds(self) -> None:
        found = extract_url_candidates(
            "example.com:0/pay example.com:70000/pay example.com:123456/pay a.b"
        )

        self.assertEqual(found, [])

    def test_redacts_bare_and_prefixed_links_without_redacting_email_domain(self) -> None:
        redacted = redact_url_references(
            "Track example.com/pay?token=123 or https://demo.example/a. Mail a@example.com.",
            lambda _raw: "<URL:redacted>",
        )

        self.assertEqual(
            redacted,
            "Track <URL:redacted> or <URL:redacted> Mail a@example.com.",
        )


class UrlReputationCheckerTests(unittest.TestCase):
    def test_off_mode_returns_not_checked_without_creating_client(self) -> None:
        checker = UrlReputationChecker(
            mode="off",
            client_factory=lambda: self.fail("client must not be created"),
        )

        verdicts = checker.check_text("Visit example.com/pay")

        self.assertEqual([item.status for item in verdicts], [NOT_CHECKED])

    def test_maps_no_match_and_malicious_threats(self) -> None:
        fake = _FakeClient(
            {
                "https://safe.example/": [],
                "https://bad.example/": ["SOCIAL_ENGINEERING"],
            }
        )
        checker = UrlReputationChecker(
            mode="enforce",
            client_factory=lambda: fake,
        )

        verdicts = checker.check_text(
            "https://safe.example/ https://bad.example/"
        )

        self.assertEqual([item.status for item in verdicts], [NO_MATCH, MALICIOUS])
        self.assertEqual(verdicts[1].threat_types, ("SOCIAL_ENGINEERING",))
        self.assertEqual(len(fake.calls), 2)
        self.assertTrue(
            all(
                call["request"]["threat_types"]
                == ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"]
                for call in fake.calls
            )
        )

    def test_lookup_exception_is_unavailable_and_does_not_log_raw_url(self) -> None:
        secret_url = "https://secret.example/private?id=1234"
        fake = _FakeClient({secret_url: TimeoutError("timed out")})
        checker = UrlReputationChecker(
            mode="enforce",
            client_factory=lambda: fake,
        )

        with self.assertLogs(
            "backend.classification.url_reputation",
            level=logging.WARNING,
        ) as logs:
            verdicts = checker.check_text(secret_url)

        self.assertEqual([item.status for item in verdicts], [UNAVAILABLE])
        self.assertNotIn(secret_url, "\n".join(logs.output))

    def test_checks_urls_in_parallel_and_marks_excess_not_checked(self) -> None:
        fake = _FakeClient({}, delay_seconds=0.12)
        checker = UrlReputationChecker(
            mode="enforce",
            max_urls=2,
            client_factory=lambda: fake,
        )
        started = time.perf_counter()

        verdicts = checker.check_text(
            "https://one.example https://two.example https://three.example"
        )
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.22)
        self.assertEqual(
            [item.status for item in verdicts],
            [NO_MATCH, NO_MATCH, NOT_CHECKED],
        )
        self.assertEqual(len(fake.calls), 2)


if __name__ == "__main__":
    unittest.main()
