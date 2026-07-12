from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.learning_registry import GcsObjectStore, LearningRegistry, LocalObjectStore


def _load_json_file(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl_file(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line:
                yield json.loads(line)


def _build_registry(args: argparse.Namespace) -> LearningRegistry:
    if args.backend == "gcs":
        bucket = args.bucket or os.environ.get("LEARNING_REGISTRY_GCS_BUCKET") or os.environ.get("FEEDBACK_GCS_BUCKET")
        if not bucket:
            raise SystemExit("missing GCS bucket")
        store = GcsObjectStore(bucket, prefix=args.prefix)
    else:
        store = LocalObjectStore(args.root, prefix=args.prefix)
    return LearningRegistry(store)


def _safe_print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="learning_registry")
    parser.add_argument("--backend", choices=("local", "gcs"), default="local")
    parser.add_argument("--root", default=str(ROOT_DIR / "learning_registry_store"))
    parser.add_argument("--bucket")
    parser.add_argument("--prefix", default="learning_registry/v1")

    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--assets", required=True)

    publish = subparsers.add_parser("publish-corpus")
    publish.add_argument("--corpus-id", required=True)
    publish.add_argument("--input", required=True)
    publish.add_argument("--metadata", required=True)

    register = subparsers.add_parser("register-release")
    register.add_argument("--file", required=True)

    tombstone = subparsers.add_parser("tombstone")
    tombstone.add_argument("--file", required=True)

    subparsers.add_parser("rebuild-index")
    subparsers.add_parser("verify")
    subparsers.add_parser("show")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = _build_registry(args)

    if args.command == "bootstrap":
        result = registry.bootstrap(args.assets)
    elif args.command == "publish-corpus":
        result = registry.publish_corpus(args.corpus_id, _load_jsonl_file(args.input), _load_json_file(args.metadata))
    elif args.command == "register-release":
        result = registry.register_release(_load_json_file(args.file))
    elif args.command == "tombstone":
        result = registry.record_tombstone(_load_json_file(args.file))
    elif args.command == "rebuild-index":
        result = registry.rebuild_index()
    elif args.command == "verify":
        result = registry.verify()
    elif args.command == "show":
        result = registry.show()
    else:
        raise SystemExit(f"unknown command: {args.command}")

    _safe_print(result)
    if args.command == "verify" and not result.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
