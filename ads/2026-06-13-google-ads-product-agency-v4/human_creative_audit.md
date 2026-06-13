# Human Creative Audit

Run: `2026-06-13-google-ads-product-agency-v4`

## Verdict

This is a much stronger pipeline test than the earlier runs, but the full batch is not production-shippable yet.

- Strict deterministic eval: clean, except the expected strict model-review requirement.
- Final strict model eval: 1 ship, 7 revise/reject.
- Best current asset: `kyc_review_landscape_google_app_landscape.png`.
- Strongest concept overall: OTP mismatch/fraud-tripwire remains the best hook, but the video and some ratios still need better brand/proof legibility.

## Product Agency

The statics now clearly show the app creating the advantage:

- `Delivery? App shows account change`
- `Prize SMS asks KYC? App warns`

This fixes the earlier "take precaution" problem. The app is no longer just advising the user to be careful; it shows a purpose/warning signal before the user acts.

Remaining issue: brand identity is weak. The small chat-check icon is present, but the model and human read both find it too generic. Future system rule should require a brand/name treatment for strict app-install outputs when the platform is not guaranteed to overlay app name.

## First-3-Second Hook Strength

The videos improved because they now start on product UI, not a poster-only intro. However:

- OTP video first beat says `App shows account change`, but drops the `Delivery?` tension.
- KYC video first beat says `KYC text? App warns`, but drops the more click-worthy `Prize SMS` trigger.
- Later KYC beat `Warning stays visible` becomes weaker and more feature-ish.

For shippable video, the first frame should preserve the full tension plus app action, even if the wording must be compressed.

## Click Power

- OTP static: high. The mismatch story is naturally thumb-stopping.
- KYC static: medium-high. Clearer now, but less emotionally sharp than OTP.
- Videos: medium. They are clearer than before, but not yet exciting enough. They need a sharper first beat and a stronger final outcome.

## Specificity

Specificity is good:

- delivery code vs account change
- prize/KYC SMS before tapping

These are concrete scenarios, not generic "safe inbox" or "cloud checks" language.

## Proof Clarity

Proof clarity improved after simplifying the synthetic proof screens:

- fewer tiny chips
- larger result text
- high-stakes state is obvious

Remaining issue: some model passes still judge in-phone secondary text as too small, especially on OTP landscape/portrait and KYC square. The system should continue preferring fewer, larger proof lines over literal app UI density.

## Machine Eval Summary

Final strict model eval:

- Ship: `kyc_review_landscape`
- Revise: `otp_agency_square`, `otp_agency_landscape`, `otp_agency_portrait`, `kyc_review_portrait`, `V_OTP_AGENCY_9x16`
- Reject: `kyc_review_square`, `V_KYC_REVIEW_9x16`

Common model objections:

- weak brand recognition / no obvious app name
- proof text still too small in some ratios
- video captions drift from the approved hook
- KYC video has one weaker convenience-like beat

## System Lessons

Already baked into this iteration:

- target-user clarity gate instead of generic average-user wording
- proof contract context in model checker brief so declared synthetic proof is not rejected solely for being synthetic
- model-review video frame sampler now includes the actual early timeline rather than arbitrary manual frames
- video-production guidance now rejects poster-only intros for shippable UI-led app-install videos
- visual-production guidance now requires ad-proof UI typography for synthetic proof screens

Still needed:

- a brand/name treatment rule for strict app-install creatives
- a video hook-continuity gate so first proof beat preserves the trigger plus product agency
- stronger deterministic or model-assisted proof-text legibility checks for in-phone UI text
