# Search Copy Eval Report

Decision: **pass**

## Summary

- `ad_groups_checked`: 3
- `rsas_checked`: 4
- `non_bid_ad_groups`: 1
- `failure_count`: 0
- `warning_count`: 4
- `keyword_metrics_status`: available
- `keyword_metrics_source`: keyword_ideas_fraud_only.json
- `keyword_metric_rows`: 200 / 200

## Portfolio Scores

- `keyword_metric_quality`: 5/5
- `portfolio_distinctness`: 4/5
- `coverage`: 5/5
- `claim_safety`: 5/5
- `combination_quality`: 5/5

## RSA Scores

- `default_sms_organizer_high_relevance/default_sms_organizer_recovery_v9` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `default_sms_organizer_high_relevance/default_sms_organizer_recovery_v9_b` Ad Strength: Excellent (5/5); intent=5, register=5, category=5, distinctness=5, message_match=5, claim=5, combinations=5
- `scam_otp_review_high_relevance/scam_otp_review_recovery_v9` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=4, message_match=5, claim=5, combinations=5
- `scam_otp_review_high_relevance/scam_otp_review_recovery_v9_b` Ad Strength: Good (4/5); intent=5, register=5, category=5, distinctness=4, message_match=5, claim=5, combinations=5

## Issues

- `warn` `scam_otp_review_high_relevance/scam_otp_review_recovery_v9` `search_headline_start_repetition`: More than two headlines start with: otp
- `warn` `scam_otp_review_high_relevance/scam_otp_review_recovery_v9` `search_keyword_coverage_low`: Include the primary query or close variant in 2-3 readable headlines.
- `warn` `scam_otp_review_high_relevance/scam_otp_review_recovery_v9_b` `search_description_repeats_headline`: Description mostly repeats a headline instead of adding proof or motivation: 'Cloud scam checks need Pro and network access; the trial lasts 14 days.'
- `warn` `portfolio` `search_portfolio_phrase_repetition`: Repeated portfolio headline phrase(s) reduce distinctness: android sms, sms app.

## Model Reviews

- `blind_serp_scan`: ship via google/gemini-2.5-flash
  - Fixes: Consider further refining headlines to enhance distinctness beyond common 'SMS app' and 'Android app' phrases, if unique features allow.
- `intent_fit_critic`: revise via google/gemini-2.5-flash
  - Fixes: Address the 'search_headline_start_repetition' in 'scam_otp_review_high_relevance' by varying headline beginnings to improve distinctness and ad strength.; Improve 'search_keyword_coverage_low' for 'privacy_trust_research_hold' by incorporating 'private sms app' or a close variant into 2-3 headlines.; Revise descriptions in 'scam_otp_review_high_relevance' to avoid repeating headlines and instead add unique proof, motivation, or complementary information.
- `skeptic_critic`: revise via google/gemini-2.5-flash
  - Fixes: Diversify headline phrasing to reduce repetition of common terms like 'Android SMS' and 'SMS App' to improve distinctness, as noted by the portfolio phrase repetition warning.; Explore more unique benefits or features beyond basic organization to stand out.
- `combination_critic`: ship via google/gemini-2.5-flash
  - Fixes: Vary headline starts to reduce repetition of 'OTP' across the portfolio.; Address 'android sms' and 'sms app' portfolio phrase repetition by finding synonyms or more specific phrasing.
