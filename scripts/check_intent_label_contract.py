"""Verify the intent label contract across metadata, pickle, and Kotlin source."""

from __future__ import annotations

import argparse
import json
import pickletools
import sys
from pathlib import Path
from typing import Sequence


REQUIRED_CANONICAL_LABELS: tuple[str, ...] = (
    "APP_ACCOUNT_CHANGE_OTP",
    "APP_LOGIN_OTP",
    "BANK_OR_CARD_TXN_OTP",
    "DELIVERY_OR_SERVICE_OTP",
    "FINANCIAL_LOGIN_OTP",
    "GENERIC_APP_ACTION_OTP",
    "KYC_OR_ESIGN_OTP",
    "NOT_OTP",
    "UPI_TXN_OR_PIN_OTP",
)


class ContractError(RuntimeError):
    """Raised when the intent label contract drifts."""


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_metadata_labels(metadata_path: Path) -> list[str]:
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"Missing metadata file: {metadata_path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in metadata file: {metadata_path}") from exc

    try:
        labels = metadata["models"]["otp_intent"]["class_names"]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            "model_metadata.json is missing models.otp_intent.class_names"
        ) from exc

    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        raise ContractError("model_metadata.json has a non-string otp_intent.class_names list")

    return labels


def load_pickle_labels(pkl_path: Path) -> list[str]:
    try:
        raw = pkl_path.read_bytes()
    except FileNotFoundError as exc:
        raise ContractError(f"Missing label encoder file: {pkl_path}") from exc

    labels: list[str] = []
    seen_classes_key = False
    capture_list = False
    in_label_mark = False

    for opcode, arg, _pos in pickletools.genops(raw):
        if not capture_list:
            if opcode.name in _STRING_OPS and arg == "classes_":
                seen_classes_key = True
                continue
            if seen_classes_key and opcode.name == "EMPTY_LIST":
                capture_list = True
                continue
            continue

        if opcode.name == "MARK":
            in_label_mark = True
            continue

        if opcode.name == "APPENDS":
            if labels:
                return labels
            break

        if in_label_mark and opcode.name in _STRING_OPS:
            labels.append(str(arg))

    raise ContractError(
        f"Could not extract classes_ labels from pickle file: {pkl_path}"
    )


def extract_kotlin_list(text: str, marker: str) -> list[str]:
    marker_pos = text.find(marker)
    if marker_pos < 0:
        raise ContractError(f"Could not find Kotlin marker: {marker}")

    list_pos = text.find("listOf(", marker_pos)
    if list_pos < 0:
        raise ContractError(f"Could not find hard-coded listOf(...) after {marker}")

    start = list_pos + len("listOf(")
    depth = 1
    labels: list[str] = []
    i = start
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_string:
            if escaped:
                current.append(ch)
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                labels.append("".join(current))
                current = []
                in_string = False
            else:
                current.append(ch)
            i += 1
            continue

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == '"':
            in_string = True
            current = []
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return labels
            if depth < 0:
                break
        i += 1

    raise ContractError(f"Failed to parse Kotlin listOf(...) in {marker}")


def load_kotlin_labels(kotlin_path: Path) -> list[str]:
    try:
        text = kotlin_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContractError(f"Missing Kotlin classifier file: {kotlin_path}") from exc

    try:
        return extract_kotlin_list(text, "private fun mapIntentIndex")
    except ContractError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ContractError(f"Failed to parse Kotlin intent labels from {kotlin_path}") from exc


def ensure_equal(name: str, actual: Sequence[str], expected: Sequence[str]) -> None:
    if list(actual) == list(expected):
        return

    missing = [label for label in expected if label not in actual]
    extra = [label for label in actual if label not in expected]
    message_lines = [f"{name} labels drifted."]
    message_lines.append(f"Expected: {list(expected)}")
    message_lines.append(f"Actual:   {list(actual)}")
    if missing:
        message_lines.append(f"Missing:  {missing}")
    if extra:
        message_lines.append(f"Extra:    {extra}")
    raise ContractError("\n".join(message_lines))


def check_contract(
    repo_root: Path | None = None,
    *,
    metadata_path: Path | None = None,
    pickle_path: Path | None = None,
    kotlin_path: Path | None = None,
    skip_pickle: bool = False,
) -> dict[str, list[str]]:
    root = repo_root or default_repo_root()
    metadata_path = metadata_path or root / "app/src/main/assets/model_metadata.json"
    pickle_path = pickle_path or root / "trained_models/label_encoder_intent.pkl"
    kotlin_path = kotlin_path or root / "app/src/main/java/com/smsclassifier/app/classification/OnDeviceClassifier.kt"

    metadata_labels = load_metadata_labels(metadata_path)
    ensure_equal("model_metadata.json otp_intent.class_names", metadata_labels, REQUIRED_CANONICAL_LABELS)

    pickle_labels: list[str] = []
    if not skip_pickle:
        pickle_labels = load_pickle_labels(pickle_path)
        ensure_equal("label_encoder_intent.pkl classes_", pickle_labels, REQUIRED_CANONICAL_LABELS)

    kotlin_labels = load_kotlin_labels(kotlin_path)
    ensure_equal("OnDeviceClassifier.kt mapIntentIndex()", kotlin_labels, REQUIRED_CANONICAL_LABELS)

    return {
        "metadata_labels": metadata_labels,
        "pickle_labels": pickle_labels,
        "kotlin_labels": kotlin_labels,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify SMS classifier intent label contract.")
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--metadata-path", type=Path)
    parser.add_argument("--pickle-path", type=Path)
    parser.add_argument("--kotlin-path", type=Path)
    parser.add_argument(
        "--skip-pickle",
        action="store_true",
        help="Check only shipped metadata and Kotlin labels when training artifacts are unavailable.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = check_contract(
            args.repo_root,
            metadata_path=args.metadata_path,
            pickle_path=args.pickle_path,
            kotlin_path=args.kotlin_path,
            skip_pickle=args.skip_pickle,
        )
    except ContractError as exc:
        print(f"INTENT LABEL CONTRACT FAILED: {exc}", file=sys.stderr)
        return 1

    labels = result["kotlin_labels"]
    print(
        "INTENT LABEL CONTRACT OK: "
        f"{len(labels)} labels verified across shipped metadata and Kotlin source"
        + ("." if args.skip_pickle else ", plus the training label encoder.")
    )
    return 0


_STRING_OPS = {
    "BINUNICODE",
    "BINUNICODE8",
    "SHORT_BINUNICODE",
    "UNICODE",
    "STRING",
}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
