from __future__ import annotations

import hashlib
import hmac
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.classification.classification_diagnostics import (
    ANONYMOUS_SUBJECT_KEY,
    GroqCostRates,
    build_classification_diagnostics,
    build_cloud_logging_payload,
    build_subject_key,
    groq_cost_micros,
)


class ClassificationDiagnosticsTests(unittest.TestCase):
    def test_subject_key_prefers_firebase_uid_for_stability(self) -> None:
        secret = "super-secret"
        install_id = "install-123"
        firebase_uid = "firebase-abc"
        client_ip = "203.0.113.7"
        expected_subject = "firebaseUid=firebase-abc"
        expected = hmac.new(
            secret.encode("utf-8"),
            expected_subject.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(
            build_subject_key(secret, install_id, firebase_uid, client_ip),
            expected,
        )
        self.assertEqual(
            build_subject_key(secret, install_id, firebase_uid, "198.51.100.9"),
            expected,
        )

    def test_subject_key_falls_back_to_install_before_ip(self) -> None:
        expected = hmac.new(b"secret", b"installId=install-123", hashlib.sha256).hexdigest()
        self.assertEqual(
            build_subject_key("secret", install_id="install-123", client_ip="203.0.113.7"),
            expected,
        )

    def test_subject_key_anonymous_when_secret_missing(self) -> None:
        self.assertEqual(
            build_subject_key(None, install_id="install-123", firebase_uid="firebase-abc", client_ip="203.0.113.7"),
            ANONYMOUS_SUBJECT_KEY,
        )
        payload = build_classification_diagnostics(
            subject_secret=None,
            install_id="install-123",
            client_ip="203.0.113.7",
        )
        self.assertEqual(payload["subject_kind"], "anonymous")

    def test_subject_key_anonymous_when_subject_missing(self) -> None:
        self.assertEqual(build_subject_key("secret"), ANONYMOUS_SUBJECT_KEY)
        self.assertEqual(
            build_subject_key("secret", install_id="   ", firebase_uid="", client_ip=None),
            ANONYMOUS_SUBJECT_KEY,
        )

    def test_groq_costs_round_half_up(self) -> None:
        rates = GroqCostRates(prompt_per_million_micros=500_000, completion_per_million_micros=499_999)
        costs = groq_cost_micros(1, 1, rates)
        self.assertEqual(costs["groq_prompt_cost_micros"], 1)
        self.assertEqual(costs["groq_completion_cost_micros"], 0)
        self.assertEqual(costs["groq_total_cost_micros"], 1)

    def test_groq_costs_scale_with_token_counts(self) -> None:
        rates = GroqCostRates(prompt_per_million_micros=2_000_000, completion_per_million_micros=4_000_000)
        costs = groq_cost_micros(250, 125, rates)
        self.assertEqual(costs, {
            "groq_prompt_cost_micros": 500,
            "groq_completion_cost_micros": 500,
            "groq_total_cost_micros": 1000,
        })

    def test_payload_is_flat_and_privacy_safe(self) -> None:
        payload = build_classification_diagnostics(
            subject_secret="super-secret",
            install_id="install-123",
            firebase_uid="firebase-abc",
            client_ip="203.0.113.7",
            model_version="1.2.3",
            model_path=Path(r"D:\models\otp-model.bin"),
            model_source="lightgbm",
            classification_path="heuristic_high_confidence",
            intent_source="heuristic",
            total_latency_ms=41.5,
            intent_confidence=0.87,
            intent_abstained=False,
            intent_shadow=True,
            groq_prompt_tokens=12,
            groq_completion_tokens=34,
            groq_model="llama-3.1-8b-instant",
            groq_cost_rates=GroqCostRates(
                prompt_per_million_micros=1_500_000,
                completion_per_million_micros=2_500_000,
            ),
        )

        expected_subject = "firebaseUid=firebase-abc"
        expected_subject_key = hmac.new(
            b"super-secret",
            expected_subject.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(payload["subject_key"], expected_subject_key)
        self.assertEqual(payload["subject_kind"], "firebase_uid")
        self.assertEqual(payload["model_version"], "1.2.3")
        self.assertEqual(payload["model_path"], r"D:\models\otp-model.bin")
        self.assertEqual(payload["model_source"], "lightgbm")
        self.assertEqual(payload["classification_path"], "heuristic_high_confidence")
        self.assertEqual(payload["intent_source"], "heuristic")
        self.assertEqual(payload["total_latency_ms"], 41.5)
        self.assertEqual(payload["intent_confidence"], 0.87)
        self.assertFalse(payload["intent_abstained"])
        self.assertTrue(payload["intent_shadow"])
        self.assertEqual(payload["groq_prompt_tokens"], 12)
        self.assertEqual(payload["groq_completion_tokens"], 34)
        self.assertEqual(payload["groq_model"], "llama-3.1-8b-instant")
        self.assertEqual(payload["groq_prompt_cost_micros"], 18)
        self.assertEqual(payload["groq_completion_cost_micros"], 85)
        self.assertEqual(payload["groq_total_cost_micros"], 103)

        forbidden_keys = {
            "sms",
            "sender",
            "reason",
            "reasons",
            "installId",
            "firebaseUid",
            "clientIp",
            "url",
        }
        self.assertTrue(forbidden_keys.isdisjoint(payload.keys()))

    def test_cloud_logging_alias_matches_builder(self) -> None:
        base = build_classification_diagnostics(
            subject_secret="secret",
            install_id="install-123",
            model_version="v1",
        )
        alias = build_cloud_logging_payload(
            subject_secret="secret",
            install_id="install-123",
            model_version="v1",
        )
        self.assertEqual(alias, base)

    def test_current_groq_model_has_nonzero_default_cost(self) -> None:
        payload = build_classification_diagnostics(
            subject_secret="secret",
            install_id="install-123",
            groq_model="llama-3.1-8b-instant",
            groq_prompt_tokens=1_000_000,
            groq_completion_tokens=1_000_000,
        )
        self.assertEqual(payload["groq_prompt_cost_micros"], 50_000)
        self.assertEqual(payload["groq_completion_cost_micros"], 80_000)
        self.assertEqual(payload["groq_total_cost_micros"], 130_000)


if __name__ == "__main__":
    unittest.main()
