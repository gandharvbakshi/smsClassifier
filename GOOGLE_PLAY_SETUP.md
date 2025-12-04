# Google Play Store Setup Guide

## Step 1: Create Release Keystore

Run the PowerShell script to create your release keystore:

```powershell
cd android_sms_classifier
.\create_release_keystore.ps1
```

**Important:**
- Choose a strong password (save it securely!)
- The keystore will be created as `release-keystore.jks`
- **BACKUP THIS FILE** - you'll need it for all future updates!

## Step 2: Create keystore.properties

After creating the keystore, create `keystore.properties` in the `android_sms_classifier` folder:

```properties
storePassword=YOUR_STORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=release-key
storeFile=release-keystore.jks
```

**Replace:**
- `YOUR_STORE_PASSWORD` with the password you entered when creating the keystore
- `YOUR_KEY_PASSWORD` with the key password (can be same as store password)
- `release-key` with the alias you used (default is "release-key")

## Step 3: Add to .gitignore

**CRITICAL:** Never commit your keystore or passwords to git!

Add to `.gitignore`:
```
keystore.properties
*.jks
*.keystore
release-keystore.jks
test-keystore.jks
```

## Step 4: Build Release AAB

Build the App Bundle for Google Play:

```bash
cd android_sms_classifier
./gradlew bundleRelease
```

The AAB will be at: `app/build/outputs/bundle/release/app-release.aab`

## Step 5: Google Play Console Setup

### 5.1 Create New App

1. Go to [Google Play Console](https://play.google.com/console)
2. Click **"Create app"**
3. Fill in:
   - **App name:** SMS Classifier (or your preferred name)
   - **Default language:** English (United States)
   - **App or game:** App
   - **Free or paid:** Free
   - **Declarations:** Check only what applies

### 5.2 Set Up App Content

1. **Privacy Policy** (REQUIRED)
   - You need a publicly accessible HTTPS URL
   - See `GOOGLE_PLAY_DEPLOYMENT_PLAN.md` section 4 for template
   - Host it on GitHub Pages, Google Sites, or your own domain

2. **Data Safety** (REQUIRED)
   - Go to **App Content → Data Safety**
   - Declare:
     - **Personal info:** Phone numbers (collected, not shared)
     - **Messages:** SMS content (collected, not shared)
     - **Data usage:** App functionality
     - **Data sharing:** No

3. **Content Rating**
   - Complete the questionnaire
   - Likely rating: **Everyone** or **Teen**

### 5.3 Upload AAB

1. Go to **Production** → **Create new release**
2. Upload `app-release.aab`
3. Fill in **Release notes** (what's new in this version)
4. Click **Save** (don't publish yet)

### 5.4 Complete Store Listing

**Required fields:**
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
- **App icon:** 512x512 PNG
- **Feature graphic:** 1024x500 PNG
- **Screenshots:** At least 2 phone screenshots (16:9 or 9:16)
- **Categories:** Productivity or Tools

### 5.5 App Signing

When you upload your first AAB:
- Google will ask if you want to use **Google Play App Signing**
- **Select YES** (recommended)
- Google will generate the app signing key
- You'll upload your **upload key** (the one you just created)
- Save the app signing certificate Google provides

## Step 6: Submit for Review

1. Complete all required sections (marked with ⚠️)
2. Review all information
3. Click **"Start rollout to Production"**
4. Google will review (usually 1-3 days)
5. You'll receive email notifications about status

## Step 7: After Approval

Once approved:
- App will be available on Google Play Store
- Users can install and set it as default SMS app
- You can track downloads, ratings, and reviews

## Troubleshooting

### "App not installed as package appears to be invalid"
- Make sure you created the keystore and keystore.properties correctly
- Rebuild: `./gradlew clean bundleRelease`

### "Default SMS app" not working
- This requires the app to be installed from Google Play Store
- Side-loaded apps (from APK) have restrictions
- Once published on Play Store, users can set it as default

### Privacy Policy Required
- You MUST have a privacy policy URL
- It must be publicly accessible via HTTPS
- See deployment plan for template

## Next Steps After First Release

1. **Monitor:** Check Play Console for crashes, reviews, ratings
2. **Update:** For updates, increment `versionCode` in `build.gradle.kts`
3. **Signing:** Always use the same keystore for updates
4. **Backup:** Keep your keystore safe - losing it means you can't update!

## Quick Reference

**Build AAB:**
```bash
./gradlew bundleRelease
```

**Location:** `app/build/outputs/bundle/release/app-release.aab`

**Upload to:** Google Play Console → Production → Create new release

