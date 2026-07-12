# Learning Registry: Start Here

This is the AI discovery entry point for the private, application-level
append-only learning registry.

## Coordinates

- Repository: `https://github.com/gandharvbakshi/smsClassifier.git`
- Canonical local checkout:
  `D:\Projects\SMS datasets and project\android_sms_classifier`
- Generic prefix: `gs://<bucket>/learning_registry/v1/`
- This live object:
  `gs://sms-classifier-feedback/learning_registry/v1/START_HERE.md`
- Full local contract: `backend/LEARNING_REGISTRY.md`

## Authoritative Layout

```text
learning_registry/v1/
  corpora/<corpusId>/cases.jsonl
  corpora/<corpusId>/manifest.json
  releases/<releaseId>.json
  tombstones/<tombstoneId>.json
  schemas/*.schema.json
  START_HERE.md
  index.json
```

Corpus pairs, releases, and tombstones are the authoritative records.
`index.json` is a mutable materialized convenience view only. Rebuild it if it
is stale; never infer history solely from it.
If you are a future AI, read this file together with
`backend/LEARNING_REGISTRY.md` and the four schema files under
`backend/learning_registry_assets/schemas/` before changing anything.

`cases.jsonl` contains canonical, deidentified reviewed cases. The private
allowlist includes case/review IDs, private source lineage, deidentified
`sender` and `text`, expected label/axis fields, category, reviewer provenance,
privacy provenance, and `retentionClass`. It contains no raw/privacy-sensitive
originals, but it remains restricted. Reviewer approval and privacy approval
are required for every published case. Exact source-ID and sender values stay
inside private registry objects and never enter manifests, the index,
documentation, or checked-in assets.

Release records are flat. They require `releaseId`, `createdAt`, `gitCommit`,
`changeSummary`, `reviewDecision`, `rolloutStatus`, `provenanceCompleteness`,
`corpusIds`, and `corpusManifestRefs`. The optional fields are `schemaVersion`,
`recordType`, `registryImplementationCommit`, `appVersion`, `versionCode`,
`cloudRunRevision`, `cloudRunService`, `image`, `policyId`, `modelVersion`,
`semanticIntentStatus`, `sourceEvidence`, `evaluation`, `feedbackMatchSummary`,
`rollout`, `knownGaps`, and `notes`. `sourceEvidence` and `evaluation` are
permissive safe private objects.
Runtime validation is schema-equivalent and revalidates authoritative objects,
including anything written through an objectAdmin bypass; `index.json` is not
treated as source of truth.

## Commands

Run from
`D:\Projects\SMS datasets and project\android_sms_classifier`. Global flags
must precede the subcommand:

```powershell
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 bootstrap --assets backend/learning_registry_assets
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 publish-corpus --corpus-id core-policy-v2026-07-12 --input "D:\secure\learning-registry\core-policy-v2026-07-12.cases.jsonl" --metadata backend/learning_registry_assets/bootstrap/corpora/core-policy-v2026-07-12.metadata.json
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 register-release --file "D:\secure\learning-registry\release-2026-07-12-ef6d180.private.json"
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 tombstone --file "D:\secure\learning-registry\tombstone-example.private.json"
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 rebuild-index
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 verify
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 show
```

There is no `read` subcommand.

`bootstrap` writes only this `START_HERE.md`, `schemas/*.schema.json`, and the
mutable `index.json`. It does not publish the checked-in corpus metadata or
release asset. Use the explicit `publish-corpus` and `register-release`
commands later. The corpus metadata describes a private 19-case sanitized core
policy JSONL; it is not a manifest.

Before `register-release`, inject exact source-feedback IDs into a private copy
of the release record. Exact IDs are omitted from Git and stored only in the
private cloud release record. Add `registryImplementationCommit` to that
post-commit private record; the checked-in bootstrap asset may omit it.

## Replay And Deletion

Every candidate replays all prior active corpus IDs. New corpora append to the
replay set rather than replacing old corpora. Apply every tombstone to exclude
its `caseIds`; record the exact replayed set in each promoted release's
`corpusIds` and `corpusManifestRefs`.

Raw deletion is physical in the separate raw feedback prefix. Registry
tombstones logically exclude derived cases from future replay. A derived case
may remain active only if it is irreversibly deidentified and policy permits
retention. Tombstones require `tombstoneId`, `createdAt`, `reason`, and
`corpusId` plus `caseIds`; their only optional fields are `sourceFeedbackIds`,
`deletionScope`, and `rawDataDeletionStatus`. Each listed `caseId` must be
path-safe, unique, and already present in the referenced corpus.

Create-only preconditions enforce append-only behavior at the application
layer, not bucket-level WORM. The private `ASIA-SOUTH1` Standard live bucket
uses uniform bucket-level access, has no object versioning or retention policy,
has 7-day soft delete, and grants the runtime service account `objectAdmin`.
`index.json` remains mutable. Do not recommend versioning without deliberate
review of deletion and privacy semantics.
