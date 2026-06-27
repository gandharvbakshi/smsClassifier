# Search Copy Eval Report

Decision: **fail**

## Summary

- `ad_groups_checked`: 7
- `rsas_checked`: 12
- `failure_count`: 22
- `warning_count`: 11
- `keyword_metrics_status`: available
- `keyword_metrics_source`: keyword_research.csv
- `keyword_metric_rows`: 48 / 48

## Portfolio Scores

- `keyword_metric_quality`: 5/5
- `portfolio_distinctness`: 4/5
- `coverage`: 5/5
- `claim_safety`: 5/5
- `combination_quality`: 1/5

## RSA Scores

- `sms_app_category_scale/messages_app_control` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `sms_app_category_scale/messages_app_challenger` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=4, message_match=5, claim=5, combinations=5
- `spam_sms_problem_scale/spam_sms_control` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `spam_sms_problem_scale/spam_sms_challenger` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=4, message_match=5, claim=5, combinations=5
- `scam_text_problem_scale/scam_text_control` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=4
- `scam_text_problem_scale/scam_text_challenger` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=4
- `otp_utility_risk_scale/otp_utility_control` Ad Strength: Average (3/5); intent=5, register=5, category=5, distinctness=4, message_match=5, claim=5, combinations=4
- `otp_utility_risk_scale/otp_utility_challenger` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `sms_organizer_control/sms_organizer_control` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=4
- `sms_organizer_control/sms_organizer_challenger` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `sms_classifier_brand_exact/brand_control` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `sms_permissions_trust_holdout/permissions_control` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5

## Issues

