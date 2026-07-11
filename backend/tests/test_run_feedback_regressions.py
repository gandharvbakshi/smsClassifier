from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, mock


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scripts.feedback_regression_cases import FeedbackRegressionCase
from backend.scripts import run_feedback_regressions as rfr


class _Request:
    def __init__(self, text: str, sender: str) -> None:
        self.text = text
        self.sender = sender


class RunFeedbackRegressionsTests(TestCase):
    def test_partial_axis_comparison_ignores_unspecified_axes(self) -> None:
        case = FeedbackRegressionCase(
            case_id="partial-axis",
            sender="SENDER",
            text="Test text",
            expected_is_otp=None,
            expected_is_phishing=True,
            expected_otp_intent=None,
            category="reviewed_feedback",
        )

        def classify(_request: _Request) -> dict[str, object]:
            return {"isOtp": False, "isPhishing": True, "otpIntent": "UNUSED", "reasons": []}

        ok, details = rfr._check_case(case, classify, _Request)

        self.assertTrue(ok)
        self.assertEqual(details["errors"], [])
        self.assertEqual(details["failed_axes"], [])

    def test_no_axis_dynamic_row_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reviewed.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "caseId": "missing-axis",
                        "sender": "SENDER",
                        "text": "Test text",
                        "expectedOtpIntent": "APP_ACCOUNT_CHANGE_OTP",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as ctx:
                rfr._read_jsonl_cases(path)

        self.assertIn(
            "at least one of expectedIsOtp or expectedIsPhishing is required",
            str(ctx.exception),
        )

    def test_static_corpus_is_retained_when_dynamic_case_shares_id(self) -> None:
        static_case = FeedbackRegressionCase(
            case_id="shared-id",
            sender="STATIC",
            text="Static text",
            expected_is_otp=False,
            expected_is_phishing=False,
            expected_otp_intent=None,
            category="static",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reviewed.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "caseId": "shared-id",
                        "sender": "DYNAMIC",
                        "text": "Dynamic text",
                        "expectedIsOtp": True,
                        "expectedIsPhishing": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(rfr, "FEEDBACK_REGRESSION_CASES", [static_case]), mock.patch.object(
                rfr, "_default_extra_paths", return_value=[]
            ):
                cases, metadata = rfr._load_cases_with_metadata([path], False)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].sender, "STATIC")
        self.assertFalse(cases[0].expected_is_otp)
        self.assertFalse(cases[0].expected_is_phishing)
        self.assertEqual(metadata["static_count"], 1)
        self.assertEqual(metadata["dynamic_count"], 0)
        self.assertEqual(metadata["loaded_dynamic_count"], 1)
        self.assertEqual(metadata["duplicate_count"], 1)

    def test_intent_comparison_is_enforced_when_supplied(self) -> None:
        case = FeedbackRegressionCase(
            case_id="intent-case",
            sender="SENDER",
            text="Test text",
            expected_is_otp=True,
            expected_is_phishing=False,
            expected_otp_intent="DELIVERY_OR_SERVICE_OTP",
            category="reviewed_feedback",
        )

        def classify(_request: _Request) -> dict[str, object]:
            return {
                "isOtp": True,
                "isPhishing": False,
                "otpIntent": "APP_ACCOUNT_CHANGE_OTP",
                "reasons": [],
            }

        ok, details = rfr._check_case(case, classify, _Request)

        self.assertFalse(ok)
        self.assertIn("otpIntent expected DELIVERY_OR_SERVICE_OTP got APP_ACCOUNT_CHANGE_OTP", details["errors"])
        self.assertIn("otpIntent", details["failed_axes"])


if __name__ == "__main__":
    unittest.main()
