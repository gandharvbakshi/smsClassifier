# Privacy Policy for SMS Classifier

**Last Updated:** May 5, 2026

## Introduction

SMS Classifier ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our SMS Classifier mobile application ("the App").

## Information We Collect

### SMS Messages
- **What we collect:** The content of SMS messages received on your device, including message text and sender phone numbers.
- **Why we collect it:** To classify messages as OTP, phishing, or general messages for your convenience and security.
- **How we use it:** Messages are processed locally on your device or sent to our secure classification service to determine message type and potential security risks.

### Phone Numbers
- **What we collect:** Phone numbers from SMS senders.
- **Why we collect it:** To help identify and categorize messages.
- **How we use it:** Phone numbers are used only for message classification and are not stored or shared.

## Data Processing

### On-Device Processing
- Classification can be performed entirely on your device using local machine learning models.
- When processed on-device, your SMS content never leaves your device.
- No data is transmitted to external servers when using on-device classification.

### Cloud Processing (Optional)
- If you enable server-based classification, SMS content is sent to our secure API endpoint hosted on Google Cloud Run.
- Messages are sent over encrypted HTTPS connections.
- Classification requests are processed in real-time. **Normally** SMS content sent only for classification is **not retained** on our servers after processing.
- Misclassification feedback (see below), when you explicitly opt in, is **stored separately** for improving the classifier — not limited to ephemeral processing.

### Misclassification Feedback (Optional)
- This feature is **off by default** (Settings → Feedback → "Help improve classification").
- When it is enabled and you tap **"Report as wrong"**, the app sends to our server over HTTPS:
  - The SMS text and sender
  - The predicted labels shown in the app (OTP, intent, phishing, scores when available)
  - Your correction note if you entered one
  - App version and an anonymous random install identifier (UUID)
- These items may be **stored on our servers indefinitely** so we can review mistakes and train or tune future models (including machine learning pipelines).
- You may email us anytime to ask that your submitted feedback tied to your install id or account inquiry be deleted, subject to technical limits (aggregated artifacts may persist).

### Local Storage
- SMS messages are stored locally on your device in an encrypted database.
- This primary message store remains on your device unless you use optional features that send SMS content to our servers (server-based classification or Help improve classification).
- You can delete all stored messages at any time through the app settings.

## Permissions

The App requires the following permissions:

- **READ_SMS:** Required to read and classify incoming SMS messages.
- **RECEIVE_SMS:** Required to receive SMS notifications and automatically classify new messages.
- **SEND_SMS:** Required if you choose to send SMS messages through the app.
- **WRITE_SMS:** Required to save classified messages locally on your device.
- **INTERNET:** Required for optional server-based classification / optional uploading of misclassification reports when you enable "Help improve classification".
- **ACCESS_NETWORK_STATE:** Required to check network connectivity for server-based classification.

## Data Security

We implement the following security measures:

- **Encryption in Transit:** All API communications use HTTPS encryption (TLS 1.2+).
- **Encryption at Rest:** Local database is encrypted using Android's built-in encryption.
- **No Data Sharing:** We do not share your SMS content or phone numbers with third parties.
- **Secure Infrastructure:** Server-based processing uses Google Cloud Run with industry-standard security practices.

## Third-Party Services

### Google Cloud Run
- Our classification service and optional misclassification feedback ingestion are hosted on Google Cloud Run (or related Google Cloud services we operate).
- Routine classification traffic may be processed without long-term storage; **misclassification feedback you opt into** may be stored there for training and quality review.
- Google's privacy policy applies to their infrastructure: [Google Privacy Policy](https://policies.google.com/privacy)

### Groq API (for Intent Classification)
- When an OTP is detected, we may use Groq's API for advanced intent classification.
- Only OTP messages are sent to Groq, and messages are not stored by Groq.
- Groq's privacy policy applies: [Groq Privacy Policy](https://groq.com/privacy-policy)

## Data Retention

- **On-Device:** Messages are stored locally until you delete them or uninstall the app.
- **Server-Side (classification):** SMS content sent **only** for real-time classification through the optional server path is normally not retained after processing.
- **Misclassification feedback:** If you turn on **Help improve classification** and submit a report, the associated SMS text, sender, labels, and your note may be **retained indefinitely** on our servers for model improvement unless you request deletion (see Contact Us).

## Your Rights

You have the following rights regarding your data:

- **Access:** You can view all stored messages within the app.
- **Deletion:** You can delete individual messages or all messages at any time through the app.
- **Uninstall:** Uninstalling the app removes all locally stored data from your device.
- **Opt-Out:** You can disable server-based classification and use only on-device processing. You can disable **Help improve classification** in Settings at any time to stop sending misclassification reports to our servers.

## Children's Privacy

Our App is not intended for children under the age of 13. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us immediately.

## Changes to This Privacy Policy

We may update this Privacy Policy from time to time. We will notify you of any changes by:
- Updating the "Last Updated" date at the top of this policy
- Posting a notice in the app (for significant changes)

Your continued use of the App after any changes constitutes acceptance of the updated Privacy Policy.

## Contact Us

If you have questions or concerns about this Privacy Policy or our data practices, please contact us:

- **Email:** gandharv@musicaigeneration.com

## Compliance

This Privacy Policy complies with:
- Google Play Store requirements
- General Data Protection Regulation (GDPR) for EU users
- California Consumer Privacy Act (CCPA) for California users

---

**Note:** This privacy policy is specific to the SMS Classifier app. By using the App, you agree to the collection and use of information in accordance with this policy.

