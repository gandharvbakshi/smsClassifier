# Monetization & Growth Plan — Implementation Guide

> **For: implementer model.** This document is a complete, ordered build plan for the SMS Classifier Android app. Execute phases **in order**. Do not skip phases. Do not rearrange. After every phase, run the verification checklist for that phase before moving on. After ALL phases are implemented and verified, **delete this file**.
>
> **Scope:** Android app at `app/src/main/java/com/smsclassifier/app/` only. Backend (Cloud Run) lives in a different repository — **do not** create backend files in this workspace. Backend changes are flagged `[BACKEND]` and are for the human user to forward to the backend repo.
>
> **Hard rule:** none of the existing user-facing features may break. The "Testing Plan" at the end of this file is mandatory.

---

## 0. Decisions baked in (do not change)

| ID | Decision | Value |
|---|---|---|
| 0.1 | Monetization model | One-time purchase, ₹X (price TBD by user — use `pro_lifetime` SKU id), preceded by 7-day trial |
| 0.2 | Trial start trigger | Fires when `first_otp_detected` event fires for the first time per install |
| 0.3 | Trial enforcement | **Client-side**, server-synced for analytics. Reinstall = fresh trial. Acceptable for v1. |
| 0.4 | Pro features | Anything that requires the backend: server-side OTP detection (full ensemble), OTP intent classification, phishing detection, phishing score |
| 0.5 | Free fallback | Local `HeuristicOtpClassifier` only. Lower recall, no intent, no phishing. Must NEVER crash or show empty/error states. |
| 0.6 | Attribution stack | Firebase Analytics + Crashlytics (Google Ads native) + Meta SDK (Facebook Ads) |
| 0.7 | Phone auth posture | **Optional. Triggered ONLY after successful purchase.** Free + trial users never see it. |
| 0.8 | Misclass redaction | Digits-only, format-preserving (4+ contiguous digits → random digits of same length). Letters and structure preserved. |
| 0.9 | Geographic targeting | India only. English language only. |
| 0.10 | Database (Firebase) | **No Firestore, no Realtime DB.** Use existing Cloud Run + backend DB. |
| 0.11 | Privacy posture | All telemetry / crash reporting / Meta SDK is **OFF by default**. Explicit consent required. |

---

## 1. Glossary

| Term | Meaning |
|---|---|
| **Pro** | User has either (a) active 7-day trial, or (b) lifetime purchase. Both grant identical capabilities. |
| **Trial** | A 7-day window starting at `trial_started_at`. After 7 days, user is downgraded to Free unless they purchase. |
| **Free** | Default state. Has neither active trial nor purchase. Heuristic classification only. |
| **Entitlement** | The runtime answer to "is this install Pro right now?". Computed by `EntitlementManager`. |
| **installId** | Existing anonymous installation identifier (currently `Settings.Secure.ANDROID_ID`-derived). Replace with `FirebaseInstallations.getId()` in Phase 1. |
| **uid** | Firebase Auth user ID. Only present for users who have completed phone auth (post-purchase). |
| **Telemetry** | All Analytics + Crashlytics + Meta SDK calls. Always behind a consent gate. |

---

## 2. Pre-flight checks (already done by user)

These are confirmed complete:

- [x] Firebase project linked to existing GCP project `smsclassifier-478611`.
- [x] `app/google-services.json` exists in repo (gitignored — verify it is in `.gitignore`).

**Implementer must verify before starting Phase 1:**

```bash
# 1. Verify google-services.json exists
test -f app/google-services.json && echo "OK" || echo "MISSING — STOP"

# 2. Verify it is gitignored
grep -q "google-services.json" .gitignore && echo "OK" || echo "ADD to .gitignore"
```

If `google-services.json` is not gitignored, add this line to `.gitignore`:

```
app/google-services.json
```

---

## 3. Phase ordering

Each phase is independently testable. Implement and verify in order:

| # | Phase | Risk | Touches existing code? |
|---|---|---|---|
| 1 | Firebase foundation + consent infra | Low | No (additive) |
| 2 | Settings cleanup (4 sections) | Low | Yes (UI only) |
| 3 | Telemetry events | Low | Yes (call-sites added) |
| 4 | Crashlytics + safe error wrapper | Low | Yes (replace some `AppLog.w`) |
| 5 | Misclass redaction + upload preview | **Medium** | Yes (FeedbackUploader request payload) |
| 6 | Satisfaction prompts (D1, D5) | Low | Yes (MainActivity adds prompt host) |
| 7 | Trial + entitlement gating | **HIGH** | **Yes — gates ServerClassifier calls** |
| 8 | Play Billing — purchase flow | Medium | No (new flow, paywall screen) |
| 9 | Phone auth (post-purchase only) | Medium | No (new flow) |
| 10 | Play Store listing automation | Low | No (resource files only) |
| 11 | Ad SDK + conversion tracking | Low | Yes (one-line init in `Application`) |
| 12 | Privacy Policy + Data Safety updates | Required | Docs only |

---

## Phase 1 — Firebase foundation + consent infrastructure

### Goal

Wire Firebase BoM, add Analytics + Crashlytics + Installations + Remote Config + Auth SDKs (Auth used in Phase 9), but **fire nothing** until consent is granted. Replace existing `installId` with `FirebaseInstallations.getId()`.

### Step 1.1 — Add the Google Services + Crashlytics gradle plugins

**File: `build.gradle.kts` (root)**

Add to the existing `plugins { ... }` block:

```kotlin
id("com.google.gms.google-services") version "4.4.2" apply false
id("com.google.firebase.crashlytics") version "3.0.2" apply false
```

**File: `app/build.gradle.kts`**

Add to the existing `plugins { ... }` block (at the bottom):

```kotlin
id("com.google.gms.google-services")
id("com.google.firebase.crashlytics")
```

### Step 1.2 — Add Firebase BoM and SDKs

**File: `app/build.gradle.kts`** — in `dependencies { ... }` block, add:

```kotlin
// Firebase
implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
implementation("com.google.firebase:firebase-analytics-ktx")
implementation("com.google.firebase:firebase-crashlytics-ktx")
implementation("com.google.firebase:firebase-installations-ktx")
implementation("com.google.firebase:firebase-config-ktx")
implementation("com.google.firebase:firebase-auth-ktx")          // used in Phase 9
implementation("androidx.credentials:credentials:1.3.0")          // used in Phase 9
implementation("androidx.credentials:credentials-play-services-auth:1.3.0")
implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
```

**Note on BoM version:** if the Firebase BoM has a newer stable release at the time of implementation, prefer it. Verify on https://firebase.google.com/support/release-notes/android. Do not use `-alpha` or `-beta` versions.

### Step 1.3 — Register the debug variant in Firebase Console

**[USER ACTION REQUIRED — implementer model: surface this in the final summary]**

The debug build uses `applicationIdSuffix = ".debug"`, so its package name is `com.smsclassifier.app.debug`. Firebase needs both apps registered:

1. Open Firebase Console → Project settings → "Your apps".
2. Click "Add app" → Android.
3. Package name: `com.smsclassifier.app.debug` ; Nickname: `SMS Classifier (debug)`.
4. Download the **merged** `google-services.json` (Firebase will combine prod + debug into one file).
5. Replace `app/google-services.json` with the merged file.

If the user has not done this yet, the implementer should still proceed — Crashlytics/Analytics for debug builds will simply be silent until the merged JSON is in place.

### Step 1.4 — Create the consent infrastructure

**New file: `app/src/main/java/com/smsclassifier/app/analytics/ConsentManager.kt`**

A thin wrapper over DataStore preferences that exposes:

```kotlin
class ConsentManager(context: Context) {
    val analyticsConsent: Flow<Boolean>            // default false
    val crashlyticsConsent: Flow<Boolean>          // default false
    val metaAdsConsent: Flow<Boolean>              // default false
    val onboardingConsentSeen: Flow<Boolean>       // default false

    suspend fun setAnalyticsConsent(value: Boolean)
    suspend fun setCrashlyticsConsent(value: Boolean)
    suspend fun setMetaAdsConsent(value: Boolean)
    suspend fun markOnboardingConsentSeen()
    
    fun analyticsEnabledNow(): Boolean             // synchronous, for fast guards
    fun crashlyticsEnabledNow(): Boolean
    fun metaAdsEnabledNow(): Boolean
}
```

Use a single DataStore named `consent_prefs`. Cache values in memory (`@Volatile`) so the synchronous getters are non-blocking.

When any consent value flips, immediately call:

```kotlin
FirebaseAnalytics.getInstance(context).setAnalyticsCollectionEnabled(analyticsEnabledNow())
FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(crashlyticsEnabledNow())
// Meta SDK enable/disable handled in Phase 11.
```

**Important:** at app cold start, before Firebase fires anything automatic, set both collection flags to the persisted values. Default = false. Do this in `Application.onCreate()` (Step 1.6).

### Step 1.5 — Create the Telemetry facade

**New file: `app/src/main/java/com/smsclassifier/app/analytics/Telemetry.kt`**

Single point of entry for all event logging. Used by all later phases.

```kotlin
object Telemetry {
    fun init(context: Context, consentManager: ConsentManager)
    
    fun logEvent(name: String, params: Map<String, Any?> = emptyMap())
    fun setUserProperty(name: String, value: String?)
    fun setUserId(uid: String?)              // called from Phase 9 phone auth
}
```

