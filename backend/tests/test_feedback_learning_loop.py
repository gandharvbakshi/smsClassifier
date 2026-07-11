from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scripts import feedback_learning_loop as fll


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class FeedbackLearningLoopTests(unittest.TestCase):
    def test_legacy_correction_kind_inference(self) -> None:
        row = {
            "sender": "BANK",
            "body": "Your verification code is 123456",
            "userCorrection": "Actually OTP",
        }

        queued = fll._queue_row(row)

        self.assertIsNotNone(queued)
        assert queued is not None
        self.assertEqual(queued["feedbackKind"], "actually_otp")
        self.assertEqual(queued["feedbackGroup"], "classification")
        self.assertTrue(queued["expectedIsOtp"])
        self.assertIsNone(queued["expectedIsPhishing"])

    def test_dedupe_by_normalized_body_independent_of_expected_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.jsonl"
            output_path = temp_path / "review_queue.jsonl"

            _write_jsonl(
                input_path,
                [
                    {
                        "id": "f1",
                        "sender": "VK-BANK",
                        "body": "Code 123456 for login",
                        "userCorrection": "Actually OTP",
                    },
                    {
                        "id": "f2",
                        "sender": "VK-BANK",
                        "body": "Code 123456 for login",
                        "userCorrection": "Not phishing",
                    },
                ],
            )

            queue_count, quarantine_count = fll.build_review_queue([input_path], output_path)

            self.assertEqual(queue_count, 1)
            self.assertEqual(quarantine_count, 0)
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["duplicateCount"], 2)
            self.assertCountEqual(rows[0]["sourceFeedbackIds"], ["f1", "f2"])
            self.assertTrue(rows[0]["expectedIsOtp"])
            self.assertFalse(rows[0]["expectedIsPhishing"])
            self.assertEqual(rows[0]["reviewId"], fll._queue_row(
                {
                    "sender": "VK-BANK",
                    "body": "Code 123456 for login",
                    "userCorrection": "Actually OTP",
                }
            )["reviewId"])

    def test_conflicting_labels_quarantine_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.jsonl"
            queue_path = temp_path / "review_queue.jsonl"
            quarantine_path = temp_path / "review_quarantine.jsonl"

            _write_jsonl(
                input_path,
                [
                    {
                        "id": "c1",
                        "sender": "VK-BANK",
                        "body": "Code 123456 for login",
                        "userCorrection": "Actually OTP",
                    },
                    {
                        "id": "c2",
                        "sender": "VK-BANK",
                        "body": "Code 123456 for login",
                        "userCorrection": "Not OTP",
                    },
                ],
            )

            queue_count, quarantine_count = fll.build_review_queue([input_path], queue_path, quarantine_path)

            self.assertEqual(queue_count, 0)
            self.assertEqual(quarantine_count, 1)
            self.assertEqual(queue_path.read_text(encoding="utf-8"), "")
            quarantined = [json.loads(line) for line in quarantine_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0]["reviewStatus"], "quarantined")
            self.assertEqual(quarantined[0]["quarantineReason"], "conflicting expectedIsOtp")
            self.assertEqual(quarantined[0]["duplicateCount"], 2)
            self.assertCountEqual(quarantined[0]["sourceFeedbackIds"], ["c1", "c2"])
            self.assertEqual(
                quarantined[0]["conflictingExpectedValues"],
                [
                    {"expectedIsOtp": True},
                    {"expectedIsOtp": False},
                ],
            )

    def test_canonical_feedback_kind_with_underscore_is_classification(self) -> None:
        queued = fll._queue_row(
            {
                "id": "canonical-kind",
                "sender": "sender",
                "body": "message",
                "feedbackKind": "not_phishing",
            }
        )

        assert queued is not None
        self.assertEqual(queued["feedbackGroup"], "classification")
        self.assertFalse(queued["expectedIsPhishing"])

    def test_other_feedback_kind_stays_in_classification_review(self) -> None:
        queued = fll._queue_row(
            {
                "id": "wrong-purpose",
                "sender": "sender",
                "body": "message",
                "feedbackKind": "other",
            }
        )

        assert queued is not None
        self.assertEqual(queued["feedbackGroup"], "classification")

    def test_corrected_otp_intent_makes_wrong_purpose_exportable(self) -> None:
        queued = fll._queue_row(
            {
                "id": "wrong-purpose-with-label",
                "sender": "sender",
                "body": "message",
                "feedbackKind": "other",
                "correctedOtpIntent": "APP_LOGIN_OTP",
            }
        )

        assert queued is not None
        self.assertTrue(queued["expectedIsOtp"])
        self.assertEqual(queued["expectedOtpIntent"], "APP_LOGIN_OTP")

    def test_unrecognized_feedback_is_not_mislabeled_as_satisfaction(self) -> None:
        queued = fll._queue_row(
            {
                "id": "future-kind",
                "sender": "sender",
                "body": "message",
                "feedbackKind": "future_kind",
            }
        )

        assert queued is not None
        self.assertEqual(queued["feedbackGroup"], "unknown")
        self.assertEqual(queued["category"], "unknown_feedback")

    def test_satisfaction_feedback_is_segregated_from_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.jsonl"
            output_path = temp_path / "review_queue.jsonl"

            _write_jsonl(
                input_path,
                [
                    {
                        "id": "s1",
                        "sender": "APP",
                        "body": "Thanks for the app",
                        "satisfactionScore": 5,
                    },
                    {
                        "id": "s2",
                        "sender": "APP",
                        "body": "Thanks for the app",
                        "userCorrection": "Not phishing",
                    },
                ],
            )

            queue_count, quarantine_count = fll.build_review_queue([input_path], output_path)

            self.assertEqual(queue_count, 2)
            self.assertEqual(quarantine_count, 0)
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertCountEqual([row["feedbackGroup"] for row in rows], ["satisfaction", "classification"])
            self.assertCountEqual([row["category"] for row in rows], ["satisfaction_feedback", "classification_feedback"])

    def test_partial_expected_labels_are_preserved(self) -> None:
        queued = fll._queue_row(
            {
                "sender": "BANK",
                "body": "Code 123456 for login",
                "expectedIsOtp": True,
            }
        )

        self.assertIsNotNone(queued)
        assert queued is not None
        self.assertTrue(queued["expectedIsOtp"])
        self.assertIsNone(queued["expectedIsPhishing"])
        self.assertEqual(queued["feedbackGroup"], "classification")

    def test_queue_cli_prints_queue_and_quarantine_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.jsonl"
            queue_path = temp_path / "queue.jsonl"
            quarantine_path = temp_path / "quarantine.jsonl"

            _write_jsonl(
                input_path,
                [
                    {
                        "id": "q1",
                        "sender": "VK-BANK",
                        "body": "Code 123456 for login",
                        "userCorrection": "Actually OTP",
                    }
                ],
            )

            with patch.object(fll, "parse_args") as mock_parse_args:
                mock_parse_args.return_value = fll.argparse.Namespace(
                    command="queue",
                    input=[input_path],
                    output=queue_path,
                    quarantine_output=quarantine_path,
                )
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = fll.main()

            self.assertEqual(exit_code, 0)
            output = buffer.getvalue()
            self.assertIn("Review queue path:", output)
            self.assertIn(str(queue_path), output)
            self.assertIn("Quarantine path:", output)
            self.assertIn(str(quarantine_path), output)

    def test_export_preserves_partial_axis_and_review_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reviewed_path = temp_path / "reviewed.jsonl"
            output_path = temp_path / "regressions.jsonl"
            _write_jsonl(
                reviewed_path,
                [
                    {
                        "reviewId": "review-safe-link",
                        "reviewStatus": "accepted",
                        "sender": "BRAND",
                        "text": "Your order is ready to review",
                        "expectedIsPhishing": False,
                        "reviewer": "reviewer-1",
                        "reviewedAt": "2026-07-11T12:00:00Z",
                        "reviewConfidence": 0.95,
                        "reviewRationale": "legitimate_receipt",
                    }
                ],
            )

            exported, skipped = fll.export_regression_cases(reviewed_path, output_path)

            self.assertEqual((exported, skipped), (1, 0))
            row = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIsNone(row["expectedIsOtp"])
            self.assertFalse(row["expectedIsPhishing"])
            self.assertEqual(row["reviewer"], "reviewer-1")
            self.assertEqual(row["reviewRationale"], "legitimate_receipt")


if __name__ == "__main__":
    unittest.main()
