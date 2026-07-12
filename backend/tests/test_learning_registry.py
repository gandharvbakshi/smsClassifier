from __future__ import annotations

import io
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.learning_registry import GcsObjectStore, LearningRegistry, LocalObjectStore, ObjectConflictError, RegistryError
from backend.scripts import learning_registry as lr_cli


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class LearningRegistryTests(unittest.TestCase):
    def _make_registry(self, temp_path: Path) -> LearningRegistry:
        store = LocalObjectStore(temp_path / "store")
        return LearningRegistry(store)

    def _make_assets(self, temp_path: Path) -> Path:
        assets = temp_path / "assets"
        (assets / "schemas").mkdir(parents=True, exist_ok=True)
        (assets / "START_HERE.md").write_text("# Start\n", encoding="utf-8")
        (assets / "schemas" / "corpus.schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
        return assets

    def _axis_row(self, case_id: str = "case-axis") -> dict:
        return {
            "caseId": case_id,
            "text": "deidentified replay text",
            "privacyStatus": "deidentified",
            "expectedIsOtp": False,
            "expectedIsPhishing": None,
            "expectedOtpIntent": None,
            "reviewer": "reviewer",
            "reviewedAt": "2026-07-12T00:00:00Z",
            "privacyReviewer": "privacy",
            "privacyReviewedAt": "2026-07-12T00:00:00Z",
        }

    def _release_record(self, release_id: str = "r1") -> dict:
        return {
            "releaseId": release_id,
            "createdAt": "2026-07-12T00:00:00Z",
            "gitCommit": "abc123",
            "changeSummary": "tighten privacy checks",
            "reviewDecision": "approved",
            "rolloutStatus": "staged",
            "provenanceCompleteness": "complete",
        }

    def _tombstone_record(self, tombstone_id: str = "t1") -> dict:
        return {
            "tombstoneId": tombstone_id,
            "createdAt": "2026-07-12T00:00:00Z",
            "caseIds": ["case-axis"],
            "reason": "duplicate",
        }

    def test_append_only_conflict_and_idempotent_same_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            store = LocalObjectStore(temp_path / "store")
            data = b"hello\n"
            self.assertTrue(store.put_create_only("a.txt", data))
            self.assertFalse(store.put_create_only("a.txt", data))
            with self.assertRaises(ObjectConflictError):
                store.put_create_only("a.txt", b"bye\n")

    def test_gcs_create_only_handles_only_precondition_failures(self) -> None:
        class FakePreconditionFailed(Exception):
            pass

        class FakeBlob:
            def __init__(self, error: Exception, existing: bytes) -> None:
                self.error = error
                self.existing = existing
                self.if_generation_match = None

            def upload_from_string(self, data: bytes, if_generation_match: int) -> None:
                self.if_generation_match = if_generation_match
                raise self.error

            def download_as_bytes(self) -> bytes:
                return self.existing

        class FakeBucket:
            def __init__(self, blob: FakeBlob) -> None:
                self._blob = blob

            def blob(self, key: str) -> FakeBlob:
                return self._blob

        store = GcsObjectStore.__new__(GcsObjectStore)
        store.prefix = ""
        store._precondition_failed = FakePreconditionFailed

        matching_blob = FakeBlob(FakePreconditionFailed(), b"same")
        store.bucket = FakeBucket(matching_blob)
        self.assertFalse(store.put_create_only("object.json", b"same"))
        self.assertEqual(matching_blob.if_generation_match, 0)

        conflicting_blob = FakeBlob(FakePreconditionFailed(), b"different")
        store.bucket = FakeBucket(conflicting_blob)
        with self.assertRaises(ObjectConflictError):
            store.put_create_only("object.json", b"same")

        store.bucket = FakeBucket(FakeBlob(RuntimeError("transient"), b"same"))
        with self.assertRaisesRegex(RuntimeError, "transient"):
            store.put_create_only("object.json", b"same")

    def test_publish_corpus_rejects_sensitive_payloads_and_requires_privacy_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            with self.assertRaises(ValueError):
                registry.publish_corpus(
                    "c1",
                    [
                        {
                            "caseId": "case-1",
                            "text": "hello",
                            "privacyStatus": "raw",
                            "expectedLabels": ["otp"],
                            "reviewer": "reviewer",
                            "reviewedAt": "2026-07-12T00:00:00Z",
                            "privacyReviewer": "privacy",
                            "privacyReviewedAt": "2026-07-12T00:00:00Z",
                        }
                    ],
                    {"source": "unit-test"},
                )

    def test_publish_corpus_rejects_source_feedback_lineage_in_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._make_registry(Path(temp_dir))
            row = self._axis_row()
            row["sourceFeedbackIds"] = ["feedback-1"]
            for forbidden_key in (
                "sourceFeedbackIds",
                "privateLineage",
                "sourceFeedbackIdLineage",
                "PRIVATELINEAGE",
                "SOURCEFEEDBACKIDLINEAGE",
            ):
                with self.subTest(forbidden_key=forbidden_key):
                    with self.assertRaisesRegex(RegistryError, f"forbidden key: {forbidden_key}"):
                        registry.publish_corpus(
                            "safe-corpus",
                            [row],
                            {"context": [{"lineage": {forbidden_key: ["feedback-1"]}}]},
                        )
            self.assertFalse(registry.store.exists("corpora/safe-corpus/cases.jsonl"))
            self.assertFalse(registry.store.exists("corpora/safe-corpus/manifest.json"))

    def test_publish_corpus_canonical_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            result = registry.publish_corpus(
                "c1",
                [
                    {
                        "caseId": "case-2",
                        "text": "deidentified text",
                        "privacyStatus": "deidentified",
                        "expectedLabels": ["otp", "sms"],
                        "reviewer": "reviewer",
                        "reviewedAt": "2026-07-12T00:00:00Z",
                        "privacyReviewer": "privacy",
                        "privacyReviewedAt": "2026-07-12T00:00:00Z",
                    }
                ],
                {"source": "unit-test"},
            )
            self.assertEqual(result["caseCount"], 1)

            cases_bytes = registry.store.read_bytes("corpora/c1/cases.jsonl")
            manifest = json.loads(registry.store.read_bytes("corpora/c1/manifest.json").decode("utf-8"))
            self.assertEqual(manifest["casesSha256"], hashlib.sha256(cases_bytes).hexdigest())
            self.assertEqual(manifest["caseCount"], 1)

    def test_publish_corpus_fails_closed_on_raw_or_duplicate_content_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._make_registry(Path(temp_dir))
            for forbidden_key in (
                "body",
                "rawBody",
                "originalText",
                "originalSender",
                "installId",
                "firebaseUid",
                "userNote",
                "message",
                "deidentifiedText",
                "deidentifiedSender",
            ):
                with self.subTest(forbidden_key=forbidden_key):
                    row = self._axis_row()
                    row[forbidden_key] = "must not persist"
                    with self.assertRaisesRegex(RegistryError, f"forbidden key: {forbidden_key}"):
                        registry.publish_corpus("safe-corpus", [row], {})

            nested_content = self._axis_row()
            nested_content["reviewRationaleNotes"] = {"sender": "must not persist"}
            with self.assertRaisesRegex(RegistryError, "forbidden key: sender"):
                registry.publish_corpus("safe-corpus", [nested_content], {})

    def test_axis_row_preserves_safe_replay_lineage_without_index_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            row = self._axis_row()
            row.update(
                {
                    "reviewId": "review-axis",
                    "sourceFeedbackIds": ["feedback-axis"],
                    "sender": "SAFE-SENDER",
                    "category": "transactional",
                    "reviewConfidence": 0.95,
                    "reviewRationale": "axis review",
                    "reviewRationaleNotes": ["checked"],
                    "privacyRationale": "identifiers removed",
                    "retentionClass": "private-lineage",
                }
            )

            result = registry.publish_corpus("worker2-axis", [row], {"pipeline": "worker2"})
            self.assertEqual(result["caseCount"], 1)
            canonical = json.loads(registry.store.read_bytes("corpora/worker2-axis/cases.jsonl"))
            self.assertIs(canonical["expectedIsOtp"], False)
            self.assertNotIn("expectedLabels", canonical)
            self.assertEqual(canonical["reviewId"], "review-axis")
            self.assertEqual(canonical["sourceFeedbackIds"], ["feedback-axis"])
            self.assertEqual(canonical["sender"], "SAFE-SENDER")
            self.assertEqual(canonical["reviewConfidence"], 0.95)

            index_json = json.dumps(registry.show(), sort_keys=True)
            self.assertNotIn("feedback-axis", index_json)
            self.assertNotIn("SAFE-SENDER", index_json)
            self.assertNotIn("deidentified replay text", index_json)
            self.assertNotIn("sourceFeedbackIds", index_json)

    def test_publish_corpus_validates_case_axes_and_optional_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))

            row = self._axis_row("case-safe")
            row.update(
                {
                    "expectedIsOtp": True,
                    "expectedIsPhishing": False,
                    "expectedOtpIntent": "APP_LOGIN_OTP",
                    "reviewId": None,
                    "sender": None,
                    "category": None,
                    "reviewRationale": None,
                    "privacyRationale": None,
                    "retentionClass": None,
                    "sourceFeedbackIds": ["feedback-1", "feedback-2"],
                    "reviewConfidence": 0.5,
                    "reviewRationaleNotes": ["checked", "safe"],
                }
            )

            result = registry.publish_corpus("safe-corpus", [row], {"source": "unit-test"})
            self.assertEqual(result["caseCount"], 1)

            stored = json.loads(registry.store.read_bytes("corpora/safe-corpus/cases.jsonl").decode("utf-8"))
            self.assertEqual(stored["caseId"], "case-safe")
            self.assertTrue(stored["expectedIsOtp"])
            self.assertFalse(stored["expectedIsPhishing"])
            self.assertEqual(stored["expectedOtpIntent"], "APP_LOGIN_OTP")
            self.assertIsNone(stored["reviewId"])
            self.assertIsNone(stored["sender"])
            self.assertIsNone(stored["category"])
            self.assertEqual(stored["sourceFeedbackIds"], ["feedback-1", "feedback-2"])
            self.assertEqual(stored["reviewConfidence"], 0.5)
            self.assertEqual(stored["reviewRationaleNotes"], ["checked", "safe"])

            for bad_row, pattern in (
                ({**self._axis_row("case/unsafe")}, "path-safe identifier"),
                ({**self._axis_row("case-bool"), "expectedIsOtp": "false"}, "boolean or null"),
                ({**self._axis_row("case-labels"), "expectedLabels": ["otp", "otp"]}, "expectedLabels must not contain duplicates"),
                ({**self._axis_row("case-feedback"), "sourceFeedbackIds": ["feedback-1", "feedback-1"]}, "sourceFeedbackIds must not contain duplicates"),
                ({**self._axis_row("case-confidence"), "reviewConfidence": 1.1}, "between 0 and 1"),
                ({**self._axis_row("case-time"), "privacyReviewedAt": "2026-07-12T00:00:00"}, "date-time"),
                ({**self._axis_row("case-intent"), "expectedOtpIntent": ""}, "expectedOtpIntent is required"),
            ):
                with self.subTest(pattern=pattern):
                    with self.assertRaisesRegex(RegistryError, pattern):
                        registry.publish_corpus("safe-corpus", [bad_row], {"source": "unit-test"})

    def test_duplicate_case_and_path_traversal_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._make_registry(Path(temp_dir))
            duplicate = self._axis_row("duplicate-case")
            with self.assertRaisesRegex(RegistryError, "duplicate caseId"):
                registry.publish_corpus("safe-corpus", [duplicate, dict(duplicate)], {})

            with self.assertRaises(RegistryError):
                registry.publish_corpus("../escape", [self._axis_row()], {})
            with self.assertRaises(RegistryError):
                registry.store.put_create_only("../escape.json", b"{}")

            release = self._release_record("../escape")
            with self.assertRaises(RegistryError):
                registry.register_release(release)

            release = self._release_record("safe-release")
            release["corpusIds"] = ["../escape"]
            release["corpusManifestRefs"] = ["corpora/safe-release/manifest.json"]
            with self.assertRaises(RegistryError):
                registry.register_release(release)

            tombstone = self._tombstone_record("../escape")
            with self.assertRaises(RegistryError):
                registry.record_tombstone(tombstone)

    def test_release_metadata_is_retained_but_not_materialized_in_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("worker2-axis", [self._axis_row()], {})
            record = self._release_record("release-metadata")
            record.update(
                {
                    "schemaVersion": "1",
                    "recordType": "learningRegistryRelease",
                    "gitCommit": "ef6d180",
                    "registryImplementationCommit": "registry-commit-123",
                    "appVersion": "2.4.0",
                    "versionCode": 240,
                    "cloudRunRevision": "classifier-00042",
                    "cloudRunService": "classifier",
                    "image": "registry.example/classifier@sha256:abc",
                    "policyId": "policy-7",
                    "modelVersion": "model-3",
                    "semanticIntentStatus": "enabled",
                    "corpusIds": ["worker2-axis"],
                    "corpusManifestRefs": ["corpora/worker2-axis/manifest.json"],
                    "sourceEvidence": {"sourceFeedbackIds": ["feedback-release"]},
                    "evaluation": {"accuracy": 0.99},
                    "feedbackMatchSummary": {"matched": 4},
                    "rollout": {"percent": 10},
                    "knownGaps": ["rare sender format"],
                    "notes": "private release note",
                }
            )

            registry.register_release(record)
            stored = json.loads(registry.store.read_bytes("releases/release-metadata.json"))
            for field, expected in record.items():
                self.assertEqual(stored[field], expected)

            index_json = json.dumps(registry.show(), sort_keys=True)
            self.assertNotIn("feedback-release", index_json)
            self.assertNotIn("private release note", index_json)
            self.assertNotIn("rare sender format", index_json)
            self.assertNotIn("registry-commit-123", index_json)

    def test_release_optional_fields_reject_null(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._make_registry(Path(temp_dir))
            registry.publish_corpus("release-corpus", [self._axis_row("release-case")], {})
            base_record = self._release_record("release-null")
            base_record["corpusIds"] = ["release-corpus"]
            base_record["corpusManifestRefs"] = ["corpora/release-corpus/manifest.json"]

            expected_errors = {
                "schemaVersion": "schemaVersion must be a string",
                "recordType": "recordType must be a string",
                "registryImplementationCommit": "registryImplementationCommit must be a string",
                "appVersion": "appVersion must be a string",
                "cloudRunRevision": "cloudRunRevision must be a string",
                "cloudRunService": "cloudRunService must be a string",
                "image": "image must be a string",
                "policyId": "policyId must be a string",
                "modelVersion": "modelVersion must be a string",
                "semanticIntentStatus": "semanticIntentStatus must be a string",
                "knownGaps": "knownGaps must be a list",
                "notes": "notes must be a string or list of strings",
            }
            for field, error in expected_errors.items():
                with self.subTest(field=field):
                    record = dict(base_record)
                    record[field] = None
                    with self.assertRaisesRegex(RegistryError, error):
                        registry.register_release(record)

    def test_registry_implementation_commit_is_retained_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._make_registry(Path(temp_dir))
            registry.publish_corpus("release-corpus", [self._axis_row("case-commit")], {"source": "unit-test"})
            record = self._release_record("release-commits")
            record["gitCommit"] = "ef6d180"
            record["registryImplementationCommit"] = "later-registry-commit"
            record["corpusIds"] = ["release-corpus"]
            record["corpusManifestRefs"] = ["corpora/release-corpus/manifest.json"]

            registry.register_release(record)
            stored = json.loads(registry.store.read_bytes("releases/release-commits.json"))
            self.assertEqual(stored["gitCommit"], "ef6d180")
            self.assertEqual(stored["registryImplementationCommit"], "later-registry-commit")

    def test_release_corpus_references_must_resolve_and_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = LearningRegistry(LocalObjectStore(temp_path / "store", prefix="learning_registry/v1"))
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("corpus-one", [self._axis_row("case-one")], {})
            registry.publish_corpus("corpus-two", [self._axis_row("case-two")], {})

            valid = self._release_record("valid-corpus-refs")
            valid["corpusIds"] = ["corpus-one"]
            valid["corpusManifestRefs"] = ["corpora/corpus-one/manifest.json"]
            registry.register_release(valid)
            stored = json.loads(registry.store.read_bytes("releases/valid-corpus-refs.json"))
            self.assertEqual(
                stored["corpusManifestRefs"],
                ["learning_registry/v1/corpora/corpus-one/manifest.json"],
            )

            missing_id = self._release_record("missing-corpus-id")
            missing_id["corpusIds"] = ["missing-corpus"]
            missing_id["corpusManifestRefs"] = ["corpora/missing-corpus/manifest.json"]
            with self.assertRaisesRegex(RegistryError, "manifest does not exist"):
                registry.register_release(missing_id)

            missing_ref = self._release_record("missing-corpus-ref")
            missing_ref["corpusIds"] = ["corpus-one"]
            missing_ref["corpusManifestRefs"] = ["corpora/missing-corpus/manifest.json"]
            with self.assertRaisesRegex(RegistryError, "manifest does not exist"):
                registry.register_release(missing_ref)

            mismatched = self._release_record("mismatched-corpus-refs")
            mismatched["corpusIds"] = ["corpus-one"]
            mismatched["corpusManifestRefs"] = ["corpora/corpus-two/manifest.json"]
            with self.assertRaisesRegex(RegistryError, "must reference the same corpora"):
                registry.register_release(mismatched)

            unsafe_ref = self._release_record("unsafe-corpus-ref")
            unsafe_ref["corpusIds"] = ["corpus-one"]
            unsafe_ref["corpusManifestRefs"] = ["corpora/../manifest.json"]
            with self.assertRaises(RegistryError):
                registry.register_release(unsafe_ref)

    def test_release_requires_matching_corpus_sets_and_schema_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("c1", [self._axis_row("case-release")], {"source": "unit-test"})

            missing_sets = self._release_record("missing-sets")
            with self.assertRaisesRegex(RegistryError, "corpusIds must be a list"):
                registry.register_release(missing_sets)

            bad_type = self._release_record("bad-type")
            bad_type["corpusIds"] = ["c1"]
            bad_type["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
            bad_type["versionCode"] = 0
            with self.assertRaisesRegex(RegistryError, "versionCode"):
                registry.register_release(bad_type)

            unknown_field = self._release_record("unknown-field")
            unknown_field["corpusIds"] = ["c1"]
            unknown_field["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
            unknown_field["unexpected"] = True
            with self.assertRaisesRegex(RegistryError, "unknown field"):
                registry.register_release(unknown_field)

            valid = self._release_record("valid-release")
            valid["corpusIds"] = ["c1"]
            valid["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
            valid["sourceEvidence"] = {"sourceFeedbackIds": ["feedback-release"]}
            self.assertEqual(registry.register_release(valid)["releaseId"], "valid-release")

    def test_release_rejects_incomplete_or_inconsistent_corpus_before_write(self) -> None:
        corruptions = (
            ("missing-cases", "corpus cases do not exist"),
            ("bad-checksum", "checksum mismatch"),
            ("bad-count", "case count mismatch"),
        )
        for corruption, expected_error in corruptions:
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                registry = self._make_registry(temp_path)
                registry.bootstrap(self._make_assets(temp_path))
                registry.publish_corpus("c1", [self._axis_row("case-release")], {"source": "unit-test"})

                cases_path = temp_path / "store" / "corpora" / "c1" / "cases.jsonl"
                manifest_path = temp_path / "store" / "corpora" / "c1" / "manifest.json"
                if corruption == "missing-cases":
                    cases_path.unlink()
                else:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if corruption == "bad-checksum":
                        manifest["casesSha256"] = "0" * 64
                    else:
                        manifest["caseCount"] += 1
                    manifest_path.write_bytes(
                        (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
                    )

                release = self._release_record(f"release-{corruption}")
                release["corpusIds"] = ["c1"]
                release["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
                with self.assertRaisesRegex(RegistryError, expected_error):
                    registry.register_release(release)
                self.assertFalse(registry.store.exists(f"releases/release-{corruption}.json"))

    def test_tombstone_requires_corpus_membership_and_schema_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("c1", [self._axis_row("case-one")], {"source": "unit-test"})

            missing_corpus = self._tombstone_record("missing-corpus")
            missing_corpus.pop("corpusId", None)
            with self.assertRaisesRegex(RegistryError, "corpusId"):
                registry.record_tombstone(missing_corpus)

            bad_case_type = self._tombstone_record("bad-case-type")
            bad_case_type["corpusId"] = "c1"
            bad_case_type["caseIds"] = ["case-one", "case-one"]
            with self.assertRaisesRegex(RegistryError, "must not contain duplicates"):
                registry.record_tombstone(bad_case_type)

            missing_member = self._tombstone_record("missing-member")
            missing_member["corpusId"] = "c1"
            missing_member["caseIds"] = ["case-missing"]
            with self.assertRaisesRegex(RegistryError, "not found in corpus"):
                registry.record_tombstone(missing_member)

            bad_optional = self._tombstone_record("bad-optional")
            bad_optional["corpusId"] = "c1"
            bad_optional["caseIds"] = ["case-one"]
            bad_optional["sourceFeedbackIds"] = "feedback-lineage"
            with self.assertRaisesRegex(RegistryError, "sourceFeedbackIds"):
                registry.record_tombstone(bad_optional)

            valid = self._tombstone_record("valid-tombstone")
            valid["corpusId"] = "c1"
            valid["caseIds"] = ["case-one"]
            valid["sourceFeedbackIds"] = ["feedback-lineage"]
            valid["deletionScope"] = "case-and-lineage"
            valid["rawDataDeletionStatus"] = "confirmed"
            self.assertEqual(registry.record_tombstone(valid)["caseCount"], 1)

    def test_non_corpus_payloads_reject_content_and_raw_keys_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("c1", [self._axis_row("case-non-corpus")], {"source": "unit-test"})

            with self.assertRaisesRegex(RegistryError, "forbidden key: rawBody"):
                registry.publish_corpus(
                    "safe-corpus",
                    [self._axis_row()],
                    {"source": {"rawBody": "must not persist"}},
                )

            release = self._release_record("safe-release")
            release["corpusIds"] = ["c1"]
            release["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
            release["sourceEvidence"] = [{"details": {"userNote": "must not persist"}}]
            with self.assertRaisesRegex(RegistryError, "forbidden key: userNote"):
                registry.register_release(release)

            with self.assertRaisesRegex(RegistryError, "forbidden key: text"):
                registry.publish_corpus(
                    "safe-corpus",
                    [self._axis_row()],
                    {"source": {"text": "must not persist"}},
                )

            release = self._release_record("sender-release")
            release["corpusIds"] = ["c1"]
            release["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
            release["sourceEvidence"] = {"sender": "must not persist"}
            with self.assertRaisesRegex(RegistryError, "forbidden key: sender"):
                registry.register_release(release)

            tombstone = self._tombstone_record("message-tombstone")
            tombstone["corpusId"] = "c1"
            tombstone["caseIds"] = ["case-non-corpus"]
            tombstone["deletionScope"] = {"message": "must not persist"}
            with self.assertRaisesRegex(RegistryError, "forbidden key: message"):
                registry.record_tombstone(tombstone)

    def test_verify_flags_malformed_records_and_bypass_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("c1", [self._axis_row("case-verify")], {"source": "unit-test"})
            registry.publish_corpus("c2", [self._axis_row("case-member")], {"source": "unit-test"})

            store_root = temp_path / "store"
            (store_root / "corpora" / "c1" / "cases.jsonl").write_text(
                json.dumps(
                    {
                        "expectedIsOtp": False,
                        "expectedIsPhishing": None,
                        "expectedOtpIntent": None,
                        "privacyReviewedAt": "2026-07-12T00:00:00Z",
                        "privacyReviewer": "privacy",
                        "privacyStatus": "deidentified",
                        "reviewedAt": "2026-07-12T00:00:00Z",
                        "reviewer": "reviewer",
                        "caseId": "case-verify",
                        "text": "deidentified replay text",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = json.loads((store_root / "corpora" / "c1" / "manifest.json").read_text(encoding="utf-8"))
            manifest["metadata"] = {"source": {"sourceFeedbackIds": ["feedback-unsafe"]}}
            (store_root / "corpora" / "c1" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            release = self._release_record("release-verify")
            release["corpusIds"] = ["c1"]
            release["corpusManifestRefs"] = ["corpora/c1/manifest.json"]
            release["versionCode"] = 1
            release["unexpected"] = "boom"
            (store_root / "releases").mkdir(parents=True, exist_ok=True)
            (store_root / "releases" / "release-verify.json").write_text(json.dumps(release, indent=2), encoding="utf-8")

            tombstone = self._tombstone_record("tombstone-verify")
            tombstone["corpusId"] = "c2"
            tombstone["caseIds"] = ["case-missing"]
            tombstone["deletionScope"] = 1
            (store_root / "tombstones").mkdir(parents=True, exist_ok=True)
            (store_root / "tombstones" / "tombstone-verify.json").write_text(json.dumps(tombstone, indent=2), encoding="utf-8")

            (store_root / "corpora" / "c1" / "admin-bypass.txt").write_text("bypass", encoding="utf-8")

            report = registry.verify()
            self.assertFalse(report["ok"])
            joined = "\n".join(report["problems"])
            self.assertIn("noncanonical corpus row", joined)
            self.assertIn("forbidden key: sourceFeedbackIds", joined)
            self.assertIn("unknown field", joined)
            self.assertIn("not found in corpus", joined)
            self.assertIn("objectAdmin-bypass object", joined)

    def test_verify_reports_malformed_indexed_tombstone_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus("c1", [self._axis_row("case-one")], {"source": "unit-test"})
            tombstone = self._tombstone_record("malformed-indexed")
            tombstone["corpusId"] = "c1"
            tombstone["caseIds"] = ["case-one"]
            registry.record_tombstone(tombstone)

            for malformed_case_ids in (7, {"case-one": True}):
                with self.subTest(case_ids=malformed_case_ids):
                    tombstone["caseIds"] = malformed_case_ids
                    registry.store.write_bytes(
                        "tombstones/malformed-indexed.json",
                        (json.dumps(tombstone, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
                    )
                    report = registry.verify()
                    self.assertFalse(report["ok"])
                    self.assertTrue(any("caseIds must be a list" in problem for problem in report["problems"]))

    def test_release_index_and_tombstone_safe_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus(
                "c1",
                [
                    {
                        "caseId": "case-3",
                        "text": "text",
                        "privacyStatus": "deidentified",
                        "expectedLabels": ["otp"],
                        "reviewer": "reviewer",
                        "reviewedAt": "2026-07-12T00:00:00Z",
                        "privacyReviewer": "privacy",
                        "privacyReviewedAt": "2026-07-12T00:00:00Z",
                    }
                ],
                {"source": "unit-test"},
            )
            release_record = {
                "releaseId": "r1",
                "createdAt": "2026-07-12T00:00:00Z",
                "gitCommit": "abc123",
                "changeSummary": "tighten privacy checks",
                "reviewDecision": "approved",
                "rolloutStatus": "staged",
                "provenanceCompleteness": "complete",
                "corpusIds": ["c1"],
                "corpusManifestRefs": ["corpora/c1/manifest.json"],
            }
            registry.register_release(
                release_record
            )
            registry.record_tombstone(
                {
                    "tombstoneId": "t1",
                    "createdAt": "2026-07-12T00:00:00Z",
                    "caseIds": ["case-3"],
                    "reason": "duplicate",
                    "corpusId": "c1",
                    "sourceFeedbackIds": ["feedback-tombstone"],
                    "deletionScope": "case-and-lineage",
                    "rawDataDeletionStatus": "confirmed",
                }
            )
            index = registry.show()
            self.assertEqual(index["counts"]["releases"], 1)
            self.assertEqual(index["counts"]["tombstones"], 1)
            self.assertNotIn("changeSummary", json.dumps(index))
            self.assertNotIn("reason", json.dumps(index))
            self.assertNotIn("feedback-tombstone", json.dumps(index))
            tombstone = json.loads(registry.store.read_bytes("tombstones/t1.json"))
            self.assertEqual(tombstone["corpusId"], "c1")
            self.assertEqual(tombstone["sourceFeedbackIds"], ["feedback-tombstone"])
            self.assertEqual(tombstone["deletionScope"], "case-and-lineage")
            self.assertEqual(tombstone["rawDataDeletionStatus"], "confirmed")

    def test_verify_detects_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus(
                "c1",
                [
                    {
                        "caseId": "case-4",
                        "text": "text",
                        "privacyStatus": "deidentified",
                        "expectedLabels": ["otp"],
                        "reviewer": "reviewer",
                        "reviewedAt": "2026-07-12T00:00:00Z",
                        "privacyReviewer": "privacy",
                        "privacyReviewedAt": "2026-07-12T00:00:00Z",
                    }
                ],
                {"source": "unit-test"},
            )
            cases_path = temp_path / "store" / "corpora" / "c1" / "cases.jsonl"
            cases_path.write_text("tampered\n", encoding="utf-8")
            report = registry.verify()
            self.assertFalse(report["ok"])
            self.assertTrue(any("checksum mismatch" in problem for problem in report["problems"]))
            self.assertTrue(any("invalid JSON" in problem for problem in report["problems"]))

    def test_verify_reports_corrupt_tombstone_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.publish_corpus(
                "c1",
                [
                    {
                        "caseId": "case-corrupt",
                        "text": "text",
                        "privacyStatus": "deidentified",
                        "expectedLabels": ["otp"],
                        "reviewer": "reviewer",
                        "reviewedAt": "2026-07-12T00:00:00Z",
                        "privacyReviewer": "privacy",
                        "privacyReviewedAt": "2026-07-12T00:00:00Z",
                    }
                ],
                {"source": "unit-test"},
            )
            tombstone = {
                "tombstoneId": "t1",
                "createdAt": "2026-07-12T00:00:00Z",
                "caseIds": ["case-corrupt"],
                "reason": "duplicate",
                "corpusId": "c1",
            }
            store_root = temp_path / "store"
            manifest_path = store_root / "corpora" / "c1" / "manifest.json"
            cases_path = store_root / "corpora" / "c1" / "cases.jsonl"
            original_manifest = manifest_path.read_text(encoding="utf-8")
            original_cases = cases_path.read_text(encoding="utf-8")

            for filename, contents, expected_problem in (
                ("manifest.json", "{", "invalid JSON in corpora/c1/manifest.json"),
                ("cases.jsonl", "not-json\n", "invalid JSON in corpora/c1/cases.jsonl"),
            ):
                with self.subTest(filename=filename):
                    target_path = store_root / "corpora" / "c1" / filename
                    target_path.write_text(contents, encoding="utf-8")
                    registry.store.put_create_only(
                        "tombstones/t1.json",
                        json.dumps(tombstone, sort_keys=True).encode("utf-8"),
                    )
                    report = registry.verify()
                    self.assertFalse(report["ok"])
                    self.assertTrue(any(expected_problem in problem for problem in report["problems"]))
                    (store_root / "tombstones" / "t1.json").unlink()
                    manifest_path.write_text(original_manifest, encoding="utf-8")
                    cases_path.write_text(original_cases, encoding="utf-8")

    def test_verify_detects_stale_index_and_unindexed_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = self._make_registry(temp_path)
            registry.bootstrap(self._make_assets(temp_path))
            registry.store.put_create_only(
                "releases/unindexed-release.json",
                json.dumps(self._release_record("unindexed-release"), sort_keys=True).encode("utf-8"),
            )
            registry.store.put_create_only("tombstones/invalid-json.json", b"{")

            report = registry.verify()
            self.assertFalse(report["ok"])
            self.assertTrue(
                any(
                    "unindexed immutable object" in problem and "unindexed-release.json" in problem
                    for problem in report["problems"]
                )
            )
            self.assertTrue(
                any("invalid JSON" in problem and "invalid-json.json" in problem for problem in report["problems"])
            )

    def test_cli_verify_failure_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            argv = ["--backend", "local", "--root", str(Path(temp_dir) / "store"), "verify"]
            with redirect_stdout(io.StringIO()) as stdout:
                exit_code = lr_cli.main(argv)
            self.assertEqual(exit_code, 1)
            self.assertFalse(json.loads(stdout.getvalue())["ok"])

    def test_cli_local_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            assets = self._make_assets(temp_path)
            input_path = temp_path / "input.jsonl"
            metadata_path = temp_path / "metadata.json"
            release_path = temp_path / "release.json"
            tombstone_path = temp_path / "tombstone.json"

            _write_jsonl(
                input_path,
                [
                    {
                        "caseId": "case-5",
                        "text": "hello",
                        "privacyStatus": "deidentified",
                        "expectedLabels": ["otp"],
                        "reviewer": "reviewer",
                        "reviewedAt": "2026-07-12T00:00:00Z",
                        "privacyReviewer": "privacy",
                        "privacyReviewedAt": "2026-07-12T00:00:00Z",
                    }
                ],
            )
            metadata_path.write_text(json.dumps({"source": "unit-test"}), encoding="utf-8")
            release_path.write_text(
                json.dumps(
                    {
                        "releaseId": "r1",
                        "createdAt": "2026-07-12T00:00:00Z",
                        "gitCommit": "abc123",
                        "changeSummary": "tighten privacy checks",
                        "reviewDecision": "approved",
                        "rolloutStatus": "staged",
                        "provenanceCompleteness": "complete",
                        "corpusIds": ["c1"],
                        "corpusManifestRefs": ["corpora/c1/manifest.json"],
                    }
                ),
                encoding="utf-8",
            )
            tombstone_path.write_text(
                json.dumps(
                    {
                        "tombstoneId": "t1",
                        "createdAt": "2026-07-12T00:00:00Z",
                        "caseIds": ["case-5"],
                        "reason": "duplicate",
                        "corpusId": "c1",
                    }
                ),
                encoding="utf-8",
            )

            argv_base = ["--backend", "local", "--root", str(temp_path / "store")]
            with redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(
                    lr_cli.main(argv_base + ["bootstrap", "--assets", str(assets)]),
                    0,
                )
                self.assertEqual(
                    lr_cli.main(argv_base + ["publish-corpus", "--corpus-id", "c1", "--input", str(input_path), "--metadata", str(metadata_path)]),
                    0,
                )
                self.assertEqual(
                    lr_cli.main(argv_base + ["register-release", "--file", str(release_path)]),
                    0,
                )
                self.assertEqual(
                    lr_cli.main(argv_base + ["tombstone", "--file", str(tombstone_path)]),
                    0,
                )
                self.assertEqual(lr_cli.main(argv_base + ["verify"]), 0)
            output = stdout.getvalue()
            self.assertNotIn("hello", output)
            self.assertNotIn("case-5", output)


if __name__ == "__main__":
    unittest.main()
