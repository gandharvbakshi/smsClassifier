# Learning Registry Contract

This is the human- and AI-readable contract for the private learning registry.
The registry records reviewed, deidentified regression corpora and promoted
releases without placing raw feedback in version control.

## Coordinates

- Repository: `https://github.com/gandharvbakshi/smsClassifier.git`
- Canonical local checkout:
  `D:\Projects\SMS datasets and project\android_sms_classifier`
- Registry prefix: `gs://<bucket>/learning_registry/v1/`
- Live entry point:
  `gs://sms-classifier-feedback/learning_registry/v1/START_HERE.md`

Run all commands below from the canonical local checkout.

## Exact Cloud Layout

```text
gs://<bucket>/learning_registry/v1/
  corpora/
    <corpusId>/
      cases.jsonl
      manifest.json
  releases/
    <releaseId>.json
  tombstones/
    <tombstoneId>.json
  schemas/
    corpus-manifest.schema.json
    index.schema.json
    release.schema.json
    tombstone.schema.json
  START_HERE.md
  index.json
```

The authoritative history is the set of corpus pairs, release records, and
tombstone records. `index.json` is only a mutable materialized convenience
view. It may be stale or rebuilt and must not be used as the sole source of
truth.

The checked-in assets are under
`backend/learning_registry_assets/`. The files under its `bootstrap/`
directory are command inputs, not objects copied by `bootstrap`.
The contract is Draft 2020-12 schema-first; runtime validation is
schema-equivalent and does not depend on an external jsonschema runtime.

## Record Contract

### Corpus

`publish-corpus` writes both objects below with create-only preconditions:

- `corpora/<corpusId>/cases.jsonl` contains canonical, deidentified reviewed
  cases sorted by `caseId`.
- `corpora/<corpusId>/manifest.json` contains exactly `corpusId`, `metadata`,
  `caseCount`, `casesSha256`, and `casesObject`.

Each published case requires `caseId`, `text`, `privacyStatus`, `reviewer`,
`reviewedAt`, `privacyReviewer`, and `privacyReviewedAt`, plus at least one
expected label or expected axis value. `privacyStatus` must be `deidentified`.
The exact canonical-row allowlist is `caseId`, `reviewId`,
`sourceFeedbackIds`, `sender`, `text`, `expectedIsOtp`,
`expectedIsPhishing`, `expectedOtpIntent`, `expectedLabels`, `category`,
`reviewer`, `reviewedAt`, `reviewConfidence`, `reviewRationale`,
`reviewRationaleNotes`, `privacyStatus`, `privacyReviewer`,
`privacyReviewedAt`, `privacyRationale`, and `retentionClass`. All other input
fields are discarded.

`cases.jsonl` contains deidentified reviewed text, not raw or
privacy-sensitive originals. It remains restricted because deidentified
message text and adjudications are not public data. Every case requires both
reviewer approval and privacy approval before publication. Any retained sender
must already be deidentified. Do not put raw SMS, raw sender values, install
IDs, UIDs, credentials, or keys in corpus rows, manifests, metadata,
documentation, or checked-in assets. Private lineage is never materialized in
`index.json`.

For corpus records, `sourceFeedbackIds` values and deidentified `sender` values
are allowed only inside the private `cases.jsonl`. Release source IDs are
allowed only inside the private release `sourceEvidence`. Never copy those
values into a manifest, `index.json`, documentation, or checked-in Git assets.

The checked-in
`bootstrap/corpora/core-policy-v2026-07-12.metadata.json` is input metadata for
a 19-case sanitized core-policy corpus. It is not a generated manifest. The
private 19-row JSONL is supplied separately to `publish-corpus`.
Corpus metadata is safe caller-supplied input; it must never contain
`sourceFeedbackIds` or any private lineage field.

### Release

