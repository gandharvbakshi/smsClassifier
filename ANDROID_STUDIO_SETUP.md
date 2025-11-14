# Android Studio Setup Guide

## Step-by-Step Instructions

### 1. **Gradle Sync** (First Time)

When you first open the project, Android Studio will prompt you to sync Gradle:

1. **Click "Sync Now"** in the notification bar at the top
2. Or go to: **File → Sync Project with Gradle Files**
3. Wait for sync to complete (may take 2-5 minutes on first run)

**What it does:**
- Downloads dependencies (ONNX Runtime, Compose, Room, etc.)
- Sets up the build configuration
- Validates project structure

### 2. **Verify Models Are in Place**

Check that ONNX models are in the assets folder:

1. In **Project** view (left sidebar), navigate to:
   ```
   app → src → main → assets
   ```
2. You should see:
   - ✅ `model_phishing.onnx` (~0.68 MB)
   - ✅ `model_isotp.onnx` (~0.68 MB)
   - ✅ `model_intent.onnx` (~3.07 MB)
   - ✅ `model_metadata.json`
   - ✅ `feature_map.json`
   - ✅ `sample_test_data.json`

**If models are missing:**
- Run the copy script: `copy_models.ps1` (Windows) or `copy_models.sh` (Mac/Linux)
- Or manually copy from `../android_model_exports/` to `app/src/main/assets/`

### 3. **Fix Any Build Errors**

Common issues and fixes:

#### Issue: "Unresolved reference" errors
**Fix:** Wait for Gradle sync to complete, then:
- **File → Invalidate Caches → Invalidate and Restart**

#### Issue: Kotlin version mismatch
**Fix:** The project uses Kotlin 1.9.20. If you see version errors:
- **File → Project Structure → Project → Kotlin Version** → Set to 1.9.20

#### Issue: Missing dependencies
**Fix:** 
- **File → Sync Project with Gradle Files**
- Check `app/build.gradle.kts` has all dependencies

### 4. **Set Up Device/Emulator**

#### Option A: Physical Device
1. Enable **Developer Options** on your Android phone:
   - Settings → About Phone → Tap "Build Number" 7 times
2. Enable **USB Debugging**:
   - Settings → Developer Options → USB Debugging
3. Connect phone via USB
4. Allow USB debugging when prompted

#### Option B: Emulator
1. **Tools → Device Manager**
2. Click **Create Device**
3. Select a device (e.g., Pixel 5)
4. Download a system image (API 26+ recommended)
5. Click **Finish**

### 5. **Build the Project**

1. Click **Build → Make Project** (or press `Ctrl+F9`)
2. Wait for build to complete
3. Check **Build** tab at bottom for any errors

**Expected build time:** 1-3 minutes (first build), 30 seconds (subsequent builds)

### 6. **Run the App**

1. Select your device/emulator from the device dropdown (top toolbar)
2. Click **Run** button (▶) or press `Shift+F10`
3. Wait for app to install and launch

**First launch:**
- App will request SMS permission
- Click **Allow** when prompted
- If permission denied, go to Settings → Apps → SMS Classifier → Permissions → SMS → Allow

### 7. **Test the App**

#### Quick Test Checklist:
- [ ] App launches without crashing
- [ ] Inbox screen shows (may be empty initially)
- [ ] Settings screen accessible
- [ ] Can toggle inference mode
- [ ] No errors in Logcat

#### Test with Sample Data:
1. Send yourself a test SMS (or use emulator SMS tool)
2. Check if message appears in inbox within 1-2 seconds
3. Verify badges appear (Safe/Suspicious/Phishing/OTP)
4. Tap a message to see detail screen
5. Check "Report as Wrong" button works

### 8. **Check Logcat for Errors**

1. **View → Tool Windows → Logcat** (or bottom panel)
2. Filter by: `SMSClassifier` or `OnDeviceClassifier`
3. Look for:
   - ✅ "Models loaded in XXXms" (should be < 800ms)
   - ✅ "Classification successful"
   - ❌ Any red errors (report these)

### 9. **Common Issues & Fixes**

#### App crashes on launch
- Check Logcat for error messages
- Verify models are in assets folder
- Check AndroidManifest.xml has correct permissions

#### Models not loading
- Verify `.onnx` files are in `app/src/main/assets/`
- Check file sizes match (0.68 MB, 0.68 MB, 3.07 MB)
- Look for ONNX loading errors in Logcat

#### Permission denied
- Go to: Settings → Apps → SMS Classifier → Permissions
- Enable "SMS" permission
- Restart app

#### No messages showing
- Check if you have SMS messages on device
- Verify SMS permission is granted
- Check WorkManager is running (Settings → Apps → SMS Classifier → Battery → Unrestricted)

### 10. **Next Steps**

Once the app is running:

1. **Test Classification:**
   - Send test SMS messages
   - Verify classification appears quickly
   - Check badges and reasons

2. **Test Filters:**
   - Use filter chips (All, OTP, Phishing, Needs Review)
   - Verify counts update correctly

3. **Test Settings:**
   - Toggle between On-Device and Server inference
   - Export labels (creates CSV file)

4. **Debug Mode:**
   - Enable dev flags to see raw features
   - Check inference times per message

## Troubleshooting

### Build Fails
- **File → Invalidate Caches → Invalidate and Restart**
- **File → Sync Project with Gradle Files**
- Check internet connection (needed for dependencies)

### App Won't Install
- Uninstall existing version: `adb uninstall com.smsclassifier.app`
- Clean build: **Build → Clean Project**
- Rebuild: **Build → Rebuild Project**

### Models Not Found
- Verify files exist: `app/src/main/assets/model_*.onnx`
- Check file sizes are correct
- Re-copy models if needed

## Getting Help

If you encounter issues:
1. Check Logcat for error messages
2. Verify all steps above are completed
3. Check `QUICKSTART.md` for additional details
4. Review `PROJECT_SUMMARY.md` for architecture details

## Success Indicators

You'll know everything is working when:
- ✅ App builds without errors
- ✅ App launches and shows inbox screen
- ✅ SMS permission is granted
- ✅ New SMS appears with badges within 1-2 seconds
- ✅ Logcat shows "Models loaded" message
- ✅ Classification works (badges appear)

Good luck! 🚀

