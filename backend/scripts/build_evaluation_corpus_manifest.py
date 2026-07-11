"""Build a privacy-safe manifest for evaluation corpora.

The command only records file metadata needed for release review. It never
prints or exports record contents.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CorpusEntry:
    path: str
    role: str
    frozen: bool


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    return default


def _repo_relative_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_registry(registry_path: Path) -> List[CorpusEntry]:
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        entries = payload.get("entries")
        if entries is None:
            entries = payload.get("corpora")
    else:
        entries = payload
    if not isinstance(entries, list):
        raise ValueError("registry must be a JSON list or an object with entries")

    corpus_entries: List[CorpusEntry] = []
    for index, raw in enumerate(entries, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"registry entry {index} must be an object")
        raw_path = raw.get("path")
        if not raw_path:
            raise ValueError(f"registry entry {index} is missing path")
        role = str(raw.get("role") or "unknown").strip() or "unknown"
        corpus_entries.append(
            CorpusEntry(
                path=str(raw_path),
                role=role,
                frozen=_coerce_bool(raw.get("frozen")),
            )
        )
    return corpus_entries


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _sha256_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _count_records(path: Path) -> Optional[int]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            row_count = -1
            for row_count, _ in enumerate(reader):
                pass
        return max(row_count, 0)
    if suffix == ".jsonl":
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                json.loads(line)
                count += 1
        return count
    return None


def _build_manifest_entry(entry: CorpusEntry, repo_root: Path) -> Dict[str, Any]:
    resolved = (repo_root / entry.path).resolve() if not Path(entry.path).is_absolute() else Path(entry.path).resolve()
    relative_path = _repo_relative_path(resolved, repo_root)
    exists = resolved.exists()
    digest = None
    byte_count = None
    record_count = None
    if exists:
        data = _read_bytes(resolved)
        digest = _sha256_digest(data)
        byte_count = len(data)
        record_count = _count_records(resolved)

    return {
        "path": relative_path,
        "role": entry.role,
        "frozen": entry.frozen,
        "exists": exists,
        "sha256": digest,
        "byteCount": byte_count,
        "recordCount": record_count,
    }


def build_manifest(registry_path: Path, repo_root: Path) -> Dict[str, Any]:
    entries = [_build_manifest_entry(entry, repo_root) for entry in _load_registry(registry_path)]
    entries.sort(key=lambda row: (row["path"], row["role"]))
    return {
        "repoRoot": ".",
        "entries": entries,
    }


def _load_manifest(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{path} is missing entries")
    return payload


def _manifest_key(entry: Dict[str, Any]) -> Tuple[str, str]:
    return str(entry.get("path")), str(entry.get("role") or "unknown")


def _compare_baseline(current: Dict[str, Any], baseline: Dict[str, Any]) -> List[str]:
    current_entries = {
        _manifest_key(entry): entry
        for entry in current.get("entries", [])
        if isinstance(entry, dict)
    }
    problems: List[str] = []
    for baseline_entry in baseline.get("entries", []):
        if not isinstance(baseline_entry, dict):
            continue
        if not baseline_entry.get("frozen"):
            continue
        key = _manifest_key(baseline_entry)
        current_entry = current_entries.get(key)
        if current_entry is None:
            problems.append(f"missing frozen corpus: {key[0]} [{key[1]}]")
            continue
        if not current_entry.get("exists"):
            problems.append(f"missing frozen corpus file: {key[0]} [{key[1]}]")
            continue
        if current_entry.get("sha256") != baseline_entry.get("sha256"):
            problems.append(f"sha256 drift for frozen corpus: {key[0]} [{key[1]}]")
        if current_entry.get("recordCount") != baseline_entry.get("recordCount"):
            problems.append(f"recordCount drift for frozen corpus: {key[0]} [{key[1]}]")
    return problems


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an evaluation corpus manifest.")
    parser.add_argument("--registry", required=True, type=Path, help="JSON registry of corpus entries")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT_DIR,
        help="Repository root used to resolve registry paths",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output manifest JSON path")
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Previous manifest JSON used to enforce frozen corpus stability",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    manifest = build_manifest(args.registry, args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.baseline:
        baseline = _load_manifest(args.baseline)
        problems = _compare_baseline(manifest, baseline)
        if problems:
            for problem in problems:
                print(problem)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
