# Backend reliability verification — 2026-09-07

## Production state

Project `smsclassifier-478611`, region `asia-south1`, service `sms-ensemble` now serves 100% from `sms-ensemble-reliability0907`.

Image: `asia-south1-docker.pkg.dev/smsclassifier-478611/cloud-run-source-deploy/sms-ensemble@sha256:e8cb4f0c9c91fc21a5fc37a81c82dbd5d9aadcd264d085f8430fc515ab42b920`.

Cloud Build: `4394b04d-c49a-4747-866b-e98950be0c37` (asia-south1).
The image overlays only the server and two transport helpers on the exact previous production image. Its dependencies and trained models are unchanged. The downloaded deployed server matched origin/main before this patch.

## Changes

- Purchase verification uses per-thread Google API clients, bounded socket timeouts and a shared auth/request time budget, static discovery, and no automatic API retries. Errors retain the existing unavailable/invalid response contract.
- Entitlement reads use one storage request instead of an existence check followed by download. Storage calls have explicit timeouts and no SDK retry expansion; purchase calls shrink later storage timeouts against an eight-second budget. Network writes no longer hold the global local-file lock. Existing local fallback remains.
- Groq uses thread-local connection pools, 1.5-second connect / 6-second read timeouts, a Retry-After cooldown on actual 429s, and bounded coalescing of identical simultaneous requests. Completed SMS payloads are not cached.
- Safe provider status/limit/latency and purchase-status telemetry makes failures visible without logging tokens or SMS bodies.
- Groq's existing credential is now supplied from Secret Manager version 1 of `sms-classifier-groq-api-key`, with runtime service-account access. The credential was not rotated.
- Purchase and Groq failure alert policies are deployed from `backend/monitoring`. Each uses the existing email channel and at most one notification per hour.
- Android reuses OkHttp clients and honors shared monotonic rate-limit cooldowns. Bulk processing uses its existing heuristic fallback during cooldown. Retry waits are cancellable.

No screens, navigation, pricing, purchase state rules, classifier prompts, model IDs, trained weights, or intent taxonomy changed. Android changes are built and tested locally; this work has not published a new Play version.

## Verification

- Backend: 118 tests and 41 subtests passed using the pinned backend dependencies. One test-tool deprecation warning.
- Android: 96 unit tests passed, debug APK assembled, and all nine intent-label contracts passed.
- Candidate received zero user traffic until checks passed.
- Five synthetic classification cases matched the previous production revision on isOtp, otpIntent, and isPhishing.
- 96 candidate classify requests succeeded: 32 requests at each of 8, 16, and 32 concurrent clients. Observed p95 latency was approximately 0.80s, 1.57s, and 2.79s respectively. These are brief mixed-workload probes, not sustained capacity guarantees or a comparison of Cloud Run concurrency settings.
- Live invalid-purchase probes returned HTTP 200 / validationStatus=invalid in 0.76–2.41 seconds. Local tests cover paid-entitlement preservation and duplicate verification. A real Play purchase/renewal/restore transaction was not executed.
- After promotion, production health and classify returned HTTP 200. Cloud Run readback confirmed 100% on the candidate revision.

Capacity settings remain 1 vCPU, 512 MiB, concurrency 80, min 0, revision max 10 and service max 20. No evidence justified a blind cap increase. A larger sustained staging benchmark is still needed before changing concurrency or warm-instance spend.

## Separate urgent finding: retired Groq model

Direct authenticated checks return 404/model_not_found for `llama-3.1-8b-instant`; it is absent from the account's available models. Groq documents its retirement on August 16, 2026 and recommends `openai/gpt-oss-20b`: https://console.groq.com/docs/deprecations.

The recommended replacement returned valid JSON in an initial smoke call, with substantial request/token headroom in that response. However, only 8/12 synthetic intent checks passed using the unchanged prompt and 256-token settings (one intent disagreement and three HTTP errors). This is insufficient evidence for a behavior-preserving migration. The replacement is NOT enabled. Further accuracy/output-budget validation needs a separate decision because the user requested preservation of classification behavior. Existing fallbacks remain active where the retired model is called.

## Rollback

```powershell
gcloud run services update-traffic sms-ensemble --project=smsclassifier-478611 --region=asia-south1 --to-revisions=sms-ensemble-00027-5sm=100
```

This restores the prior backend revision. Android source changes have not been released through Play. Per-instance rate counters, ephemeral entitlement fallback during storage outages, and real purchase/restore verification remain operational limits to address before major growth.
