"""Focused tests for the privacy-safe semantic intent shadow evaluator."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import semantic_intent_shadow as shadow  # noqa: E402


class FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]]):
        self.mapping = mapping

    def encode(self, texts):
        return [self.mapping[text] for text in texts]


def _example(row_id: int, sender: str, body: str, label: str, source: str = "csv") -> shadow.SemanticExample:
    return shadow.SemanticExample(
        row_id=row_id,
        sender=sender,
        body=body,
        label=label,
        source=source,
        group_id=shadow.group_key(sender, body),
    )


class SemanticIntentShadowTests(unittest.TestCase):
    def test_split_examples_by_group_keeps_same_template_together(self):
        examples = [
            _example(1, "Bank", "Your OTP is 111111", "APP_LOGIN_OTP"),
            _example(2, "Bank", "Your OTP is 222222", "APP_LOGIN_OTP"),
            _example(3, "Shop", "Use code 333333", "DELIVERY_OR_SERVICE_OTP"),
            _example(4, "Shop", "Use code 444444", "DELIVERY_OR_SERVICE_OTP"),
            _example(5, "Wallet", "Verify with 555555", "FINANCIAL_LOGIN_OTP"),
            _example(6, "Wallet", "Verify with 666666", "FINANCIAL_LOGIN_OTP"),
        ]

        splits = shadow.split_examples_by_group(examples)
        group_to_split: dict[str, set[str]] = {}
        for split_name, split_examples in splits.items():
            for example in split_examples:
                group_to_split.setdefault(example.group_id, set()).add(split_name)

        self.assertTrue(group_to_split)
        for split_names in group_to_split.values():
            self.assertEqual(split_names, {next(iter(split_names))})

    def test_load_training_examples_filters_conflicts_and_appends_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "corpus.csv"
            jury_path = tmp_path / "jury.jsonl"
            synthetic_path = tmp_path / "synthetic.jsonl"

            with csv_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=["id", "sender", "body", "is_otp", "otp_intent"],
                )
                writer.writeheader()
                writer.writerow({"id": 10, "sender": "A", "body": "one", "is_otp": "true", "otp_intent": "app_login_otp"})
                writer.writerow({"id": 20, "sender": "B", "body": "two", "is_otp": "true", "otp_intent": "generic_app_action_otp"})
                writer.writerow({"id": 30, "sender": "C", "body": "three", "is_otp": "true", "otp_intent": "kyc_or_esign_otp"})

            jury_records = [
                {"row_id": 10, "provider": "a", "ok": True, "verdict": {"is_otp": True, "otp_intent": "BANK_OR_CARD_TXN_OTP"}},
                {"row_id": 20, "provider": "a", "ok": True, "verdict": {"is_otp": False}},
            ]
            with jury_path.open("w", encoding="utf-8") as fh:
                for record in jury_records:
                    fh.write(json.dumps(record) + "\n")

            synthetic_records = [
                {
                    "sender": "SYN",
                    "body": "four",
                    "is_otp": True,
                    "otp_intent": "delivery_or_service_otp",
                    "approved": True,
                }
            ]
            with synthetic_path.open("w", encoding="utf-8") as fh:
                for record in synthetic_records:
                    fh.write(json.dumps(record) + "\n")

            examples, counts = shadow.load_training_examples(csv_path, jury_path=jury_path, synthetic_path=synthetic_path)

            self.assertEqual(len(examples), 3)
            self.assertEqual(counts["csv_positive"], 3)
            self.assertEqual(counts["jury_supported_positive"], 1)
            self.assertEqual(counts["jury_intent_override"], 1)
            self.assertEqual(counts["skipped_conflict"], 1)
            self.assertEqual(counts["synthetic_total"], 1)
            self.assertEqual(counts["synthetic_approved"], 1)
            self.assertTrue(all(example.label in shadow.CANONICAL_INTENTS for example in examples))
            self.assertIn("BANK_OR_CARD_TXN_OTP", {example.label for example in examples})

    def test_synthetic_examples_are_training_only(self):
        examples = [
            _example(1, "A", "alpha one", "APP_LOGIN_OTP"),
            _example(2, "A", "alpha two", "APP_LOGIN_OTP"),
            _example(3, "A", "alpha three", "APP_LOGIN_OTP"),
            _example(4, "S", "synthetic alpha", "APP_LOGIN_OTP", source="synthetic"),
        ]

        splits = shadow.split_real_examples_with_training_only_synthetic(examples)

        self.assertIn(examples[3], splits["train"])
        self.assertNotIn(examples[3], splits["calibration"])
        self.assertNotIn(examples[3], splits["heldout"])

    def test_threshold_selection_abstains_on_low_margin_example(self):
        train_examples = [
            _example(1, "A", "alpha-1", "APP_LOGIN_OTP"),
            _example(2, "A", "alpha-2", "APP_LOGIN_OTP"),
            _example(3, "B", "beta-1", "BANK_OR_CARD_TXN_OTP"),
            _example(4, "B", "beta-2", "BANK_OR_CARD_TXN_OTP"),
        ]
        calibration_examples = [
            _example(5, "A", "alpha-calibrated", "APP_LOGIN_OTP"),
            _example(6, "A", "alpha-ambiguous", "APP_LOGIN_OTP"),
            _example(7, "B", "beta-calibrated", "BANK_OR_CARD_TXN_OTP"),
        ]
        heldout_examples = [
            _example(8, "A", "alpha-heldout", "APP_LOGIN_OTP"),
            _example(9, "A", "alpha-ambiguous-heldout", "APP_LOGIN_OTP"),
        ]

        vectors = {
            train_examples[0].encoder_text: [1.0, 0.0],
            train_examples[1].encoder_text: [1.0, 0.0],
            train_examples[2].encoder_text: [0.0, 1.0],
            train_examples[3].encoder_text: [0.0, 1.0],
            calibration_examples[0].encoder_text: [1.0, 0.0],
            calibration_examples[1].encoder_text: [0.4, 0.6],
            calibration_examples[2].encoder_text: [0.0, 1.0],
            heldout_examples[0].encoder_text: [1.0, 0.0],
            heldout_examples[1].encoder_text: [0.4, 0.6],
        }
        embedder = FakeEmbedder(vectors)

        prototypes, support, dim = shadow.fit_class_prototypes(train_examples, embedder)
        self.assertEqual(dim, 2)
        self.assertEqual(support["APP_LOGIN_OTP"], 2)
        self.assertEqual(support["BANK_OR_CARD_TXN_OTP"], 2)

        selection = shadow.select_thresholds(calibration_examples, prototypes, embedder)
        self.assertAlmostEqual(selection.calibration_accepted_accuracy, 1.0)
        self.assertAlmostEqual(selection.calibration_coverage, 2 / 3)

        predictions = shadow.predict_examples(
            heldout_examples,
            prototypes,
            embedder,
            similarity_threshold=selection.similarity_threshold,
            margin_threshold=selection.margin_threshold,
        )

        predicted_labels = [prediction.label for prediction in predictions]
        self.assertIn(shadow.UNKNOWN_LABEL, predicted_labels)
        self.assertEqual(predicted_labels[0], "APP_LOGIN_OTP")
        self.assertEqual(predicted_labels[1], shadow.UNKNOWN_LABEL)

    def test_synthetic_prototype_influence_is_bounded(self):
        real = _example(1, "A", "real", "APP_LOGIN_OTP")
        synthetic = _example(2, "S", "synthetic", "APP_LOGIN_OTP", source="synthetic")
        embedder = FakeEmbedder(
            {
                real.encoder_text: [1.0, 0.0],
                synthetic.encoder_text: [0.0, 1.0],
            }
        )

        prototypes, _, _ = shadow.fit_class_prototypes(
            [real, synthetic],
            embedder,
            synthetic_blend_weight=0.10,
        )

        prototype = prototypes["APP_LOGIN_OTP"]
        self.assertGreater(prototype[0], prototype[1])
        self.assertGreater(prototype[0], 0.9)


if __name__ == "__main__":
    unittest.main()
