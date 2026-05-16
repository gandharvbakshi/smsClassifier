"""Run the sanitized SMS feedback regression harness.

This script tries to import and call `backend.scripts.android_backend_server`
directly so it exercises the real backend classifier when the local models and
imports are available.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Allow local import of the backend module even when the shell session does not
# already have a Groq key configured. The classifier only needs the key if a
# test case falls through to the Groq fallback.
os.environ.setdefault("GROQ_API_KEY", "local-feedback-regression-placeholder")

from backend.scripts.feedback_regression_cases import FEEDBACK_REGRESSION_CASES


def _load_classifier() -> Tuple[Any, Any]:
    from backend.scripts.android_backend_server import ClassifyRequest, classify

    return ClassifyRequest, classify


def _get_field(value: Any, name: str) -> Any:
    if hasattr(value, name):
        return getattr(value, name)
    if isinstance(value, dict):
        return value.get(name)
    return None


def _check_case(case, classify_fn, request_type) -> Tuple[bool, Dict[str, Any]]:
    request = request_type(text=case.text, sender=case.sender)
    result = classify_fn(request)

    actual_is_otp = bool(_get_field(result, "isOtp"))
    actual_is_phishing = bool(_get_field(result, "isPhishing"))
    actual_intent = _get_field(result, "otpIntent")

    errors = []
    if actual_is_otp != case.expected_is_otp:
        errors.append(
            f"isOtp expected {case.expected_is_otp} got {actual_is_otp}"
        )
    if actual_is_phishing != case.expected_is_phishing:
        errors.append(
            f"isPhishing expected {case.expected_is_phishing} got {actual_is_phishing}"
        )
    if case.expected_otp_intent is not None and actual_intent != case.expected_otp_intent:
        errors.append(
            f"otpIntent expected {case.expected_otp_intent} got {actual_intent}"
        )

    details = {
        "case_id": case.case_id,
        "category": case.category,
        "sender": case.sender,
        "expected": {
            "isOtp": case.expected_is_otp,
            "isPhishing": case.expected_is_phishing,
            "otpIntent": case.expected_otp_intent,
        },
        "actual": {
            "isOtp": actual_is_otp,
            "isPhishing": actual_is_phishing,
            "otpIntent": actual_intent,
        },
        "reasons": _get_field(result, "reasons") or [],
        "errors": errors,
    }
    return not errors, details


def main() -> int:
    try:
        request_type, classify_fn = _load_classifier()
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP: backend classifier unavailable: {exc}")
        return 2

    passed = 0
    failed = 0
    failures = []

    for case in FEEDBACK_REGRESSION_CASES:
        ok, details = _check_case(case, classify_fn, request_type)
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(details)

    total = passed + failed
    print(f"Feedback regressions: {passed}/{total} passed")

    if failures:
        print("Failures:")
        for item in failures:
            expected = item["expected"]
            actual = item["actual"]
            print(
                f"- {item['case_id']} [{item['category']}] "
                f"expected={expected} actual={actual}"
            )
            if item["errors"]:
                print(f"  errors: {', '.join(item['errors'])}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
