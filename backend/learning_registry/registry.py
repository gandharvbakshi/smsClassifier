from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from math import isfinite
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


class RegistryError(ValueError):
    pass


class ObjectConflictError(RegistryError):
    pass


_PATH_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_RELEASE_REQUIRED_FIELDS = (
    "releaseId",
    "createdAt",
    "gitCommit",
    "changeSummary",
    "reviewDecision",
    "rolloutStatus",
    "provenanceCompleteness",
    "corpusIds",
    "corpusManifestRefs",
)
_TOMBSTONE_REQUIRED_FIELDS = ("tombstoneId", "createdAt", "reason", "caseIds", "corpusId")
_CORPUS_MANIFEST_REQUIRED_FIELDS = ("corpusId", "metadata", "caseCount", "casesSha256", "casesObject")
_CORPUS_SAFE_FIELDS = (
    "caseId",
    "reviewId",
    "sourceFeedbackIds",
    "sender",
    "text",
    "expectedIsOtp",
    "expectedIsPhishing",
    "expectedOtpIntent",
    "expectedLabels",
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
)
_RELEASE_OPTIONAL_FIELDS = (
    "schemaVersion",
    "recordType",
    "registryImplementationCommit",
    "appVersion",
    "versionCode",
    "cloudRunRevision",
    "cloudRunService",
    "image",
    "policyId",
    "modelVersion",
    "semanticIntentStatus",
    "sourceEvidence",
    "evaluation",
    "feedbackMatchSummary",
    "rollout",
    "knownGaps",
    "notes",
)
_TOMBSTONE_OPTIONAL_FIELDS = (
    "sourceFeedbackIds",
    "deletionScope",
    "rawDataDeletionStatus",
)
_RAW_FORBIDDEN_KEY_NAMES = frozenset(
    key.casefold()
    for key in (
        "body",
        "rawBody",
        "originalText",
        "originalSender",
        "installId",
        "firebaseUid",
        "userNote",
    )
)
_DUPLICATE_CONTENT_KEY_NAMES = frozenset({"deidentifiedtext", "deidentifiedsender"})
_CORPUS_FORBIDDEN_KEY_NAMES = (
    _RAW_FORBIDDEN_KEY_NAMES | _DUPLICATE_CONTENT_KEY_NAMES | frozenset({"message"})
)
_NON_CORPUS_FORBIDDEN_KEY_NAMES = (
    _CORPUS_FORBIDDEN_KEY_NAMES | frozenset({"text", "sender"})
)
_CORPUS_METADATA_FORBIDDEN_KEY_NAMES = (
    _NON_CORPUS_FORBIDDEN_KEY_NAMES
    | frozenset(
        {
            "privatelineage",
            "sourcefeedbackids",
            "sourcefeedbackid",
            "sourcefeedbackidlineage",
            "sourcefeedbacklineage",
        }
    )
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json_bytes(payload: Any, *, indent: Optional[int] = None) -> bytes:
    if indent is None:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=indent) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    return prefix.strip("/").replace("\\", "/")


def _join_key(prefix: str, key: str) -> str:
    key = key.strip("/")
    if not prefix:
        return key
    return f"{prefix}/{key}"


def _validate_path_safe_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{field_name} must be a path-safe identifier")
    identifier = value.strip()
    if not _PATH_SAFE_ID_RE.fullmatch(identifier) or ".." in identifier:
        raise RegistryError(f"{field_name} must be a path-safe identifier")
    return identifier


