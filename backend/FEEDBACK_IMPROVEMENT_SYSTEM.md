# Feedback Improvement System

## Safety Contract

Raw user feedback is evidence, not ground truth. No scheduled job may accept a
label, modify a frozen corpus, train a production model, deploy, or change a
classification threshold. Promotion always requires a reviewed candidate,
reproducible evaluation, and an explicit human decision.

Never place raw SMS text, plaintext install IDs, Firebase IDs, or access tokens
in reports or manifests. Use redacted text for review, HMAC subject IDs for
concentration checks, and aggregate counts for monitoring.

## Weekly Read-Only Loop

1. Ingest opted-in feedback into a temporary workspace and validate the schema.
2. Normalize legacy correction kinds and separate satisfaction feedback from
   classifier corrections.
3. Deduplicate by normalized message identity. Track duplicate counts and cap
   the influence of each subject, sender, and template cluster.
4. Quarantine contradictory labels. Preserve all source feedback IDs and both
   sides of the conflict for review.
5. Cluster new, clean corrections by failure axis, sender/domain context,
   template, app version, and current score band. Report only aggregates.
6. Ask a human reviewer, or a multi-model jury followed by a human for disputed
   or safety-sensitive cases, to set the accepted label, confidence, rationale,
   reviewer, and review time.
7. Export only accepted labels as candidate regression cases. A partial user
   correction constrains only that axis; it must not invent labels for the other
   axes.
8. Evaluate the current model and any candidate. The weekly monitor reports the
   results and stops.

## Evaluation Corpus

Every candidate is evaluated on five independently reported slices:

- Core safety golden: hand-reviewed OTP, non-OTP, legitimate-link, and phishing
  invariants. Frozen between deliberate corpus-version reviews.
- Reviewed feedback replay: accepted real-world errors, deduplicated and capped
  so one person or template cannot dominate.
- Synthetic edge set: controlled minimal pairs for urgency, KYC, delivery OTP,
  payment receipt versus payment request, and confusing intent pairs.
- Jury benchmark: a broad historical corpus with high-agreement labels. Freeze
  the exact file fingerprint used for a release decision.
- Recent time split: the newest reviewed examples, never used to fit that same
  candidate, to expose template and distribution drift.

Use `build_evaluation_corpus_manifest.py` to record path, role, frozen state,
SHA-256, byte count, and record count without exporting record contents. A
baseline comparison must fail when a frozen corpus is missing or changed.

## Training And Splits

- Train OTP intent only on reviewed OTP-positive examples. Do not make
  `NOT_OTP` the dominant intent class; OTP detection is a separate task.
- Split by normalized template and sender group, then keep a final time-based
  holdout. Random row splits are not release evidence because near-duplicate
  SMS templates leak across train and test.
- Start with a compact sentence encoder using supervised contrastive learning
  and class prototypes. Add hard-negative pairs for APP_LOGIN versus
  FINANCIAL_LOGIN, BANK_OR_CARD versus UPI, and account change versus generic
  app action.
- Add an explicit UNKNOWN/AMBIGUOUS reject path. Route only uncertain cases to a
  larger model with retrieved, reviewed examples; never let the larger model
  silently contradict the outer OTP decision.
- Calibrate probabilities on held-out data. Use conformal or class-specific
  rejection thresholds where coverage is adequate.
- Keep a replay mix from all prior corpus versions during candidate training to
  reduce catastrophic forgetting.

## Promotion Gates

A candidate is promotable only when all gates pass:

- 100 percent pass on core safety cases, with no deleted or changed baseline.
- No reduction in phishing recall on the safety and jury slices, and no increase
  in legitimate-message false positives beyond the approved tolerance.
- Intent macro F1 improves on both the grouped holdout and recent time split;
  no supported intent class loses more than the approved per-class tolerance.
- OTP precision and recall remain above the current approved release floor.
- Calibration error and abstention coverage are reported, not hidden inside
  accuracy. UNKNOWN must be counted as abstention, not silently scored correct.
- Per-subject, per-sender, and per-template-cluster results show that gains are
  not driven by duplicate-heavy feedback.
- Latency, model size, provider-call rate, and variable cost remain within the
  release budget.

Threshold values belong in a versioned release-evaluation config after a larger
reviewed holdout is available. Until then, require no core regression and human
review of every changed safety verdict.

## Rollout

Run the candidate in shadow mode first and compare decisions without changing
the UI. Then canary to a small opted-in cohort, monitoring false-positive
feedback, OTP misses, abstentions, latency, provider usage, and uninstall or
satisfaction signals. Promote gradually only after the observation window.
Keep the previous model and thresholds deployable for immediate rollback.

Version every model with its code commit, training-data manifest, evaluation
manifest, metrics, thresholds, reviewer decision, and rollout status. New
feedback is appended to a new reviewed corpus version; historical frozen
corpora are never rewritten in place.

## Research Basis

- Few-shot supervised contrastive intent classification:
  https://aclanthology.org/2021.emnlp-main.144/
- Context augmentation and self-distillation for few-shot intent detection:
  https://aclanthology.org/2023.findings-acl.706/
- Sentence-transformer intent classification with out-of-scope detection:
  https://aclanthology.org/2024.emnlp-industry.68/
- Fine-grained intent learning with contrastive feedback:
  https://aclanthology.org/2025.coling-main.151/
- Conformal prediction for a calibrated reject option:
  https://proceedings.mlr.press/v230/garcia-galindo24a.html
