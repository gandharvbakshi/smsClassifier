# Qwen 3.6 staging validation — 2026-09-07

**Staging passed the bounded full-backend validation. Production was not promoted.** Qwen 3.6 27B with reasoning explicitly disabled classified all 24 synthetic cases that naturally reached Groq with the expected intent. All 146 earlier baseline cases retained the same `isOtp`, `otpIntent`, and `isPhishing` outputs as production.

## Deployed candidate

- Project/region/service: `smsclassifier-478611` / `asia-south1` / `sms-ensemble`.
- Candidate revision: `sms-ensemble-qwen0907b`, tag `qwen-staging`, **0% default traffic**.
- Candidate URL: https://qwen-staging---sms-ensemble-hhpimusmbq-el.a.run.app
- Production remains **100% on `sms-ensemble-reliability0907`**; its health still reports the retired `llama-3.1-8b-instant`.
- Image: `asia-south1-docker.pkg.dev/smsclassifier-478611/cloud-run-source-deploy/sms-ensemble@sha256:d230667c24662811fd5de26f4be0c2d8f28a798e5bf233abc3c9e46d8e1c7194`.
- Cloud Build: `75ea944f-772c-4709-9f65-120af844abcb`, successful. Image overlays only the server and provider transport on the exact deployed reliability image; trained models, packages and purchase transport are unchanged.

Candidate environment settings:

| Setting | Value |
| --- | --- |
| `GROQ_INTENT_MODEL` | `qwen/qwen3.6-27b` |
| `GROQ_REASONING_EFFORT` | `none` |
| `GROQ_MAX_TOKENS` | `1024` |
| `GROQ_PROMPT_COST_PER_MILLION_MICROS` | `600000` |
| `GROQ_COMPLETION_COST_PER_MILLION_MICROS` | `3000000` |

The literal string `none` is sent in the provider request; omitting the setting does not disable reasoning. Cost settings reflect USD0.60/3.00 per million input/output tokens. Qwen remains a preview model, which Groq describes as unsuitable for production and subject to discontinuation. The user authorized staging validation with that limitation. [Groq reasoning](https://console.groq.com/docs/reasoning), [model lifecycle/pricing](https://console.groq.com/docs/models)

No UI, navigation, API schema, prompt, intent taxonomy, heuristic/ML thresholds, phishing mode, timeout/cooldown policy, capacity limits, or Play release changed. Candidate capacity remains 1 CPU/512MiB/concurrency80/revision max10/min0. Existing Secret Manager bindings are inherited; no credentials were printed or committed.

## Verification

| Check | Result |
| --- | --- |
| Backend tests | 131 passed +41 subtests; one dependency deprecation warning |
| Original baseline corpus, hosted production vs candidate | 146/146 match on the three classification fields |
| Naturally Groq-routed synthetic cases | 24/24 reached Groq and returned expected intents |
| OTP/phishing flags on routed cases | 24/24 unchanged from production |
| Response field names | Unchanged for all170 cases |
| Hosted successful-run HTTP responses | 340/340 HTTP200 across both revisions |
| Candidate provider logs | 24/24 HTTP200; no provider errors or429s |
| Local full-path failure checks | Existing fallback preserved for404,429,timeout and malformed content |
| Traffic readback | Production100%, candidate0% |

For the 24 Groq-backed candidate API requests, measured end-to-end from the validation machine at four concurrent clients: **median214.6ms, p95369.1ms, maximum380.0ms**. Production returned fast provider-error fallbacks (median66ms), so its latency is not a successful-classification baseline and should not be presented as a speed comparison. The previous direct-model benchmark remains the source for comparisons between supported models.

The 24 routed cases span all eight OTP intents, each with three numeric formats: space-separated, hyphen-separated, and nine digits. These bypass the contiguous4–8-digit heuristic, are classified as OTP by the unchanged ML model, and naturally invoke the existing Groq intent branch. No threshold override, forced-routing hook or special endpoint was deployed. Expected intent labels were set before hosted calls. These are synthetic cases, not a representative sample of private production traffic.

On these cases, production's retired model failed24/24 and left `isOtp=true, otpIntent=NOT_OTP`; the candidate restored the expected OTP purpose. That is an intended classification behavior change on the broken provider path. Existing fallback behavior during provider failure is preserved, including that pre-existing inconsistent field combination; this staging task did not redesign it.

Provider response headers reported minimum remaining tokens242,197 and requests499,977 during this small test. Those are provider-window snapshots, not a per-minute quota assertion or proof of sustained headroom. No scale setting was increased.

The first staging revision (`sms-ensemble-qwen0907a`) caught a PowerShell argument-formatting error: environment assignments had been combined into the model ID. It never received default user traffic. Revision `b` corrected the deployment arguments using an explicit subprocess argument list, and exact environment/health readback passed before repeating the tests. The validation script now rejects an incorrect candidate model ID before classification requests.

## Operational next step

Keep this tagged candidate isolated until a production rollout decision accounts for preview lifecycle and the limited sample. More representative, consented or sanitized Groq-routed cases would improve confidence. A production promotion is not included in this authorization. No significant UI/UX change is expected from the patch; users whose requests previously hit the retired model would receive recovered OTP intent classification after promotion.

The service's latest revision template now carries the Qwen staging settings. Future deployments must explicitly choose the intended model/settings and traffic behavior; do not assume the latest template equals the currently serving production revision. To stop access to the candidate, remove only the `qwen-staging` tag; preserve the production100% assignment.

## Reproduction and evidence

```powershell
python backend/scripts/validate_qwen_staging.py --candidate-url https://qwen-staging---sms-ensemble-hhpimusmbq-el.a.run.app --output-dir .tmp/qwen-staging-rerun
```

This performs170 classify requests on each revision, with no feedback, entitlement or purchase writes. For future gcloud calls from PowerShell, quote the entire comma-separated `--update-env-vars` argument or pass it as one explicit subprocess argument.

- [Summary](summary.json), [production outputs](baseline.json), [candidate outputs](candidate.json)
- [Synthetic routed cases](routed_cases.jsonl), [local failure checks](local_failure_checks.json)
- [Safe provider log evidence](provider_logs.json), [deployment settings and traffic](deployment.json)
- Source files: `backend/scripts/android_backend_server.py`, `backend/classification/provider_transport.py`, `backend/tests/test_provider_transport.py`, `backend/tests/test_groq_generation_config.py`, `backend/scripts/validate_qwen_staging.py`.
