# Human Creative Audit

Run: `2026-06-14-google-ads-copy-lab-v7`

## Verdict

This is the strongest SMS Classifier run so far. The system now generates ads from stakes and proof instead of feature labels. The OTP concept finally sells the real product agency: an OTP scam can change an account, and the SMS app warns before sharing. The family-scam concept is also understandable to the documented target user: parents may tap scam SMS, and the app warns them.

Would Opus call it perfect? Probably not. It would likely still ask for more visual dynamism and shorter video first-frame text. But it should no longer reject the run for the core failures from earlier iterations: unclear category, KYC/domain jargon, weak "app warns" fragments, proof text too small, missing product UI, or videos that change too fast.

## Machine Eval Summary

- Strict copy preflight: pass.
- Deterministic strict eval: only fails without model review, as intended for shippable app-install assets.
- Final model-backed strict eval: 7 ship, 1 revise, 0 hard-fail rejects.
- Remaining model revise: `otp_scam_benefit_headline_square` asks for a shorter one-second headline. I consider this a useful variant request, not a blocker, because the deeper account-change stake is worth the extra words and the landscape/portrait OTP versions ship.

## Fundamentals

1. Product/category clarity: strong.
   The user sees `SMS Classifier`, `SMS app`, OTP, scam SMS, and a phone/app proof surface. This fixes the v5 problem where abstract graphics did not reveal what product was being sold.

2. First-3-second pain: strong, especially in video.
   OTP: "An OTP scam can change your account" establishes stakes fast.
   Family: "Worried your parents might tap a scam SMS?" is immediately understandable to the target user.

3. Tension and resolution: strong.
   OTP uses the correct contradiction: delivery story vs account-change warning.
   Family uses prize link vs suspicious-link warning.

4. Product agency: strong.
   The app is not merely telling users to be careful. It visibly classifies/warns in the SMS surface before the user shares or taps.

5. Proof clarity: much stronger.
   Proof screens now use ad-scale typography, three proof zones, high-contrast warning states, no KYC, no dense inbox, no cloud/config callouts, and no tiny debug UI.

## Remaining Weaknesses

- The static compositions are clean but conservative. They are clear and shippable, but not visually surprising.
- The OTP square headline is long for a one-second glance. It is strategically right, but a future copy test should include a shorter variant such as "OTP scams can change accounts."
- Videos are still slideshow-style. They are readable and paced, but the next system improvement should support simple reveal motion: caller claim -> app verdict -> warning outcome.
- Some model recommendations ask for baked CTAs, but this run intentionally keeps install/download CTA language in platform fields, not image pixels.

## Process Learnings Folded Back

- High-stakes hooks must name the concrete consequence, not just "app warns."
- Preserved video rows in `creative_matrix.csv` must refresh from `message_map.yaml` when copy changes.
- Synthetic proof specs must declare thumbnail-safe typography and all important chip/warning contrast checks.
- Proof-source screenshots should minimize duplicate app chrome and spend text budget on trigger, verdict, and user implication.
- Density checks need to account for declared ad-scale proof typography; large text and strong warning blocks are not the same as a dense screenshot.

