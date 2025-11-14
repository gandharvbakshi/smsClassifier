# Quick Start Guide

## Prerequisites

- Android Studio Hedgehog (2023.1.1) or later
- Android SDK 26+ (Android 8.0+)
- Kotlin 1.9.20+

## Setup Steps

### 1. Copy Model Files

**Windows (PowerShell):**
```powershell
cd android_sms_classifier
.\copy_models.ps1
```

**Linux/Mac:**
```bash
cd android_sms_classifier
chmod +x copy_models.sh
./copy_models.sh
```

This copies:
- `model_phishing.onnx`
- `model_isotp.onnx`
- `model_intent.onnx`
- `model_metadata.json` (optional)

### 2. Open Project

1. Open Android Studio
2. File → Open → Select `android_sms_classifier` folder
3. Wait for Gradle sync to complete

### 3. Grant Permissions

The app requires SMS read permission. On first launch:
- Grant SMS permission when prompted
- Or manually: Settings → Apps → SMS Classifier → Permissions → SMS

### 4. Build & Run

1. Connect Android device (API 26+) or start emulator
2. Click Run (▶) or press `Shift+F10`
3. App will install and launch

## Testing

### Sample Test Data

The app includes `sample_test_data.json` in assets with 4 test messages:
- ICICI Bank OTP (should be OTP, not phishing)
- Amazon login OTP (should be OTP, APP_LOGIN_OTP)
- Phishing message (should be phishing)
- Swiggy delivery OTP (should be OTP, DELIVERY_OR_SERVICE_OTP)

### Dev Build Features

Enable in `BuildConfig`:
- Show raw features
- Show inference time
- Toggle heuristic-only mode

## Troubleshooting

### Models Not Loading

- Check `app/src/main/assets/` contains all 3 `.onnx` files
- Check file sizes match exported models (~0.68MB, ~0.68MB, ~3MB)
- Check logcat for ONNX loading errors

### Permission Denied

- Go to Settings → Apps → SMS Classifier → Permissions
- Enable "SMS" permission
- Restart app

### Classification Not Working

- Check logcat for errors
- Verify ONNX Runtime is included in dependencies
- Check WorkManager is scheduling jobs (Settings → Apps → SMS Classifier → Battery → Unrestricted)

## Next Steps

1. Test with real SMS messages
2. Export feedback labels for retraining
3. Tune model thresholds in `OnDeviceClassifier`
4. Add server endpoint URL in `ServerClassifier`