Inside `logEvent`:
1. If `consentManager.analyticsEnabledNow() == false`, return immediately. Do not log.
2. Convert `params: Map<String, Any?>` to a `Bundle` (keys must be ≤40 chars, snake_case).
3. Call `FirebaseAnalytics.getInstance(context).logEvent(name, bundle)`.
4. If `consentManager.metaAdsEnabledNow() == true` AND the event is in the `META_DUPLICATED_EVENTS` set (defined in Phase 11), also log to Meta `AppEventsLogger`.

Add the `appName` and `versionCode` automatically as user properties. Do NOT log any SMS body, sender, OTP code, or contact name as event parameters.

**Reject parameters that look like PII.** In debug builds, throw `IllegalArgumentException` if any parameter value matches `\b\d{4,}\b` (likely an OTP or account number) or matches `+?\d{10,}` (phone number) or matches a basic email regex. In release builds, silently drop the parameter and call `recordException`.

### Step 1.6 — Application initialization

**Find or create:** `app/src/main/java/com/smsclassifier/app/SmsClassifierApplication.kt`

If an `Application` subclass exists already, augment it. If not, create one and register it in `app/src/main/AndroidManifest.xml` with `android:name=".SmsClassifierApplication"`.

In `onCreate()`, in this exact order:

```
1. super.onCreate()
2. consentManager = ConsentManager(this)              // synchronous load of cached prefs
3. FirebaseAnalytics.getInstance(this).setAnalyticsCollectionEnabled(consentManager.analyticsEnabledNow())
4. FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(consentManager.crashlyticsEnabledNow())
5. Telemetry.init(this, consentManager)
6. (Phase 7) entitlementManager = EntitlementManager(this, consentManager)
7. (Phase 11) MetaInit.init(this, consentManager)     // also conditional
```

Expose `consentManager` and `entitlementManager` (Phase 7) via a simple `AppContainer` singleton so screens / workers can grab them without DI complexity. Do NOT introduce Hilt or Dagger — keep it simple.

### Step 1.7 — Replace the existing `installId` with Firebase Installations ID

**Find every reference to the current installId:**

```bash
rg -n "installId" --type kt
```

Replace generation logic so that `installId` is fetched once from `FirebaseInstallations.getInstance().id.await()` and cached in DataStore (key: `firebase_install_id`). The on-disk legacy id should be migrated by the first launch after upgrade:

- On Application start, check if `firebase_install_id` is empty in DataStore.
- If empty, fetch from `FirebaseInstallations`, write to DataStore.
- Wherever code currently reads the legacy id, read from DataStore instead.

Keep the legacy id available in DataStore under key `legacy_install_id` so we can attach it to one-time backend migration calls if needed. Mark with a `// TODO: remove after 2 releases` comment.

### Step 1.8 — Create the first-run consent screen

**New file: `app/src/main/java/com/smsclassifier/app/ui/screens/ConsentOnboardingScreen.kt`**

A single-screen Compose flow shown the first time the user opens the app after the Phase 1 release. Trigger: `consentManager.onboardingConsentSeen` is false.

Design:

- Top: app icon + "Welcome to SMS Classifier" + 1 sentence value prop.
- Three toggles, all DEFAULT OFF, with one-line descriptions:
  - "Help improve the app (anonymous usage analytics)"
  - "Send crash reports (no SMS content)"
  - "Personalize ads we see when promoting this app (Meta)"
- Bottom: a primary `Continue` button (always enabled — user can skip all toggles).
- Footer link: "Privacy policy" → opens `https://gandharvbakshi.github.io/smsClassifier/privacy.html` (or whatever URL is in Phase 12).

On Continue:
- Persist all three toggle states.
- Call `consentManager.markOnboardingConsentSeen()`.
- Navigate to the existing main inbox screen.

### Step 1.9 — Wire the screen into navigation

**File: `app/src/main/java/com/smsclassifier/app/MainActivity.kt`**

In the existing `NavHost`, set the start destination dynamically:

- If `consentManager.onboardingConsentSeen == false` → start at `consent_onboarding`.
- Otherwise → keep current start destination.

Add a route `composable("consent_onboarding") { ConsentOnboardingScreen(onContinue = { navController.navigate("inbox") { popUpTo("consent_onboarding") { inclusive = true } } }) }`.

### Step 1.10 — Add a "Privacy & data" Settings sub-screen

This will be reorganized properly in Phase 2 / Phase 5; for now, just add a minimal entry under existing Settings → Feedback:

- "Analytics consent" toggle (binds to `consentManager.analyticsConsent`)
- "Crash reports consent" toggle
- "Personalised ads" toggle

User can flip these any time. Each flip immediately calls `setAnalyticsCollectionEnabled` / `setCrashlyticsCollectionEnabled`.

### Phase 1 verification

- [ ] `./gradlew assembleDebug` succeeds.
- [ ] `./gradlew assembleRelease` succeeds (uses existing keystore).
- [ ] App installs on emulator and shows the consent screen on first launch (after a clean install).
- [ ] All toggles default to OFF.
- [ ] Tapping Continue with all toggles OFF advances to the inbox.
- [ ] No `Telemetry.logEvent` call results in a Firebase Analytics network call (verify with `adb logcat | rg FA-SVC` — there should be no `Logging event` lines).
- [ ] Toggling "Analytics" on in Settings → next event call IS sent (verify `adb logcat | rg FA-SVC`).
- [ ] Force a test crash (`throw RuntimeException("test crash")` in a debug-only menu item) → with crash consent OFF, nothing is sent. Force-restart, flip crash consent ON, repeat → crash appears in Crashlytics dashboard within 5 minutes.
- [ ] Existing inbox / settings / feedback flows still work (no regression).

### Phase 1 rollback

Revert the two new gradle plugins, the BoM dependency, the consent screen, and the new package directory. Existing app continues to work without Firebase.

---

## Phase 2 — Settings cleanup (do this BEFORE telemetry so we have clean call-sites)

### Goal

Restructure `SettingsScreen.kt` from 8 sections to 4 top-level sections. No behaviour change. This is purely UX polish but it sets up sub-screens for later phases.

### New structure

```
[General]
  • Default SMS app
  • Notifications                  → tap opens NotificationSettingsSubScreen

[Classifier]
  • Backend status (read-only dot, no Check button by default)
  • Help improve classification    (the consent toggle, opens preview dialog)
  • Misclassification logs         → tap opens existing LogsScreen

[Privacy & Data]
  • Analytics consent              (toggle)
  • Crash reports consent          (toggle)
  • Personalised ads               (toggle)
  • Privacy policy                 → opens browser
  • Export my data                 → tap opens ExportSubScreen
  • Delete my data                 → opens deletion confirmation (Phase 12 wires backend)

[Help]
  • Contact developer
  • Diagnostics & self-test        → tap opens DiagnosticsSubScreen
  • About                          (version, build, OSS licenses)
```

