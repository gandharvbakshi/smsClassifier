# Google Play Store Deployment Plan

## 1. Security Audit & Fixes

### 🔴 Critical Security Issues Found

#### 1.1 Cleartext Traffic Enabled
**Location:** `app/src/main/AndroidManifest.xml:26`
```xml
android:usesCleartextTraffic="true"
```
**Risk:** Allows unencrypted HTTP connections, which can be intercepted.
**Fix:** Remove this line (HTTPS is already used for Cloud Run).

#### 1.2 Network Security Config for Emulator
**Location:** `app/src/main/res/xml/network_security_config.xml`
**Risk:** Allows cleartext to emulator IP (10.0.2.2). Should be debug-only.
**Fix:** Create separate configs for debug/release builds.

#### 1.3 ProGuard/R8 Disabled
**Location:** `app/build.gradle.kts:33`
```kotlin
isMinifyEnabled = false
```
**Risk:** Makes reverse engineering easier, exposes code structure.
**Fix:** Enable R8 with proper ProGuard rules.

#### 1.4 Debug Logging in Production
**Location:** Multiple files (ServerClassifier, ClassificationWorker, etc.)
**Risk:** Logs may contain SMS content, sender numbers, API URLs.
**Fix:** Gate all logging behind `BuildConfig.DEBUG` or remove for release.

#### 1.5 Cloud Run URL Exposure
**Location:** `app/build.gradle.kts:24-28`
**Status:** ✅ **ACCEPTABLE** - This is a public API endpoint, no secrets exposed.
**Note:** The URL is public anyway, but consider using environment variables for flexibility.

### ✅ Security Strengths

- ✅ No API keys in Android app (GROQ_API_KEY is backend-only)
- ✅ No hardcoded secrets
- ✅ HTTPS-only for production API calls
- ✅ Proper permission declarations
- ✅ FileProvider correctly configured (not exported)
- ✅ Content providers have proper permissions

---

## 2. Security Fixes Implementation

### Fix 1: Remove Cleartext Traffic (Production)

**File:** `app/src/main/AndroidManifest.xml`
- Remove `android:usesCleartextTraffic="true"` from `<application>` tag
- Keep `android:networkSecurityConfig` but make it debug-only

### Fix 2: Debug-Only Network Security Config

**Create:** `app/src/debug/res/xml/network_security_config.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
    </domain-config>
</network-security-config>
```

**Create:** `app/src/release/res/xml/network_security_config.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- Production: HTTPS only -->
</network-security-config>
```

**Update:** `app/src/main/AndroidManifest.xml`
- Remove `android:usesCleartextTraffic="true"` (line 26)

### Fix 3: Enable R8/ProGuard

**File:** `app/build.gradle.kts`
```kotlin
buildTypes {
    release {
        isMinifyEnabled = true  // Changed from false
        isShrinkResources = true  // Add this
        proguardFiles(
            getDefaultProguardFile("proguard-android-optimize.txt"),
            "proguard-rules.pro"
        )
    }
}
```

**Update:** `app/proguard-rules.pro`
```proguard
# Keep app classes
-keep class com.smsclassifier.app.** { *; }

# Keep ONNX Runtime
-keep class ai.onnxruntime.** { *; }

# Keep Kotlin serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Keep Room entities
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-keep class * extends androidx.room.RoomDatabase$Callback

# Keep WorkManager
-keep class androidx.work.** { *; }
-dontwarn androidx.work.**

# Remove debug logging in release
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}

# Keep BuildConfig
-keep class com.smsclassifier.app.BuildConfig { *; }
```

### Fix 4: Remove/Gate Debug Logging

**Option A: Remove all Log statements (Recommended)**
- Search and remove all `Log.d()`, `Log.w()`, `Log.e()` calls
- Or use a logging utility that gates on `BuildConfig.DEBUG`

