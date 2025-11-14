# Fix Gradle Error: fileCollection Method Not Found

## Problem
```
Unable to find method 'org.gradle.api.file.FileCollection 
org.gradle.api.artifacts.Configuration.fileCollection(org.gradle.api.specs.Spec)'
```

This happens because:
1. Gradle daemon is still running with old version (9.0-milestone-1)
2. Gradle cache is corrupted
3. kapt plugin version mismatch

## Solution (Do ALL Steps)

### Step 1: Close Android Studio
**Completely close Android Studio** - don't just minimize it.

### Step 2: Stop Gradle Daemons

**Option A: Use PowerShell Script (Easiest)**
```powershell
cd "D:\Projects\SMS datasets and project\android_sms_classifier"
.\stop_gradle.ps1
```

**Option B: Manual Commands**
```powershell
# Stop Gradle daemons
cd "D:\Projects\SMS datasets and project\android_sms_classifier"
.\gradlew.bat --stop

# Kill all Java processes (if Gradle still running)
taskkill /F /IM java.exe
```

### Step 3: Clear Gradle Cache

**Delete these folders:**
```powershell
# Gradle user cache
Remove-Item -Recurse -Force "$env:USERPROFILE\.gradle\caches"

# Project build folders
cd "D:\Projects\SMS datasets and project\android_sms_classifier"
Remove-Item -Recurse -Force ".gradle" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "app\build" -ErrorAction SilentlyContinue
```

### Step 4: Verify Gradle Wrapper Version

Check `gradle/wrapper/gradle-wrapper.properties`:
```properties
distributionUrl=https\://services.gradle.org/distributions/gradle-8.2-bin.zip
```

Should be **Gradle 8.2**, NOT 9.0-milestone-1.

### Step 5: Reopen Android Studio

1. **Open Android Studio**
2. **File → Invalidate Caches...**
   - Check "Clear file system cache and Local History"
   - Click "Invalidate and Restart"
3. Wait for Android Studio to restart

### Step 6: Sync Project

1. **File → Sync Project with Gradle Files**
2. Wait for sync to complete (may take 2-5 minutes)
3. Check for any errors in the **Build** tab

### Step 7: Build

1. **Build → Clean Project**
2. **Build → Make Project** (or `Ctrl+F9`)

## If Still Failing

### Check Gradle Version
In Android Studio terminal:
```bash
.\gradlew.bat --version
```

Should show: **Gradle 8.2**

### Force Gradle Wrapper Update
```bash
.\gradlew.bat wrapper --gradle-version 8.2
```

### Check Android Gradle Plugin
In `build.gradle.kts` (root):
```kotlin
id("com.android.application") version "8.2.0" apply false
```

Should be **8.2.0**, NOT 8.13.1.

## Verification

After all steps, you should see:
- ✅ Gradle sync completes without errors
- ✅ No "fileCollection" method errors
- ✅ Build succeeds
- ✅ `gradlew --version` shows Gradle 8.2

## Still Having Issues?

1. **Delete `.idea` folder** (Android Studio will regenerate)
2. **Re-import project** in Android Studio
3. **Check internet connection** (needed to download Gradle)

## Quick Reference

**Correct Versions:**
- Gradle: **8.2**
- Android Gradle Plugin: **8.2.0**
- Kotlin: **1.9.20**
- kapt: **1.9.20** (matches Kotlin version)

