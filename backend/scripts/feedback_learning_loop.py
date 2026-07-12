"""Build review-gated learning artifacts from misclassification feedback.

The loop is intentionally conservative:
1. Raw app feedback becomes a deduped review queue.
2. A human marks queue rows accepted/rejected and confirms expected labels.
3. Accepted rows become JSONL regression cases consumed by run_feedback_regressions.py.

This does not train or deploy a model automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_FEEDBACK_INPUT = ROOT_DIR / "feedback_corpus"
DEFAULT_REVIEW_QUEUE = ROOT_DIR / "feedback_corpus" / "review_queue.jsonl"
DEFAULT_REGRESSION_OUTPUT = ROOT_DIR / "feedback_corpus" / "reviewed_feedback_regression_cases.jsonl"
DEFAULT_REGISTRY_OUTPUT = ROOT_DIR / "feedback_corpus" / "reviewed_feedback_registry_cases.jsonl"
DEFAULT_QUARANTINE_OUTPUT = ROOT_DIR / "feedback_corpus" / "review_quarantine.jsonl"
GENERATED_ARTIFACT_NAMES = {
    DEFAULT_REVIEW_QUEUE.name,
    DEFAULT_REGRESSION_OUTPUT.name,
    DEFAULT_REGISTRY_OUTPUT.name,
    DEFAULT_QUARANTINE_OUTPUT.name,
}

LEGACY_USER_CORRECTION_KIND_MAP = {
    "actually otp": "actually_otp",
    "actual otp": "actually_otp",
    "otp": "actually_otp",
    "is otp": "actually_otp",
    "not otp": "not_otp",
    "wrong otp": "not_otp",
    "no otp": "not_otp",
    "phishing": "phishing",
    "is phishing": "phishing",
    "not phishing": "not_phishing",
    "safe": "not_phishing",
    "benign": "not_phishing",
    "not scam": "not_phishing",
}


def _iter_input_files(paths: Iterable[Path], skip_generated: bool = True) -> Iterator[Path]:
    for path in paths:
        if path.is_dir():
            yield from sorted(
                p
                for p in path.rglob("*")
                if p.suffix.lower() in {".json", ".jsonl"}
                and (not skip_generated or p.name not in GENERATED_ARTIFACT_NAMES)
            )
        elif path.exists():
            if skip_generated and path.name in GENERATED_ARTIFACT_NAMES:
                continue
            yield path


def _iter_json_records(paths: Iterable[Path], skip_generated: bool = True) -> Iterator[Dict[str, Any]]:
    for path in _iter_input_files(paths, skip_generated=skip_generated):
        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line_no, raw_line in enumerate(handle, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
                    if isinstance(row, dict):
                        yield row
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON: {exc}") from exc
        if isinstance(payload, list):
            for row in payload:
                if isinstance(row, dict):
                    yield row
        elif isinstance(payload, dict):
            yield payload


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


def _sanitize_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        length = len(match.group(0))
        if length <= 6:
            return "123456"[:length]
        if length <= 12:
            return "123456789012"[:length]
        return "123456789012"

    text = re.sub(r"\d{4,}", repl, text or "")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_feedback_kind(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()
    return normalized


def _infer_legacy_correction_kind(row: Dict[str, Any]) -> Optional[str]:
    kind = _normalize_feedback_kind(row.get("feedbackKind"))
    if kind:
        return kind.replace(" ", "_")
    normalized_correction = _normalize_feedback_kind(row.get("userCorrection"))
    return LEGACY_USER_CORRECTION_KIND_MAP.get(normalized_correction)


def _is_classification_feedback(row: Dict[str, Any], feedback_kind: Optional[str]) -> bool:
    if feedback_kind in {"actually_otp", "not_otp", "phishing", "not_phishing", "other"}:
        return True
    if _stable_bool(row.get("expectedIsOtp")) is not None:
        return True
    if _stable_bool(row.get("expectedIsPhishing")) is not None:
        return True
    if row.get("userCorrection") is not None and str(row.get("userCorrection")).strip():
        return True
    return False


def _is_satisfaction_feedback(row: Dict[str, Any], feedback_kind: Optional[str]) -> bool:
    if feedback_kind == "satisfaction":
        return True
    if _is_classification_feedback(row, feedback_kind):
        return False
    return row.get("satisfactionScore") is not None or row.get("userNote") is not None


def _infer_expected(kind: Optional[str], row: Dict[str, Any]) -> Tuple[Optional[bool], Optional[bool]]:
    expected_otp = _stable_bool(row.get("expectedIsOtp"))
    expected_phishing = _stable_bool(row.get("expectedIsPhishing"))
    normalized = (kind or "").strip().lower()
    if normalized == "actually_otp":
        expected_otp = True
    elif normalized == "not_otp":
        expected_otp = False
    elif normalized == "phishing":
        expected_phishing = True
    elif normalized == "not_phishing":
        expected_phishing = False
    return expected_otp, expected_phishing


def _case_key(
    sender: str,
    text: str,
    feedback_group: str,
) -> str:
    raw = json.dumps(
        {
            "sender": sender,
            "text": text,
            "feedbackGroup": feedback_group,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _regression_case_key(
    sender: str,
    text: str,
    expected_otp: Optional[bool],
    expected_phishing: Optional[bool],
    expected_otp_intent: Optional[str],
) -> str:
    raw = json.dumps(
        {
            "sender": sender,
            "text": text,
            "expectedIsOtp": expected_otp,
            "expectedIsPhishing": expected_phishing,
            "expectedOtpIntent": expected_otp_intent,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _queue_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = _sanitize_text(str(row.get("body") or row.get("text") or ""))
    sender = str(row.get("sender") or "UNKNOWN").strip()[:128] or "UNKNOWN"
    if not text:
        return None

    feedback_kind = _infer_legacy_correction_kind(row)
    if _is_classification_feedback(row, feedback_kind):
        feedback_group = "classification"
    elif _is_satisfaction_feedback(row, feedback_kind):
        feedback_group = "satisfaction"
    else:
        feedback_group = "unknown"
    expected_otp, expected_phishing = _infer_expected(feedback_kind, row) if feedback_group == "classification" else (None, None)
    expected_otp_intent = row.get("expectedOtpIntent") or row.get("correctedOtpIntent")
    if feedback_kind == "other" and expected_otp_intent:
        expected_otp = True
    key = _case_key(sender, text, feedback_group)
    feedback_id = str(row.get("id") or row.get("feedbackId") or key)
    source_feedback_ids = row.get("sourceFeedbackIds")
    if isinstance(source_feedback_ids, list) and source_feedback_ids:
        source_feedback_ids = [str(item) for item in source_feedback_ids if item is not None and str(item).strip()]
    else:
        source_feedback_ids = [feedback_id]
    category = f"{feedback_group}_feedback"

    return {
        "reviewId": f"review_{key}",
        "reviewStatus": "pending",
        "feedbackGroup": feedback_group,
        "sourceFeedbackIds": source_feedback_ids,
        "duplicateCount": 1,
        "sender": sender,
        "text": text,
        "bodyHash": row.get("body_hash") or row.get("bodyHash"),
        "feedbackKind": feedback_kind or None,
        "category": category,
        "appVersionCode": row.get("appVersionCode"),
        "appVersionName": row.get("appVersionName"),
        "predictedIsOtp": _stable_bool(row.get("predictedIsOtp")),
        "predictedOtpIntent": row.get("predictedOtpIntent"),
        "predictedIsPhishing": _stable_bool(row.get("predictedIsPhishing")),
        "predictedPhishScore": row.get("predictedPhishScore"),
        "userCorrection": row.get("userCorrection"),
        "expectedIsOtp": expected_otp,
        "expectedIsPhishing": expected_phishing,
        "expectedOtpIntent": expected_otp_intent,
        "reviewer": row.get("reviewer"),
        "reviewedAt": row.get("reviewedAt"),
        "reviewConfidence": row.get("reviewConfidence"),
        "reviewRationale": row.get("reviewRationale") or "",
        "reviewRationaleNotes": row.get("reviewRationaleNotes") or "",
        "reviewNote": row.get("reviewNote") or "",
        "privacyStatus": row.get("privacyStatus") or "pending",
        "privacyReviewer": row.get("privacyReviewer"),
        "privacyReviewedAt": row.get("privacyReviewedAt"),
        "privacyRationale": row.get("privacyRationale") or "",
        "deidentifiedText": row.get("deidentifiedText") or "",
        "deidentifiedSender": row.get("deidentifiedSender"),
        "retentionClass": row.get("retentionClass") or "raw_feedback",
    }


def _merge_expected(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Optional[str]:
    for field in ("expectedIsOtp", "expectedIsPhishing", "expectedOtpIntent"):
        if field not in existing:
            existing[field] = incoming.get(field)
            continue
        existing_value = existing.get(field)
        incoming_value = incoming.get(field)
        if existing_value is None:
            existing[field] = incoming_value
            continue
        if incoming_value is None:
            continue
        if existing_value != incoming_value:
            return field
    return None


def _expected_values(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        field: row.get(field)
        for field in ("expectedIsOtp", "expectedIsPhishing", "expectedOtpIntent")
        if row.get(field) is not None
    }


def build_review_queue(
    input_paths: List[Path],
    output_path: Path,
    quarantine_path: Optional[Path] = None,
) -> Tuple[int, int]:
    grouped: Dict[str, Dict[str, Any]] = {}
    quarantined: Dict[str, Dict[str, Any]] = {}
    quarantined_keys = set()
    for raw in _iter_json_records(input_paths):
        queued = _queue_row(raw)
        if queued is None:
            continue
        key = queued["reviewId"]
        if key in quarantined_keys:
            existing = quarantined[key]
            existing["duplicateCount"] = int(existing.get("duplicateCount") or 1) + 1
            for feedback_id in queued["sourceFeedbackIds"]:
                if feedback_id not in existing["sourceFeedbackIds"]:
                    existing["sourceFeedbackIds"].append(feedback_id)
            continue
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = queued
            continue
        existing["duplicateCount"] = int(existing.get("duplicateCount") or 1) + 1
        for feedback_id in queued["sourceFeedbackIds"]:
            if feedback_id not in existing["sourceFeedbackIds"]:
                existing["sourceFeedbackIds"].append(feedback_id)
        conflict_field = _merge_expected(existing, queued)
        if conflict_field is not None:
            quarantine_key = existing["reviewId"]
            quarantined[quarantine_key] = {
                **existing,
                "reviewStatus": "quarantined",
                "quarantineReason": f"conflicting {conflict_field}",
                "quarantineFields": [conflict_field],
                "conflictingExpectedValues": [
                    _expected_values(existing),
                    _expected_values(queued),
                ],
            }
            quarantined_keys.add(quarantine_key)
            grouped.pop(key, None)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(grouped.values(), key=lambda item: item["reviewId"]):
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    quarantine_count = len(quarantined)
    if quarantine_path is not None:
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        with quarantine_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in sorted(quarantined.values(), key=lambda item: item["reviewId"]):
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(grouped), quarantine_count


def _is_accepted(row: Dict[str, Any]) -> bool:
    status = str(row.get("reviewStatus") or "").strip().lower()
    return status in {"accepted", "approved"} or row.get("accepted") is True


def export_regression_cases(reviewed_path: Path, output_path: Path) -> Tuple[int, int]:
    accepted = 0
    skipped = 0
    emitted: Dict[str, Dict[str, Any]] = {}
    for row in _iter_json_records([reviewed_path], skip_generated=False):
        if not _is_accepted(row):
            skipped += 1
            continue
        expected_otp = _stable_bool(row.get("expectedIsOtp"))
        expected_phishing = _stable_bool(row.get("expectedIsPhishing"))
        text = _sanitize_text(str(row.get("text") or row.get("body") or ""))
        sender = str(row.get("sender") or "UNKNOWN").strip()[:128] or "UNKNOWN"
        if (expected_otp is None and expected_phishing is None) or not text:
            skipped += 1
            continue
        expected_otp_intent = row.get("expectedOtpIntent") or None
        key = _regression_case_key(
            sender,
            text,
            expected_otp,
            expected_phishing,
            expected_otp_intent,
        )
        emitted[key] = {
            "caseId": str(row.get("caseId") or row.get("reviewId") or f"feedback_{key}"),
            "reviewId": row.get("reviewId"),
            "sender": sender,
            "text": text,
            "expectedIsOtp": expected_otp,
            "expectedIsPhishing": expected_phishing,
            "expectedOtpIntent": expected_otp_intent,
            "category": row.get("category") or "reviewed_feedback",
            "sourceFeedbackIds": row.get("sourceFeedbackIds") or [],
            "reviewer": row.get("reviewer"),
            "reviewedAt": row.get("reviewedAt"),
            "reviewConfidence": row.get("reviewConfidence"),
            "reviewRationale": row.get("reviewRationale"),
            "reviewRationaleNotes": row.get("reviewRationaleNotes"),
            "privacyStatus": row.get("privacyStatus") or "pending",
            "privacyReviewer": row.get("privacyReviewer"),
            "privacyReviewedAt": row.get("privacyReviewedAt"),
            "privacyRationale": row.get("privacyRationale"),
            "deidentifiedText": row.get("deidentifiedText") or "",
            "deidentifiedSender": row.get("deidentifiedSender"),
            "retentionClass": row.get("retentionClass") or "raw_feedback",
        }
        accepted += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(emitted.values(), key=lambda item: item["caseId"]):
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(emitted), skipped


def export_registry_cases(reviewed_path: Path, output_path: Path) -> Tuple[int, int]:
    emitted = 0
    skipped = 0
    rows: Dict[str, Dict[str, Any]] = {}
    for row in _iter_json_records([reviewed_path], skip_generated=False):
        if not _is_accepted(row):
            skipped += 1
            continue
        if str(row.get("privacyStatus") or "").strip().lower() != "deidentified":
            skipped += 1
            continue
        deidentified_text = str(row.get("deidentifiedText") or "").strip()
        if not deidentified_text:
            skipped += 1
            continue
        if not row.get("reviewer") or not row.get("reviewedAt") or not row.get("privacyReviewer") or not row.get("privacyReviewedAt"):
            skipped += 1
            continue
        expected_otp = _stable_bool(row.get("expectedIsOtp"))
        expected_phishing = _stable_bool(row.get("expectedIsPhishing"))
        expected_otp_intent = row.get("expectedOtpIntent") or None
        if expected_otp is None and expected_phishing is None and not expected_otp_intent:
            skipped += 1
            continue
        sender = str(row.get("deidentifiedSender") or "UNKNOWN").strip()[:128] or "UNKNOWN"
        key = _regression_case_key(
            sender,
            deidentified_text,
            expected_otp,
            expected_phishing,
            expected_otp_intent,
        )
        rows[key] = {
            "caseId": str(row.get("caseId") or row.get("reviewId") or f"feedback_{key}"),
            "reviewId": row.get("reviewId"),
            "sourceFeedbackIds": row.get("sourceFeedbackIds") or [],
            "sender": sender,
            "text": deidentified_text,
            "expectedIsOtp": expected_otp,
            "expectedIsPhishing": expected_phishing,
            "expectedOtpIntent": expected_otp_intent,
            "category": row.get("category") or "reviewed_feedback",
            "reviewer": row.get("reviewer"),
            "reviewedAt": row.get("reviewedAt"),
            "reviewConfidence": row.get("reviewConfidence"),
            "reviewRationale": row.get("reviewRationale"),
            "reviewRationaleNotes": row.get("reviewRationaleNotes"),
            "privacyStatus": "deidentified",
            "privacyReviewer": row.get("privacyReviewer"),
            "privacyReviewedAt": row.get("privacyReviewedAt"),
            "privacyRationale": row.get("privacyRationale"),
            "retentionClass": "deidentified_regression",
        }
        emitted += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(rows.values(), key=lambda item: item["caseId"]):
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows), skipped


def summarize(path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in _iter_json_records([path], skip_generated=False):
        status = str(row.get("reviewStatus") or "unknown").strip().lower() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review-gated feedback learning loop.")
    sub = parser.add_subparsers(dest="command", required=True)

    queue = sub.add_parser("queue", help="Build a deduped human review queue from raw feedback.")
    queue.add_argument("--input", action="append", type=Path, default=[], help="Feedback JSON/JSONL file or directory.")
    queue.add_argument("--output", type=Path, default=DEFAULT_REVIEW_QUEUE)
    queue.add_argument("--quarantine-output", type=Path, default=DEFAULT_QUARANTINE_OUTPUT)

    regressions = sub.add_parser("regressions", help="Export accepted review rows as regression JSONL.")
    regressions.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEW_QUEUE)
    regressions.add_argument("--output", type=Path, default=DEFAULT_REGRESSION_OUTPUT)

    registry = sub.add_parser("registry-cases", help="Export deidentified registry rows from reviewed feedback.")
    registry.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEW_QUEUE)
    registry.add_argument("--output", type=Path, default=DEFAULT_REGISTRY_OUTPUT)

    summary = sub.add_parser("summary", help="Summarize review statuses in a queue file.")
    summary.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEW_QUEUE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "queue":
            inputs = args.input or [DEFAULT_FEEDBACK_INPUT]
            count, quarantined = build_review_queue(inputs, args.output, args.quarantine_output)
            print(f"Review queue rows: {count}")
            print(f"Review queue path: {args.output}")
            print(f"Quarantine rows: {quarantined}")
            print(f"Quarantine path: {args.quarantine_output}")
            return 0
        if args.command == "regressions":
            count, skipped = export_regression_cases(args.reviewed, args.output)
            print(f"Regression cases exported: {count}")
            print(f"Skipped rows: {skipped}")
            print(f"Wrote: {args.output}")
            return 0
        if args.command == "registry-cases":
            count, skipped = export_registry_cases(args.reviewed, args.output)
            print(f"Registry cases exported: {count}")
            print(f"Skipped rows: {skipped}")
            print(f"Wrote: {args.output}")
            return 0
        if args.command == "summary":
            print(json.dumps(summarize(args.reviewed), indent=2, sort_keys=True))
            return 0
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