def _validate_no_forbidden_keys(value: Any, context: str, forbidden_keys: frozenset[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in forbidden_keys:
                raise RegistryError(f"{context} contains forbidden key: {key}")
            _validate_no_forbidden_keys(child, context, forbidden_keys)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_no_forbidden_keys(child, context, forbidden_keys)


def _validate_corpus_row_payload(row: Dict[str, Any]) -> None:
    for key, child in row.items():
        normalized_key = str(key).casefold()
        if normalized_key in _CORPUS_FORBIDDEN_KEY_NAMES:
            raise RegistryError(f"corpus row contains forbidden key: {key}")
        if key in {"text", "sender"}:
            if child is not None and not isinstance(child, str):
                raise RegistryError(f"corpus row {key} must be a string")
            continue
        if normalized_key in {"text", "sender"}:
            raise RegistryError(f"corpus row contains noncanonical content key: {key}")
        _validate_no_forbidden_keys(child, "corpus row", _NON_CORPUS_FORBIDDEN_KEY_NAMES)


def _trimmed_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_string_field(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{field_name} must be a string")
    trimmed = value.strip()
    if not allow_empty and not trimmed:
        raise RegistryError(f"{field_name} is required")
    return trimmed


def _validate_optional_string_field(value: Any, field_name: str, *, allow_empty: bool = False) -> Optional[str]:
    if value is None:
        return None
    return _validate_string_field(value, field_name, allow_empty=allow_empty)


def _validate_optional_bool_field(value: Any, field_name: str) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise RegistryError(f"{field_name} must be a boolean or null")


def _validate_optional_number_field(value: Any, field_name: str) -> Optional[float | int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RegistryError(f"{field_name} must be a number")
    if not isfinite(float(value)) or value < 0 or value > 1:
        raise RegistryError(f"{field_name} must be between 0 and 1")
    return value


def _validate_datetime_field(value: Any, field_name: str) -> str:
    trimmed = _validate_string_field(value, field_name)
    candidate = trimmed.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise RegistryError(f"{field_name} must be date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RegistryError(f"{field_name} must be date-time")
    return trimmed


def _validate_nonempty_int_field(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RegistryError(f"{field_name} must be an integer")
    if value < 0:
        raise RegistryError(f"{field_name} must be greater than or equal to 0")
    return value


def _validate_positive_int_field(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RegistryError(f"{field_name} must be an integer")
    if value < 1:
        raise RegistryError(f"{field_name} must be greater than or equal to 1")
    return value


def _validate_string_list(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = False,
    path_safe: bool = False,
    unique: bool = False,
) -> List[str]:
    if not isinstance(value, list):
        raise RegistryError(f"{field_name} must be a list")
    if not allow_empty and not value:
        raise RegistryError(f"{field_name} is required")
    result: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise RegistryError(f"{field_name} entries must be strings")
        trimmed = item.strip()
        if not trimmed:
            raise RegistryError(f"{field_name} entries must be strings")
        if path_safe:
            trimmed = _validate_path_safe_id(trimmed, f"{field_name} entry")
        result.append(trimmed)
    if unique and len(set(result)) != len(result):
        raise RegistryError(f"{field_name} must not contain duplicates")
    return result


def _ensure_allowed_fields(payload: Dict[str, Any], allowed_fields: frozenset[str], context: str) -> None:
    for key in payload:
        if key not in allowed_fields:
            raise RegistryError(f"{context} contains unknown field: {key}")


def _validate_corpus_manifest_metadata(metadata: Any) -> Dict[str, Any]:
    if not isinstance(metadata, dict):
        raise RegistryError("metadata must be an object")
    _validate_no_forbidden_keys(metadata, "metadata", _CORPUS_METADATA_FORBIDDEN_KEY_NAMES)
    return metadata


def _validate_expected_labels(row: Dict[str, Any]) -> List[str]:
    source_field = None
    candidate: Any = None
    for field in ("expectedLabels", "labels", "expectedLabel", "label"):
        if field in row:
            source_field = field
            candidate = row.get(field)
            break
    if source_field is None or candidate is None:
        return []
    if isinstance(candidate, str):
        values = [candidate]
    elif isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
        values = list(candidate)
    else:
        raise RegistryError("expectedLabels must be a string or list of strings")
    labels: List[str] = []
    for value in values:
        if not isinstance(value, str):
            raise RegistryError("expectedLabels entries must be strings")
        trimmed = value.strip()
        if not trimmed:
            raise RegistryError("expectedLabels entries must be strings")
        labels.append(trimmed)
    if len(set(labels)) != len(labels):
        raise RegistryError("expectedLabels must not contain duplicates")
    return labels


def _validate_corpus_row_values(row: Dict[str, Any]) -> Dict[str, Any]:
    for key, child in row.items():
        normalized_key = str(key).casefold()
        if normalized_key in _CORPUS_FORBIDDEN_KEY_NAMES:
            raise RegistryError(f"corpus row contains forbidden key: {key}")
        if key in {"text", "sender"}:
            if child is not None and not isinstance(child, str):
                raise RegistryError(f"corpus row {key} must be a string")
            continue
        if normalized_key in {"text", "sender"}:
            raise RegistryError(f"corpus row contains noncanonical content key: {key}")
        _validate_no_forbidden_keys(child, "corpus row", _NON_CORPUS_FORBIDDEN_KEY_NAMES)
    return row


def _validate_corpus_case_row(row: Dict[str, Any]) -> Dict[str, Any]:
    _validate_corpus_row_values(row)
    privacy_status = _validate_string_field(row.get("privacyStatus"), "privacyStatus")
    if privacy_status != "deidentified":
        raise RegistryError("privacyStatus must be deidentified")

    case_id = _validate_path_safe_id(row.get("caseId"), "caseId")
    text = _validate_string_field(row.get("text"), "text")
    expected_is_otp = _validate_optional_bool_field(row.get("expectedIsOtp"), "expectedIsOtp")
    expected_is_phishing = _validate_optional_bool_field(row.get("expectedIsPhishing"), "expectedIsPhishing")
    expected_otp_intent = _validate_optional_string_field(row.get("expectedOtpIntent"), "expectedOtpIntent")
    labels = _validate_expected_labels(row)
    has_expected_axis = any(value is not None for value in (expected_is_otp, expected_is_phishing, expected_otp_intent))
    reviewer = _validate_string_field(row.get("reviewer"), "reviewer")
    reviewed_at = _validate_datetime_field(row.get("reviewedAt"), "reviewedAt")
    privacy_reviewer = _validate_string_field(row.get("privacyReviewer"), "privacyReviewer")
    privacy_reviewed_at = _validate_datetime_field(row.get("privacyReviewedAt"), "privacyReviewedAt")

    if not labels and not has_expected_axis:
        raise RegistryError("at least one expected label or expected axis value is required")

    canonical_row = {field: row[field] for field in _CORPUS_SAFE_FIELDS if field in row}
    canonical_row.update(
        {
            "caseId": case_id,
            "expectedIsOtp": expected_is_otp,
            "expectedIsPhishing": expected_is_phishing,
            "expectedOtpIntent": expected_otp_intent,
            "privacyReviewedAt": privacy_reviewed_at,
            "privacyReviewer": privacy_reviewer,
            "privacyStatus": "deidentified",
            "reviewedAt": reviewed_at,
            "reviewer": reviewer,
            "text": text,
        }
    )
    if labels or any(field in row for field in ("expectedLabels", "labels", "expectedLabel", "label")):
        canonical_row["expectedLabels"] = labels
    if "reviewConfidence" in row:
        canonical_row["reviewConfidence"] = _validate_optional_number_field(row.get("reviewConfidence"), "reviewConfidence")
    for field in ("reviewId", "sender", "category", "reviewRationale", "privacyRationale", "retentionClass"):
        if field in row:
            canonical_row[field] = _validate_optional_string_field(row.get(field), field)
    if "sourceFeedbackIds" in row:
        canonical_row["sourceFeedbackIds"] = _validate_string_list(
            row.get("sourceFeedbackIds"),
            "sourceFeedbackIds",
            unique=True,
        )
    if "reviewRationaleNotes" in row:
        notes = row.get("reviewRationaleNotes")
        if notes is None:
            canonical_row["reviewRationaleNotes"] = None
        elif isinstance(notes, str):
            canonical_row["reviewRationaleNotes"] = _validate_string_field(notes, "reviewRationaleNotes")
        elif isinstance(notes, list):
            canonical_row["reviewRationaleNotes"] = _validate_string_list(notes, "reviewRationaleNotes", allow_empty=True)
        else:
            raise RegistryError("reviewRationaleNotes must be a string, list of strings, or null")
    _validate_corpus_row_values(canonical_row)
    return canonical_row


def _validate_corpus_cases_bytes(corpus_id: str, cases_bytes: bytes, *, validate_canonical_rows: bool) -> List[Dict[str, Any]]:
    canonical_rows: List[Dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    case_lines = [line for line in cases_bytes.splitlines() if line.strip()]
    for line_number, line in enumerate(case_lines, start=1):
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RegistryError(f"invalid JSON in corpora/{corpus_id}/cases.jsonl at line {line_number}") from exc
        if not isinstance(row, dict):
            raise RegistryError(f"invalid JSON object in corpora/{corpus_id}/cases.jsonl at line {line_number}")
        canonical_row = _validate_corpus_case_row(row)
        case_id = canonical_row["caseId"]
        if case_id in seen_case_ids:
            raise RegistryError(f"duplicate caseId in corpus cases: {case_id}")
        seen_case_ids.add(case_id)
        if validate_canonical_rows:
            canonical_line = json.dumps(canonical_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if line != canonical_line:
                raise RegistryError(f"noncanonical corpus row in corpora/{corpus_id}/cases.jsonl at line {line_number}")
        canonical_rows.append(canonical_row)
    return canonical_rows


def _validate_corpus_manifest_payload(
    manifest: Dict[str, Any],
    *,
    corpus_id: str,
    cases_key: str,
    expected_cases_object: str,
    validate_canonical_json: bool = False,
    manifest_bytes: bytes | None = None,
) -> Dict[str, Any]:
    _ensure_allowed_fields(manifest, frozenset(_CORPUS_MANIFEST_REQUIRED_FIELDS), f"corpus manifest {cases_key}")
    manifest_corpus_id = _validate_string_field(manifest.get("corpusId"), "corpusId")
    if manifest_corpus_id != corpus_id:
        raise RegistryError(f"manifest corpusId mismatch for {cases_key}")
    metadata = _validate_corpus_manifest_metadata(manifest.get("metadata"))
    case_count = _validate_nonempty_int_field(manifest.get("caseCount"), "caseCount")
    cases_sha256 = _validate_string_field(manifest.get("casesSha256"), "casesSha256")
    if not re.fullmatch(r"[a-f0-9]{64}", cases_sha256):
        raise RegistryError("casesSha256 must be a sha256 hex digest")
    cases_object = _validate_string_field(manifest.get("casesObject"), "casesObject")
    if cases_object not in {cases_key, expected_cases_object}:
        raise RegistryError(f"manifest cases object mismatch for {cases_key}")
    canonical_manifest = {
        "caseCount": case_count,
        "casesObject": expected_cases_object,
        "casesSha256": cases_sha256,
        "corpusId": corpus_id,
        "metadata": metadata,
    }
    if validate_canonical_json and manifest_bytes is not None:
        expected_bytes = _canonical_json_bytes(canonical_manifest, indent=2)
        if manifest_bytes != expected_bytes:
            raise RegistryError(f"noncanonical corpus manifest in {cases_key}")
    return canonical_manifest


def _validate_corpus_pair(
    store: BaseObjectStore,
    corpus_id: str,
    *,
    validate_canonical_contents: bool = True,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    corpus_id = _validate_path_safe_id(corpus_id, "corpusId")
    manifest_key = f"corpora/{corpus_id}/manifest.json"
    cases_key = f"corpora/{corpus_id}/cases.jsonl"
    if not store.exists(manifest_key):
        raise RegistryError(f"referenced corpus manifest does not exist: {manifest_key}")
    if not store.exists(cases_key):
        raise RegistryError(f"referenced corpus cases do not exist: {cases_key}")

    manifest_bytes = store.read_bytes(manifest_key)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"invalid JSON in {manifest_key}") from exc
    if not isinstance(manifest, dict):
        raise RegistryError(f"invalid JSON object in {manifest_key}")

    canonical_manifest = _validate_corpus_manifest_payload(
        manifest,
        corpus_id=corpus_id,
        cases_key=cases_key,
        expected_cases_object=store.key(cases_key),
        validate_canonical_json=validate_canonical_contents,
        manifest_bytes=manifest_bytes if validate_canonical_contents else None,
    )
    cases_bytes = store.read_bytes(cases_key)
    canonical_rows = _validate_corpus_cases_bytes(
        corpus_id,
        cases_bytes,
        validate_canonical_rows=validate_canonical_contents,
    )
    if canonical_manifest["caseCount"] != len(canonical_rows):
        raise RegistryError(f"case count mismatch for {manifest_key}")
    if canonical_manifest["casesSha256"] != _sha256_bytes(cases_bytes):
        raise RegistryError(f"cases checksum mismatch for {manifest_key}")
    return canonical_manifest, canonical_rows


def _validate_release_payload(
    record: Dict[str, Any],
    *,
    store: BaseObjectStore,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise RegistryError("record must be an object")
    _validate_no_forbidden_keys(record, "release record", _NON_CORPUS_FORBIDDEN_KEY_NAMES)
    _ensure_allowed_fields(record, frozenset(_RELEASE_REQUIRED_FIELDS + _RELEASE_OPTIONAL_FIELDS), "release record")

    release_id = _validate_path_safe_id(record.get("releaseId"), "releaseId")
    created_at = _validate_datetime_field(record.get("createdAt"), "createdAt")
    git_commit = _validate_string_field(record.get("gitCommit"), "gitCommit")
    change_summary = _validate_string_field(record.get("changeSummary"), "changeSummary")
    review_decision = _validate_string_field(record.get("reviewDecision"), "reviewDecision")
    rollout_status = _validate_string_field(record.get("rolloutStatus"), "rolloutStatus")
    provenance_completeness = _validate_string_field(record.get("provenanceCompleteness"), "provenanceCompleteness")
    corpus_ids = _validate_string_list(record.get("corpusIds"), "corpusIds", unique=True, path_safe=True)
    manifest_refs_raw = record.get("corpusManifestRefs")
    if not isinstance(manifest_refs_raw, list):
        raise RegistryError("corpusManifestRefs must be a list")
    if not manifest_refs_raw:
        raise RegistryError("corpusManifestRefs is required")

    prefix = f"{store.prefix}/" if store.prefix else ""
    canonical_manifest_refs: List[str] = []
    referenced_corpus_ids: List[str] = []
    for manifest_ref in manifest_refs_raw:
        if not isinstance(manifest_ref, str):
            raise RegistryError("corpusManifestRefs entries must be safe manifest paths")
        trimmed_ref = manifest_ref.strip()
        if not trimmed_ref:
            raise RegistryError("corpusManifestRefs entries must be safe manifest paths")
        relative_ref = trimmed_ref[len(prefix) :] if prefix and trimmed_ref.startswith(prefix) else trimmed_ref
        parts = relative_ref.split("/")
        if len(parts) != 3 or parts[0] != "corpora" or parts[2] != "manifest.json":
            raise RegistryError("corpusManifestRefs entries must be safe manifest paths")
        corpus_ref_id = _validate_path_safe_id(parts[1], "corpusManifestRefs corpusId")
        expected_relative_ref = f"corpora/{corpus_ref_id}/manifest.json"
        expected_ref = expected_relative_ref if not store.prefix else store.key(expected_relative_ref)
        if trimmed_ref not in {expected_relative_ref, expected_ref}:
            raise RegistryError("corpusManifestRefs entries must match expected manifest paths")
        _validate_corpus_pair(store, corpus_ref_id)
        referenced_corpus_ids.append(corpus_ref_id)
        canonical_manifest_refs.append(expected_ref)
    if len(set(referenced_corpus_ids)) != len(referenced_corpus_ids):
        raise RegistryError("corpusManifestRefs must not contain duplicates")
    if set(corpus_ids) != set(referenced_corpus_ids):
        raise RegistryError("corpusIds and corpusManifestRefs must reference the same corpora")

    payload: Dict[str, Any] = {
        "changeSummary": change_summary,
        "createdAt": created_at,
        "corpusIds": corpus_ids,
        "corpusManifestRefs": canonical_manifest_refs,
        "gitCommit": git_commit,
        "provenanceCompleteness": provenance_completeness,
        "releaseId": release_id,
        "reviewDecision": review_decision,
        "rolloutStatus": rollout_status,
    }

    optional_string_fields = (
        "schemaVersion",
        "recordType",
        "registryImplementationCommit",
        "appVersion",
        "cloudRunRevision",
        "cloudRunService",
        "image",
        "policyId",
        "modelVersion",
        "semanticIntentStatus",
    )
    for field in optional_string_fields:
        if field in record:
            payload[field] = _validate_string_field(record.get(field), field)

    if "versionCode" in record:
        payload["versionCode"] = _validate_positive_int_field(record.get("versionCode"), "versionCode")
    if "sourceEvidence" in record:
        value = record.get("sourceEvidence")
        if not isinstance(value, dict):
            raise RegistryError("sourceEvidence must be an object")
        payload["sourceEvidence"] = value
    if "evaluation" in record:
        value = record.get("evaluation")
        if not isinstance(value, dict):
            raise RegistryError("evaluation must be an object")
        payload["evaluation"] = value
    if "feedbackMatchSummary" in record:
        value = record.get("feedbackMatchSummary")
        if not isinstance(value, dict):
            raise RegistryError("feedbackMatchSummary must be an object")
        payload["feedbackMatchSummary"] = value
    if "rollout" in record:
        value = record.get("rollout")
        if not isinstance(value, dict):
            raise RegistryError("rollout must be an object")
        payload["rollout"] = value
    if "knownGaps" in record:
        payload["knownGaps"] = _validate_string_list(record.get("knownGaps"), "knownGaps", allow_empty=True)
    if "notes" in record:
        notes = record.get("notes")
        if isinstance(notes, str):
            payload["notes"] = _validate_string_field(notes, "notes")
        elif isinstance(notes, list):
            payload["notes"] = _validate_string_list(notes, "notes", allow_empty=True)
        else:
            raise RegistryError("notes must be a string or list of strings")
    return payload


def _validate_tombstone_payload(
    record: Dict[str, Any],
    *,
    store: BaseObjectStore,
    validate_corpus_contents: bool,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise RegistryError("record must be an object")
    _validate_no_forbidden_keys(record, "tombstone record", _NON_CORPUS_FORBIDDEN_KEY_NAMES)
    _ensure_allowed_fields(record, frozenset(_TOMBSTONE_REQUIRED_FIELDS + _TOMBSTONE_OPTIONAL_FIELDS), "tombstone record")

    tombstone_id = _validate_path_safe_id(record.get("tombstoneId"), "tombstoneId")
    created_at = _validate_datetime_field(record.get("createdAt"), "createdAt")
    reason = _validate_string_field(record.get("reason"), "reason")
    corpus_id = _validate_path_safe_id(record.get("corpusId"), "corpusId")
    case_ids = _validate_string_list(record.get("caseIds"), "caseIds", unique=True, path_safe=True)

    _, canonical_rows = _validate_corpus_pair(
        store,
        corpus_id,
        validate_canonical_contents=validate_corpus_contents,
    )
    existing_case_ids = {row["caseId"] for row in canonical_rows}
    missing_case_ids = [case_id for case_id in case_ids if case_id not in existing_case_ids]
    if missing_case_ids:
        raise RegistryError(f"caseIds not found in corpus {corpus_id}: {missing_case_ids[0]}")

    payload: Dict[str, Any] = {
        "caseIds": case_ids,
        "corpusId": corpus_id,
        "createdAt": created_at,
        "reason": reason,
        "tombstoneId": tombstone_id,
    }
    if "sourceFeedbackIds" in record:
        payload["sourceFeedbackIds"] = _validate_string_list(record.get("sourceFeedbackIds"), "sourceFeedbackIds", unique=True)
    if "deletionScope" in record:
        payload["deletionScope"] = _validate_string_field(record.get("deletionScope"), "deletionScope")
    if "rawDataDeletionStatus" in record:
        payload["rawDataDeletionStatus"] = _validate_string_field(record.get("rawDataDeletionStatus"), "rawDataDeletionStatus")
    return payload


class BaseObjectStore:
    def __init__(self, prefix: str = "") -> None:
        self.prefix = _normalize_prefix(prefix)

    def key(self, relative_path: str) -> str:
        return _join_key(self.prefix, relative_path)

    def resolve_key(self, relative_path: str) -> str:
        normalized = str(relative_path).strip("/")
        if not self.prefix:
            return normalized
        if normalized == self.prefix or normalized.startswith(self.prefix + "/"):
            return normalized
        return self.key(normalized)

    def read_bytes(self, relative_path: str) -> bytes:
        raise NotImplementedError

    def write_bytes(self, relative_path: str, data: bytes) -> None:
        raise NotImplementedError

    def exists(self, relative_path: str) -> bool:
        raise NotImplementedError

    def list_keys(self, relative_prefix: str = "") -> List[str]:
        raise NotImplementedError

    def get_generation(self, relative_path: str) -> Optional[int]:
        return None

    def replace_bytes(self, relative_path: str, data: bytes, expected_generation: Optional[int] = None) -> None:
        raise NotImplementedError

    def put_create_only(self, relative_path: str, data: bytes) -> bool:
        raise NotImplementedError


class LocalObjectStore(BaseObjectStore):
    def __init__(self, root: str | Path, prefix: str = "") -> None:
        super().__init__(prefix=prefix)
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, relative_path: str) -> Path:
        root = self.root.resolve()
        path = (root / self.resolve_key(relative_path)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RegistryError("object path escapes local store root") from exc
        return path

    def read_bytes(self, relative_path: str) -> bytes:
        return self._path(relative_path).read_bytes()

    def write_bytes(self, relative_path: str, data: bytes) -> None:
        path = self._path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(path.parent), prefix=path.name + ".tmp-") as handle:
            handle.write(data)
            temp_name = handle.name
        os.replace(temp_name, path)

    def exists(self, relative_path: str) -> bool:
        return self._path(relative_path).exists()

    def list_keys(self, relative_prefix: str = "") -> List[str]:
        base = self._path(relative_prefix)
        if base.is_file():
            return [self.key(relative_prefix)]
        start = self.root / self.prefix if self.prefix else self.root
        if not start.exists():
            return []
        keys: List[str] = []
        for path in start.rglob("*"):
            if path.is_file():
                keys.append(path.relative_to(self.root).as_posix())
        return sorted(keys)

    def put_create_only(self, relative_path: str, data: bytes) -> bool:
        path = self._path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            existing = path.read_bytes()
            if existing == data:
                return False
            raise ObjectConflictError(f"conflicting bytes for {self.key(relative_path)}")

        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return True

    def replace_bytes(self, relative_path: str, data: bytes, expected_generation: Optional[int] = None) -> None:
        self.write_bytes(relative_path, data)


class GcsObjectStore(BaseObjectStore):
    def __init__(self, bucket_name: str, prefix: str = "") -> None:
        super().__init__(prefix=prefix)
        from google.cloud import storage  # lazy import
        from google.api_core.exceptions import PreconditionFailed

        self._storage = storage
        self._precondition_failed = PreconditionFailed
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def _blob(self, relative_path: str):
        return self.bucket.blob(self.resolve_key(relative_path))

    def read_bytes(self, relative_path: str) -> bytes:
        blob = self._blob(relative_path)
        return blob.download_as_bytes()

    def write_bytes(self, relative_path: str, data: bytes) -> None:
        self.put_create_only(relative_path, data)

    def exists(self, relative_path: str) -> bool:
        return self._blob(relative_path).exists(self.client)

    def list_keys(self, relative_prefix: str = "") -> List[str]:
        prefix = self.key(relative_prefix)
        blobs = self.client.list_blobs(self.bucket, prefix=prefix if prefix else None)
        keys = [blob.name for blob in blobs]
        return sorted(keys)

    def get_generation(self, relative_path: str) -> Optional[int]:
        blob = self._blob(relative_path)
        if not blob.exists(self.client):
            return None
        blob.reload()
        return int(blob.generation)

    def put_create_only(self, relative_path: str, data: bytes) -> bool:
        blob = self._blob(relative_path)
        try:
            blob.upload_from_string(data, if_generation_match=0)
            return True
        except self._precondition_failed as exc:
            existing = blob.download_as_bytes()
            if existing == data:
                return False
            raise ObjectConflictError(f"conflicting bytes for {self.key(relative_path)}") from exc

    def replace_bytes(self, relative_path: str, data: bytes, expected_generation: Optional[int] = None) -> None:
        blob = self._blob(relative_path)
        if expected_generation is None:
            expected_generation = self.get_generation(relative_path)
        precondition = 0 if expected_generation is None else int(expected_generation)
        blob.upload_from_string(data, if_generation_match=precondition)


class LearningRegistry:
    def __init__(self, store: BaseObjectStore) -> None:
        self.store = store

    @property
    def prefix(self) -> str:
        return self.store.prefix

    def _object_path(self, relative_path: str) -> str:
        return self.store.key(relative_path)

    def bootstrap(self, asset_root: str | Path) -> Dict[str, Any]:
        asset_root = Path(asset_root)
        if not asset_root.exists():
            raise FileNotFoundError(asset_root)

        copied = []
        start_here = asset_root / "START_HERE.md"
        if not start_here.exists():
            raise FileNotFoundError(start_here)
        self.store.put_create_only("START_HERE.md", start_here.read_bytes())
        copied.append("START_HERE.md")

        schemas_root = asset_root / "schemas"
        if not schemas_root.exists():
            raise FileNotFoundError(schemas_root)
        for schema_path in sorted(schemas_root.rglob("*.schema.json")):
            rel = schema_path.relative_to(asset_root).as_posix()
            self.store.put_create_only(rel, schema_path.read_bytes())
            copied.append(rel)
        if not copied[1:]:
            raise FileNotFoundError(schemas_root / "*.schema.json")

        self.rebuild_index()
        return {"ok": True, "copied": copied}

    def publish_corpus(self, corpus_id: str, rows: Iterable[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        corpus_id = _validate_path_safe_id(corpus_id, "corpus_id")
        metadata = _validate_corpus_manifest_metadata(metadata)

        canonical_rows: List[Dict[str, Any]] = []
        seen_case_ids = set()
        for row in rows:
            if not isinstance(row, dict):
                raise RegistryError("each corpus row must be an object")
            canonical_row = _validate_corpus_case_row(row)
            case_id = canonical_row["caseId"]
            if case_id in seen_case_ids:
                raise RegistryError(f"duplicate caseId: {case_id}")
            seen_case_ids.add(case_id)
            canonical_rows.append(canonical_row)

        canonical_rows.sort(key=lambda item: item["caseId"])
        cases_bytes = b"".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
            for row in canonical_rows
        )
        cases_sha256 = _sha256_bytes(cases_bytes)
        manifest = {
            "corpusId": corpus_id,
            "metadata": metadata,
            "caseCount": len(canonical_rows),
            "casesSha256": cases_sha256,
            "casesObject": self._object_path(f"corpora/{corpus_id}/cases.jsonl"),
        }
        manifest_bytes = _canonical_json_bytes(manifest, indent=2)

        self.store.put_create_only(f"corpora/{corpus_id}/cases.jsonl", cases_bytes)
        self.store.put_create_only(f"corpora/{corpus_id}/manifest.json", manifest_bytes)
        self.rebuild_index()
        return {"ok": True, "corpusId": corpus_id, "caseCount": len(canonical_rows), "casesSha256": cases_sha256}

    def register_release(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = _validate_release_payload(record, store=self.store)
        release_id = payload["releaseId"]
        data = _canonical_json_bytes(payload, indent=2)
        self.store.put_create_only(f"releases/{release_id}.json", data)
        self.rebuild_index()
        return {"ok": True, "releaseId": release_id}

    def record_tombstone(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = _validate_tombstone_payload(record, store=self.store, validate_corpus_contents=True)
        tombstone_id = payload["tombstoneId"]
        data = _canonical_json_bytes(payload, indent=2)
        self.store.put_create_only(f"tombstones/{tombstone_id}.json", data)
        self.rebuild_index()
        return {"ok": True, "tombstoneId": tombstone_id, "caseCount": len(payload["caseIds"])}

    def _iter_known_objects(self) -> Dict[str, List[str]]:
        keys = self.store.list_keys()
        grouped = {
            "corpora": sorted([key for key in keys if "/corpora/" in f"/{key}" and key.endswith("/manifest.json")]),
            "releases": sorted([key for key in keys if "/releases/" in f"/{key}" and key.endswith(".json")]),
            "tombstones": sorted([key for key in keys if "/tombstones/" in f"/{key}" and key.endswith(".json")]),
            "schemas": sorted([key for key in keys if key.endswith(".schema.json")]),
        }
        return grouped

    def rebuild_index(self) -> Dict[str, Any]:
        keys = set(self.store.list_keys())
        corpora = []
        for manifest_key in sorted(k for k in keys if k.endswith("/manifest.json") and "/corpora/" in f"/{k}"):
            manifest = json.loads(self.store.read_bytes(manifest_key).decode("utf-8"))
            corpus_dir = manifest_key.rsplit("/", 1)[0]
            cases_key = f"{corpus_dir}/cases.jsonl"
            corpora.append(
                {
                    "caseCount": manifest.get("caseCount"),
                    "casesObject": cases_key,
                    "casesSha256": manifest.get("casesSha256"),
                    "corpusId": manifest.get("corpusId"),
                    "manifestObject": manifest_key,
                }
            )

        releases = []
        for release_key in sorted(k for k in keys if k.endswith(".json") and "/releases/" in f"/{k}"):
            payload = json.loads(self.store.read_bytes(release_key).decode("utf-8"))
            releases.append(
                {
                    "createdAt": payload.get("createdAt"),
                    "gitCommit": payload.get("gitCommit"),
                    "provenanceCompleteness": payload.get("provenanceCompleteness"),
                    "releaseId": payload.get("releaseId"),
                    "releaseObject": release_key,
                    "reviewDecision": payload.get("reviewDecision"),
                    "rolloutStatus": payload.get("rolloutStatus"),
                }
            )

        tombstones = []
        for tombstone_key in sorted(k for k in keys if k.endswith(".json") and "/tombstones/" in f"/{k}"):
            payload = json.loads(self.store.read_bytes(tombstone_key).decode("utf-8"))
            tombstones.append(
                {
                    "caseCount": len(payload.get("caseIds", []) or []),
                    "createdAt": payload.get("createdAt"),
                    "tombstoneId": payload.get("tombstoneId"),
                    "tombstoneObject": tombstone_key,
                }
            )

        index_payload = {
            "corpora": corpora,
            "counts": {
                "corpora": len(corpora),
                "releases": len(releases),
                "schemas": len([key for key in keys if key.endswith(".schema.json")]),
                "tombstones": len(tombstones),
            },
            "prefix": self.store.prefix,
            "releases": releases,
            "schemas": [key for key in sorted(keys) if key.endswith(".schema.json")],
            "tombstones": tombstones,
            "updatedAt": _utc_now(),
            "version": 1,
        }
        data = _canonical_json_bytes(index_payload, indent=2)
        expected_generation = self.store.get_generation("index.json")
        self.store.replace_bytes("index.json", data, expected_generation=expected_generation)
        return index_payload

    def _read_index(self) -> Optional[Dict[str, Any]]:
        if not self.store.exists("index.json"):
            return None
        return json.loads(self.store.read_bytes("index.json").decode("utf-8"))

    def verify(self) -> Dict[str, Any]:
        problems: List[str] = []
        keys = set(self.store.list_keys())
        manifest_keys = {
            key for key in keys if key.endswith("/manifest.json") and "/corpora/" in f"/{key}"
        }
        cases_keys = {
            key for key in keys if key.endswith("/cases.jsonl") and "/corpora/" in f"/{key}"
        }
        release_keys = {
            key for key in keys if key.endswith(".json") and "/releases/" in f"/{key}"
        }
        tombstone_keys = {
            key for key in keys if key.endswith(".json") and "/tombstones/" in f"/{key}"
        }
        schema_keys = {key for key in keys if key.endswith(".schema.json")}
        counts: Dict[str, Any] = {
            "actualObjects": len(keys),
            "actualCorpora": len(manifest_keys),
            "actualReleases": len(release_keys),
            "actualSchemas": len(schema_keys),
            "actualTombstones": len(tombstone_keys),
        }

        def add_problem(problem: str) -> None:
            if problem not in problems:
                problems.append(problem)

        if not self.store.exists("START_HERE.md"):
            add_problem("missing START_HERE.md")
        if not schema_keys:
            add_problem("missing schemas")

        def _relative_key(object_key: str) -> str:
            prefix = self.store.prefix
            if prefix and object_key.startswith(prefix + "/"):
                return object_key[len(prefix) + 1 :]
            if prefix and object_key == prefix:
                return ""
            return object_key

        def _is_allowed_object_key(object_key: str) -> bool:
            relative_key = _relative_key(object_key)
            if relative_key in {"START_HERE.md", "index.json"}:
                return True
            if relative_key.startswith("schemas/") and relative_key.endswith(".schema.json"):
                return True
            if relative_key.startswith("corpora/"):
                parts = relative_key.split("/")
                return len(parts) == 3 and parts[1] and _PATH_SAFE_ID_RE.fullmatch(parts[1]) is not None and parts[2] in {
                    "manifest.json",
                    "cases.jsonl",
                }
            if relative_key.startswith("releases/"):
                parts = relative_key.split("/")
                return (
                    len(parts) == 2
                    and parts[1].endswith(".json")
                    and _PATH_SAFE_ID_RE.fullmatch(parts[1][:-5]) is not None
                )
            if relative_key.startswith("tombstones/"):
                parts = relative_key.split("/")
                return (
                    len(parts) == 2
                    and parts[1].endswith(".json")
                    and _PATH_SAFE_ID_RE.fullmatch(parts[1][:-5]) is not None
                )
            return False

        for object_key in sorted(keys):
            if not _is_allowed_object_key(object_key):
                add_problem(f"objectAdmin-bypass object: {object_key}")

        parsed_objects: Dict[str, Dict[str, Any]] = {}
        validated_tombstones: Dict[str, Dict[str, Any]] = {}
        for object_key in sorted(manifest_keys | release_keys | tombstone_keys | schema_keys):
            try:
                raw_bytes = self.store.read_bytes(object_key)
                payload = json.loads(raw_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                add_problem(f"invalid JSON in {object_key}")
                continue
            if not isinstance(payload, dict):
                add_problem(f"invalid JSON object in {object_key}")
                continue
            parsed_objects[object_key] = payload

            try:
                if object_key in manifest_keys:
                    corpus_dir = object_key.rsplit("/", 1)[0]
                    corpus_id = corpus_dir.rsplit("/", 1)[-1]
                    _validate_corpus_pair(self.store, corpus_id)
                elif object_key in release_keys:
                    canonical_release = _validate_release_payload(payload, store=self.store)
                    expected_release_key = self.store.key(f"releases/{canonical_release['releaseId']}.json")
                    if object_key != expected_release_key:
                        add_problem(f"release path/id mismatch: {object_key}")
                    if raw_bytes != _canonical_json_bytes(canonical_release, indent=2):
                        add_problem(f"noncanonical release record: {object_key}")
                elif object_key in tombstone_keys:
                    canonical_tombstone = _validate_tombstone_payload(payload, store=self.store, validate_corpus_contents=True)
                    validated_tombstones[object_key] = canonical_tombstone
                    expected_tombstone_key = self.store.key(f"tombstones/{canonical_tombstone['tombstoneId']}.json")
                    if object_key != expected_tombstone_key:
                        add_problem(f"tombstone path/id mismatch: {object_key}")
                    if raw_bytes != _canonical_json_bytes(canonical_tombstone, indent=2):
                        add_problem(f"noncanonical tombstone record: {object_key}")
            except RegistryError as exc:
                add_problem(str(exc))

        cases_bytes_by_key: Dict[str, bytes] = {}
        case_counts_by_key: Dict[str, int] = {}
        for cases_key in sorted(cases_keys):
            cases_bytes = self.store.read_bytes(cases_key)
            cases_bytes_by_key[cases_key] = cases_bytes
            try:
                rows = _validate_corpus_cases_bytes(cases_key.rsplit("/", 1)[0].rsplit("/", 1)[-1], cases_bytes, validate_canonical_rows=True)
            except RegistryError as exc:
                add_problem(str(exc))
                rows = []
            case_counts_by_key[cases_key] = len(rows)

        for manifest_key in sorted(manifest_keys):
            manifest = parsed_objects.get(manifest_key)
            if manifest is None:
                continue
            corpus_dir = manifest_key.rsplit("/", 1)[0]
            cases_key = f"{corpus_dir}/cases.jsonl"
            if cases_key not in cases_keys:
                add_problem(f"missing cases for manifest: {manifest_key}")
                continue
            cases_bytes = cases_bytes_by_key[cases_key]
            if manifest.get("casesSha256") != _sha256_bytes(cases_bytes):
                add_problem(f"cases checksum mismatch for {manifest_key}")
            if manifest.get("caseCount") != case_counts_by_key[cases_key]:
                add_problem(f"case count mismatch for {manifest_key}")

        for cases_key in sorted(cases_keys):
            manifest_key = f"{cases_key.rsplit('/', 1)[0]}/manifest.json"
            if manifest_key not in manifest_keys:
                add_problem(f"missing manifest for cases: {cases_key}")

        index: Optional[Dict[str, Any]] = None
        if not self.store.exists("index.json"):
            add_problem("missing index.json")
        else:
            try:
                index_payload = json.loads(self.store.read_bytes("index.json").decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                add_problem("invalid JSON in index.json")
            else:
                if isinstance(index_payload, dict):
                    index = index_payload
                else:
                    add_problem("invalid JSON object in index.json")

        if index is not None:
            def index_entries(name: str) -> List[Dict[str, Any]]:
                value = index.get(name)
                if not isinstance(value, list):
                    add_problem(f"invalid {name} list in index.json")
                    return []
                entries: List[Dict[str, Any]] = []
                for position, entry in enumerate(value):
                    if not isinstance(entry, dict):
                        add_problem(f"invalid {name} entry in index.json at position {position}")
                    else:
                        entries.append(entry)
                return entries

            corpus_entries = index_entries("corpora")
            release_entries = index_entries("releases")
            tombstone_entries = index_entries("tombstones")
            indexed_schema_value = index.get("schemas")
            if not isinstance(indexed_schema_value, list) or not all(
                isinstance(key, str) for key in indexed_schema_value
            ):
                add_problem("invalid schemas list in index.json")
                indexed_schema_keys: set[str] = set()
            else:
                indexed_schema_keys = set(indexed_schema_value)

            def indexed_keys(entries: List[Dict[str, Any]], field: str, label: str) -> set[str]:
                result: set[str] = set()
                for position, entry in enumerate(entries):
                    object_key = entry.get(field)
                    if not isinstance(object_key, str) or not object_key:
                        add_problem(f"missing {label} object in index.json at position {position}")
                    else:
                        result.add(object_key)
                return result

            indexed_manifest_keys = indexed_keys(corpus_entries, "manifestObject", "corpus manifest")
            indexed_cases_keys = indexed_keys(corpus_entries, "casesObject", "corpus cases")
            indexed_release_keys = indexed_keys(release_entries, "releaseObject", "release")
            indexed_tombstone_keys = indexed_keys(tombstone_entries, "tombstoneObject", "tombstone")
            actual_immutable_keys = manifest_keys | cases_keys | release_keys | tombstone_keys | schema_keys
            indexed_immutable_keys = (
                indexed_manifest_keys
                | indexed_cases_keys
                | indexed_release_keys
                | indexed_tombstone_keys
                | indexed_schema_keys
            )
            for object_key in sorted(actual_immutable_keys - indexed_immutable_keys):
                add_problem(f"stale index: unindexed immutable object: {object_key}")
            for object_key in sorted(indexed_immutable_keys - actual_immutable_keys):
                add_problem(f"stale index: indexed object missing: {object_key}")

            counts.update(
                {
                    "corpora": len(corpus_entries),
                    "releases": len(release_entries),
                    "schemas": len(indexed_schema_keys),
                    "tombstones": len(tombstone_entries),
                    "indexedObjects": len(indexed_immutable_keys),
                    "indexObjects": {
                        "corpora": len(corpus_entries),
                        "releases": len(release_entries),
                        "tombstones": len(tombstone_entries),
                    },
                }
            )

            if index.get("prefix") != self.store.prefix:
                add_problem("stale index: prefix mismatch")
            index_counts = index.get("counts")
            expected_index_counts = {
                "corpora": len(corpus_entries),
                "releases": len(release_entries),
                "schemas": len(indexed_schema_keys),
                "tombstones": len(tombstone_entries),
            }
            if not isinstance(index_counts, dict):
                add_problem("invalid counts in index.json")
            else:
                for name, expected_count in expected_index_counts.items():
                    if index_counts.get(name) != expected_count:
                        add_problem(f"stale index count mismatch for {name}")

            for corpus in corpus_entries:
                manifest_key = corpus.get("manifestObject")
                if not isinstance(manifest_key, str):
                    continue
                manifest = parsed_objects.get(manifest_key)
                if manifest is None:
                    continue
                expected_cases_key = f"{manifest_key.rsplit('/', 1)[0]}/cases.jsonl"
                expected_summary = {
                    "caseCount": manifest.get("caseCount"),
                    "casesObject": expected_cases_key,
                    "casesSha256": manifest.get("casesSha256"),
                    "corpusId": manifest.get("corpusId"),
                }
                for field, expected_value in expected_summary.items():
                    if corpus.get(field) != expected_value:
                        add_problem(f"stale index corpus summary for {manifest_key}: {field}")

            for release in release_entries:
                release_key = release.get("releaseObject")
                if not isinstance(release_key, str):
                    continue
                payload = parsed_objects.get(release_key)
                if payload is None:
                    continue
                for field in (
                    "createdAt",
                    "gitCommit",
                    "provenanceCompleteness",
                    "releaseId",
                    "reviewDecision",
                    "rolloutStatus",
                ):
                    if release.get(field) != payload.get(field):
                        add_problem(f"stale index release summary for {release_key}: {field}")

            for tombstone in tombstone_entries:
                tombstone_key = tombstone.get("tombstoneObject")
                if not isinstance(tombstone_key, str):
                    continue
                payload = validated_tombstones.get(tombstone_key)
                if payload is None:
                    continue
                expected_summary = {
                    "caseCount": len(payload.get("caseIds", []) or []),
                    "createdAt": payload.get("createdAt"),
                    "tombstoneId": payload.get("tombstoneId"),
                }
                for field, expected_value in expected_summary.items():
                    if tombstone.get(field) != expected_value:
                        add_problem(f"stale index tombstone summary for {tombstone_key}: {field}")

        return {"ok": not problems, "problems": problems, "counts": counts}

    def show(self) -> Dict[str, Any]:
        index = self._read_index()
        if index is None:
            return {"ok": False, "problems": ["missing index.json"]}
        return index
