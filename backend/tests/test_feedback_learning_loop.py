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

    def test_queue_defaults_privacy_state_and_preserves_provenance(self) -> None:
        queued = fll._queue_row(
            {
                "id": "f-preserve",
                "sender": "BANK",
                "body": "Code 123456",
                "sourceFeedbackIds": ["f-original", "f-dup"],
                "reviewer": "reviewer-1",
                "reviewedAt": "2026-07-11T10:00:00Z",
                "privacyReviewer": "privacy-1",
                "privacyReviewedAt": "2026-07-11T11:00:00Z",
            }
        )

        assert queued is not None
        self.assertEqual(queued["privacyStatus"], "pending")
        self.assertEqual(queued["retentionClass"], "raw_feedback")
        self.assertEqual(queued["privacyReviewer"], "privacy-1")
        self.assertEqual(queued["privacyReviewedAt"], "2026-07-11T11:00:00Z")
        self.assertEqual(queued["reviewer"], "reviewer-1")
        self.assertEqual(queued["reviewedAt"], "2026-07-11T10:00:00Z")
        self.assertEqual(queued["sourceFeedbackIds"], ["f-original", "f-dup"])

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
                        "privacyStatus": "deidentified",
                        "privacyReviewer": "privacy-7",
                        "privacyReviewedAt": "2026-07-11T12:30:00Z",
                        "privacyRationale": "safe_to_release",
                        "deidentifiedText": "Your order is ready to review",
                        "deidentifiedSender": "BRAND",
                        "retentionClass": "deidentified_regression",
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
            self.assertEqual(row["reviewId"], "review-safe-link")
            self.assertEqual(row["privacyStatus"], "deidentified")
            self.assertEqual(row["privacyReviewer"], "privacy-7")
            self.assertEqual(row["privacyReviewedAt"], "2026-07-11T12:30:00Z")
            self.assertEqual(row["privacyRationale"], "safe_to_release")
            self.assertEqual(row["deidentifiedText"], "Your order is ready to review")
            self.assertEqual(row["deidentifiedSender"], "BRAND")
            self.assertEqual(row["retentionClass"], "deidentified_regression")

    def test_registry_export_requires_reviewed_deidentified_privacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reviewed_path = temp_path / "reviewed.jsonl"
            output_path = temp_path / "registry.jsonl"
            _write_jsonl(
                reviewed_path,
                [
                    {
                        "reviewId": "review-pending",
                        "reviewStatus": "accepted",
                        "reviewer": "reviewer-1",
                        "reviewedAt": "2026-07-11T12:00:00Z",
                        "privacyStatus": "pending",
                        "deidentifiedText": "safe text",
                        "deidentifiedSender": "SAFE",
                        "expectedIsOtp": False,
                    }
                ],
            )

            exported, skipped = fll.export_registry_cases(reviewed_path, output_path)

            self.assertEqual(exported, 0)
            self.assertEqual(skipped, 1)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "")

    def test_registry_export_uses_safe_field_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reviewed_path = temp_path / "reviewed.jsonl"
            output_path = temp_path / "registry.jsonl"
            _write_jsonl(
                reviewed_path,
                [
                    {
                        "caseId": "case-1",
                        "reviewId": "review-safe",
                        "reviewStatus": "approved",
                        "sourceFeedbackIds": ["src-1"],
                        "reviewer": "reviewer-1",
                        "reviewedAt": "2026-07-11T12:00:00Z",
                        "reviewConfidence": 0.9,
                        "reviewRationale": "ok",
                        "reviewRationaleNotes": "notes",
                        "privacyStatus": "deidentified",
                        "privacyReviewer": "privacy-1",
                        "privacyReviewedAt": "2026-07-11T13:00:00Z",
                        "privacyRationale": "safe",
                        "deidentifiedText": "masked text",
                        "deidentifiedSender": "SAFE-SENDER",
                        "retentionClass": "raw_feedback",
                        "expectedIsOtp": True,
                        "expectedIsPhishing": False,
                        "expectedOtpIntent": "APP_LOGIN_OTP",
                        "text": "original text",
                        "body": "original body",
                        "sender": "original sender",
                        "installId": "install-1",
                        "firebaseUid": "uid-1",
                        "userNote": "note",
                    }
                ],
            )

            exported, skipped = fll.export_registry_cases(reviewed_path, output_path)

            self.assertEqual((exported, skipped), (1, 0))
            row = json.loads(output_path.read_text(encoding="utf-8"))
            expected_keys = {
                "caseId",
                "reviewId",
                "sourceFeedbackIds",
                "sender",
                "text",
                "expectedIsOtp",
                "expectedIsPhishing",
                "expectedOtpIntent",
                "category",
                "reviewer",
                "reviewedAt",
                "reviewConfidence",
                "reviewRationale",
                "reviewRationaleNotes",
                "privacyStatus",
                "privacyReviewer",
                "privacyReviewedAt",
                "privacyRationale",
                "retentionClass",
            }
            self.assertEqual(set(row), expected_keys)
            self.assertEqual(row["text"], "masked text")
            self.assertEqual(row["sender"], "SAFE-SENDER")
            self.assertEqual(row["retentionClass"], "deidentified_regression")
            self.assertNotIn("body", row)
            self.assertNotIn("installId", row)
            self.assertNotIn("firebaseUid", row)
            self.assertNotIn("userNote", row)
            self.assertNotIn("deidentifiedText", row)
            self.assertNotIn("deidentifiedSender", row)

    def test_registry_cli_prints_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            reviewed_path = temp_path / "reviewed.jsonl"
            output_path = temp_path / "registry.jsonl"
            _write_jsonl(
                reviewed_path,
                [
                    {
                        "reviewId": "review-safe",
                        "reviewStatus": "accepted",
                        "reviewer": "reviewer-1",
                        "reviewedAt": "2026-07-11T12:00:00Z",
                        "privacyStatus": "deidentified",
                        "privacyReviewer": "privacy-1",
                        "privacyReviewedAt": "2026-07-11T13:00:00Z",
                        "deidentifiedText": "masked text",
                        "deidentifiedSender": "SAFE",
                        "expectedIsOtp": True,
                    }
                ],
            )

            with patch.object(fll, "parse_args") as mock_parse_args:
                mock_parse_args.return_value = fll.argparse.Namespace(
                    command="registry-cases",
                    reviewed=reviewed_path,
                    output=output_path,
                )
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = fll.main()

            self.assertEqual(exit_code, 0)
            output = buffer.getvalue()
            self.assertIn("Registry cases exported:", output)
            self.assertIn("Wrote:", output)
            self.assertIn(str(output_path), output)


if __name__ == "__main__":
    unittest.main()