- `warn` `sms_app_category_scale/messages_app_challenger` `search_description_repeats_headline`: Description mostly repeats a headline instead of adding proof or motivation: 'The app highlights review cues for odd links and account-code texts.'
- `warn` `spam_sms_problem_scale/spam_sms_challenger` `search_description_repeats_headline`: Description mostly repeats a headline instead of adding proof or motivation: 'The app highlights odd reply requests and bank-detail language.'
- `warn` `scam_text_problem_scale/scam_text_control` `search_rsa_combination_quality_low`: 5/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk.
- `warn` `scam_text_problem_scale/scam_text_challenger` `search_rsa_combination_quality_low`: 6/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk.
- `warn` `otp_utility_risk_scale/otp_utility_control` `search_description_repeats_headline`: Description mostly repeats a headline instead of adding proof or motivation: 'The app shows code context before a bank OTP is shared under pressure.'
- `warn` `otp_utility_risk_scale/otp_utility_control` `search_rsa_combination_quality_low`: 6/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk.
- `warn` `sms_organizer_control/sms_organizer_control` `search_rsa_combination_quality_low`: 5/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk.
- `warn` `sms_classifier_brand_exact` `search_rsas_per_ad_group_low`: Google recommends at least 2 Good/Excellent RSAs per ad group when possible.
- `warn` `sms_classifier_brand_exact/brand_control` `search_keyword_coverage_low`: Include the primary query or close variant in 2-3 readable headlines.
- `warn` `sms_permissions_trust_holdout` `search_rsas_per_ad_group_low`: Google recommends at least 2 Good/Excellent RSAs per ad group when possible.
- `warn` `portfolio` `search_portfolio_phrase_repetition`: Repeated portfolio headline phrase(s) reduce distinctness: sms app, sms review.
- `fail` `blind_serp_scan` `search_model_blind_serp_scan_reject`: blind_serp_scan rejected the Search copy pack.
- `fail` `blind_serp_scan` `search_model_blind_serp_scan_hard_fail`: Multiple RSA combinations lose product agency, repeat copy, or create claim risk.
- `fail` `blind_serp_scan` `search_model_blind_serp_scan_hard_fail`: Descriptions frequently repeat headlines, reducing added value.
- `fail` `blind_serp_scan` `search_model_blind_serp_scan_hard_fail`: Generic portfolio headline phrases ('sms app', 'sms review') are overused, impacting distinctness.
- `fail` `blind_serp_scan` `search_model_blind_serp_scan_hard_fail`: Primary query keyword coverage is low in headlines for some ad groups.
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_reject`: intent_fit_critic rejected the Search copy pack.
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Description mostly repeats a headline instead of adding proof or motivation: 'The app highlights review cues for odd links and account-code texts.' (sms_app_category_scale/messages_app_challenger)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Description mostly repeats a headline instead of adding proof or motivation: 'The app highlights odd reply requests and bank-detail language.' (spam_sms_problem_scale/spam_sms_challenger)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Description mostly repeats a headline instead of adding proof or motivation: 'The app shows code context before a bank OTP is shared under pressure.' (otp_utility_risk_scale/otp_utility_control)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: 5/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk. (scam_text_problem_scale/scam_text_control)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: 6/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk. (scam_text_problem_scale/scam_text_challenger)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: 6/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk. (otp_utility_risk_scale/otp_utility_control)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: 5/30 sampled RSA combinations lose category/product agency, repeat copy, or create claim risk. (sms_organizer_control/sms_organizer_control)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Google recommends at least 2 Good/Excellent RSAs per ad group when possible. (sms_classifier_brand_exact)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Google recommends at least 2 Good/Excellent RSAs per ad group when possible. (sms_permissions_trust_holdout)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Include the primary query or close variant in 2-3 readable headlines. (otp_utility_risk_scale)
- `fail` `intent_fit_critic` `search_model_intent_fit_critic_hard_fail`: Repeated portfolio headline phrase(s) reduce distinctness: sms app, sms review.
- `fail` `skeptic_critic` `search_model_skeptic_critic_reject`: skeptic_critic rejected the Search copy pack.
- `fail` `skeptic_critic` `search_model_skeptic_critic_hard_fail`: search_description_repeats_headline: Descriptions frequently repeat headlines, leading to redundant copy and reduced clarity.
- `fail` `skeptic_critic` `search_model_skeptic_critic_hard_fail`: search_rsa_combination_quality_low: Multiple ad groups have low RSA combination quality, indicating lost category/product agency, repetition, or claim risk in generated ad variations.
- `fail` `skeptic_critic` `search_model_skeptic_critic_hard_fail`: search_portfolio_phrase_repetition: Repetitive phrasing across the portfolio (e.g., 'sms app', 'sms review') reduces overall distinctness.
- `fail` `skeptic_critic` `search_model_skeptic_critic_hard_fail`: search_rsas_per_ad_group_low: Insufficient unique RSA assets per ad group limits testing and optimization potential.

## Model Reviews

- `blind_serp_scan`: reject via google/gemini-2.5-flash
  - Fixes: Address and resolve RSA combinations that lose product agency, repeat copy, or create claim risk.; Rewrite descriptions to provide unique value and avoid repeating headline content.; Diversify headline phrasing to improve distinctness and reduce reliance on generic terms.
- `intent_fit_critic`: reject via google/gemini-2.5-flash
  - Fixes: Rewrite descriptions to provide unique value, proof, or motivation, avoiding direct repetition of headlines.; Improve RSA combination quality by reviewing and refining asset pairings to ensure they add value and avoid redundancy or claim risk.; Add more high-quality RSAs to ad groups, especially for 'sms_classifier_brand_exact' and 'sms_permissions_trust_holdout', to meet Google's recommendation of at least 2 Good/Excellent RSAs.
- `skeptic_critic`: reject via google/gemini-2.5-flash
  - Fixes: Rewrite descriptions to provide new, complementary information or motivation, avoiding direct repetition of headlines.; Expand RSA asset libraries within each ad group to include more unique headlines and descriptions, aiming for at least 2 Good/Excellent RSAs per group.; Review and revise headline/description combinations to ensure they create strong, distinct messages and avoid redundancy or diluted product agency.
- `combination_critic`: ship via google/gemini-2.5-flash