**Option B: Create Logging Utility**
**Create:** `app/src/main/java/com/smsclassifier/app/util/AppLog.kt`
```kotlin
package com.smsclassifier.app.util

import android.util.Log
import com.smsclassifier.app.BuildConfig

object AppLog {
    fun d(tag: String, message: String, throwable: Throwable? = null) {
        if (BuildConfig.DEBUG) {
            if (throwable != null) Log.d(tag, message, throwable)
            else Log.d(tag, message)
        }
    }
    
    fun w(tag: String, message: String, throwable: Throwable? = null) {
        if (BuildConfig.DEBUG) {
            if (throwable != null) Log.w(tag, message, throwable)
            else Log.w(tag, message)
        }
    }
    
    fun e(tag: String, message: String, throwable: Throwable? = null) {
        // Always log errors, even in release
        if (throwable != null) Log.e(tag, message, throwable)
        else Log.e(tag, message)
    }
}
```

Then replace all `Log.d()` with `AppLog.d()`, etc.

**Critical:** Remove logs that contain:
- SMS message content (`input.text`)
- Sender phone numbers (`input.sender`)
- Full API URLs with parameters

### Fix 5: Verify No Sensitive Data in BuildConfig

**Current:** Only `SERVER_API_BASE_URL` (public endpoint) ✅
**Action:** No changes needed.

---

## 3. Google Play Console Setup

### 3.1 App Signing Key

#### Option A: Use Google Play App Signing (Recommended)
**Benefits:**
- Google manages your signing key
- Automatic key rotation
- Protection against key loss
- Smaller APK size (App Bundle optimization)

**Steps:**
1. **Generate Upload Key** (for signing your uploads):
   ```bash
   keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
   - Store password securely (use a password manager)
   - Save `upload-keystore.jks` in a secure location (NOT in git)
   - Create `keystore.properties` (add to `.gitignore`):
     ```
     storePassword=your_store_password
     keyPassword=your_key_password
     keyAlias=upload
     storeFile=../upload-keystore.jks
     ```

2. **Configure Gradle for Signing:**
   **Create:** `android_sms_classifier/keystore.properties` (add to `.gitignore`)
   ```
   storePassword=your_store_password
   keyPassword=your_key_password
   keyAlias=upload
   storeFile=upload-keystore.jks
   ```

   **Update:** `app/build.gradle.kts`
   ```kotlin
   // Add at top level
   val keystorePropertiesFile = rootProject.file("keystore.properties")
   val keystoreProperties = Properties()
   if (keystorePropertiesFile.exists()) {
       keystoreProperties.load(FileInputStream(keystorePropertiesFile))
   }

   android {
       // ... existing config ...
       
       signingConfigs {
           create("release") {
               keyAlias = keystoreProperties["keyAlias"] as String?
               keyPassword = keystoreProperties["keyPassword"] as String?
               storeFile = keystoreProperties["storeFile"]?.let { file(it) }
               storePassword = keystoreProperties["storePassword"] as String?
           }
       }
       
       buildTypes {
           release {
               isMinifyEnabled = true
               isShrinkResources = true
               signingConfig = signingConfigs.getByName("release")
               proguardFiles(
                   getDefaultProguardFile("proguard-android-optimize.txt"),
                   "proguard-rules.pro"
               )
           }
       }
   }
   ```

   **Add to:** `android_sms_classifier/.gitignore`
   ```
   keystore.properties
   upload-keystore.jks
   *.jks
   ```

3. **First Upload:**
   - Upload your first AAB to Google Play Console
   - Google will generate the app signing key
   - You'll receive the app signing certificate (save it!)

#### Option B: Self-Managed Signing
**Not recommended** - You're responsible for key security and rotation.

### 3.2 Build Release App Bundle (AAB)

**Command:**
```bash
cd android_sms_classifier
./gradlew bundleRelease
```

**Output:** `app/build/outputs/bundle/release/app-release.aab`

**Note:** Google Play requires AAB format (not APK) for new apps.

### 3.3 Google Play Console Setup Steps

1. **Create New App**
   - Go to [Google Play Console](https://play.google.com/console)
   - Click "Create app"
   - Fill in:
     - **App name:** "SMS Classifier" (or your preferred name)
     - **Default language:** English (United States)
     - **App or game:** App
     - **Free or paid:** Free
     - **Declarations:** Check "This app contains ads" only if applicable

2. **App Access**
   - **All or some of your content is restricted:** Select "No" (unless you have age restrictions)

3. **Set Up App Content**
   - **Privacy Policy:** ⚠️ **REQUIRED** (see section 4)
   - **Data Safety:** ⚠️ **REQUIRED** (see section 5)
   - **Target Audience:** Select appropriate age group
   - **Content Rating:** Complete questionnaire (likely "Everyone" or "Teen")

4. **Upload AAB**
   - Go to "Production" → "Create new release"
   - Upload `app-release.aab`
   - Fill in "Release notes"
   - Click "Save" (don't publish yet)

5. **Store Listing**
   - **App name:** SMS Classifier
   - **Short description:** (80 chars max)
     ```
     Smart SMS classifier for OTP detection and phishing protection
     ```
   - **Full description:** (4000 chars max)
     ```
     SMS Classifier helps you identify and organize your SMS messages with intelligent classification.

     Features:
     • Automatic OTP detection and extraction
     • Phishing and scam message detection
     • Smart categorization (OTP, Phishing, General, Needs Review)
     • Copy OTP with one tap
     • Sensitivity badges for security awareness
     • Export misclassification logs for feedback

     Perfect for managing transaction OTPs, delivery codes, and keeping your messages organized while staying safe from phishing attempts.
     ```
   - **App icon:** 512x512 PNG (required)
   - **Feature graphic:** 1024x500 PNG (required)
   - **Screenshots:** 
     - Phone: At least 2, max 8 (16:9 or 9:16)
     - Tablet: Optional
   - **Categories:** Productivity or Tools

6. **Pricing & Distribution**
   - Set as "Free"
   - Select countries (or "All countries")
   - **Device compatibility:** Should auto-detect (minSdk 26)

---

## 4. Privacy Policy (REQUIRED)

### Why Required
- App requests SMS permissions (sensitive)
- App processes personal data (SMS content)
- Google Play requires privacy policy for apps with sensitive permissions

### What to Include

**Create:** `PRIVACY_POLICY.md` (or host on your website)

```markdown
# Privacy Policy for SMS Classifier

