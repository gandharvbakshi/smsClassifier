# SMS Classifier Android App

A Kotlin/Jetpack Compose Android app for classifying SMS messages as OTP, phishing, or regular messages using on-device ML models.

## Setup

1. **Copy ONNX models to assets:**
   ```bash
   cp android_model_exports/model_phishing.onnx app/src/main/assets/
   cp android_model_exports/model_isotp.onnx app/src/main/assets/
   cp android_model_exports/model_intent.onnx app/src/main/assets/
   ```

2. **Build and run:**
   ```bash
   ./gradlew assembleDebug
   ```

## Features

- **Inbox Screen**: Paginated list of SMS with search and filters (All, OTP, Phishing, Needs Review)
- **Detail Screen**: Raw SMS, badges, reasons, share advice
- **Settings Screen**: Toggle on-device vs server inference, export labels
- **Background Classification**: WorkManager job processes new SMS automatically
- **Privacy**: All processing on-device by default, PII hashing for server mode

## Architecture

- **Room Database**: Local storage for messages and feedback
- **ONNX Runtime**: On-device ML inference
- **WorkManager**: Background classification jobs
- **Jetpack Compose**: Modern UI framework
- **Paging**: Efficient list rendering

## Testing

The app includes dev build flags to show:
- Raw features
- Inference time per message
- Heuristic-only mode toggle

## Model Files

Place these files in `app/src/main/assets/`:
- `model_phishing.onnx`
- `model_isotp.onnx`
- `model_intent.onnx`
- `feature_map.json`

