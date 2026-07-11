from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scripts import build_evaluation_corpus_manifest as bem


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class BuildEvaluationCorpusManifestTests(unittest.TestCase):
    def test_manifest_is_deterministic_for_same_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = temp_path / "repo"
            corpus = repo_root / "data" / "train.jsonl"
            registry = temp_path / "registry.json"
            output_one = temp_path / "manifest-one.json"
            output_two = temp_path / "manifest-two.json"

            _write_text(corpus, '{"id": 1}\n{"id": 2}\n')
            _write_json(
                registry,
                [
                    {"path": "data/train.jsonl", "role": "training", "frozen": True},
                ],
            )

            manifest_one = bem.build_manifest(registry, repo_root)
            manifest_two = bem.build_manifest(registry, repo_root)

            _write_json(output_one, manifest_one)
            _write_json(output_two, manifest_two)

            self.assertEqual(
                json.loads(output_one.read_text(encoding="utf-8")),
                json.loads(output_two.read_text(encoding="utf-8")),
            )
            entry = manifest_one["entries"][0]
            self.assertEqual(entry["path"], "data/train.jsonl")
            self.assertEqual(entry["role"], "training")
            self.assertTrue(entry["frozen"])
            self.assertTrue(entry["exists"])
            self.assertEqual(entry["recordCount"], 2)

    def test_missing_file_reports_exists_false_and_null_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = temp_path / "repo"
            registry = temp_path / "registry.json"
            _write_json(
                registry,
                [
                    {"path": "data/missing.csv", "role": "benchmark", "frozen": False},
                ],
            )

            manifest = bem.build_manifest(registry, repo_root)
            entry = manifest["entries"][0]

            self.assertFalse(entry["exists"])
            self.assertIsNone(entry["sha256"])
            self.assertIsNone(entry["byteCount"])
            self.assertIsNone(entry["recordCount"])

    def test_frozen_hash_drift_fails_against_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = temp_path / "repo"
            corpus = repo_root / "data" / "frozen.jsonl"
            registry = temp_path / "registry.json"
            baseline = temp_path / "baseline.json"
            output = temp_path / "manifest.json"

            _write_text(corpus, '{"id": 1}\n')
            _write_json(
                registry,
                [
                    {"path": "data/frozen.jsonl", "role": "core", "frozen": True},
                ],
            )
            baseline_manifest = bem.build_manifest(registry, repo_root)
            _write_json(baseline, baseline_manifest)

            _write_text(corpus, '{"id": 2}\n')
            exit_code = bem.main(
                [
                    "--registry",
                    str(registry),
                    "--repo-root",
                    str(repo_root),
                    "--output",
                    str(output),
                    "--baseline",
                    str(baseline),
                ]
            )

            self.assertNotEqual(exit_code, 0)
            self.assertTrue(output.exists())

    def test_non_frozen_drift_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = temp_path / "repo"
            frozen = repo_root / "data" / "frozen.jsonl"
            mutable = repo_root / "data" / "mutable.csv"
            registry = temp_path / "registry.json"
            baseline = temp_path / "baseline.json"
            output = temp_path / "manifest.json"

            _write_text(frozen, '{"id": 1}\n')
            _write_text(mutable, "id,text\n1,alpha\n")
            _write_json(
                registry,
                [
                    {"path": "data/frozen.jsonl", "role": "core", "frozen": True},
                    {"path": "data/mutable.csv", "role": "recent", "frozen": False},
                ],
            )
            baseline_manifest = bem.build_manifest(registry, repo_root)
            _write_json(baseline, baseline_manifest)

            _write_text(mutable, "id,text\n1,beta\n2,gamma\n")
            exit_code = bem.main(
                [
                    "--registry",
                    str(registry),
                    "--repo-root",
                    str(repo_root),
                    "--output",
                    str(output),
                    "--baseline",
                    str(baseline),
                ]
            )

            self.assertEqual(exit_code, 0)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            mutable_entry = next(
                entry for entry in manifest["entries"] if entry["path"] == "data/mutable.csv"
            )
            self.assertEqual(mutable_entry["recordCount"], 2)


if __name__ == "__main__":
    unittest.main()
