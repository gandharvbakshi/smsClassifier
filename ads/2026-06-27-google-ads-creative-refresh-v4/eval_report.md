# Eval Report

## IMG_OTP_ACCOUNT_SQUARE: ship

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
**Visual metrics:** product_ui_area_fraction=0.5376, proof_density_limit=0.38, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1823
**Strengths:**
- The on-image headline is clear, concise, and directly matches the brief's requirement.
- The visual proof (synthetic app UI) clearly demonstrates the product's core feature and directly supports the headline and creative story contract.
- Excellent mobile legibility for both the headline and the text within the synthetic product UI, adhering to declared proof readability and contrast checks.
**Recommendations:**
- blind_one_second: Consider slightly increasing the font size of the warning text inside the phone screen, specifically 'Code changes mobile number', to enhance readability on smaller mobile devices.
- blind_one_second: Add a clear call to action (CTA) to guide users on the next step, as the ad currently lacks one.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## IMG_OTP_ACCOUNT_PORTRAIT: ship

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
| pricing_honesty | 5 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.549, proof_density_limit=0.38, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.197
**Strengths:**
- The headline is clear, concise, and effectively communicates the core problem and solution.
- The visual proof (synthetic app UI) directly supports the headline and clearly demonstrates the app's functionality and value proposition.
- All on-image text, including within the synthetic UI, is highly legible and maintains excellent contrast, ensuring readability on mobile devices.
**Recommendations:**
- blind_one_second: The bottom portion of the phone screen is mostly empty, showing only pagination dots. While the main message is clear, this area could potentially be utilized to hint at other features or provide a subtle call to action if space allows without cluttering the primary message.
**Checker:** deterministic_rules+google/gemini-2.5-flash
