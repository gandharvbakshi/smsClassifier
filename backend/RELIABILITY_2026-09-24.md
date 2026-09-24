# Purchase warning fixes — 2026-09-24

## Delivered to Cloud Monitoring

- Failure policy `11753309725355080829` now matches purchase HTTP 5xx or structured `validation_status` of `unavailable`/`error`.
- New latency policy `11310519106676661028` matches purchase requests exceeding eight seconds. Its description explains that a slow request can succeed or include a Cloud Run cold start.
- Both enabled policies retain the existing email channel, hourly notification limit and 30-minute autoclose. Browser readback confirmed both saved filters. Latency coverage was created before removing it from the failure policy.

The September 24 warning included a successful HTTP 200 request taking 9.952 seconds; startup consumed most of that time. The structured purchase result was `verified` in 1,970 ms. The last-seven-days audit found three separate `unavailable` results with `TimeoutError`, among 152 verification log entries. These counts are attempts, not purchases or revenue. No purchase endpoint HTTP 5xx appeared in that query.

## Purchase retry deployed

`purchase_transport.py` now retries a GET once after `TimeoutError`, only while its original five-second auth/request deadline has time remaining. Socket calls retain their two-second limit and shrink to the remaining deadline. Other methods, exception types and HTTP error responses are not retried. Entitlement and billing behavior are unchanged.

- Focused transport tests: 13 passed.
- Full backend suite with the existing pinned dependency environment: 126 tests and 41 subtests passed; one test-tool deprecation warning.
- System Python initially produced 13 fixture errors because its older FastAPI rejects the existing HTTP 204 route. Using the pinned FastAPI 0.121.2 environment resolved these without unrelated source changes.
- `git diff --check -- backend` passed. Both alert templates parse as JSON.
- Cloud SDK reauthentication completed. Purchase-only revision `sms-ensemble-purchase0924` passed five classification comparisons and a synthetic invalid-purchase check (HTTP 200 / `invalid`, 1,025 ms), then briefly served 100%. The final provider revision below includes this same purchase fix.
- Purchase image: `asia-south1-docker.pkg.dev/smsclassifier-478611/cloud-run-source-deploy/sms-ensemble@sha256:111c5b0aea0b5c28f5a0c8daca2bb1e18de1dbcaa0083ae581a965c74438fc80`; Cloud Build `58ea2761-b27a-4053-a3ff-a979af3bcd9f` succeeded. It overlays only the purchase transport on the exact previous serving image.

The working branch is `codex/purchase-warning-fix-20260924` in the existing `android_sms_classifier` folder. The deployed backend-only baseline was imported from `a05701f` as `afbec91`; existing unfinished Android and store-listing work was preserved. No alternate checkout was created.

## Provider replacement deployed after separate validation

An authenticated model-list request with the existing local Groq configuration returned HTTP 200. `llama-3.1-8b-instant` was absent; GPT-OSS 120B and 20B were present. Qwen 3.6 and 3.8 were also listed, so do not infer account-specific Qwen availability solely from the general retirement notice. Production's recent sampled Groq error was HTTP 404, not a quota 429.

A fresh, bounded GPT-OSS 120B comparison used the unchanged classifier prompt, `reasoning_effort=low`, `max_tokens=1024`, and 170 synthetic/sanitized cases from the existing evaluation tools at `e179a41`:

- 170/170 HTTP 200 and valid output; no observed timeout.
- Intent reference agreement 160/165 (96.97%); OTP agreement 169/170; phishing agreement 146/146 scored cases.
- All 24 formatted-OTP cases agreed with their references. This was a direct provider test, not a new deployed routing test.
- Provider round-trip median 332 ms, p95 1,088 ms, maximum 2,315 ms.
- Five intent disagreements: `synthetic_015`, `synthetic_122`, `regression_otp_whatsapp_phone_change`, `regression_phish_bank_login_link`, `fresh_generic_4`.
- Local evidence: `.tmp/provider-check-20260924/` (cases, manifest, per-request records and summary; no API keys).

The candidate preserved all 146 baseline classification outputs and response schemas. All 24 formatted-OTP cases exercised Groq successfully with their expected intents and unchanged OTP/phishing flags; the corresponding baseline made 24 failing Groq calls. Candidate end-to-end routed latency was median 337 ms / p95 924 ms. The five direct-provider disagreements above did not produce baseline regressions in this full-pipeline check, because those baseline cases are handled earlier by the existing pipeline. This finite synthetic set does not establish accuracy on all real messages.

Production now serves **100% from `sms-ensemble-gptoss0924`**, using `openai/gpt-oss-120b`, `GROQ_MAX_TOKENS=1024`, and `GROQ_REASONING_EFFORT=low`. Image: `asia-south1-docker.pkg.dev/smsclassifier-478611/cloud-run-source-deploy/sms-ensemble@sha256:2bdfb605ba3d47e318bdea11409ce092ba4cbc4b6d690e6c9ac8a15fdf8bf627`; successful Cloud Build `afa9e0d7-0d99-4304-86d4-faf88d5e039f`. This image overlays only the server and provider transport on the purchase-fixed image. Models, packages, classifier prompts, taxonomy and Android UI are unchanged.

Revision readback exactly matched the prior serving specification except for the new image and three explicit model settings. In particular, runtime account, secret references, 1 CPU / 512 MiB, concurrency 80, timeout 60 seconds, revision max 10, service max 20 and scale-to-zero behavior remain. The old Qwen staging template was not inherited.

- Final backend suite: 136 tests and 41 subtests passed, with the same test-tool warning.
- Final public endpoint: health HTTP 200, GPT-OSS 120B reported, 8/8 provider-routed smoke cases succeeded with expected intents, and synthetic purchase HTTP 200 / `invalid` in 945 ms.
- Candidate evidence: `.tmp/provider-deploy-20260924/verification.json`, `production-verification.json` and per-case comparison files.
- Both candidates had zero user traffic until their checks passed. Older revision tags remain available for rollback/testing.

## Rollback and remaining checks

1. Roll back just the model change with `gcloud run services update-traffic sms-ensemble --project=smsclassifier-478611 --region=asia-south1 --to-revisions=sms-ensemble-purchase0924=100`. This retains the retry fix but restores the unavailable Llama model, so it is an emergency rollback, not a steady-state solution.
2. Roll back both runtime changes by assigning 100% to `sms-ensemble-reliability0907`. Alert policies are independent of runtime revisions.
3. A real paid Play purchase/restore was not performed; synthetic invalid-token checks and mocked timeout recovery do not establish the complete paid flow. Review subsequent organic purchase/provider incidents before claiming long-term recovery.

The Beta INR 1,000 monthly threshold is an advisory budget, not a service cutoff. The live billing audit showed INR 1,096 through September 23 and an INR 1,562.33 month-end forecast. Current ordinary traffic is on `beta-backend-staging-everyday-0916-d`; seven older tags still address `beta-backend-staging-history-final-3613430`. Both revisions have minimum one instance. A request-log query for the older revision since September 17 returned zero entries, which supports reviewing those tags but does not prove nobody will need their URLs. Prior decisions explicitly preserve a warm singleton for process-local workflow sessions. No Beta runtime/tag changes, budget increase, payment or security change was made. Account verification and two-step-verification notices require owner follow-through.
