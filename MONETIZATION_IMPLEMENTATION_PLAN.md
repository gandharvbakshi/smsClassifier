# Monetization Implementation and Verification Plan

Status: Phase 1 implementation complete; later phases remain planned
Change class: medium, split into independently verifiable phases
Current release baseline: Android `1.2.26` / versionCode `51`, Play beta

## Scope and non-negotiables

Goal: fix the consent-safe telemetry gap, prove the real `pro_yearly` purchase path, make Pro delivery measurable, and only then improve the in-app offer.

This plan makes **no Google Ads changes**. Campaign status, spend, budgets, bidding, targeting, creatives, and conversion actions remain untouched.

Other non-negotiables:

- Preserve explicit analytics opt-out. Do not use server-side analytics to bypass it.
- Keep core SMS reading, sending, OTP copy, and default-SMS behavior available after trial expiry.
- Treat Play Order management and Play purchase state as payment truth. GA4 is supporting funnel evidence only.
- Keep each implementation diff narrow; do not combine telemetry, Billing repairs, and funnel UI into one release.

## Phase 0: freeze the baseline

Before editing:

1. Record the current code, Play beta version, backend revision, product catalog price, and existing GA4/Cloud Run baseline.
2. Capture distinct users separately from raw event totals.
3. Record consent coverage. Backend trial starts include non-consenting users, so GA4 trial totals are not expected to equal backend totals.
4. Preserve the dirty worktree and all unrelated user files.

Evidence to retain:

- successful backend trial starts;
- consented `trial_started` and `trial_started_from_paywall` users;
- `paywall_shown`, `begin_checkout`, verified Play orders, and restored entitlements;
- `server_classify_success`, `server_classify_failed`, `server_classify_skipped_offline`, and rate-limited message counts by app version.

## Phase 1: consent-safe onboarding telemetry

### Required behavior

Do not move the current `persistConsent()` wholesale before the remote trial request. It also marks onboarding seen and logs onboarding completion, which would incorrectly complete onboarding when trial creation fails.

Split the responsibilities:

1. Apply the selected analytics and Crashlytics choices.
2. Start the remote trial.
3. If the trial succeeds, mark onboarding seen, seed/log first-open data as appropriate, log onboarding completion, and navigate to Inbox.
4. If the trial fails, remain on the Pro step, keep the user’s consent choice, show the existing retry/Basic option, and do not mark onboarding complete.
5. For “Use app without Pro,” apply consent, mark onboarding complete, log the Basic choice when permitted, and navigate normally.
6. If analytics is off, emit no GA4 trial or onboarding events. Backend trial creation must still work.

### Likely files

- `app/src/main/java/com/smsclassifier/app/ui/screens/ConsentOnboardingScreen.kt`
- `app/src/main/java/com/smsclassifier/app/analytics/ConsentManager.kt`
- `app/src/main/java/com/smsclassifier/app/analytics/Telemetry.kt`
- a small extracted onboarding coordinator/policy only if needed for deterministic unit tests
- new focused tests under `app/src/test/java/com/smsclassifier/app/ui/screens/`

### Tests and acceptance

Smallest first:

1. Analytics on + trial success: consent is applied before `trial_started`; onboarding completes once.
2. Analytics on + trial failure: onboarding is not marked complete and no false success event is logged.
3. Analytics off + trial success: trial starts, onboarding completes locally, and no analytics event is emitted.
4. Basic path: consent is applied, onboarding completes once, and no trial is created.
5. Repeated taps/recomposition do not create duplicate trials or completion events.

Then run:

- focused unit tests;
- `testDebugUnitTest`;
- `lintDebug`;
- a clean-install emulator walkthrough of all four paths above.

Measurement gate:

- at least 95% of **consented, successful onboarding trial starts** emit one client trial event;
- zero trial analytics events for explicit opt-out;
- backend totals are reconciled with, not incorrectly equated to, consented GA4 totals.

## Phase 2: prove `pro_yearly` before changing Billing

This phase begins as verification-only. Do not edit Billing code unless a reproducible defect is found.

### Licensed-tester matrix

Using the Play-distributed beta and a licensed tester:

1. Open the current paywall and confirm the localized annual offer is `pro_yearly`.
2. Launch the real Play checkout sheet with a test payment method.
3. Confirm backend validation returns a verified active subscription, not a provisional fallback.
4. Confirm Play acknowledgement succeeds.
5. Confirm Pro remains active after process death and app restart.
6. Confirm reinstall plus Restore Pro recovers the entitlement.
7. Confirm cancellation/expiry eventually removes paid access according to Play state.
8. Reconcile the test transaction in Play Order management; do not infer payment from GA4.

### Existing paths to inspect if a test fails

- `app/src/main/java/com/smsclassifier/app/billing/PlayBillingRepository.kt`
- `app/src/main/java/com/smsclassifier/app/entitlement/EntitlementManager.kt`
- `app/src/main/java/com/smsclassifier/app/entitlement/EntitlementSyncClient.kt`
- `../backend/scripts/android_backend_server.py` purchase verification endpoint

The current client acknowledges after backend verification and does not wait for acknowledgement success before emitting the success path. If acknowledgement fails in the licensed test, fix and test that exact state transition rather than rewriting Billing.