### Files to touch

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` — rewrite top-level structure.
- New: `NotificationSettingsSubScreen.kt`
- New: `ExportSubScreen.kt` (moves the existing Export Labels / Full / Logs into one screen)
- New: `DiagnosticsSubScreen.kt` (moves OTP self-test, Performance stats, Diag info, Notification debug into one screen)
- New: `AboutSubScreen.kt`

### Implementation rules

- Reuse the existing `SettingsSection`, `SettingsRow`, `ToggleRow`, `SectionDivider`, `CheckLine`, `DiagLine` composables verbatim. Do not redefine them.
- All sub-screens must have a back arrow that returns to Settings.
- Add new routes to `MainActivity.kt` `NavHost`:
  - `settings_notifications`
  - `settings_export`
  - `settings_diagnostics`
  - `settings_about`
- The existing `notification_debug` route (debug-only) becomes a row inside `DiagnosticsSubScreen`, gated on `BuildConfig.DEBUG`.

### Phase 2 verification

- [ ] All previously-accessible features remain accessible (Default SMS, notification sound/vibration, export labels, export full, export logs, OTP self-test, diagnostics, contact developer, misclassification logs, feedback consent toggle, notification debug in debug builds).
- [ ] Settings home now has 4 sections instead of 8.
- [ ] Each sub-screen has a working back button.
- [ ] No regression in existing screens (inbox, detail, logs).

---

## Phase 3 — Telemetry events

### Goal

Fire the events from the table below at the listed call-sites. Each call goes through `Telemetry.logEvent(...)`, which will silently drop if analytics consent is off.

### Event catalog

| Event name | Parameters | Call-site |
|---|---|---|
| `app_first_open` | none | `Application.onCreate` (gated by "have we fired this once" flag in DataStore) |
| `app_open` | none | `MainActivity.onResume` (rate-limited to once per 60s) |
| `daily_active` | `dau_date: yyyy-MM-dd` | First foreground per UTC day; gated by DataStore `last_dau_date` |
| `permission_post_notifications_granted` | none | After Android 13+ POST_NOTIFICATIONS prompt accept |
| `permission_post_notifications_denied` | none | After deny |
| `default_sms_set` | none | When `MainActivity` detects we just became default (compare prev state) |
| `default_sms_declined` | none | After the user dismisses the prompt without setting |
| `first_sms_classified` | none | First time `ClassificationWorker` finishes a message; one-shot |
| `first_otp_detected` | `seconds_since_first_open: Long` | First time `ClassificationWorker` outputs `isOtp=true`; one-shot. **CRITICAL: also calls `entitlementManager.startTrialIfNotStarted()` (Phase 7).** |
| `feedback_submitted` | `correction_kind: String` (`"not_otp"` / `"actually_otp"` / `"phishing"` / `"not_phishing"` / `"other"`) | Tap of "Report as wrong" |
| `feedback_upload_consent_granted` | none | User flips the existing feedback upload toggle ON |
| `consent_changed` | `consent_kind: String`, `value: Boolean` | Each consent toggle flip |
| `paywall_shown` | `trigger: String` (`"trial_expired"` / `"feature_locked"` / `"settings"`) | When paywall sheet opens (Phase 8) |
| `purchase_started` | `sku: String` | User taps Buy (Phase 8) |
| `purchase_completed` | `sku: String`, `value: Double`, `currency: String` | After Play returns success (Phase 8) |
| `purchase_failed` | `sku: String`, `error_code: String` | Play returns non-success (Phase 8) |
| `phone_auth_started` | none | Phone auth screen opens (Phase 9) |
| `phone_auth_completed` | none | After Firebase Auth success (Phase 9) |
| `satisfaction_prompted` | `prompt_kind: String` (`"d1"` / `"d5"`) | When prompt shown (Phase 6) |
| `satisfaction_response` | `prompt_kind: String`, `score: Int` (1..5) | When user picks an emoji (Phase 6) |
| `pro_feature_blocked` | `feature_name: String` | When a free user attempts a Pro feature (Phase 7) |

### User properties

Set these once at app start (not per-event):

- `entitlement_state` — `"free"` / `"trial"` / `"pro"` / `"unknown"` (Phase 7 sets the real value)
- `default_sms` — `"true"` / `"false"` (refresh on `MainActivity.onResume`)
- `app_install_age_days` — integer

### Hard rules

- **NEVER include sender, body, OTP code, contact name, phone number, or email as a parameter value.** The Telemetry facade has a debug-time guard for this; respect it.
- All event names are snake_case, ≤40 chars.
- All param keys are snake_case, ≤40 chars; values ≤100 chars (Firebase truncates silently otherwise).

### Phase 3 verification

- [ ] With analytics consent ON, fresh install → `adb logcat | rg "Logging event"` shows `app_first_open` once, then `app_open` and `daily_active`.
- [ ] Receive a real OTP SMS → `first_otp_detected` event fires with the elapsed seconds parameter.
- [ ] Toggle Settings → Default SMS → `default_sms_set` event fires.
- [ ] Each consent toggle flip → `consent_changed` event with correct `consent_kind` and `value`.
- [ ] No event fires when analytics consent is OFF.
- [ ] No event ever contains an SMS body / sender / OTP code (grep the logs).

---

## Phase 4 — Crashlytics + safe error wrapper

### Goal

All non-fatal errors in critical paths get reported to Crashlytics, but with PII strictly stripped.

### Step 4.1 — Custom keys

In `Application.onCreate()`, after `setCrashlyticsCollectionEnabled`, set:

```
crashlytics.setCustomKey("default_sms", isDefaultSms.toString())
crashlytics.setCustomKey("inference_mode", "server")    // updated by Phase 7 to "free" / "trial" / "pro"
crashlytics.setCustomKey("install_age_days", ageDays)
```

Update these on app foreground via a lightweight observer.

### Step 4.2 — Safe error wrapper

**New file: `app/src/main/java/com/smsclassifier/app/util/SafeError.kt`**

```kotlin
object SafeError {
    /**
     * Reports an exception to Crashlytics with PII-stripped context.
     * Allowed context keys: "tag", "code", "stage", "ms_elapsed".
     * Disallowed keys raise IllegalArgumentException in debug; dropped in release.
     */
    fun report(tag: String, msg: String, t: Throwable? = null, context: Map<String, Any?> = emptyMap())
}
```

`msg` is stripped server-side as well: replace any 4+ digit run with `<digits:N>`, any 10+ digit run with `<phone>`, any email-shape with `<email>`. Apply same to `t.message` recursively.

Add a Detekt-style runtime guard: if `msg` or any context value contains `body=` or `sender=` substrings (common log pattern), strip the whole value and log a warning that someone tried to log raw SMS data.

### Step 4.3 — Migrate critical-path AppLog.w calls

Replace these specific call patterns:

```bash
# Find them
rg -n "AppLog\\.(w|e)\\(.*Throwable" --type kt
```

For each call in: `ServerClassifier`, `SmsDeliverReceiver`, `ClassificationWorker`, `FeedbackUploader`, `NotificationHelper`, `MainActivity` (default-SMS detection branch) — replace with both an `AppLog.w(...)` AND `SafeError.report(...)`. Logcat keeps debug power; Crashlytics keeps production visibility.

Do NOT migrate AppLog calls in UI/ViewModel layer — they're noisy and PII-prone.

### Phase 4 verification

- [ ] Force a `RuntimeException` from `ServerClassifier` (e.g. point `SERVER_API_BASE_URL` at `https://invalid.example.com/api` in a local debug build) → with crash consent ON, the exception appears in Crashlytics dashboard within 5 minutes with custom keys (`default_sms`, `inference_mode`).
- [ ] Crashlytics report message contains `<digits:6>` or `<phone>` placeholders, NOT real numbers.
- [ ] No regression in normal classification flow.

---

## Phase 5 — Misclassification redaction (digits-only) + upload preview

### Goal

The misclassification report uploaded to backend has all 4+ digit runs replaced with random digits of the same length. User can preview exactly what gets sent.

### Step 5.1 — Redaction utility

**New file: `app/src/main/java/com/smsclassifier/app/redaction/SmsRedactor.kt`**

```kotlin
object SmsRedactor {
    /**
     * Replaces every contiguous run of 4 or more ASCII digits with a same-length
     * run of random ASCII digits. Letters, punctuation, whitespace, non-ASCII
     * characters preserved exactly. Single, two, and three-digit runs preserved
     * (so things like "Rs 50" or "12-Jan" stay readable).
     *
     * Deterministic for a given (input, salt) pair so the preview matches the
     * upload. Pass salt = installId so different users redact differently.
     */
    fun redactDigits(body: String, salt: String): String

    /**
     * Convenience: also redacts +XX phone numbers (10–14 digit runs preceded
     * by + and country code) and email-shaped tokens to "<email>".
     */
    fun redactDigitsAndPhonesAndEmails(body: String, salt: String): String
}
```

**Algorithm:**

1. Use a `Regex("\\d{4,}")` find-replace.
2. For each match, generate a length-N random digit string seeded by `(salt + match.range.first + match.value)` so the result is stable for the same input.
3. Preserve everything else byte-for-byte.

**Phone-shape regex:** `\\+\\d{1,3}[\\s-]?\\d{6,14}` → replace whole match with same-length random digits (preserve `+`, spaces, dashes by mapping non-digit chars through unchanged).

**Email-shape regex:** `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}` → replace with `<email>`.

### Step 5.2 — Unit tests

**New file: `app/src/test/java/com/smsclassifier/app/redaction/SmsRedactorTest.kt`**

Cover at minimum:

| Input | Expected behaviour |
|---|---|
| `"OTP 123456 valid for 10 mins"` | `"OTP \d{6} valid for 10 mins"` (the "10" preserved — only 2 digits) |
| `"Your OTP is 9876"` | digits replaced (4 chars) |
| `"Acct ending 1234 debited Rs 500.00 on 12/05/2026"` | `1234` → 4 random digits; `500` preserved; `00` preserved; `12/05/2026` → `12/05/\d{4}` (only the `2026` is 4+ digits) |
| `"Call +91 9876543210"` (phone version) | `+91` preserved; phone digits randomised |
| `"Email me at foo@bar.com"` (phone version) | email replaced with `<email>` |
| `""` | returns `""` |
| `"No digits here"` | returns identical |
| Same `(input, salt)` called twice | identical output (deterministic) |
| Same input with different salts | different outputs |
| Real OTP SMS with mixed letters/digits like `"6789 is your OTP, do not share with anyone. -HDFCBK"` | digits replaced; `HDFCBK` preserved |
| Multiline body | works across lines |

### Step 5.3 — Wire into FeedbackUploader

**File: `app/src/main/java/com/smsclassifier/app/feedback/FeedbackUploader.kt`**

Modify `FeedbackRequest`:

```kotlin
@Serializable
data class FeedbackRequest(
    val installId: String,
    val firebaseUid: String? = null,                 // Phase 9 sets this
    val appVersionCode: Int,
    val appVersionName: String,
    val sender: String,                              // sender stays (it's a shortcode, not user PII)
    val body: String,                                // <-- now the redacted body
    val bodyRedactionScheme: String = "digits_v1",   // <-- NEW
    val predictedIsOtp: Boolean? = null,
    val predictedOtpIntent: String? = null,
    val predictedIsPhishing: Boolean? = null,
    val predictedPhishScore: Float? = null,
    val userCorrection: String?,
    val userNote: String? = null,
    val clientCreatedAt: Long
)
```

Modify the call-site that builds the request — find it in `FeedbackUploadWorker.kt` or wherever `FeedbackUploader.upload(...)` is invoked. Before calling `upload`, transform the body:

```kotlin
val redactedBody = SmsRedactor.redactDigits(rawBody, installId)
```