**Last updated:** [Date]

## Data Collection

SMS Classifier processes SMS messages on your device to classify them. We do NOT:

- Transmit SMS content to external servers (except for classification API calls)
- Store SMS messages on external servers
- Share your data with third parties
- Collect personal information

## Data Processing

- **On-Device Processing:** Classification can be performed entirely on your device using local machine learning models.
- **Optional Cloud Processing:** If you enable server-based classification, SMS content is sent to our secure API endpoint (hosted on Google Cloud Run) for classification only. Messages are not stored on the server.
- **Local Storage:** SMS messages are stored locally on your device in an encrypted database.

## Permissions

- **READ_SMS:** Required to read and classify incoming SMS messages
- **RECEIVE_SMS:** Required to receive SMS notifications
- **INTERNET:** Required only if you enable server-based classification

## Data Security

- All API communications use HTTPS encryption
- Local database is encrypted
- No data is shared with third parties

## Your Rights

You can:
- Disable server-based classification at any time
- Delete all stored messages from the app
- Uninstall the app to remove all local data

## Contact

For questions about this privacy policy, contact: [your-email@example.com]
```

### Hosting Options

1. **GitHub Pages** (Free)
   - Create a `gh-pages` branch
   - Upload `PRIVACY_POLICY.md` as `index.html` or `privacy-policy.html`
   - URL: `https://yourusername.github.io/repo-name/privacy-policy.html`

2. **Google Sites** (Free)
   - Create a simple site with the policy
   - URL: `https://sites.google.com/view/your-app-name/privacy-policy`

3. **Your Own Domain** (if you have one)

**Required URL format:** Must be publicly accessible HTTPS URL.

---

## 5. Data Safety Section (REQUIRED)

In Google Play Console → App Content → Data Safety, declare:

### Data Collected
- **Personal info:** Phone numbers (collected, not shared)
- **Messages:** SMS content (collected, not shared)

### Data Usage
- **App functionality:** SMS classification
- **Analytics:** None (unless you add analytics later)

### Data Sharing
- **Shared with third parties:** No
- **Collected data types:** Phone numbers, SMS messages

### Security Practices
- ✅ Data is encrypted in transit (HTTPS)
- ✅ Data is encrypted at rest (Room database encryption)
- ✅ Users can request data deletion (via app uninstall)

---

## 6. Pre-Launch Checklist

### Code Quality
- [ ] All security fixes applied (cleartext traffic, ProGuard, logging)
- [ ] Release build tested on physical device
- [ ] No debug code in release build
- [ ] Version code and version name updated
- [ ] ProGuard rules tested (app works after obfuscation)

### Google Play Requirements
- [ ] Privacy policy URL ready and accessible
- [ ] Data Safety section completed
- [ ] Content rating completed
- [ ] Store listing assets prepared (icon, screenshots, descriptions)
- [ ] App signing key generated and secured
- [ ] Release AAB built and tested

### Testing
- [ ] Test on Android 8.0+ (minSdk 26)
- [ ] Test on Android 14 (targetSdk 34)
- [ ] Test SMS receiving and classification
- [ ] Test OTP copying
- [ ] Test misclassification logging
- [ ] Test export/share functionality
- [ ] Test with server classification enabled/disabled
- [ ] Verify no crashes in release build

### Legal
- [ ] Privacy policy complies with local laws (GDPR if EU users)
- [ ] App name doesn't infringe trademarks
- [ ] All third-party licenses acknowledged (if required)

---

## 7. Version Management

### Update Version Before Release

**File:** `app/build.gradle.kts`
```kotlin
defaultConfig {
    versionCode = 1  // Increment for each release
    versionName = "1.0.0"  // Semantic versioning
}
```

**Version Code Rules:**
- Must be an integer
- Must increase with each release
- Google Play uses this to determine which version is newer

**Version Name Rules:**
- Human-readable (e.g., "1.0.0", "1.1.0", "2.0.0")
- Can be any string

---

## 8. Post-Upload Steps

1. **Internal Testing** (Recommended first step)
   - Upload AAB to "Internal testing" track
   - Add testers (your email)
   - Test the release build before going to production

2. **Review Process**
   - Google reviews apps (usually 1-3 days)
   - May request clarifications on permissions or data usage

3. **Production Release**
   - Once approved, publish to production
   - App will be available within hours

---

## 9. Ongoing Maintenance

### Monitoring
- Monitor crash reports in Google Play Console
- Check user reviews and ratings
- Monitor API usage (Cloud Run) for cost control

### Updates
- Increment `versionCode` for each update
- Update `versionName` appropriately
- Test thoroughly before releasing updates

### Security
- Keep dependencies updated
- Monitor for security vulnerabilities
- Rotate API keys if compromised (backend)

---

## 10. Quick Reference Commands

### Build Release AAB
```bash
cd android_sms_classifier
./gradlew bundleRelease
```

### Test Release Build Locally
```bash
./gradlew assembleRelease
adb install app/build/outputs/apk/release/app-release.apk
```

### Verify AAB
```bash
bundletool build-apks --bundle=app/build/outputs/bundle/release/app-release.aab --output=app.apks --mode=universal
bundletool install-apks --apks=app.apks
```

### Check AAB Size
```bash
bundletool get-size total --bundle=app/build/outputs/bundle/release/app-release.aab
```

---

## Summary

**Critical Actions:**
1. ✅ Fix security issues (cleartext, ProGuard, logging)
2. ✅ Generate signing key
3. ✅ Create privacy policy
4. ✅ Complete Data Safety section
5. ✅ Build release AAB
6. ✅ Upload to Google Play Console
7. ✅ Complete store listing
8. ✅ Submit for review

**Timeline:** Allow 1-2 weeks for first-time setup and Google review.

**Cost:** $25 one-time Google Play Developer registration fee (if not already paid).

