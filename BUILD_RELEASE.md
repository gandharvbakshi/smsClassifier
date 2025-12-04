# Building Release Version 1.0.3

## Prerequisites

1. ✅ **Keystore configured**: Ensure `keystore.properties` exists in `android_sms_classifier/` folder
2. ✅ **Version updated**: Version is now `1.0.3` (versionCode `4`)

## Build Commands

### Option 1: Build Android App Bundle (AAB) - **Recommended for Google Play**

**Windows (PowerShell):**
```powershell
cd android_sms_classifier
.\gradlew clean bundleRelease
```

**Linux/Mac:**
```bash
cd android_sms_classifier
./gradlew clean bundleRelease
```

**Output Location:**
- `app/build/outputs/bundle/release/app-release.aab`

---

### Option 2: Build APK (For testing/alternative distribution)

**Windows (PowerShell):**
```powershell
cd android_sms_classifier
.\gradlew clean assembleRelease
```

**Linux/Mac:**
```bash
cd android_sms_classifier
./gradlew clean assembleRelease
```

**Output Location:**
- `app/build/outputs/apk/release/app-release.apk`

---

## Verify Build Success

### Check AAB was created:
```powershell
# Windows PowerShell
Test-Path app\build\outputs\bundle\release\app-release.aab
dir app\build\outputs\bundle\release\app-release.aab

# Windows CMD
dir app\build\outputs\bundle\release\app-release.aab

# Linux/Mac
ls -lh app/build/outputs/bundle/release/app-release.aab
```

### Check APK was created:
```powershell
# Windows PowerShell
Test-Path app\build\outputs\apk\release\app-release.apk
dir app\build\outputs\apk\release\app-release.apk

# Linux/Mac
ls -lh app/build/outputs/apk/release/app-release.apk
```

---

## What Each Command Does

### `clean`
- Removes previous build artifacts
- Ensures a fresh build
- Recommended before release builds

### `bundleRelease`
- Builds Android App Bundle (AAB)
- Optimized format for Google Play
- Google Play generates optimized APKs for each device
- **Use this for Google Play uploads**

### `assembleRelease`
- Builds standalone APK
- Can be installed directly on devices
- Larger file size (includes all architectures)
- **Use for direct testing/alternative distribution**

---

## Upload to Google Play Console

1. Go to [Google Play Console](https://play.google.com/console)
2. Select your app
3. Go to **Production** (or **Internal/Closed/Open testing**)
4. Click **Create new release**
5. Upload `app-release.aab` from:
   - `android_sms_classifier/app/build/outputs/bundle/release/app-release.aab`
6. Add release notes (e.g., "Bug fixes: OnePlus device compatibility, notification improvements, UI enhancements")
7. Review and submit

---

## Troubleshooting

### Build fails with "keystore.properties not found"
- Make sure `keystore.properties` exists in `android_sms_classifier/` folder
- Verify the file contains correct passwords and paths

### Build succeeds but APK/AAB is not signed
- Check that `keystore.properties` is properly configured
- Verify the keystore file path is correct
- Ensure passwords match what you set when creating the keystore

### "Task 'clean' not found" or Gradle errors
- Make sure you're in the `android_sms_classifier` directory
- Try: `gradlew.bat clean bundleRelease` (Windows) or `./gradlew clean bundleRelease` (Linux/Mac)

### Build is slow
- First build can take 2-5 minutes (downloads dependencies)
- Subsequent builds are faster
- Clean builds take longer but ensure everything is fresh

---

## File Sizes (Expected)

- **AAB**: ~4-6 MB (varies based on models and resources)
- **APK**: ~5-8 MB (includes all architectures in one file)

---

## Quick Reference

**Build AAB for Google Play:**
```powershell
cd android_sms_classifier
.\gradlew clean bundleRelease
```

**Build APK for testing:**
```powershell
cd android_sms_classifier
.\gradlew clean assembleRelease
```

**Find your release file:**
- AAB: `app\build\outputs\bundle\release\app-release.aab`
- APK: `app\build\outputs\apk\release\app-release.apk`

---

Good luck with your release! 🚀