Pass `redactedBody` instead of `rawBody`. Local Room DB still keeps raw body so the user can review their reports.

### Step 5.4 — Preview dialog

When user taps "Report as wrong" in `LogsScreen` or wherever the report flow starts, show a confirmation sheet **before** uploading:

```
[ Preview of what will be sent ]
Sender: AX-AMAZON
Body (numbers replaced for privacy):
"Use OTP 738291 to login. Do not share. -Amazon"
                  ^^^^^^ random
[Cancel]   [Send report]
```

Use a Compose `ModalBottomSheet`. The redacted body is displayed verbatim. Add a subtle helper line: "We can't see your real codes. Your account numbers and OTPs are randomised before sending."

### Step 5.5 — `[BACKEND]` Schema notes for backend repo (forward to user)

The backend `/feedback` endpoint should accept the new optional fields:

- `firebaseUid: string | null` — store next to the row.
- `bodyRedactionScheme: string` — recommend index.

No client behaviour relies on the backend handling these; it'll just ignore unknown fields if you haven't updated yet. But if the user wants to query reports per-uid, the backend needs the column.

### Phase 5 verification

- [ ] `./gradlew testDebugUnitTest` passes the new SmsRedactor tests.
- [ ] On device: receive a real OTP SMS → tap "Report as wrong" → preview shows the redacted body with random digits → tap Send → backend receives the redacted version (verify with `gcloud logging read` or equivalent on the backend).
- [ ] Local Room DB still contains the raw body (verify via Settings → Misclassification logs).
- [ ] No regression in feedback upload flow when consent is on/off.

---

## Phase 6 — Satisfaction prompts (D1, D5)

### Goal

Capture qualitative PMF signal at day 1 and day 5 of usage. Drive happy users to Play Store rating, route unhappy users to a private text-feedback flow.

### Step 6.1 — Prompt scheduler

**New file: `app/src/main/java/com/smsclassifier/app/feedback/SatisfactionPromptManager.kt`**

State stored in DataStore:
- `first_open_at: Long`
- `d1_prompt_shown: Boolean`
- `d5_prompt_shown: Boolean`
- `last_prompt_dismissed_at: Long?` (for the 30-day cooldown rule)

```kotlin
class SatisfactionPromptManager(context: Context) {
    fun nextPromptToShow(now: Long = System.currentTimeMillis()): PromptKind?
    
    suspend fun markShown(kind: PromptKind)
    suspend fun markDismissed()                 // updates last_prompt_dismissed_at
}

enum class PromptKind { D1, D5 }
```

Logic:
- D1: show if `now - first_open_at >= 24h`, `d1_prompt_shown == false`, `last_prompt_dismissed_at == null` or `> 30d ago`.
- D5: show if `now - first_open_at >= 5*24h`, `d5_prompt_shown == false`, AND D1 was answered (or skipped >2d ago).
- Never show more than one prompt per session.
- Never show if user has not yet completed the consent onboarding.

### Step 6.2 — Compose UI

**New file: `app/src/main/java/com/smsclassifier/app/ui/components/SatisfactionPromptHost.kt`**

A composable that observes `SatisfactionPromptManager` and shows one of two bottom sheets when triggered. Embed in `MainActivity`'s root composable so it can appear over any screen.

**D1 sheet:**
- Title: "How's it going?"
- 5 emoji buttons: 😡 😕 😐 🙂 😍 (scores 1..5)
- "Skip for now" text button
- Tapping any emoji calls `Telemetry.logEvent("satisfaction_response", mapOf("prompt_kind" to "d1", "score" to score))` and dismisses.

**D5 sheet (two-step):**
- Step 1: same emoji row.
- Step 2 conditional:
  - Score ≥ 4 → "Glad you like it! Mind rating us on Play?" with two buttons:
    - "Sure" → invoke Play In-App Review API (`com.google.android.play:review-ktx`)
    - "Maybe later" → dismiss
  - Score ≤ 3 → "Sorry to hear it. What would make it better?" with a TextField + "Send" button. On Send, POST to `/feedback` (existing endpoint) with `{kind: "satisfaction", score, comment, installId, firebaseUid?}`. Use the existing `FeedbackUploader` infrastructure but a new `kind` field — backend will accept it as a generic feedback record. **No SMS data attached.**

### Step 6.3 — Add Play In-App Review dependency

**File: `app/build.gradle.kts`**

```kotlin
implementation("com.google.android.play:review-ktx:2.0.1")
```

### Phase 6 verification

- [ ] On a fresh install with consent granted: wait 24h (or temporarily set `first_open_at` 25h in the past via a debug menu) → D1 prompt appears.
- [ ] Pick a 5-emoji → `satisfaction_response` event fired with correct score.
- [ ] After D1 dismissed, set `first_open_at` 6 days back → D5 prompt appears.
- [ ] Score 5 + Sure → Play In-App Review overlay appears.
- [ ] Score 2 + Send → text routes to backend `/feedback` endpoint.
- [ ] No prompt ever shown if onboarding consent was never seen.
- [ ] No prompt shown twice; cooldown rule respected.

---

## Phase 7 — Trial + entitlement gating (THE BIG ONE)

### Goal

Free users get heuristic-only classification. Trial (7 days from `first_otp_detected`) and Pro (purchased) users get the full ensemble. **Existing flow must not break — server calls just stop happening for Free users.**

### Step 7.1 — EntitlementManager

**New file: `app/src/main/java/com/smsclassifier/app/entitlement/EntitlementManager.kt`**

```kotlin
enum class EntitlementState { FREE, TRIAL_ACTIVE, TRIAL_EXPIRED, PRO, UNKNOWN }

class EntitlementManager(
    context: Context,
    private val telemetry: Telemetry = Telemetry,
) {
    val stateFlow: StateFlow<EntitlementState>     // hot, observable from UI
    
    fun isPro(now: Long = System.currentTimeMillis()): Boolean
    fun currentState(now: Long = System.currentTimeMillis()): EntitlementState
    fun trialDaysRemaining(now: Long = System.currentTimeMillis()): Int       // 0 if not trial
    
    suspend fun startTrialIfNotStarted()           // called by Phase 3 first_otp_detected
    suspend fun markPurchased(purchaseToken: String, sku: String, purchasedAt: Long)
    suspend fun clearPurchase()                    // for refund handling
    
    // Restoration
    suspend fun reconcileWithPlay(billingClient: PlayBillingClient)   // Phase 8
}
```

DataStore keys:
- `trial_started_at: Long?`
- `trial_acknowledged: Boolean` (we showed user a one-time banner)
- `pro_purchase_token: String?`
- `pro_sku: String?`
- `pro_purchased_at: Long?`

Logic:
- `isPro(now)`:
  - if `pro_purchase_token != null` → true
  - else if `trial_started_at != null` AND `(now - trial_started_at) < 7 * 24 * 3600 * 1000` → true
  - else → false
- `currentState(now)` returns the enum based on the same logic.
- `startTrialIfNotStarted()`:
  - If already started or pro, no-op.
  - Set `trial_started_at = now`.
  - Fire `Telemetry.logEvent("trial_started")`.
  - **`[BACKEND]`** POST `/users/trial-start` with `{installId, firebaseUid?, startedAt}` (best-effort, no retry needed for v1).
- On state transitions, update the Crashlytics custom key `inference_mode`.

### Step 7.2 — Gate the ServerClassifier

**File: `app/src/main/java/com/smsclassifier/app/work/ClassificationWorker.kt`** (or wherever `ServerClassifier.classify(...)` is called)

Find the existing call site. Wrap it:

```kotlin
val entitled = AppContainer.entitlementManager.isPro()
val serverResult = if (entitled) {
    runCatching { ServerClassifier.classify(sender, body) }.getOrNull()
} else {
    null
}
val heuristicResult = HeuristicOtpClassifier.classify(sender, body)
val merged = ClassificationUtils.merge(serverResult, heuristicResult)
```

If `merge(...)` is not yet a function in `ClassificationUtils.kt`, create one. Its contract:

- If `serverResult != null`, prefer server's `isOtp`, `otpIntent`, `isPhishing`, `phishScore`.
- If `serverResult == null`, use heuristic's `isOtp` only. Set `otpIntent = null`, `isPhishing = null`, `phishScore = null`.
- Heuristic veto rules (existing `isHeuristicVeto` logic) still apply on top.

### Step 7.3 — Trial-started one-shot banner

When `trial_started_at` is just set (single-shot, gated by `trial_acknowledged`), show an in-app banner / snackbar in the inbox:

```
"You've unlocked 7-day free trial of Pro features —
 OTP classification, phishing detection, and intent."
[Got it]
```

Tap "Got it" → set `trial_acknowledged = true`. Banner never shown again.

### Step 7.4 — Trial-ending warnings

In the inbox, if `currentState == TRIAL_ACTIVE` AND `trialDaysRemaining() <= 2`, show a small persistent banner:

```
"Trial ends in 2 days. Keep Pro for ₹X →"   [Buy] [Dismiss]
```

`Buy` → opens paywall (Phase 8). `Dismiss` → temporary suppression for 24h.

### Step 7.5 — Trial-expired UX

When `currentState == TRIAL_EXPIRED`:

