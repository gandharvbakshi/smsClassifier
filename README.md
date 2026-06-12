# SMS Classifier Android App

A Kotlin/Jetpack Compose Android SMS app that sorts messages, detects OTPs, and shows scam warnings when trial or Pro cloud checks are available.

## Current Classification Path

- **Free/basic mode:** local heuristic OTP sorting runs on the phone. SMS content is stored in the app database on the device.
- **Trial/Pro mode:** cloud classification can be used for scam warnings, code purpose, risk scores, and explanation reasons. The app sends the SMS body and sender over HTTPS to the backend `/classify` API for real-time classification.
- **Feedback uploads:** optional and off by default. When enabled, misclassification reports upload a redacted message body for model improvement.
- **Links in SMS:** SMS bodies are rendered as plain text in the app; URL text is not directly clickable from the message body.

Routine cloud-classification requests are intended for real-time processing and are not retained after the response. Optional feedback uploads are a separate flow and can be retained for review/model improvement.

## Setup

1. Build and run:
   ```bash
   ./gradlew assembleDebug
   ```

2. Optional legacy ONNX assets:
   ```bash
   cp android_model_exports/model_phishing.onnx app/src/main/assets/
   cp android_model_exports/model_isotp.onnx app/src/main/assets/
   cp android_model_exports/model_intent.onnx app/src/main/assets/
   ```

## Features

- **Inbox Screen:** Paginated list of SMS with search and filters.
- **Detail Screen:** Raw SMS, OTP intent, risk badges, scam score, reasons, and correction reporting.
- **Background Classification:** WorkManager processes new SMS automatically.
- **Pro/Trial:** Cloud scam warnings and code-purpose explanations.
- **Privacy Controls:** Analytics, crash reports, and redacted feedback uploads can be controlled from Settings.

## Architecture

- **Room Database:** Local storage for messages and feedback.
- **WorkManager:** Background classification jobs.
- **Jetpack Compose:** Modern UI framework.
- **Paging:** Efficient list rendering.
- **Backend API:** Cloud classification and entitlement/feedback endpoints.
- **ONNX Runtime:** Legacy on-device classifier code remains in the app, but the active worker path is local heuristics plus gated cloud classification.

## Testing

Run JVM unit tests:
```bash
./gradlew testDebugUnitTest
```

