# Eval Report

## otp_story_benefit_headline_square: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 5 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4026, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 0.963, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.0977, proof_top_edge_ink_fraction=0.0398
**Strengths:**
- The on-image headline is clear, concise, and directly addresses the target user's pain point.
- The synthetic product UI provides excellent visual proof, clearly demonstrating the app's core feature (OTP scam warning) and how it intervenes.
- The visual hierarchy is well-executed, guiding the viewer from the brand and hook to the compelling product proof.
**Recommendations:**
- blind_one_second: No pricing information is provided, so the 'pricing_honesty' score is 0. If relevant, consider including pricing or value proposition.
- blind_one_second: While clear, the ad could benefit from a subtle call to action if space allows without cluttering the primary message.
- depth_critic: Ensure the smallest text within the app UI (e.g., 'Share OTP for parcel', 'Do not share this code') maintains optimal legibility across all thumbnail sizes, though the primary warning is very clear.
- skeptic_critic: Consider slightly increasing the font size of the smallest text within the simulated UI ('Share OTP for parcel') to ensure maximum legibility across all potential thumbnail sizes.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## otp_story_benefit_headline_landscape: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 5 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 3 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4146, proof_inner_bbox_pct={'x': 0.0, 'y': 0.012, 'w': 1.0, 'h': 0.972}, proof_inner_bottom_empty_fraction=0.1818, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.07, proof_top_edge_ink_fraction=0.0115
**Strengths:**
- Clear and concise headline that directly addresses the user's pain point.
- Effective visual proof (synthetic UI) that clearly demonstrates the app's core feature and resolves the tension presented in the headline.
- Excellent mobile legibility and contrast for all on-image text, including within the synthetic UI.
**Recommendations:**
- blind_one_second: The smaller grey text, specifically 'Share OTP for parcel' and 'Do not share this code' within the phone screen, is difficult to read quickly on a mobile device; increase its font size or contrast for better legibility.
- blind_one_second: The 'SMS app warning' text in the red box is also quite small and could be made more prominent to ensure it's caught in a one-second glance.
- depth_critic: Consider refining the headline to explicitly mention 'account-change' to align even more deeply with the high-stakes warning shown in the visual proof (e.g., 'Account-change OTP fraud? SMS app warns first') to maximize hook depth and specificity.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## otp_story_benefit_headline_portrait: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 5 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.5208, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1713, proof_top_edge_ink_fraction=0.2856
**Strengths:**
- Clear and concise headline that immediately communicates the app's value proposition.
- Effective use of synthetic UI proof that clearly demonstrates the app's core feature (OTP warning) and resolves the user's pain point.
- Excellent mobile legibility for all on-image text, including the headline and text within the synthetic UI.
**Recommendations:**
- blind_one_second: The text 'Share OTP for parcel' within the 'Caller says: delivery' box could be slightly larger to improve legibility on smaller mobile screens.
- skeptic_critic: No significant fixes are required; the asset is highly effective and compliant as is.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## scam_sms_benefit_headline_square: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 3 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4026, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 0.963}, proof_inner_bottom_empty_fraction=0.0468, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.103, proof_top_edge_ink_fraction=0.4483
**Strengths:**
- The on-image headline is clear, concise, and directly addresses the target user's pain point.
- The synthetic product UI provides excellent visual proof, clearly demonstrating the app's core 'scam SMS warning' feature as described in the brief.
- All on-image text, including within the synthetic UI, is highly legible with good contrast, ensuring readability on mobile devices.
**Recommendations:**
- blind_one_second: Ensure the smallest text, such as 'Unknown sender' and 'Could be a fake KYC link', remains perfectly legible on the smallest mobile screens.
- blind_one_second: Consider making the 'Fraud warning in SMS' bubble slightly more descriptive or visually distinct to immediately convey its purpose within the app's interface.
- skeptic_critic: Consider slightly increasing the size of the app UI within the square canvas to maximize the visual proof's impact, ensuring it remains within the recommended 40-55% target.
- skeptic_critic: The 'Fraud warning in SMS' label at the top of the app UI is somewhat generic and could potentially be made more specific or removed if the prominent red warning box is deemed sufficient for clarity.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## scam_sms_benefit_headline_landscape: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 5 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 3 |
| pricing_honesty | 3 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4146, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0018, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1752, proof_top_edge_ink_fraction=0.3688
**Strengths:**
- Clear and concise headline that immediately communicates the problem and solution.
- Effective visual proof (synthetic app UI) that directly supports the headline and demonstrates the product's core feature.
- Excellent mobile legibility due to large, high-contrast text and a clean, uncluttered layout.
**Recommendations:**
- blind_one_second: Consider adding a clear call to action if this is meant to drive immediate app downloads or engagement.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## scam_sms_benefit_headline_portrait: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 5 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 3 |
| pricing_honesty | 3 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.5208, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0247, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.2002, proof_top_edge_ink_fraction=0.2686
**Strengths:**
- Clear and concise headline that immediately communicates the app's value proposition.
- Effective visual proof showing the app's core feature (scam SMS warning) in a clean, understandable synthetic UI.
- Excellent mobile legibility for all on-image text, including within the app UI.
**Recommendations:**
- blind_one_second: Review the legibility of the smallest text elements, such as 'Unknown sender' and 'Could be a fake KYC link', to ensure they are perfectly clear on all mobile screen sizes.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## V_OTP_STORY_9x16: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 3 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Strengths:**
- Clear and concise headline that immediately addresses the target user's pain point.
- Effective visual proof clearly demonstrates the app's core feature (OTP warning) and how it resolves the tension.
- Excellent mobile legibility with high-contrast text and well-sized elements.
**Recommendations:**
- blind_one_second: The first two images are identical; if this is a sequence, the repetition is a missed opportunity to convey more information or show progression.
- blind_one_second: The blue tag in the third image ('App warns: account-change OTP') is somewhat redundant with the red warning box below it, which already states 'Account-change OTP'. This space could be used for additional feature highlights or benefits.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## V_SCAM_SMS_9x16: ship

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 4 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 5 |

**Hard failures:** none
**Strict contract:** passed
**Strengths:**
- Clear and concise headline that effectively communicates the app's value proposition.
- Strong visual proof demonstrating the core feature (scam SMS warning) within the app's UI.
- Excellent mobile legibility and visual hierarchy, ensuring all key information is easily digestible.
**Recommendations:**
- blind_one_second: Increase the font size of the smaller descriptive text within the simulated app (e.g., 'Unknown sender', 'Could be a fake KYC link', 'Review before sharing') to improve legibility at a glance on mobile screens.
**Checker:** deterministic_rules+google/gemini-2.5-flash