- Inbox: messages from the period when the user was Pro/Trial keep their server-derived labels (no retroactive blanking).
- Messages received AFTER trial expiry get heuristic-only labels.
- Add an "Unlock Pro" CTA on the inbox top bar.
- Detail screen: if a message has `otpIntent == null` AND `isPhishing == null` AND state is FREE/TRIAL_EXPIRED, show a small placeholder:

  ```
  [🔒 Unlock Pro to see intent and phishing risk for this message]
  ```

  Tapping → opens paywall.

### Step 7.6 — Server load reduction

Free users send ZERO requests to your Cloud Run backend. Verify by checking that no `/classify` call (or whatever the existing endpoint is) is invoked when `isPro() == false`. Cost saving is the point.

### Phase 7 verification

- [ ] Fresh install. **No** OTP received yet → state is FREE. Receive a transactional SMS → no server call (verify in `adb logcat | rg ServerClassifier`). Local heuristic fires.
- [ ] Receive an OTP SMS → trial starts, banner appears, `first_otp_detected` event fires, `trial_started` event fires, server call happens for THIS message.
- [ ] Subsequent messages: server calls happen, full classification applies.
- [ ] Manually backdate `trial_started_at` to 8 days ago in DataStore (use a debug menu) → state flips to TRIAL_EXPIRED, banner changes, future server calls stop.
- [ ] On TRIAL_EXPIRED, the inbox still loads, still shows OTP heuristic labels, never crashes.
- [ ] Detail screen for a FREE-mode message shows the "Unlock Pro" placeholder.
- [ ] No null-pointer crashes from `serverResult == null` paths anywhere in the codebase. Run a full instrumented test of the ClassificationWorker with `entitled = false` to confirm.
- [ ] Crashlytics custom key `inference_mode` reflects current state.

### Phase 7 risk callouts (read carefully)

- **Risk 1:** Existing code paths may assume `serverResult` is never null. Audit every reference. Specifically check: `ClassificationUtils.extractOtpForCopy`, `NotificationHelper.renderNotification`, `LogsScreen.kt`, `DetailViewModel.kt`. Add null-safe handling.
- **Risk 2:** `phishScore` is currently a `Float`. If existing UI does `phishScore > 0.5f` without null-checking, it'll crash. Use `phishScore?.let { it > 0.5f } == true` patterns.
- **Risk 3:** The misclassification feedback path also captures `predictedIsPhishing` etc. If those are null, the upload should still succeed (the field is nullable in the request). Verify Phase 5 changes are compatible.
- **Risk 4:** Notifications for free users should still show the OTP code if heuristic detected one — only the "phishing risk" / "intent" badges should be hidden.

---

## Phase 8 — Play Billing — purchase flow

### Goal

User can tap "Buy Pro" in the paywall and complete a one-time purchase via Google Play. The app then permanently flips to Pro state.

### Step 8.1 — Play Console product setup `[USER ACTION]`

Implementer: surface this in the final summary. The user must:

1. Play Console → SMS Classifier → Monetize → In-app products → Create product.
2. Product ID: `pro_lifetime`.
3. Type: Managed product.
4. Name / description / price: user's choice.
5. Activate.

### Step 8.2 — Add Play Billing dependency

**File: `app/build.gradle.kts`**

```kotlin
implementation("com.android.billingclient:billing-ktx:7.1.1")
```

### Step 8.3 — Billing client wrapper

**New file: `app/src/main/java/com/smsclassifier/app/billing/PlayBillingClient.kt`**

```kotlin
class PlayBillingClient(context: Context) {
    suspend fun startConnection(): Result<Unit>
    suspend fun queryProducts(): Result<List<ProductInfo>>     // returns the pro_lifetime SKU details
    suspend fun launchBillingFlow(activity: Activity, sku: String): Result<Unit>
    suspend fun queryPurchases(): Result<List<PurchaseInfo>>   // for restore + reconcile

    val purchaseUpdates: SharedFlow<PurchaseInfo>              // emits on async purchase results
    
    suspend fun acknowledgePurchase(purchaseToken: String): Result<Unit>
    
    fun close()
}

data class ProductInfo(val sku: String, val title: String, val priceFormatted: String, val priceMicros: Long, val currency: String)
data class PurchaseInfo(val sku: String, val purchaseToken: String, val purchasedAt: Long, val isAcknowledged: Boolean, val state: PurchaseState)
enum class PurchaseState { PURCHASED, PENDING, UNSPECIFIED }
```

Use Billing Library 7's `BillingClient` and `PurchasesUpdatedListener`. Wrap callbacks into suspend funs / Flow.

**Critical:** ALL purchases MUST be acknowledged within 3 days or Google auto-refunds. Acknowledge as soon as `EntitlementManager.markPurchased` returns success.

### Step 8.4 — Paywall screen

**New file: `app/src/main/java/com/smsclassifier/app/ui/screens/PaywallScreen.kt`**

Layout:
- Hero: app icon + "SMS Classifier Pro"
- Bullet list of Pro features:
  - Smart OTP detection (catches every OTP, no false positives)
  - OTP intent (login / payment / signup / verification)
  - Phishing protection
  - Phishing risk score on suspicious messages
- Trial status row:
  - If TRIAL_ACTIVE: "Trial active, X days remaining."
  - If TRIAL_EXPIRED: "Trial ended."
  - If FREE (never started trial): "Start using and we'll auto-unlock a 7-day free trial when you receive your first OTP."
- Big primary button: "Unlock Pro for ₹X" (price loaded dynamically from `queryProducts`).
- Secondary text: "One-time purchase. No subscription."
- Tertiary text button: "Restore purchase" (calls `queryPurchases` → if found, marks Pro).
- Bottom: privacy policy + terms links.

When user taps "Unlock Pro":
- Fire `purchase_started` event.
- Call `launchBillingFlow(activity, "pro_lifetime")`.
- Observe `purchaseUpdates`:
  - `PURCHASED` → call `EntitlementManager.markPurchased`, acknowledge, fire `purchase_completed` event with price/currency, navigate to `PostPurchasePhoneAuthScreen` (Phase 9).
  - `PENDING` → show "Payment pending — we'll unlock as soon as it clears." Listen for the next update.
  - error → fire `purchase_failed` with code, show toast.

### Step 8.5 — Reconcile on app start

In `Application.onCreate()` (or first `MainActivity` resume), call `EntitlementManager.reconcileWithPlay(playBillingClient)` async:

- `queryPurchases()` returns all entitlements Google knows about.
- If a `pro_lifetime` purchase is present and acknowledged, ensure local state is Pro. If our local state says FREE but Play says owned → flip to Pro (this handles uninstall+reinstall+restore).
- If a previously-Pro local state has no matching Play purchase → treat as refunded, call `EntitlementManager.clearPurchase()`. Show a one-shot snackbar "Your Pro purchase has been refunded. Reverting to Free."

### Step 8.6 — Wire paywall triggers

Three triggers:
- TRIAL_EXPIRED user opens app → Inbox top bar `Unlock Pro` button → paywall.
- TRIAL_EXPIRED user taps a message in inbox → detail screen shows "🔒 Unlock Pro" placeholder → tap → paywall.
- Always-on entry: Settings → "About" → "Upgrade to Pro" row.

For each, fire `paywall_shown` event with appropriate `trigger` value.

### Phase 8 verification

- [ ] On a real device with the app installed via Play **Internal Testing** track (sandboxed billing): tap Buy → Play overlay appears with the test card → complete purchase → app flips to PRO state.
- [ ] Verify the purchase is acknowledged (Play Console → Monetize → Subscriptions and one-time products → look for the test purchase, confirm "Acknowledged").
- [ ] Force-stop app, clear data, reinstall → tap "Restore purchase" → state flips back to PRO.
- [ ] Pending state: use the Play test card "Pending" → app shows pending message → pending resolves → state flips to PRO.
- [ ] Refund the test purchase via Play Console → wait for app reconcile (next foreground) → app flips back to FREE with a snackbar.
- [ ] All purchase events (`purchase_started`, `purchase_completed`, `purchase_failed`) appear in Firebase Analytics.

### Phase 8 backend `[BACKEND]`

For v1, no backend purchase verification is required — Play Billing's local check is the source of truth. Optional for later: send the purchase token to backend, backend calls Google Play Developer API to verify and store. Out of scope for this plan.

---

## Phase 9 — Phone authentication (post-purchase only)

### Goal

After successful purchase, prompt the user to bind their account to a phone number so the entitlement survives reinstall on any device.

### Step 9.1 — Firebase Console setup `[USER ACTION]`

Implementer: surface in summary.

1. Firebase Console → Authentication → Sign-in method → Phone → Enable.
2. Project settings → Your apps → SMS Classifier (release) → Add SHA-1 of the release keystore (the `.jks` file currently used to sign — get via `keytool -list -v -keystore release-keystore.jks`).
3. Project settings → Your apps → SMS Classifier (debug) → Add SHA-1 of the debug keystore.

### Step 9.2 — PhoneAuthManager

**New file: `app/src/main/java/com/smsclassifier/app/auth/PhoneAuthManager.kt`**

```kotlin
class PhoneAuthManager(private val auth: FirebaseAuth = FirebaseAuth.getInstance()) {
    suspend fun sendVerificationCode(phoneE164: String, activity: Activity): Result<VerificationHandle>
    suspend fun verifyCode(handle: VerificationHandle, code: String): Result<FirebaseUser>
    
    fun currentUid(): String?
    suspend fun signOut()
}

data class VerificationHandle(val verificationId: String, val resendToken: PhoneAuthProvider.ForceResendingToken?)
```

