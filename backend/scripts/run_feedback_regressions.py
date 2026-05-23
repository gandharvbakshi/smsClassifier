"""Run the sanitized SMS feedback regression harness.

This script tries to import and call `backend.scripts.android_backend_server`
directly so it exercises the real backend classifier when the local models and
imports are available.
"""

from __future__ import annotations

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Allow local import of the backend module even when the shell session does not
# already have a Groq key configured. The classifier only needs the key if a
# test case falls through to the Groq fallback.
os.environ.setdefault("GROQ_API_KEY", "local-feedback-regression-placeholder")

from backend.scripts.feedback_regression_cases import FEEDBACK_REGRESSION_CASES
from backend.scripts.feedback_regression_cases import FeedbackRegressionCase


DEFAULT_EXTRA_CASE_PATHS = [
    ROOT_DIR / "feedback_corpus" / "reviewed_feedback_regression_cases.jsonl",
    ROOT_DIR / "backend" / "data" / "reviewed_feedback_regression_cases.jsonl",
]


def _load_classifier() -> Tuple[Any, Any]:
    from backend.scripts.android_backend_server import ClassifyRequest, classify

    return ClassifyRequest, classify


def _get_field(value: Any, name: str) -> Any:
    if hasattr(value, name):
        return getattr(value, name)
    if isinstance(value, dict):
        return value.get(name)
    return None


def _stable_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
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


def _read_jsonl_cases(path: Path) -> List[FeedbackRegressionCase]:
    cases: List[FeedbackRegressionCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            case_id = row.get("caseId") or row.get("case_id")
            expected_is_otp = row.get("expectedIsOtp", row.get("expected_is_otp"))
            expected_is_phishing = row.get("expectedIsPhishing", row.get("expected_is_phishing"))
            expected_is_otp_bool = _stable_bool(expected_is_otp)
            expected_is_phishing_bool = _stable_bool(expected_is_phishing)
            if not case_id or expected_is_otp_bool is None or expected_is_phishing_bool is None:
                raise ValueError(
                    f"{path}:{line_no}: caseId, expectedIsOtp, and expectedIsPhishing bools are required"
                )
            cases.append(
                FeedbackRegressionCase(
                    case_id=str(case_id),
                    sender=str(row.get("sender") or "UNKNOWN"),
                    text=str(row.get("text") or row.get("body") or ""),
                    expected_is_otp=expected_is_otp_bool,
                    expected_is_phishing=expected_is_phishing_bool,
                    expected_otp_intent=row.get("expectedOtpIntent") or row.get("expected_otp_intent"),
                    category=str(row.get("category") or "reviewed_feedback"),
                )
            )
    return cases


def _default_extra_paths() -> List[Path]:
    for path in DEFAULT_EXTRA_CASE_PATHS:
        if path.exists():
            return [path]
    return []


def _dedupe_cases(cases: List[FeedbackRegressionCase]) -> Tuple[List[FeedbackRegressionCase], int]:
    seen = set()
    deduped: List[FeedbackRegressionCase] = []
    skipped = 0
    for case in cases:
        if case.case_id in seen:
            skipped += 1
            continue
        seen.add(case.case_id)
        deduped.append(case)
    return deduped, skipped


def _load_cases(extra_paths: List[Path], static_only: bool) -> List[FeedbackRegressionCase]:
    cases = list(FEEDBACK_REGRESSION_CASES)
    if static_only:
        return cases

    paths = _default_extra_paths() + list(extra_paths)
    loaded = 0
    for path in paths:
        if not path.exists():
            continue
        extra = _read_jsonl_cases(path)
        cases.extend(extra)
        loaded += len(extra)
    if loaded:
        print(f"Loaded {loaded} reviewed feedback regression case(s)")
    deduped, skipped = _dedupe_cases(cases)
    if skipped:
        print(f"Skipped {skipped} duplicate regression case id(s)")
    return deduped


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SMS classifier feedback regressions.")
    parser.add_argument(
        "--extra-cases",
        action="append",
        type=Path,
        default=[],
        help="JSONL file of reviewed feedback regression cases. Can be passed more than once.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Ignore generated reviewed-feedback regression case files.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        request_type, classify_fn = _load_classifier()
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP: backend classifier unavailable: {exc}")
        return 2

    try:
        regression_cases = _load_cases(list(args.extra_cases), args.static_only)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    passed = 0
    failed = 0
    failures = []

    for case in regression_cases:
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
