# Purchase warning fixes — 2026-09-24

## Delivered to Cloud Monitoring

- Failure policy `11753309725355080829` now matches purchase HTTP 5xx or structured `validation_status` of `unavailable`/`error`.
- New latency policy `11310519106676661028` matches purchase requests exceeding eight seconds. Its description explains that a slow request can succeed or include a Cloud Run cold start.
- Both enabled policies retain the existing email channel, hourly notification limit and 30-minute autoclose. Browser readback confirmed both saved filters. Latency coverage was created before removing it from the failure policy.

The September 24 warning included a successful HTTP 200 request taking 9.952 seconds; startup consumed most of that time. The structured purchase result was `verified` in 1,970 ms. The last-seven-days audit found three separate `unavailable` results with `TimeoutError`, among 152 verification log entries. These counts are attempts, not purchases or revenue. No purchase endpoint HTTP 5xx appeared in that query.

## Tested code, deployment pending

`purchase_transport.py` now retries a GET once after `TimeoutError`, only while its original five-second auth/request deadline has time remaining. Socket calls retain their two-second limit and shrink to the remaining deadline. Other methods, exception types and HTTP error responses are not retried. Entitlement and billing behavior are unchanged.

- Focused transport tests: 13 passed.
- Full backend suite with the existing pinned dependency environment: 126 tests and 41 subtests passed; one test-tool deprecation warning.
- System Python initially produced 13 fixture errors because its older FastAPI rejects the existing HTTP 204 route. Using the pinned FastAPI 0.121.2 environment resolved these without unrelated source changes.
- `git diff --check -- backend` passed. Both alert templates parse as JSON.
- Production remains on `sms-ensemble-reliability0907`; the retry code is **not deployed**. Google Cloud SDK reauthentication is waiting for the owner to complete the password check in Chrome. Browser Console access works independently.

The working branch is `codex/purchase-warning-fix-20260924` in the existing `android_sms_classifier` folder. The deployed backend-only baseline was imported from `a05701f` as `afbec91`; existing unfinished Android and store-listing work was preserved. No alternate checkout was created.

## Provider issue remains separate

An authenticated model-list request with the existing local Groq configuration returned HTTP 200. `llama-3.1-8b-instant` was absent; GPT-OSS 120B and 20B were present. Qwen 3.6 and 3.8 were also listed, so do not infer account-specific Qwen availability solely from the general retirement notice. Production's recent sampled Groq error was HTTP 404, not a quota 429.

A fresh, bounded GPT-OSS 120B comparison used the unchanged classifier prompt, `reasoning_effort=low`, `max_tokens=1024`, and 170 synthetic/sanitized cases from the existing evaluation tools at `e179a41`:

- 170/170 HTTP 200 and valid output; no observed timeout.
- Intent reference agreement 160/165 (96.97%); OTP agreement 169/170; phishing agreement 146/146 scored cases.
- All 24 formatted-OTP cases agreed with their references. This was a direct provider test, not a new deployed routing test.
- Provider round-trip median 332 ms, p95 1,088 ms, maximum 2,315 ms.
- Five intent disagreements: `synthetic_015`, `synthetic_122`, `regression_otp_whatsapp_phone_change`, `regression_phish_bank_login_link`, `fresh_generic_4`.
- Local evidence: `.tmp/provider-check-20260924/` (cases, manifest, per-request records and summary; no API keys).

No model or generation settings were changed in production. Review the disagreements and validate complete candidate responses against production before promotion. The Cloud Run latest template belongs to the older Qwen staging work and must not be treated as the serving production template.

## Resume steps

1. Complete Cloud SDK reauthentication. Read back the serving revision/image, traffic, environment, secrets and capacity before building.
2. Overlay only the purchase transport on the exact serving image, deploy a zero-traffic candidate with explicit production settings, run health/classification and synthetic invalid-purchase checks, then promote with rollback to `sms-ensemble-reliability0907` available. Do not upload the dirty repository or credentials as build context.
3. Treat provider migration as a separately validated candidate. A real paid Play purchase/restore was not performed; a synthetic invalid-token check cannot establish that full flow.

The Beta INR 1,000 monthly threshold is an advisory budget, not a service cutoff. The live billing audit showed INR 1,096 through September 23 and an INR 1,562.33 month-end forecast. No budget increase, paid warm-instance setting, payment, security change or Beta runtime change was made. Account verification and two-step-verification notices require owner follow-through.