Acceptance:

- one documented `pro_yearly` test transaction completes validation and acknowledgement;
- entitlement survives restart;
- restore succeeds after reinstall;
- Play Order management and backend state agree;
- no claim is based solely on `purchase`/`purchase_completed` analytics.

## Phase 3: measure whether Pro is delivered

### Event semantics

Use message counts, not GA4 event invocation counts, for delivery rates:

- successful cloud-classified messages;
- server-fallback messages by reason;
- offline-skipped messages;
- rate-limited messages;
- attempted Pro messages as the denominator.

Report:

- distinct consented users;
- message totals;
- app version;
- entitlement state (`trial` or paid `pro`);
- success rate = successful cloud results / attempted Pro messages.

Do not log SMS bodies, senders, OTPs, URLs, purchase tokens, Firebase IDs, or raw install IDs.

### Likely files and analytics setup

- `app/src/main/java/com/smsclassifier/app/work/ClassificationWorker.kt`
- `app/src/main/java/com/smsclassifier/app/analytics/Telemetry.kt`
- focused policy tests beside `ClassificationWorkerPolicyTest.kt`
- GA4 custom metric/dimension registration notes, or GA4 BigQuery export if event-parameter sums and cohort joins are required

`appVersion` is already available as a built-in GA4 dimension. Register only the custom parameters actually needed, and use BigQuery rather than creating high-cardinality custom dimensions.

Acceptance:

- reports can separate users, event invocations, and message counts;
- current-version trial and paid users can be compared without blending them with Basic users;
- explicit opt-out remains dark;
- at least seven complete days of trustworthy data exist before judging Pro reliability.

## Phase 4: clarify and surface the offer

Start only after Phases 1–3 pass.

### Product behavior

1. Show the localized Play price wherever the annual purchase is offered. In India this should render as approximately `₹199/year`; do not hardcode a currency for future regions.
2. Explain the no-card trial plainly: “No payment method. You pay only if you later choose Subscribe.”
3. State the boundary:
   - Basic: on-device sorting, OTP finding/copy, and core SMS use.
   - Pro: cloud scam warnings, OTP purpose, and do-not-share guidance.
4. Add a contextual, deduplicated CTA for users who skipped the trial. Do not show it on every open; trigger it after meaningful use or a locked Pro-value moment and give it a cooldown.
5. At expiry, show a one-time dismissible sheet with Subscribe and Continue with Basic. Never block the Inbox or normal SMS use.

### Likely files

- `app/src/main/java/com/smsclassifier/app/ui/screens/ConsentOnboardingScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/PaywallScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/InboxScreen.kt`
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt`
- `app/src/main/java/com/smsclassifier/app/entitlement/EntitlementManager.kt`
- focused copy/policy tests under `app/src/test/`

### UX and accessibility checks

- localized price loads and has a safe fallback state;
- all primary actions remain at least 48dp;
- TalkBack reads the price, Basic/Pro distinction, dismiss action, and post-dismiss state;
- back navigation and dismissal never trap the user;
- large text and narrow screens do not clip CTA/copy;
- trial skippers and expired users do not see repeated prompts in the same session or cooldown;
- Inbox, OTP copy, sending, and Settings remain functional in Basic mode.

## Delivery sequence

Use separate changes:

1. consent sequencing plus tests;
2. licensed purchase verification, with a code fix only if a defect reproduces;
3. Pro-delivery event semantics and analytics configuration;
4. offer/expiry UX plus accessibility tests.

For any Android release, follow the repository’s normal full path: focused tests, unit suite, lint, signed release build, emulator/device checks, version bump, GitHub review, Play beta upload, and live track readback. Implementation and release require a separate explicit request; this document does not authorize publishing.

## Rollback gates

Stop or roll back if:

- a failed trial can mark onboarding complete;
- an opted-out user produces analytics;
- a trial or purchase can be created twice from repeated UI actions;
- verified Pro cannot survive restart or restore;
- reported delivery rates use event counts as message counts;
- the expiry or CTA UI interferes with core SMS use;
- crash/ANR or classification failure rates regress.

## Success metrics

Instrumentation:

- consented onboarding trial attribution coverage ≥95%;
- explicit opt-out leakage = 0;
- unique users and message totals are independently queryable.

Purchase:

- licensed `pro_yearly` checkout, validation, acknowledgement, restart, reinstall, and restore all pass;
- Play Order management is reconciled with backend entitlement state.

Funnel:

- eligible exposure, CTA taps, paywall views, checkouts, verified purchases, and dismissals are measurable as distinct users;
- trial-to-checkout and checkout-to-verified-purchase are reported without calling test transactions revenue.

Product safety:

- Basic mode remains fully usable;
- no blocking expiry gate;
- no Ads state changes.

## Explicitly out of scope

- pausing or editing any Ads campaign;
- budget, bidding, targeting, creative, or conversion-action changes;
- hardcoding India pricing for all users;
- a blocking paywall;
- bypassing analytics consent;
- a Billing or backend rewrite without a reproduced defect;
- implementation, GitHub publishing, or Play release during this planning task.