A release record requires `releaseId`, `createdAt`, `gitCommit`,
`changeSummary`, `reviewDecision`, `rolloutStatus`, and
`provenanceCompleteness`. The implementation also permits the safe optional
flat fields `schemaVersion`, `recordType`, `registryImplementationCommit`,
`appVersion`, `versionCode`, `cloudRunRevision`, `cloudRunService`, `image`,
`policyId`, `modelVersion`, `semanticIntentStatus`, `corpusIds`,
`corpusManifestRefs`, `sourceEvidence`, `evaluation`, `feedbackMatchSummary`,
`rollout`, `knownGaps`, and `notes`. There are no nested `app`, `cloud`,
`policy`, or `corpus` containers.

Every promoted release must list the exact replayed corpus IDs and manifest
objects in `corpusIds` and `corpusManifestRefs`. Release linkage is
append-only: changing a corpus or release requires a new ID and object, never
an overwrite.
Private release records may carry exact `sourceFeedbackIds` only inside
`sourceEvidence`; checked-in bootstrap assets omit them.

The checked-in release asset intentionally omits exact source-feedback IDs.
For `release-2026-07-12-ef6d180`, those IDs are injected into
`sourceEvidence.sourceFeedbackIds` only in the private release file used for
the live `register-release` command. They are omitted from Git and stored in
the private cloud release record.

`sourceEvidence` and `evaluation` are permissive safe objects because the
private release can use `rawFeedbackSnapshot`, `reviewQueue`,
`acceptedPolicyFixes`, `rejectedSafetyHolds`, and `jury` sections. Their exact
private shape need not match the checked-in aggregate example. Raw message
text, raw sender values, install IDs, UIDs, credentials, and keys remain
forbidden.

`registryImplementationCommit` is optional and intentionally absent from the
checked-in bootstrap asset. Add it when generating the post-commit private
release record.

### Tombstone

A tombstone contains `tombstoneId`, `createdAt`, `reason`, one or more
`caseIds`, and the owning `corpusId`. Its optional safe context fields are `corpusId`,
`sourceFeedbackIds`, `deletionScope`, and `rawDataDeletionStatus`. Exact
lineage is allowed only in the private tombstone object and is omitted from
`index.json` and Git. A tombstone is an append-only exclusion instruction; it
does not rewrite or physically erase a published corpus object.
Each tombstoned `caseId` must be path-safe, unique, and already present in the
referenced corpus.

### Index

`index.json` contains `version`, `updatedAt`, `prefix`, `counts`, `corpora`,
`releases`, `schemas`, and `tombstones`. Its entries are safe summaries and
object paths. The index deliberately omits case text, release change details,
tombstone reasons, and source-feedback IDs.

## CLI

Global flags must appear before the subcommand. These are the exact live GCS
forms:

```powershell
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 bootstrap --assets backend/learning_registry_assets
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 publish-corpus --corpus-id core-policy-v2026-07-12 --input "D:\secure\learning-registry\core-policy-v2026-07-12.cases.jsonl" --metadata backend/learning_registry_assets/bootstrap/corpora/core-policy-v2026-07-12.metadata.json
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 register-release --file "D:\secure\learning-registry\release-2026-07-12-ef6d180.private.json"
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 tombstone --file "D:\secure\learning-registry\tombstone-example.private.json"
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 rebuild-index
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 verify
python -m backend.scripts.learning_registry --backend gcs --bucket sms-classifier-feedback --prefix learning_registry/v1 show
```

Command behavior:

- `bootstrap` creates `START_HERE.md` and `schemas/*.schema.json`, then writes
  the initial mutable `index.json`. It does not publish a corpus, register a
  release, or copy anything under the checked-in `bootstrap/` directory.
- `publish-corpus` canonicalizes the private deidentified JSONL, writes
  `cases.jsonl` and its generated `manifest.json` create-only, then rebuilds
  the index.
- `register-release` writes `releases/<releaseId>.json` create-only, then
  rebuilds the index. Use the private release file containing the exact source
  lineage, not the checked-in lineage-safe asset.
- `tombstone` writes `tombstones/<tombstoneId>.json` create-only, then rebuilds
  the index.
