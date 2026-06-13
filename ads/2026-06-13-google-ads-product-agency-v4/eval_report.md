# Eval Report

## otp_agency_square: revise

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 5 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 0 |
| composition_aesthetics | 3 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4224, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0495, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1706, proof_top_edge_ink_fraction=0.0
**Strengths:**
- The on-image headline perfectly matches the brief and is concise.
- The synthetic UI clearly demonstrates the declared proof moment: showing a mismatch between a caller's claim and the OTP's purpose.
- Excellent mobile legibility with large, clear text and good contrast throughout the image.
**Recommendations:**
- blind_one_second: Introduce clear branding (logo, app name) to identify whose app this is, as no brand is visible.
- blind_one_second: Add a clear call to action (e.g., 'Download now', 'Protect your account') to guide users on what to do next.
- blind_one_second: Consider a more concise and impactful headline that integrates the brand or solution, rather than just posing a question.
- blind_one_second: While the problem is clear, explicitly state the app's name or core feature to make the solution more tangible and memorable.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## otp_agency_landscape: revise

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 3 |
| brand_consistency | 0 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.3868, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0634, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1817, proof_top_edge_ink_fraction=0.0
**Strengths:**
- The headline is clear, concise, and directly addresses the app's core functionality.
- The synthetic UI effectively demonstrates the app's value proposition by contrasting caller claims with actual OTP purpose.
- The design is clean, uncluttered, and adheres to mobile-first principles with good use of whitespace.
**Recommendations:**
- blind_one_second: Increase the font size of the smaller explanatory text within the phone screen, such as 'SMS Classifier shows code purpose', to ensure it is easily legible on a mobile device at a glance.
- blind_one_second: Integrate clear branding, such as a logo or app name, to establish brand consistency and help users identify the product.
- blind_one_second: Consider a more explicit headline or sub-headline that clearly states the product's category (e.g., 'OTP Security App', 'Fraud Protection') to ensure immediate understanding.
- blind_one_second: Add a clear call to action to guide users on the next step after seeing the ad.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## otp_agency_portrait: revise

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 3 |
| visual_hierarchy | 3 |
| mobile_legibility | 3 |
| brand_consistency | 0 |
| composition_aesthetics | 3 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4392, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0896, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1522, proof_top_edge_ink_fraction=0.0
**Strengths:**
- Clear and concise headline directly addressing the user's potential problem.
- Excellent visual proof that clearly demonstrates the app's core feature (OTP purpose detection) and the declared proof moment.
- Clean, uncluttered design with good visual hierarchy, making it easy to understand the message quickly.
**Recommendations:**
- blind_one_second: Increase the font size of the smaller text within the app screenshot (e.g., 'SMS Classifier shows code purpose', 'Caller says', 'SMS Classifier shows') to ensure legibility on a mobile screen at a quick glance.
- blind_one_second: Make the product name (e.g., 'SMS Classifier' or the app's brand name) more prominent, as it's currently secondary to the problem statement.
- blind_one_second: Add a clear brand logo or identifier to establish brand consistency.
- blind_one_second: Consider simplifying the top headline 'Delivery? App shows account change' to be more direct about the solution, e.g., 'Stop OTP Scams: See the Real Purpose'.
- skeptic_critic: Consider slightly increasing the visual prominence of the brand logo, if brand recognition is a primary goal, without compromising the clean aesthetic.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## kyc_review_square: reject

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 4 |
| mobile_legibility | 0 |
| brand_consistency | 3 |
| composition_aesthetics | 4 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** Unreadable-on-mobile text: Several lines of text within the synthetic UI are too small to be legible on mobile devices and at thumbnail sizes (e.g., 'SMS Classifier warns before tap', 'Message asks', 'Do not rush').
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4224, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0495, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1691, proof_top_edge_ink_fraction=0.0
**Model hard fails:** Unreadable-on-mobile text: Several lines of text within the synthetic UI are too small to be legible on mobile devices and at thumbnail sizes (e.g., 'SMS Classifier warns before tap', 'Message asks', 'Do not rush').
**Fixes:**
- Increase the font size of all text within the synthetic UI, particularly the smaller explanatory lines, to ensure readability on mobile devices and at various thumbnail sizes.
**Strengths:**
- Clear and direct headline that sets the context for the app's function.
- Effective visual proof that clearly demonstrates the app's core feature (SMS classification and warning).
- Clean and uncluttered composition, adhering to the clutter budget.
**Recommendations:**
- Increase the font size of all text within the synthetic UI, particularly the smaller explanatory lines, to ensure readability on mobile devices and at various thumbnail sizes.
- blind_one_second: If the small blue icon is the only brand identifier, consider making the app's brand name more prominent.
- blind_one_second: The phrase 'SMS Classifier warns before tap' is present in both the sub-headline and within the phone frame; consider varying the wording to avoid redundancy.
- blind_one_second: The ad could benefit from a clear call to action to guide users on the next step.
- depth_critic: The phrase 'SMS Classifier warns before tap' appears redundantly as a subtitle and within the warning box; consider streamlining for conciseness.
- depth_critic: The main title within the app UI, 'Review Texts', could be more specific to the risk/scam detection aspect to further enhance the proof's impact, e.g., 'Scam Text Review' or 'Risky SMS Alerts'.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## kyc_review_landscape: ship

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
| pricing_honesty | 3 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.3868, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0634, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1802, proof_top_edge_ink_fraction=0.0
**Fixes:**
- Consider slightly increasing the font size of the smaller text elements within the synthetic UI (e.g., 'SMS Classifier warns before tap', 'Message asks') to ensure maximum legibility on the smallest mobile screens.
**Strengths:**
- Headline is clear, concise, and matches the brief exactly.
- Visual proof is highly effective, clearly demonstrating the app's core function and aligning with the declared proof moment.
- Design is clean, modern, and uncluttered, adhering to the clutter budget.
**Recommendations:**
- Consider slightly increasing the font size of the smaller text elements within the synthetic UI (e.g., 'SMS Classifier warns before tap', 'Message asks') to ensure maximum legibility on the smallest mobile screens.
- blind_one_second: Introduce a clear brand name or more prominent logo to improve brand recall, as only a generic icon is visible.
- blind_one_second: Condense or rephrase repetitive phrases like 'SMS Classifier warns before tap' for brevity and impact.
- blind_one_second: Consider making the 'Do not rush' warning more prominent or integrating it into a clearer call to action for the user.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## kyc_review_portrait: revise

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 3 |
| mobile_legibility | 4 |
| brand_consistency | 0 |
| composition_aesthetics | 3 |
| policy_safety | 5 |
| pricing_honesty | 0 |

**Hard failures:** none
**Strict contract:** passed
**Visual metrics:** product_ui_area_fraction=0.4392, proof_inner_bbox_pct={'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}, proof_inner_bottom_empty_fraction=0.0896, proof_inner_detection=light_ui_bbox, proof_inner_ink_fraction=0.1509, proof_top_edge_ink_fraction=0.0
**Strengths:**
- Clear and concise headline that immediately communicates the app's value proposition.
- Effective visual proof (synthetic UI) that directly supports the headline and demonstrates the core feature.
- Clean and uncluttered design with excellent visual hierarchy, making it easy to understand at a glance.
**Recommendations:**
- blind_one_second: Add a clear brand name and logo to the ad; currently, there is no brand identity visible.
- blind_one_second: Include a clear call to action (e.g., 'Download Now', 'Protect Your Texts') to guide the user on the next step.
- blind_one_second: Simplify and condense some of the repetitive text within the simulated app screen to improve one-second comprehension (e.g., 'SMS Classifier warns', 'Review before tap', 'Do not rush' could be more concise).
- blind_one_second: Consider a more dynamic or visually engaging representation of the warning, as the current ad is very text-heavy and static.
- skeptic_critic: Consider slightly increasing the prominence of the brand logo for better recognition, though its current size is acceptable.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## V_OTP_AGENCY_9x16: revise

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 5 |
| product_proof | 4 |
| message_clarity | 4 |
| visual_hierarchy | 3 |
| mobile_legibility | 3 |
| brand_consistency | 0 |
| composition_aesthetics | 3 |
| policy_safety | 5 |
| pricing_honesty | 4 |

**Hard failures:** none
**Strict contract:** passed
**Fixes:**
- The on-image headline 'App shows account change' is missing 'Delivery?' from the required headline 'Delivery? App shows account change' specified in the brief.
- The on-image headline 'Story doesn't match' is not the required headline 'Delivery? App shows account change' specified in the brief.
- Revise the on-image headline to precisely match the brief's requirement: 'Delivery? App shows account change'. Ensure this headline is consistently used or appropriately integrated if the video features a headline progression.
**Strengths:**
- Excellent visual proof that clearly demonstrates the app's core feature of detecting OTP purpose discrepancies.
- Strong message clarity, effectively communicating the app's value proposition through the visual proof.
- Optimal mobile legibility with large, high-contrast text elements and clear visual hierarchy.
**Recommendations:**
- The on-image headline 'App shows account change' is missing 'Delivery?' from the required headline 'Delivery? App shows account change' specified in the brief.
- The on-image headline 'Story doesn't match' is not the required headline 'Delivery? App shows account change' specified in the brief.
- Revise the on-image headline to precisely match the brief's requirement: 'Delivery? App shows account change'. Ensure this headline is consistently used or appropriately integrated if the video features a headline progression.
- blind_one_second: Integrate clear brand identification (logo, brand colors) into the ad to establish who is offering this product.
- blind_one_second: Add a compelling headline or call to action that explicitly states the user benefit, such as 'Avoid OTP fraud' or 'Verify your OTPs'.
- blind_one_second: Increase the font size of smaller explanatory text within the app UI, such as 'SMS Classifier shows code purpose', to ensure maximum legibility on all mobile screens.
- blind_one_second: Consider a more dynamic or visually engaging presentation for the sequence to capture attention more effectively within a one-second glance.
- depth_critic: The on-image headline must be revised to precisely match the brief's required hook: "Delivery? App shows account change". While the current headlines are clear, they deviate from the explicit requirement.
**Checker:** deterministic_rules+google/gemini-2.5-flash

## V_KYC_REVIEW_9x16: reject

| Dimension | Score |
|---|---|
| technical_compliance | 5 |
| creative_quality | 0 |
| product_proof | 4 |
| message_clarity | 0 |
| visual_hierarchy | 4 |
| mobile_legibility | 4 |
| brand_consistency | 0 |
| composition_aesthetics | 4 |
| policy_safety | 0 |
| pricing_honesty | 0 |

**Hard failures:** depth_critic:The creative's headline in frame 3 ('Warning stays visible') sells a surface feature/convenience benefit (warning persistence) while the underlying product mechanism supports a deeper user stake (avoided loss, risk reduction from KYC scams). This is a security/fraud product, and convenience-only positioning is a hard fail., depth_critic:The on-image headline deviates from the brief's required hook ('Prize SMS asks KYC? App warns') in all frames, significantly so in frame 3., depth_critic:verdict_reject, The on-image headline does not match the required text from the brief across all frames, which is a critical deviation from the intended brand message.
**Strict contract:** passed
**Model hard fails:** The on-image headline does not match the required text from the brief across all frames, which is a critical deviation from the intended brand message.
**Fixes:**
- The on-image headline in all frames must be updated to precisely match the brief's requirement: 'Prize SMS asks KYC? App warns'.
**Strengths:**
- The synthetic product UI is clear, legible, and effectively demonstrates the app's functionality as described in the proof contract.
- All on-image text is highly legible for mobile viewing.
- The composition is clean, aesthetically pleasing, and adheres to clutter budget rules.
**depth_critic hard fails:** The creative's headline in frame 3 ('Warning stays visible') sells a surface feature/convenience benefit (warning persistence) while the underlying product mechanism supports a deeper user stake (avoided loss, risk reduction from KYC scams). This is a security/fraud product, and convenience-only positioning is a hard fail., The on-image headline deviates from the brief's required hook ('Prize SMS asks KYC? App warns') in all frames, significantly so in frame 3.
**Recommendations:**
- Revise hard-fail issues before export.
- The on-image headline in all frames must be updated to precisely match the brief's requirement: 'Prize SMS asks KYC? App warns'.
- blind_one_second: Incorporate a clear brand name and logo to build brand recognition and differentiate the product.
- blind_one_second: Add a clear call to action (e.g., 'Get the App', 'Protect Your Texts') to guide users on the next step.
- blind_one_second: Streamline the text within the warning box to avoid repetition (e.g., 'SMS Classifier warns' appears twice).
- depth_critic: Ensure all on-image headlines consistently use the brief's required hook: 'Prize SMS asks KYC? App warns' to clearly communicate the core value proposition.
- depth_critic: Re-evaluate the video sequence to ensure the primary hook (risk mitigation and avoided loss) is consistently emphasized throughout, rather than secondary features.
- depth_critic: Consider incorporating a more distinct brand element beyond the generic chat bubble icon to improve brand consistency.
**Checker:** deterministic_rules+google/gemini-2.5-flash
