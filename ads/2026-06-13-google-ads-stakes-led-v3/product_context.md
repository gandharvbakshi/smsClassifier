# SMS Classifier Product Context

SMS Classifier is an Android SMS inbox and classification helper. It can become the default SMS app so it can receive, read, send, and organize SMS on the user's phone.

The strongest acquisition value is not generic inbox organization. The highest-stakes hook is that the app can show purpose hints for OTPs, so a user can notice when a caller's story does not match what the code appears to authorize.

## Top Product Jobs

1. Identifies OTP messages and groups them into an OTP-focused inbox.
2. Shows OTP intent/purpose hints when classifier data supports it.
3. Highlights sensitivity hints such as do-not-share situations.
4. Classifies messages into OTP, suspicious, review-needed, and general buckets.
5. Flags phishing or risky-looking message signals when classification data supports it.
6. Lets users copy OTPs quickly from message surfaces.
7. Helps users search and manage SMS conversations.
8. Stores messages locally so the inbox can work on-device.
9. Can use cloud classification during trial/Pro access for richer explanations.
10. Provides data controls such as export/delete local data from Settings.

## Differentiation Thesis

Stock SMS apps show message text. SMS Classifier can add classification labels and purpose/risk signals. The defensible top-funnel differentiator is the OTP-purpose mismatch moment: the SMS itself may be genuine, but the social context can be false.

## Claim Boundaries

Use decision-aid language: helps, highlights, shows a signal, easier to review. Do not claim that the app blocks fraud, guarantees safety, catches every scam, or that messages never leave the device.

## Evidence

- android_sms_classifier/store_assets/store-listing-text.md
- android_sms_classifier/app/src/main/assets/model_metadata.json
- android_sms_classifier/app/src/main/java/com/smsclassifier/app/classification/Prediction.kt
- android_sms_classifier/app/src/main/java/com/smsclassifier/app/classification/HeuristicOtpClassifier.kt
- Owner correction in this thread: OTP intent is a fraud/social-engineering avoidance hook, not merely usability.
