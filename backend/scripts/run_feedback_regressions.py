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
os.environ.setdefault("CLASSIFICATION_DIAGNOSTICS_ENABLED", "false")

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
    failed_axes = []
    if case.expected_is_otp is not None and actual_is_otp != case.expected_is_otp:
        errors.append(
            f"isOtp expected {case.expected_is_otp} got {actual_is_otp}"
        )
        failed_axes.append("isOtp")
    if case.expected_is_phishing is not None and actual_is_phishing != case.expected_is_phishing:
        errors.append(
            f"isPhishing expected {case.expected_is_phishing} got {actual_is_phishing}"
        )
        failed_axes.append("isPhishing")
    if case.expected_otp_intent is not None and actual_intent != case.expected_otp_intent:
        errors.append(
            f"otpIntent expected {case.expected_otp_intent} got {actual_intent}"
        )
        failed_axes.append("otpIntent")

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
        "failed_axes": failed_axes,
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
            expected_otp_intent = row.get("expectedOtpIntent") or row.get("expected_otp_intent")
            if not case_id:
                raise ValueError(f"{path}:{line_no}: caseId is required")
            if expected_is_otp_bool is None and expected_is_phishing_bool is None:
                raise ValueError(
                    f"{path}:{line_no}: at least one of expectedIsOtp or expectedIsPhishing is required"
                )
            cases.append(
                FeedbackRegressionCase(
                    case_id=str(case_id),
                    sender=str(row.get("sender") or "UNKNOWN"),
                    text=str(row.get("text") or row.get("body") or ""),
                    expected_is_otp=expected_is_otp_bool,
                    expected_is_phishing=expected_is_phishing_bool,
                    expected_otp_intent=expected_otp_intent,
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


def _load_cases_with_metadata(
    extra_paths: List[Path], static_only: bool
) -> Tuple[List[FeedbackRegressionCase], Dict[str, int]]:
    static_cases = list(FEEDBACK_REGRESSION_CASES)
    cases = list(static_cases)
    origin_by_case_id = {case.case_id: "static" for case in static_cases}
    dynamic_loaded = 0
    if static_only:
        metadata = {
            "static_count": len(static_cases),
            "dynamic_count": 0,
            "loaded_dynamic_count": 0,
            "duplicate_count": 0,
        }
        return cases, metadata

    paths = _default_extra_paths() + list(extra_paths)
    for path in paths:
        if not path.exists():
            continue
        extra = _read_jsonl_cases(path)
        cases.extend(extra)
        dynamic_loaded += len(extra)
        for case in extra:
            origin_by_case_id.setdefault(case.case_id, "dynamic")

    if dynamic_loaded:
        print(f"Loaded {dynamic_loaded} reviewed feedback regression case(s)")

    deduped, skipped = _dedupe_cases(cases)
    if skipped:
        print(f"Skipped {skipped} duplicate regression case id(s)")

    static_count = sum(1 for case in deduped if origin_by_case_id.get(case.case_id) == "static")
    metadata = {
        "static_count": static_count,
        "dynamic_count": len(deduped) - static_count,
        "loaded_dynamic_count": dynamic_loaded,
        "duplicate_count": skipped,
    }
    return deduped, metadata


def _load_cases(extra_paths: List[Path], static_only: bool) -> List[FeedbackRegressionCase]:
    cases, _ = _load_cases_with_metadata(extra_paths, static_only)
    return cases


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
    parser.add_argument(
        "--summary-json",
        type=Path,
        help="Write a JSON summary/manifest of the regression run to this path.",
    )
    return parser.parse_args()


def _failure_axis_counts(failures: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"isOtp": 0, "isPhishing": 0, "otpIntent": 0}
    for item in failures:
        for axis in item.get("failed_axes", []):
            if axis in counts:
                counts[axis] += 1
    return counts


def main() -> int:
    args = _parse_args()
    try:
        request_type, classify_fn = _load_classifier()
    except Exception as exc:  # noqa: BLE001
        print(f"SKIP: backend classifier unavailable: {exc}")
        return 2

    try:
        regression_cases, load_metadata = _load_cases_with_metadata(list(args.extra_cases), args.static_only)
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

    if args.summary_json:
        summary = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "static_count": load_metadata["static_count"],
            "dynamic_count": load_metadata["dynamic_count"],
            "loaded_dynamic_count": load_metadata["loaded_dynamic_count"],
            "duplicate_count": load_metadata["duplicate_count"],
            "failures_by_axis": _failure_axis_counts(failures),
            "failures": failures,
        }
        try:
            args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: failed to write summary JSON to {args.summary_json}: {exc}")
            return 2

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