- `rebuild-index` rescans authoritative objects and replaces only
  `index.json`.
- `verify` checks required bootstrap objects, index counts and references, and
  each indexed corpus count and SHA-256 checksum. It revalidates the
  authoritative corpus, release, and tombstone objects directly, including
  objects created through an objectAdmin bypass.
- `show` prints only the materialized index. There is no `read` subcommand.

The schema files are the interchange contract. Validate command inputs against
them before a live write; `verify` performs registry integrity checks using
schema-equivalent validation rather than an external jsonschema runtime.

## Publish And Replay Order

1. Run `bootstrap` once to create the discoverability document, schemas, and
   empty index.
2. Run `publish-corpus` explicitly for each approved deidentified corpus.
3. Build a private release record, inject exact source-feedback IDs there, and
   run `register-release` explicitly.
4. Run `verify`, and use `show` only as a convenient summary.

Every candidate must replay every prior active corpus ID, not only the newest
corpus. A newly published corpus does not supersede an older one. Resolve the
authoritative corpus manifests, apply every tombstone to exclude its `caseIds`,
and then evaluate the candidate on all remaining cases. The promoted release
must record that exact corpus set. If `index.json` disagrees with source
objects, rebuild it and use the source objects.

## Append-Only And Bucket Guarantees

Create-only object preconditions provide application-level append-only
behavior for `START_HERE.md`, schemas, corpus objects, releases, and
tombstones. Repeating identical bytes is idempotent; different bytes at an
existing object name are a conflict. `index.json` is mutable and uses a
generation precondition when replaced.

This is not bucket-level WORM. The live bucket
`gs://sms-classifier-feedback` is:

- private
- `ASIA-SOUTH1` Standard
- uniform bucket-level access enabled
- object versioning disabled
- no retention policy
- 7-day soft delete enabled
- writable by the runtime service account with `objectAdmin`

These controls do not prevent an authorized principal from deleting or
replacing objects outside the registry API. Do not recommend enabling
versioning as a shortcut: deletion and privacy semantics require deliberate
review before any storage-policy change.

## Deletion And Privacy

Raw feedback deletion is physical deletion in the separate raw feedback
prefix. A registry tombstone is not a substitute for deleting raw data.

Derived registry cases are append-only. After a deletion or withdrawal
decision:

- a derived case may remain active only when it is irreversibly deidentified
  and no policy decision requires exclusion;
- otherwise, append a tombstone listing the derived `caseId`;
- all future replay must exclude every tombstoned case ID;
- never place raw object paths, raw text, raw sender values, install IDs, UIDs,
  credentials, or keys in a tombstone;
- keep any deletion-lineage `sourceFeedbackIds` private and out of Git and the
  index. The reconstructed IDs for `release-2026-07-12-ef6d180` belong only in
  that private release record.

The original corpus bytes remain in registry history until a separately
approved physical registry-deletion procedure exists. The tombstone records
the required logical exclusion.

## Release 2026-07-12

`release-2026-07-12-ef6d180` records:

- git commit `ef6d18001c8201114b603784dbbe7007544f0536`
- app `1.2.21`, version code `46`
- Cloud Run revision `sms-ensemble-00025-ldq`
- image `gcr.io/smsclassifier-478611/sms-ensemble:ef6d180`
- 100 percent Cloud Run rollout and completed Play beta rollout
- policy `contextual-phishing-v2`
- semantic intent still `shadow-only`

Its private reconstruction found 68 raw reports, producing 50 deduplicated
review groups and 2 quarantined conflicts. Ten verdict changes match accepted
corrections. One reported-not-phishing safety hold remained phishing. The
release evaluation/feedback summary records 11 of 11 current feedback outcomes
matched, 2,582 deterministic evaluation messages, and 50 fewer phishing false
positives at the same recall.

`provenanceCompleteness` is `reconstructed_current`. Exact source-feedback ID
lineage is omitted from the checked-in asset but stored in the private cloud
release record.
