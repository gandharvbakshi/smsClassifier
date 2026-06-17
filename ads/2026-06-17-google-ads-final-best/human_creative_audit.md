# Human Creative Audit

Run: `2026-06-17-google-ads-final-best`

## Verdict

This is the strongest SMS Classifier batch so far. The final matrix contains 9 shippable assets: 7 static images and 2 UI-led videos. The strict checker-model eval shipped all 9 with no hard failures, rejects, or revise verdicts.

## What Improved

- Category is clear: the ads consistently say or show `SMS app` / `SMS Classifier`.
- Pain is immediate: OTP scam, scam caller, parents tapping scam texts, and suspicious links are visible in the first read.
- Product agency is clear: the app warns before sharing/tapping, instead of merely telling the user to be careful.
- Proof is concrete: the phone UI shows `Delivery code? -> Account change / Do not share` and `Prize link? -> Suspicious link / May steal details`.
- Videos now have readable mobile captions, Gemini Indian-English voiceover, explicit Google Play CTA, and 3+ second holds.
- Voiceover no longer reads the caption text aloud. Captions carry the glance-readable hook/proof, while VO adds caller pressure, family context, mechanism, and reassurance.

## Current Video Critique

- OTP video is now much clearer than the previous version: the first frame names the moment, the second frame gives the contradiction, and the VO explains why the mismatch matters. It feels more like an app helping in the moment, not generic precaution advice.
- Parent/family video is clear for the target buyer and avoids hard-to-understand shorthand like `KYC`. It still relies on synthetic proof rather than a realistic SMS thread, so the next creative frontier is making the message look more native and emotionally lived-in.
- Both videos are still UI-led and restrained. That is safer for product proof, but a future high-performing variant should test a human-context opener plus deterministic UI proof.

## Remaining Taste Notes

- The final assets are clean and persuasive, but still utilitarian. A future visual direction could add more human context without sacrificing product proof.
- The family scam proof is understandable, but a future screenshot could look more like a real SMS thread rather than a synthetic warning card.
- Raw generative video is not yet reliable enough for primary product proof. Seedance and Kling produced text artifacts/uncontrolled phone text; Veo produced stronger human emotion but letterboxed output.

## Final Recommendation

Use the top-level `assets/` and `exports/` files as the final shippable set. Treat `assets/revise_candidates/` and `model_bakeoff_selected/` as labeled references only.