Use `PhoneAuthProvider.verifyPhoneNumber(...)` with a `PhoneAuthOptions.Builder` configured for India (`.setActivity(activity)`, no special country code restriction needed but you can set to `+91` defaults in the UI).

### Step 9.3 — PostPurchasePhoneAuthScreen

**New file: `app/src/main/java/com/smsclassifier/app/ui/screens/PostPurchasePhoneAuthScreen.kt`**

Two-step flow:
- Step 1: "Save your purchase to a phone number"
  - Subtext: "So your Pro stays active if you reinstall or get a new phone."
  - Phone input (default +91 prefix).
  - "Send code" button.
  - Skip button: "Skip — keep my purchase only on this phone." (Acceptable; user can do it later from Settings.)
- Step 2: "Enter the 6-digit code"
  - 6-digit OTP input (use SMS Retriever auto-fill via Firebase Auth's built-in handling).
  - "Verify" button.
  - "Resend code" link.

After verify success:
- Fire `phone_auth_completed` event.
- Set `Telemetry.setUserId(uid)`.
- **`[BACKEND]`** POST `/users/link-phone` with `{installId, firebaseUid, purchaseToken}`.
- Show a confirmation: "All set! Your Pro is now linked to your phone number."
- Navigate to inbox.

### Step 9.4 — Settings → Account sub-screen

Under the General section, add an "Account" row:

- If signed in: show masked phone (e.g. `+91 ••••• ••210`) + "Sign out" button.
- If not signed in but Pro: "Save purchase to phone number" → opens PostPurchasePhoneAuthScreen.
- If not signed in and not Pro: hide the row.

### Step 9.5 — Restore Pro by phone (the win condition)

When a previously-Pro user reinstalls:
- They sign in with phone via Settings → Account.
- After Firebase Auth success, app calls **`[BACKEND]`** GET `/users/me` with the new `firebaseUid`.
- Backend returns `{ pro: true, purchaseToken: "..." }`.
- Client calls `EntitlementManager.markPurchased(purchaseToken, ...)` → state flips to PRO.

### Phase 9 verification

- [ ] Complete a purchase → PostPurchasePhoneAuthScreen appears.
- [ ] Enter your real Indian mobile number → receive SMS → enter OTP → screen confirms.
- [ ] `phone_auth_started` and `phone_auth_completed` events fire.
- [ ] Settings → Account shows masked phone.
- [ ] Sign out → state stays PRO (purchase is local), but uid clears.
- [ ] Uninstall, reinstall fresh, sign in via Settings → Account → state flips back to PRO.
- [ ] Skip flow works: Skip button on PostPurchasePhoneAuthScreen returns to inbox without breaking.

### Phase 9 risk callouts

- Firebase free tier: 10K SMS/month. If usage exceeds, costs $0.06/SMS in India. Set GCP budget alert.
- SMS Retriever auto-fill needs the SHA-1 to be registered. If verification times out at "Auto-fetching OTP...", the SHA-1 is wrong — fall back to manual entry.

---

## Phase 10 — Play Store listing automation

### Goal

Listing copy + screenshots managed in-repo. `./gradlew publishListing` updates Play Console.

### Step 10.1 — Bootstrap from current Play listing

Implementer: surface as a one-time command for the user.

```bash
./gradlew bootstrapReleaseListing
```

This pulls the current Play Console listing into `app/src/main/play/listings/en-US/`. Do this once. Commit the result.

### Step 10.2 — File layout

After bootstrap, you should have:

```
app/src/main/play/
  release-notes/
    en-US/
      default.txt                # already exists
  listings/
    en-US/
      title                      # 30 chars max
      short-description          # 80 chars max
      full-description           # 4000 chars max
      video                      # optional youtube URL
      graphics/
        icon/                    # 1 file, 512x512 PNG, no alpha
        feature-graphic/         # 1 file, 1024x500 PNG/JPEG, no alpha
        phone-screenshots/       # 2-8 files, 1080x1920 PNG/JPEG (or 1080x2400)
        tablet-7-inch-screenshots/      # optional
        tablet-10-inch-screenshots/     # optional
```

Implementer should NOT generate screenshots. Leave a `README.md` in `app/src/main/play/listings/en-US/graphics/` instructing the user to drop screenshots in.

### Step 10.3 — Suggested listing copy (English, India)

The implementer should pre-populate the text files with a marketing-quality default. User can edit.

**`title`** (≤30 chars):

```
SMS Classifier — OTP & Spam
```

**`short-description`** (≤80 chars):

```
Detect OTPs, spot phishing, organise your SMS inbox automatically.
```

**`full-description`** (≤4000 chars): a clean, India-targeted writeup highlighting OTP autofill, phishing detection, transactional SMS organisation, on-device privacy ("we never read your messages on our servers without your permission"), and the 7-day free trial.

### Step 10.4 — Publishing

```bash
./gradlew publishListing                    # listing only, no app upload
./gradlew publishReleaseBundle              # bundle + listing (existing flow)
```

### Phase 10 verification

- [ ] After `bootstrapReleaseListing` succeeds, the files exist locally.
- [ ] Editing `title` and running `./gradlew publishListing` updates Play Console (verify in Play Console UI).

---

## Phase 11 — Ad SDK + conversion tracking

### Goal

- Google Ads tracking comes "free" via Firebase Analytics (no SDK needed beyond Phase 1).
- Meta SDK added for Facebook Ads conversion tracking. Initialised only with consent.

### Step 11.1 — Mark conversion events `[USER ACTION]`

Implementer: surface in summary. The user must:

1. Firebase Console → Analytics → Custom definitions → Conversions tab → Mark these as conversions:
   - `default_sms_set`
   - `purchase_completed`
   - `first_otp_detected`
2. Firebase Console → Project settings → Integrations → Google Ads → link your Google Ads account.

### Step 11.2 — Add Meta SDK

**File: `app/build.gradle.kts`**

```kotlin
implementation("com.facebook.android:facebook-android-sdk:18.0.0")
```

**File: `app/src/main/AndroidManifest.xml`**

Add inside `<application>`:

```xml
<meta-data
    android:name="com.facebook.sdk.ApplicationId"
    android:value="@string/facebook_app_id" />
<meta-data
    android:name="com.facebook.sdk.ClientToken"
    android:value="@string/facebook_client_token" />
```

**`[USER ACTION]`** Get `facebook_app_id` and `facebook_client_token` from Meta Business / developers.facebook.com. Add to `app/src/main/res/values/strings.xml`:

```xml
<string name="facebook_app_id">YOUR_APP_ID</string>
<string name="facebook_client_token">YOUR_CLIENT_TOKEN</string>
```

### Step 11.3 — Meta init wrapper

**New file: `app/src/main/java/com/smsclassifier/app/analytics/MetaInit.kt`**

```kotlin
object MetaInit {
    fun init(context: Context, consentManager: ConsentManager) {
        // Hard-disable everything until consent
        FacebookSdk.setAutoLogAppEventsEnabled(false)
        FacebookSdk.setAdvertiserIDCollectionEnabled(false)
        FacebookSdk.sdkInitialize(context.applicationContext)
        
        if (consentManager.metaAdsEnabledNow()) {
            enable(context)
        }
    }
    
    fun enable(context: Context) {
        FacebookSdk.setAutoLogAppEventsEnabled(true)
        FacebookSdk.setAdvertiserIDCollectionEnabled(true)
    }
    
    fun disable() {
        FacebookSdk.setAutoLogAppEventsEnabled(false)
        FacebookSdk.setAdvertiserIDCollectionEnabled(false)
    }
}
```

Call `MetaInit.init` from `Application.onCreate()`. When the consent toggle flips, call `enable()` or `disable()` accordingly.

### Step 11.4 — Mirror conversion events to Meta

In `Telemetry.logEvent`, after the Firebase log, if the event name is in `META_DUPLICATED_EVENTS = setOf("default_sms_set", "purchase_completed", "first_otp_detected")` AND meta consent is on, also call:

```kotlin
AppEventsLogger.newLogger(context).logEvent(eventName, bundle)
```

For `purchase_completed`, prefer `logPurchase(BigDecimal, Currency)` for proper revenue attribution.

### Phase 11 verification

- [ ] With Meta consent OFF, no Meta network calls (verify with `adb logcat | rg facebook` or a packet inspector).
- [ ] With Meta consent ON, conversion events appear in Meta Events Manager (test mode).
- [ ] Google Ads conversion column populates within 24h after `default_sms_set` events fire.

---

## Phase 12 — Privacy Policy + Data Safety + compliance

### Goal

Ship-blocker compliance. Without these, the build that contains the new SDKs MUST NOT be promoted to production.

### Step 12.1 — Update Privacy Policy

The current privacy policy URL (probably in `app/src/main/res/values/strings.xml` or hardcoded somewhere). Update it to disclose:

- Data collected:
  - **Anonymous:** install ID, app interaction events, device info (model, OS version, country), crash reports.
  - **With consent:** Meta Ads conversion events, advertising ID.
  - **For paying users only:** phone number (for account recovery), Firebase Auth UID.
  - **Misclassification reports (only if user opts in):** sender, REDACTED message body (digits randomised), predicted/actual labels.
- Data NOT collected: SMS bodies in raw form, contacts, location, photos.
- Third parties: Google (Firebase, Play Billing, Google Ads), Meta (Facebook Ads, optional).
- User rights: account deletion via in-app, data deletion via email.
- Retention: telemetry 14 months, crash reports 90 days, misclass reports indefinite (until user requests deletion), purchase records 7 years (legal).
- Contact email.

### Step 12.2 — Data Safety form in Play Console `[USER ACTION]`

Implementer: surface in final summary. The user must update the Data Safety form to reflect EVERY new SDK and data type. Match the Privacy Policy exactly. Do not lie. This is the most common Play takedown trigger.

Required disclosures:
- App activity (events) — collected, optional, for analytics.
- Crash logs — collected, optional, for app functionality.
- Advertising ID — collected (Meta SDK only), optional.
- Phone number — collected (Pro purchase only), required for account, processed by Firebase Auth.
- Purchase history — collected, required, processed by Google Play.
- Other user-generated content (misclass reports) — collected, optional, processed in our cloud.
- All "shared with third parties" — Google, Meta.

### Step 12.3 — Account deletion flow `[REQUIRED BY PLAY]`

Settings → Privacy & Data → "Delete my data" → confirmation dialog → calls **`[BACKEND]`** DELETE `/users/me?installId=X&uid=Y`.

Backend wipes: feedback rows, satisfaction rows, trial start record, purchase token (but keeps anonymised purchase analytics row).

After backend confirms, client wipes local Room DB and DataStore (except the consent flags so re-onboarding doesn't happen). Sign out of Firebase Auth. Show "Your data has been deleted."

### Phase 12 verification

- [ ] Privacy Policy URL loads, reflects every new data type.
- [ ] Data Safety form matches Privacy Policy exactly.
- [ ] Settings → Privacy & Data → Delete my data → calls backend, wipes local data.

---

## Testing Plan (mandatory — execute before any release)

This section is for the **testing model / QA pass**. Runs after all phases are implemented. Each test marked `[REGRESSION]` is a guard against breaking pre-existing behaviour. Each test marked `[NEW]` validates a phase deliverable.

### Test environment

- 1 physical Android device, API 28+ (e.g. Pixel 6 / OnePlus / Samsung — vendor variety matters).
- Optional second device, API 26 (minSdk floor) to confirm bottom of range.
- Active Indian SIM that receives real OTPs (Amazon, Swiggy, bank).
- Play account enrolled in Internal Testing track for the build under test.
- A Firebase test account (separate from prod analytics view).
- Meta Events Manager in test mode (App ID has Test Events configured).

### Section A — Regression suite (must pass after every phase)

| # | Test | Expected | Phase to re-run after |
|---|---|---|---|
| A1 | `[REGRESSION]` Fresh install → set as default SMS app | Prompt appears, accepting succeeds, app shows as default in Settings | Every phase |
| A2 | `[REGRESSION]` Receive a real OTP from Amazon | Notification appears with OTP code visible; tapping copies code | Every phase |
| A3 | `[REGRESSION]` Receive a real OTP from Swiggy | Same as A2 | Every phase |
| A4 | `[REGRESSION]` Receive a transactional SMS (e.g. UPI debit) | Notification appears categorised correctly (NOT as OTP) | Every phase |
| A5 | `[REGRESSION]` Open the inbox, scroll, tap a message | Detail screen loads, no crash, all metadata present | Every phase |
| A6 | `[REGRESSION]` Settings → Default SMS shows correct state | Yes/No matches reality | Every phase |
| A7 | `[REGRESSION]` Settings → Notification sound + vibration toggles persist | Toggle, kill app, reopen, state preserved | Every phase |
| A8 | `[REGRESSION]` Settings → Export labels CSV | CSV downloads, openable, data present | Every phase |
| A9 | `[REGRESSION]` Settings → Export full classification CSV | Same as A8 | Every phase |
| A10 | `[REGRESSION]` Tap "Report as wrong" on a message | Report flow appears, completes without crash | Every phase |
| A11 | `[REGRESSION]` Settings → Misclassification logs shows past reports | Each row visible | Every phase |
| A12 | `[REGRESSION]` Settings → Backend status → Check | Returns Healthy with latency OR an explanatory error (no crash) | Every phase |
| A13 | `[REGRESSION]` Settings → OTP autofill self-test → Run | Returns all checks; no crash | Every phase |
| A14 | `[REGRESSION]` Background SMS classification still runs when app is closed | Receive SMS with app force-stopped → notification appears | Every phase |
| A15 | `[REGRESSION]` SMS that arrives during dual-SIM setup gets `SUBSCRIPTION_ID` populated | Inspect via OTP self-test | Every phase |
| A16 | `[REGRESSION]` Existing notifications still show OTP code on lock screen with autofill working in Amazon | Auto-fill chip appears in Amazon login | Every phase touching `NotificationHelper` |
| A17 | `[REGRESSION]` `assembleDebug` succeeds with no warnings beyond pre-existing | `./gradlew assembleDebug` exits 0 | Every phase |
| A18 | `[REGRESSION]` `assembleRelease` succeeds with no warnings beyond pre-existing | `./gradlew assembleRelease` exits 0 | Every phase |
| A19 | `[REGRESSION]` Existing unit tests pass | `./gradlew testDebugUnitTest` exits 0 | Every phase |
| A20 | `[REGRESSION]` App size has not regressed by >2 MB | Inspect AAB size before vs after | Every phase |
| A21 | `[REGRESSION]` App start time has not regressed by >300 ms | Inspect with `adb shell am start -W` 5x avg | Every phase |
| A22 | `[REGRESSION]` Battery usage normal | Use Battery Historian for 1h passive | Once before final release |

### Section B — Phase 1 (Firebase + Consent)

| # | Test | Expected |
|---|---|---|
| B1 | `[NEW]` Fresh install → consent screen appears as start destination | Yes |
| B2 | `[NEW]` All three toggles default OFF | Yes |
| B3 | `[NEW]` Tap Continue with all OFF → inbox opens | Yes |
| B4 | `[NEW]` Re-launch app → consent screen NOT shown again | Yes |
| B5 | `[NEW]` Settings → Privacy & Data → toggle Analytics ON → kill, reopen, still ON | Yes |
| B6 | `[NEW]` Verify `installId` is now Firebase Installations ID format (UUID-ish) | Inspect DataStore via debug menu |
| B7 | `[NEW]` Crashlytics receives a test crash within 5 minutes (with consent ON) | Verify in Crashlytics dashboard |
| B8 | `[NEW]` Crashlytics receives nothing with consent OFF | Verify |

### Section C — Phase 2 (Settings cleanup)

| # | Test | Expected |
|---|---|---|
| C1 | `[NEW]` Settings home shows exactly 4 sections (General, Classifier, Privacy & Data, Help) | Yes |
| C2 | `[NEW]` Each previously-existing settings option is reachable in ≤2 taps | Yes — verify all 17 from the original 8-section list |
| C3 | `[NEW]` Each sub-screen back button returns to Settings root | Yes |

### Section D — Phase 3 (Telemetry events)

| # | Test | Expected |
|---|---|---|
| D1 | `[NEW]` `app_first_open` fires exactly once on install | Verify in Firebase DebugView |
| D2 | `[NEW]` `daily_active` fires once per day | Verify after 24h |
| D3 | `[NEW]` `default_sms_set` fires when becoming default | Verify |
| D4 | `[NEW]` `first_otp_detected` fires on first OTP, never again | Verify on second OTP — should not fire |
| D5 | `[NEW]` `feedback_submitted` fires on report | Verify |
| D6 | `[NEW]` No event ever contains SMS body or sender as parameter value | Inspect `adb logcat | rg "Logging event"` |
| D7 | `[NEW]` Toggling consent OFF → events stop within 1 second | Verify |
| D8 | `[NEW]` All event names ≤40 chars, snake_case | Static check |

### Section E — Phase 4 (Crashlytics)

| # | Test | Expected |
|---|---|---|
| E1 | `[NEW]` Force a `RuntimeException` from `ServerClassifier` | Crashlytics receives report with custom keys |
| E2 | `[NEW]` PII placeholder works: log `"Bad OTP 123456 from +919876543210"` via SafeError | Crashlytics shows `"Bad OTP <digits:6> from <phone>"` |
| E3 | `[NEW]` Custom keys `default_sms`, `inference_mode`, `install_age_days` present on every report | Verify |
| E4 | `[NEW]` AppLog calls in UI/ViewModel layer NOT migrated (no Crashlytics noise) | Code grep |

### Section F — Phase 5 (Redaction)

| # | Test | Expected |
|---|---|---|
| F1 | `[NEW]` Unit tests pass | `./gradlew :app:testDebugUnitTest --tests "*SmsRedactor*"` |
| F2 | `[NEW]` Receive a real OTP, tap "Report as wrong" → preview shows redacted body with random digits | Visual |
| F3 | `[NEW]` Send the report → backend receives the redacted version | Verify backend log |
| F4 | `[NEW]` Local Misclassification log shows the ORIGINAL body | Yes |
| F5 | `[NEW]` Same SMS reported from two devices produces different random digits | Yes (because salt = installId) |
| F6 | `[NEW]` Same SMS reported twice from same device produces SAME random digits | Yes (deterministic) |

### Section G — Phase 6 (Satisfaction prompts)

| # | Test | Expected |
|---|---|---|
| G1 | `[NEW]` D1 prompt fires on first foreground after 24h | Use debug menu to backdate `first_open_at` |
| G2 | `[NEW]` Picking 5 emojis logs correct score | Verify event |
| G3 | `[NEW]` D5 prompt fires after 5 days | Use debug menu |
| G4 | `[NEW]` Score ≥ 4 → Play In-App Review API invoked | Visual |
| G5 | `[NEW]` Score ≤ 3 → text input → submit → backend `/feedback` receives `kind=satisfaction` | Backend log |
| G6 | `[NEW]` Each prompt shows at most once | Verify by trying to retrigger |
| G7 | `[NEW]` Onboarding consent not yet seen → no prompts | Verify |

### Section H — Phase 7 (Trial + entitlement) — CRITICAL

| # | Test | Expected |
|---|---|---|
| H1 | `[NEW]` FREE state, receive transactional SMS → no `/classify` server call | `adb logcat | rg ServerClassifier` shows nothing |
| H2 | `[NEW]` FREE state, receive transactional SMS → notification still appears, classified by heuristic | Visual |
| H3 | `[NEW]` FREE state, receive an OTP → trial starts, banner appears, server call HAPPENS for this message | Yes |
| H4 | `[NEW]` TRIAL_ACTIVE, receive subsequent OTP → server call happens | Yes |
| H5 | `[NEW]` Backdate trial 8 days → state flips to TRIAL_EXPIRED | Yes |
| H6 | `[NEW]` TRIAL_EXPIRED, receive OTP → no server call, heuristic-only label, "🔒 Unlock Pro" placeholder in detail screen | Yes |
| H7 | `[NEW]` Inbox top bar shows "Unlock Pro" when not Pro | Yes |
| H8 | `[NEW]` `pro_feature_blocked` event fires when free user taps a Pro placeholder | Yes |
| H9 | `[NEW]` Crashlytics custom key `inference_mode` updates when state changes | Yes |
| H10 | `[NEW]` Existing messages classified during TRIAL keep their server-derived labels after expiry | No retroactive blanking |
| H11 | `[CRITICAL]` Audit ALL nullable accesses to `serverResult`, `phishScore`, `otpIntent`, `isPhishing` — NO null pointer crashes when serverResult == null | Code review + instrumented test |
| H12 | `[CRITICAL]` Notification renders correctly with serverResult == null (heuristic-detected OTP shows code, no phishing badge) | Visual |
| H13 | `[CRITICAL]` Misclassification report flow works in FREE state (some predicted fields are null but upload succeeds) | Verify backend |

### Section I — Phase 8 (Play Billing)

| # | Test | Expected |
|---|---|---|
| I1 | `[NEW]` Paywall opens from inbox CTA | Yes |
| I2 | `[NEW]` Paywall opens from detail "🔒 Unlock Pro" | Yes |
| I3 | `[NEW]` Price loads from Play (not hardcoded) | Yes |
| I4 | `[NEW]` Tap Buy → Play overlay → test card → success → state flips to PRO | Yes |
| I5 | `[NEW]` Purchase acknowledged within 3 days (verify Play Console) | Yes |
| I6 | `[NEW]` Reinstall + Restore → state flips back to PRO | Yes |
| I7 | `[NEW]` Refund → reconcile on next foreground → state flips back to FREE | Yes |
| I8 | `[NEW]` Pending state handled gracefully | Yes |
| I9 | `[NEW]` Purchase events fire in Analytics with correct `value` and `currency` | Yes |

### Section J — Phase 9 (Phone auth)

| # | Test | Expected |
|---|---|---|
| J1 | `[NEW]` Post-purchase, phone auth screen appears | Yes |
| J2 | `[NEW]` Skip → returns to inbox, no PRO state lost | Yes |
| J3 | `[NEW]` Real phone number → SMS arrives → enter code → success | Yes |
| J4 | `[NEW]` Auto-fill via SMS Retriever (if SHA-1 set up) | Yes |
| J5 | `[NEW]` Settings → Account shows masked phone | Yes |
| J6 | `[NEW]` Sign out + reinstall + sign in → state flips back to PRO | Yes |
| J7 | `[NEW]` Wrong code → clear error message, retry possible | Yes |
| J8 | `[NEW]` `phone_auth_started` and `phone_auth_completed` events fire | Yes |

### Section K — Phase 10 (Listing automation)

| # | Test | Expected |
|---|---|---|
| K1 | `[NEW]` `./gradlew bootstrapReleaseListing` succeeds | Yes |
| K2 | `[NEW]` Edit `title` → `./gradlew publishListing` updates Play Console | Yes |

### Section L — Phase 11 (Meta SDK)

| # | Test | Expected |
|---|---|---|
| L1 | `[NEW]` Meta consent OFF → zero Meta network calls | Verify with mitmproxy or `adb logcat | rg facebook` |
| L2 | `[NEW]` Meta consent ON → conversion events appear in Meta Events Manager test mode | Yes |
| L3 | `[NEW]` `purchase_completed` logged via `logPurchase(BigDecimal, Currency)` | Yes |

### Section M — Phase 12 (Compliance)

| # | Test | Expected |
|---|---|---|
| M1 | `[NEW]` Privacy Policy URL loads, mentions every collected data type | Manual review |
| M2 | `[NEW]` Data Safety form in Play Console matches Privacy Policy exactly | Manual review |
| M3 | `[NEW]` Account deletion → backend wipes data, local Room DB cleared, Firebase signed out | Yes |

### Section N — End-to-end happy path

Runs the complete user journey on a real device with a real SIM:

1. Fresh install → consent screen → toggle Analytics + Crash ON → Continue.
2. Set as default SMS app.
3. Receive a real Amazon OTP.
4. Verify trial banner appears.
5. Verify auto-fill works in Amazon's login screen.
6. Use the app for ~5 minutes, mark a misclassified SMS.
7. Wait 24h → D1 prompt appears, pick 5.
8. Wait 5d (or backdate via debug menu) → D5 prompt appears, pick 5 → Play review overlay.
9. Wait 8d (or backdate) → trial expires → "🔒 Unlock Pro" placeholders appear.
10. Tap Unlock → paywall → buy (Internal Testing card) → purchase succeeds.
11. Phone auth screen → enter real number → SMS arrives → verify → success.
12. Verify all features back to working: server classification active, intent + phishing visible.
13. Uninstall, reinstall fresh → consent → sign in via Settings → state flips to PRO.
14. Settings → Delete my data → confirm → all data wiped.

If any step fails or crashes, that's a hard release-blocker.

### Section O — Performance & stability sanity

- Load 1000 mock SMS into the inbox → scroll smoothly at 60fps.
- Background classification of 100 SMS in burst → no ANR.
- 24h soak test on idle phone → no battery drain anomaly.

---

## Cleanup

When ALL phases are complete and ALL Section A regression tests pass:

1. Bump `versionCode` and `versionName` in `app/build.gradle.kts`.
2. Update `app/src/main/play/release-notes/en-US/default.txt` with user-facing release notes.
3. Run `.\gradlew publishReleaseBundle --track=internal` first to validate the upload.
4. Promote to beta after one round of user testing.
5. **Delete this file** (`MONETIZATION_AND_GROWTH_PLAN.md`).
6. Commit with message: `feat: monetization, telemetry, trial gating, phone auth (v1.x.x)`.

---

## Backend changes summary `[BACKEND]`

For the human user to forward to the Cloud Run backend repo. Not implemented in this workspace.

| Endpoint | Method | Purpose | Phase |
|---|---|---|---|
| `/users/trial-start` | POST | `{installId, firebaseUid?, startedAt}` — record trial start (analytics only) | 7 |
| `/users/me` | GET | Returns `{pro: bool, purchaseToken?: string}` for the calling `firebaseUid` | 9 |
| `/users/link-phone` | POST | `{installId, firebaseUid, purchaseToken}` — bind purchase to uid | 9 |
| `/users/me` | DELETE | Wipe user data on request | 12 |
| `/feedback` | POST | Existing endpoint, accept new optional fields: `firebaseUid`, `bodyRedactionScheme`, `kind` (`"misclass"` default, `"satisfaction"` for D5) | 5, 6 |

Schema additions: feedback table needs `firebase_uid`, `body_redaction_scheme`, `kind` columns. Add a `users` table keyed by `firebase_uid` storing `(installId, purchase_token, purchased_at, refunded_at, created_at)`.

---

## Decision log (for context if questions arise)

- One-time purchase chosen over subscription: simpler, less Indian-user friction, but trial enforced client-side (acceptable: bypass requires reinstall; phone-bound entitlement defeats this for paying users).
- Phone auth deferred to post-purchase: keeps free user journey friction-free; ironically avoids the "SMS app needs SMS to verify itself" trust issue.
- Heuristic-only fallback for free users: dramatic feature-quality difference is the point — drives trial-to-paid conversion via real, perceived value.
- Digits-only redaction: preserves structural information for ML retraining while removing all sensitive numeric content. Letters/structure preserved for human-readable diagnosis.
- No Firestore: existing Cloud Run + DB is the source of truth. Firestore would create a second source of truth. Avoid.
- Crashlytics PII stripper: defense in depth — even if a developer accidentally logs an SMS body in an exception, it gets sanitised before leaving the device.
