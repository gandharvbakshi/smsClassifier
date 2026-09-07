# Groq SMS model replacement evaluation — 2026-09-07

**Qwen 3.6 27B won this speed/quality comparison.** With reasoning disabled it achieved 97.9% agreement with the project's intent reference labels, a 192 ms median, and a 485 ms p95 provider round trip. Qwen 3.8 offered no aggregate agreement improvement and was slower and more expensive. GPT-OSS 20B is the inexpensive production-listed alternative, with lower intent agreement on this set.

**Deployment decision remains open.** Groq currently lists both Qwen candidates as preview models, explicitly unsuitable for production and potentially discontinued at short notice. Use Qwen 3.6 as the leading staging candidate; GPT-OSS 20B is the preferred production-listed candidate if lifecycle stability is required. This evaluation did not change the live model, backend runtime, Android app, UI, or taxonomy. [Groq model lifecycle and pricing](https://console.groq.com/docs/models)

## Measured results

Pooled results from two rounds, each using the same 146 unique cases. Intent agreement excludes five cases without a reference intent: each model has 282 scored outputs from 141 unique labeled cases. Repeats are not additional independent examples.

| Model | Intent agreement | Macro F1 | Median | p95 | Estimated USD / 1,000 model calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen 3.6 27B | 276/282 (97.9%) | 0.963 | 192 ms | 485 ms | $0.285 |
| Qwen 3.8 27B | 276/282 (97.9%) | 0.960 | 410 ms | 875 ms | $0.405 |
| GPT-OSS 120B | 271/282 (96.1%) | 0.935 | 409 ms | 1,848 ms | $0.106 |
| GPT-OSS 20B | 264/282 (93.6%) | 0.904 | 206 ms | 753 ms | $0.050 |

All **1,168 benchmark requests** returned HTTP 200 and passed strict output-schema validation. No observed timeouts or rate-limit responses occurred in this bounded test; that does not establish sustained quota headroom. Qwen 3.6's p95 was 503 ms in round one and 464 ms in round two. Model order was reversed in round two to reduce order/time bias.

Latency measures client-to-Groq round trips from the evaluation machine, including network time, at four concurrent requests per model. It is not Android-to-backend latency or decode throughput. Costs use returned token usage and uncached list prices; they exclude Cloud Run and network costs and apply to **model calls, not every SMS**. Current input/output USD per million tokens: GPT-OSS 20B 0.075/0.30; GPT-OSS 120B 0.15/0.60; Qwen 3.6 0.60/3.00; Qwen 3.8 0.80/4.00. [Groq pricing](https://console.groq.com/docs/models)

## Llama availability

Authenticated model enumeration on the app's current Groq account returned only Llama Prompt Guard 2 (22M and 86M). These are safety classifiers, not general generative replacements for the SMS intent prompt. Explicit generation probes for `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` both returned HTTP 404 / `model_not_found`. Their error-response timings are not inference benchmarks.

Groq documents retirement of these generative Llama models on August 16, 2026 for free/developer accounts, with enterprise contract exceptions. This finding is scoped to this account; Llama through other providers was not tested. [Groq deprecations](https://console.groq.com/docs/deprecations), [account evidence](llama-availability.json)

## Protocol and corpus

- Exact current backend `SYSTEM_PROMPT`, `USER_TEMPLATE`, and nine-label taxonomy read using Python AST; same sender/text normalization, temperature 0 and JSON object response mode.
- `max_tokens=1024` for every candidate; GPT reasoning `low`, Qwen reasoning `none`. Qwen's `none` disables reasoning. A one-case parameter pilot produced a Qwen 3.6 JSON-validation failure at the old 256-token/default-reasoning setting and succeeded with the evaluated settings. The larger test therefore supersedes the earlier 8/12 smoke result as a model-selection comparison, without claiming the settings are already integrated into production. [Reasoning controls](https://console.groq.com/docs/reasoning)
- Per-thread persistent HTTP sessions, connect/read timeouts 1.5/6 seconds, no retries. Strict output requires exactly `is_otp`, `otp_intent`, and `is_phishing`, correctly typed and internally consistent.
- 91 unique synthetic text/sender pairs from the existing 200-row project set; 109 exact duplicates removed. Added 19 sanitized code regression cases and 36 fresh synthetic challenges (four per intent). No private feedback queue or raw user SMS was downloaded.
- Labels were frozen before benchmark requests. They are project reference labels, not independently adjudicated human ground truth. Existing synthetic templates remain similar after exact deduplication, and several classes have small support.
- Per-case evidence stores IDs, hashes, reference labels, predictions, timings, token counts and safe status metadata. It does not store API credentials or model reasoning. The separate corpus contains synthetic/sanitized test text.

## Limits and disagreement review

**This is a direct model-component benchmark, not a measured improvement in app accuracy.** In the local routing check, all 146 cases were resolved by existing heuristic/ML paths (`groq_needed=false`). The check used the deployed model files, disabled Web Risk, and replaced provider calls with an unavailable stub. The corpus therefore does not measure the actual distribution of production messages that reach Groq, or full-stack behavior after migration.

All candidates disagreed with two existing regression labels: a WhatsApp phone-change case was interpreted as login, and a malicious bank-link message containing a numeric code was interpreted as OTP despite the full pipeline's NOT_OTP policy. Existing pipeline vetoes matter here; direct-model disagreements do not establish that the live app would misclassify these cases. Reference labels were not changed after observing outputs.

Qwen 3.6 matched all 36 fresh intent labels in both rounds. Its additional disagreement was a vague account-verification/bonus synthetic case. Qwen 3.8 missed a fresh password-reset intent in both rounds. GPT-OSS 20B's extra misses included ambiguous generic verification messages classified as login. These findings favor Qwen 3.6 for further evaluation, but do not prove behavior preservation on unseen fallback traffic.

## Recommended next step

Add configurable reasoning effort and output-token budget in an isolated migration patch, preserving the prompt, nine labels, heuristic overrides, provider deadlines and fallback behavior. The current runtime still uses the retired Llama ID and old output budget; merely changing the model name would not reproduce this test. Validate actual Groq-routed cases in staging and compare final API outputs before any canary/promotion. A production rollout must account for Qwen's preview lifecycle or select the production-listed GPT-OSS 20B after its quality gaps are addressed. No model migration or release was performed here.

## Reproduction and evidence

From repository root with backend requirements installed and `GROQ_API_KEY` configured (otherwise the evaluator uses authenticated gcloud access to the app's existing Secret Manager secret):

```powershell
python backend/scripts/evaluate_groq_replacements.py --cases backend/evaluation/groq-20260907/cases.jsonl --output-dir .tmp/groq-new-run --workers 4 --max-tokens 1024
```

This command makes paid provider requests; use a new output directory for a fresh run, or `--resume` to reuse matching case/config hashes. The default model order is GPT-OSS 20B, GPT-OSS 120B, Qwen 3.6, Qwen 3.8. Round two used the reverse order through `--models`.

- [Pooled metrics](comparison.json), [corpus manifest and hashes](corpus_manifest.json), [frozen cases](cases.jsonl)
- [Round one manifest](run1/manifest.json), [round two manifest](run2/manifest.json); per-model directories contain request records and summaries.
- [Parameter pilot](model-parameter-pilot.json), [Llama availability](llama-availability.json)
- Harness validation: **122 backend tests passed, plus 41 subtests**; one dependency deprecation warning. No Android code changed in this evaluation.
