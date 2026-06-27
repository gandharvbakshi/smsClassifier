# Search Copy Eval Report

Decision: **pass**

## Summary

- `ad_groups_checked`: 7
- `rsas_checked`: 12
- `failure_count`: 0
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
