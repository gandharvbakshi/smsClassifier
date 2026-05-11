# Implementation Handoff — Cleanups & Next Phases

> **Audience:** smaller / faster delegate models executing well-bounded tasks.
> **Lead orchestrator:** keeps debugging, architecture, and final review.
> **Project:** `android_sms_classifier` (the Android app at repo root).
> Companion document: `MONETIZATION_AND_GROWTH_PLAN.md`.

## How to use this file

1. Pick **one task** from the table below per delegation.
2. Read the **entire** task block (Goal, Files, Steps, Verification, Gotchas) before editing.
3. Follow `AGENTS.md` Diff Discipline — minimal changes only, no drive-by refactors.
4. After every code edit, run `./gradlew.bat assembleDebug` from the repo root.
5. Report back using the template at the end of each task.

## Task index

| ID | Title | Effort | Risk | Depends on |
|---|---|---|---|---|
| T1 | De-duplicate `paywall_shown` event | XS | low | — |
| T2 | `SatisfactionPromptHost` polish | S | low | — |
| T3 | `ClassificationWorker` network constraint — fix the comment, harden the path | S | low | — |
| T4 | Manifest + build hygiene (`extractNativeLibs`, Coil keep-rules) | S | low | — |
| T5 | Play Billing readiness — Play Console checklist + minor app polish | S (code) + USER ACTION | medium (Play side) | Internal Testing track |
| T6 | Phone Auth — full Firebase Phone Auth flow | M | medium | Firebase Console enablement |
| T7 | Delete my data — Layer A (local wipe + signOut + email fallback) | S | low | — |
| T8 | Delete my data — Layer B (backend `DELETE /users/me`) | M | medium | `[BACKEND]` endpoint |

> Convention: `[USER ACTION]` = something only the human operator can do (Play Console, Firebase Console, signing keys). `[BACKEND]` = work in the `beta backend` project, not this repo.

---

## T1 — De-duplicate `paywall_shown` event

**Project:** `android_sms_classifier`  
**Task classification:** small (mechanical edit)  
**Effort:** ~5 min

### Goal

Currently `paywall_shown` fires twice when the user opens the paywall from Settings:
1. The Settings row's `onClick` logs `paywall_shown(trigger="settings")` before navigating.
2. `PaywallScreen.LaunchedEffect(Unit)` then logs `paywall_shown(trigger=<param>)` on entry.

Single source of truth: **`PaywallScreen` owns the event.** Settings should only navigate.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` — find the "Upgrade to Pro" row (`logEvent("paywall_shown", mapOf("trigger" to "settings"))` near the `onNavigateToPaywall()` call).
- `app/src/main/java/com/smsclassifier/app/ui/screens/PaywallScreen.kt` — confirm the `LaunchedEffect(Unit)` block already logs `paywall_shown` with `telemetryTrigger`. **Do not change this file.**

### Files likely to change

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` (1 line removed).

### Steps

1. In `SettingsScreen.kt`, locate the `SettingsRow` whose label is "Upgrade to Pro".
2. Inside its `onClick = { ... }` block, **remove only** the `AppContainer.telemetry.logEvent("paywall_shown", ...)` line.
3. Keep the `onNavigateToPaywall()` call. The `MainActivity` route is `paywall/settings`, so `PaywallScreen` will log with `trigger="settings"` automatically.

### Verification

- `./gradlew.bat assembleDebug` succeeds.
- Manual: open Settings → tap "Upgrade to Pro" → check Logcat for **exactly one** `paywall_shown` Firebase event with `trigger=settings`.

### Gotchas

- Do not remove the `onNavigateToPaywall()` call.
- Do not change `PaywallScreen.kt`.

### Reporting template

```
T1 result:
Files changed:
Build result:
Logcat verification (one event vs two):
```

---

## T2 — `SatisfactionPromptHost` polish

**Project:** `android_sms_classifier`  
**Task classification:** small  
**Effort:** ~30 min

### Goal

The current dialog uses Material 3 `AlertDialog` with `confirmButton = {}` (empty composable). This renders correctly on most devices but looks unbalanced and is technically discouraged. Also missing: emoji content descriptions, suppression while sensitive screens are visible, and per-session debounce.

### Behavioural requirements (final state)

1. Dialog only shows when `consentCompleted == true` AND `peekNextPrompt()` returns non-null.
2. **Suppress** while the current Nav route is `consent_onboarding`, `paywall/{trigger}`, or `phone_auth`.
3. Replace the empty `confirmButton` with either:
   - A `TextButton("Submit")` (disabled until a score is selected), OR
   - Restructure so the 5 emoji buttons are themselves the confirm action and use only `dismissButton = TextButton("Skip")`. **Preferred.**
4. Each emoji `TextButton` must set `Modifier.semantics { contentDescription = "Rate <n> of 5: <face name>" }` (e.g. "Rate 1 of 5: angry").
5. After dismissal (Skip or after-rating), call `mgr.markDismissedSession()` so the same session does not retry.
6. Per-app-process: never show more than once. Already handled by `sessionShown`. Verify it's still true after the refactor.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/components/SatisfactionPromptHost.kt`
- `app/src/main/java/com/smsclassifier/app/feedback/SatisfactionPromptManager.kt`
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt` — to inject the current Nav route into the host (read-only suggestion below).

### Files likely to change

- `app/src/main/java/com/smsclassifier/app/ui/components/SatisfactionPromptHost.kt`
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt` — pass `currentRoute` into `SatisfactionPromptHost(consentCompleted = ..., currentRoute = currentRoute)`.

### Steps

1. Add a new optional parameter `currentRoute: String? = null` to `SatisfactionPromptHost`. In the `LaunchedEffect`, return early if `currentRoute in setOf("consent_onboarding", "phone_auth")` or starts with `"paywall/"`.
2. Replace `confirmButton = {}` with `confirmButton = { TextButton(onClick = { finish(kind) }) { Text("Skip") } }` and remove the duplicate `dismissButton`. **OR** preferred: keep `dismissButton = TextButton("Skip")` and pass `confirmButton = {}` only after switching to Material 3's `BasicAlertDialog` if available — check the Compose BOM in `app/build.gradle.kts` (`androidx.compose:compose-bom:2024.06.00`); `BasicAlertDialog` exists, prefer it for a custom layout that needs no confirm button.
3. Add `Modifier.semantics { contentDescription = ... }` to every emoji button.
4. Wire `currentRoute = currentRoute` from `MainActivity` (the route is already read via `currentBackStackEntryAsState`).
5. Call `mgr.markDismissedSession()` inside `finish(kind)` if not already called.

### Verification

- `./gradlew.bat assembleDebug` succeeds.
- Manual: open paywall — dialog must NOT appear. Open inbox — dialog appears once after ~1.8s if eligible. Tap an emoji — dialog dismisses. Reopen app — depending on D1/D5 windows it should appear again only when due.
- TalkBack: announce "Rate 4 of 5: smiling" when focused on the smiling button.

### Gotchas

- `BasicAlertDialog` is in `androidx.compose.material3` but tagged `@ExperimentalMaterial3Api`. Add `@OptIn(ExperimentalMaterial3Api::class)` if you go this route.
- Do not change `SatisfactionPromptManager.kt` storage keys; they already gate D1/D5 across sessions.

### Reporting template

```
T2 result:
Files changed:
Build result:
Manual UX verification:
TalkBack verification:
```

---

## T3 — `ClassificationWorker.enqueue` constraint hygiene

**Project:** `android_sms_classifier`  
**Task classification:** small (comment + light hardening)  
**Effort:** ~20 min

### Goal

The constraint `NetworkType.NOT_REQUIRED` is **correct** for the heuristic-first design (FREE tier must run offline). The comment in source ("Temporarily use NOT_REQUIRED to test if network constraint is blocking … Will change back to CONNECTED once we confirm worker runs") is misleading and gives the impression of a TODO. Two changes:

1. Update the comment so future readers understand `NOT_REQUIRED` is the chosen design.
2. Inside `doWork()`, when `useServer == true`, check connectivity. If offline, **skip the server call and fall back to heuristic** without throwing.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/work/ClassificationWorker.kt`
- `app/src/main/java/com/smsclassifier/app/classification/ServerClassifier.kt` (read-only — confirm it throws on no network).
- `app/src/main/java/com/smsclassifier/app/util/AppLog.kt` (read-only).

### Files likely to change

- `app/src/main/java/com/smsclassifier/app/work/ClassificationWorker.kt`

### Steps

1. Replace the misleading comment in `enqueue()` with something like:
   - "Heuristic-first design: workers must run offline for FREE-tier users. Server call inside `doWork` is best-effort and short-circuits when offline."
2. Inside `doWork()`, just before the `ServerClassifier().predict(features)` call, add a connectivity check using `ConnectivityManager.activeNetwork` (or `NetworkCapabilities.NET_CAPABILITY_INTERNET`). If unavailable: log via `AppLog.d`, do NOT call server, use `hPred` directly (same as the catch branch).
3. Telemetry (optional): increment a count via `AppContainer.telemetry.logEvent("server_classify_skipped_offline", emptyMap())` — only if `Telemetry.validateParams` accepts an empty map; otherwise omit.

### Verification

- `./gradlew.bat assembleDebug` succeeds.
- Manual on a device: turn airplane mode ON, force-trigger classification (send a test SMS), confirm Logcat shows the offline-skip path and the message ends up classified by heuristic only (`isPhishing == null`). Turn airplane mode OFF, send another, server path runs.

### Gotchas

- Do **not** change the `Constraints.Builder().setRequiredNetworkType(...)` value.
- `ConnectivityManager` requires `ACCESS_NETWORK_STATE` permission — already in `AndroidManifest.xml`.

### Reporting template

```
T3 result:
Files changed:
Build result:
Airplane mode test:
```

---

## T4 — Manifest + build hygiene

**Project:** `android_sms_classifier`  
**Task classification:** small  
**Effort:** ~15 min

### Goals

Two unrelated low-risk hygiene fixes batched together because they're tiny.

#### 4a. `extractNativeLibs` deprecation warning

`AndroidManifest.xml` line 23 uses `android:extractNativeLibs="true"`. AGP recommends moving this to `app/build.gradle.kts`'s `packaging.jniLibs.useLegacyPackaging = true` (which already exists). Therefore the manifest attribute is redundant.

#### 4b. Coil release/R8 keep rules

`io.coil-kt:coil-compose:2.5.0` was added in this round. Coil ships its own consumer-proguard rules; just confirm release builds (`./gradlew.bat assembleRelease`) still load avatar images. No code change unless release breaks.

### Files to inspect

- `app/src/main/AndroidManifest.xml`
- `app/build.gradle.kts`
- `app/proguard-rules.pro`
- `app/src/main/java/com/smsclassifier/app/ui/components/ConversationItem.kt` (read-only).

### Files likely to change

- `app/src/main/AndroidManifest.xml` (remove `android:extractNativeLibs="true"` from `<application>`).

### Steps

1. Remove the `android:extractNativeLibs="true"` attribute from the `<application>` tag.
2. Re-run `./gradlew.bat assembleDebug` to confirm no warning regression.
3. Run `./gradlew.bat assembleRelease`. If R8 strips Coil and avatars don't render in release builds, add coil's keep rules to `proguard-rules.pro` (Coil 2.x consumer rules normally suffice; only add manually if signed APK shows missing symbols).

### Verification

- Build succeeds (debug + release).
- `adb logcat | rg extractNativeLibs` shows no warning after the manifest change.

### Gotchas

- Do not touch `useLegacyPackaging = true` in `app/build.gradle.kts` — it was set deliberately.

### Reporting template

```
T4 result:
Files changed:
Debug build:
Release build:
Manifest warning gone (Y/N):
```

---

## T5 — Play Billing readiness checklist

**Project:** `android_sms_classifier` + `[USER ACTION]` Play Console  
**Task classification:** mostly USER ACTION; tiny code polish allowed  
**Effort:** ~30 min code, ~1h Play Console

### Goal

The app code is complete (`PlayBillingRepository`, `PaywallScreen`, `EntitlementManager.markPurchasedFromPlay`). Real purchases require Play Console configuration. This task documents the gating steps.

### `[USER ACTION]` checklist (operator must do this; do NOT ask the model to do it)

1. Play Console → app → **Monetize → Products → In-app products** → create:
   - Product ID: `pro_lifetime`
   - Type: One-time
   - Status: Active
   - Price: set local prices (or default tier)
   - Title and description: "SMS Classifier Pro" / 1-line description.
2. Build, sign, and upload an **Internal Testing** AAB with `versionCode > current production`. Promote to Internal track.
3. Play Console → **Setup → License testing** → add tester Google accounts. Make sure the device's primary Google account is in this list.
4. On the test device, opt in to the Internal Testing track via the share link.
5. Re-open the app on the device. Open paywall — price should now render (e.g. "Unlock Pro — ₹399").

### Code polish (small, optional, do this in the same PR if time)

#### 5a. Surface `purchase_failed` to the user

Current `PlayBillingRepository.listener` logs the failure to telemetry but the UI is silent. Add a `MutableSharedFlow<String>` named `purchaseError` in `PlayBillingRepository`, emit a friendly message ("Purchase couldn't complete — try again or restore."), and `collect` it in `PaywallScreen` to show a `Snackbar`.

#### 5b. Auto-launch phone-auth screen after first paid purchase

After `purchaseSuccess.tryEmit(Unit)` runs in `handlePurchase`, the `MainActivity` `LaunchedEffect` already pops back to the previous screen. Optional: navigate to `phone_auth` instead of popping when `wasPaidPro == false`. **Only ship this once T6 (Phone Auth) is implemented**; otherwise the user lands on a stub.

#### 5c. Disable the Buy button while the billing flow is in flight

Track `isLaunching: MutableStateFlow<Boolean>` in `PlayBillingRepository`. Set `true` in `launchBillingFlow`, set `false` in the `listener` callback. `PaywallScreen` collects this state and uses it to enable/disable the Buy button.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/billing/PlayBillingRepository.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/PaywallScreen.kt`
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt`

### Verification

- After `[USER ACTION]` 1–4, `PaywallScreen` shows the real price within 2s of opening.
- License-testing tester sees a "Test card, always approves" purchase option.
- After purchase, `EntitlementManager.isPaidPro()` returns true and the inbox banner switches off.

### Gotchas

- A new product ID can take up to a few hours to propagate. If you see no price after 30 min on a fresh build, check the Play Console product **Status = Active**.
- Play Billing requires the app to be **published to at least one track** (Internal counts) for `productDetails` to resolve, even with a license tester account.
- Do NOT bump `versionCode` in this task; that's part of release. Only do it during the actual release PR.

### Reporting template

```
T5 result:
Code polish included (5a/5b/5c):
Files changed:
Build result:
Play Console checklist run by operator (Y/N):
Tester device sees price (Y/N):
```

---

## T6 — Firebase Phone Auth — replace stub

**Project:** `android_sms_classifier` + `[USER ACTION]` Firebase Console  
**Task classification:** medium  
**Effort:** ~3–5h code + ~30 min Firebase setup

### Goal

`PhoneAuthScreen.kt` is currently a one-screen stub. Replace with a real two-step flow:

1. **Step A — phone entry:** country code picker + national number → "Send code".
2. **Step B — OTP entry:** 6-digit code field → "Verify". Resend after 30s.
3. On success: store Firebase Auth UID via `Firebase.auth.currentUser.uid`, set Crashlytics user identifier, log `phone_auth_completed` with `success=true`, navigate back.
4. On error or skip: log with reason, navigate back. Do not block the user from using the app.

### `[USER ACTION]` Firebase Console (operator must do this)

1. Firebase Console → Authentication → **Sign-in method** → enable **Phone**.
2. Project Settings → Add the **debug** SHA-1 (`./gradlew.bat signingReport` to print) and the **release** SHA-1 (from your upload key).
3. Project Settings → Add the **Play App Signing** SHA-256 (Play Console → Setup → App integrity).
4. Authentication → **Settings → Authorized domains** — leave defaults.
5. Optional: Authentication → **Settings → Phone numbers for testing** — add one test number with a fixed code so QA can verify without real SMS quota.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/PhoneAuthScreen.kt` (current stub)
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt` (route already registered as `phone_auth`)
- `app/build.gradle.kts` (`firebase-auth-ktx` already declared)
- `app/src/main/AndroidManifest.xml` (no extra perm needed; `android.permission.INTERNET` is enough)

### Files likely to change

- `app/src/main/java/com/smsclassifier/app/ui/screens/PhoneAuthScreen.kt` — full rewrite.
- A new `app/src/main/java/com/smsclassifier/app/auth/PhoneAuthRepository.kt` — encapsulate Firebase Phone Auth APIs (state, callbacks, verification id, resend token).
- `app/src/main/java/com/smsclassifier/app/util/CrashlyticsBootstrap.kt` — extend to set `setUserId(uid)` when called with a non-null UID.
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt` — pass `auth` repo or wire via `AppContainer`.
- `app/src/main/java/com/smsclassifier/app/AppContainer.kt` — add `lateinit var phoneAuthRepository`.

### Architecture (suggested)

```
PhoneAuthRepository
  state: MutableStateFlow<AuthState>
    AuthState.Idle
    AuthState.AwaitingCode(verificationId, resendToken)
    AuthState.Success(uid)
    AuthState.Error(messageRes)
  fun sendCode(activity, e164PhoneNumber)
  fun verify(code: String)
  fun resend(activity, e164PhoneNumber)

PhoneAuthScreen
  val state by repo.state.collectAsState()
  when (state):
    Idle -> PhoneEntryStep
    AwaitingCode -> OtpEntryStep with 30s countdown
    Success -> LaunchedEffect { onDoneSkip() }
    Error -> Snackbar + back to PhoneEntry
```

### Steps

1. Add `PhoneAuthRepository.kt` (Phase 9 in `MONETIZATION_AND_GROWTH_PLAN.md` has a sketch — update API surface to match Firebase 23.x).
2. Wire it through `AppContainer.init`.
3. Rewrite `PhoneAuthScreen.kt` per the architecture above. Use a simple country-code dropdown (curated list of top 10 countries — full libphonenumber is overkill at this stage).
4. Validate phone with a local regex before calling `sendCode`.
5. After `Success`, call `CrashlyticsBootstrap.setUserId(uid)` (new helper). Telemetry: `phone_auth_completed` with `success=true`.
6. On `Error`: show snackbar with the localized message; telemetry `phone_auth_completed` with `success=false, reason=<short>` — keep PII out of the reason.

### Verification

- `./gradlew.bat assembleDebug` succeeds.
- Manual with a real Indian number: enter +91 followed by 10 digits → "Send code" → SMS arrives → 6-digit code → "Verify" → success → returns to inbox. Crashlytics dashboard later shows custom key for the new user.
- Test number (from Firebase Console "Phone numbers for testing"): bypasses real SMS.

### Gotchas

- Phone Auth requires either Play Integrity or reCAPTCHA. On emulators without Play Services, reCAPTCHA WebView appears — that's expected.
- SHA-1 mismatch is the #1 cause of "App not authorized" errors. Always re-add SHA after rotating the upload key.
- Don't write the phone number to local prefs. Only persist the Firebase UID (already done by `Firebase.auth`). Privacy Policy disclosure required (see Phase 12).
- Do NOT auto-launch phone-auth from anywhere except after a successful purchase. Otherwise FREE-tier users will see it and bounce.

### Reporting template

```
T6 result:
Files changed:
Files added:
Build result:
Firebase Console steps confirmed by operator (Y/N):
Test number flow verified:
Real number flow verified:
```

---

## T7 — Delete my data — Layer A (local wipe + signOut + email fallback)

**Project:** `android_sms_classifier`  
**Task classification:** small  
**Effort:** ~1.5h

### Goal

Replace the placeholder dialog at `SettingsScreen.kt` ("Server-side deletion will be available in a future update") with a real local-wipe flow. Backend wipe arrives in T8; this layer ships **today**.

### Behaviour

1. Settings → Privacy & Data → **Delete my data** → confirmation dialog with bold copy: "This permanently removes all SMS classifications, feedback, and account data on this device. Your purchase will be preserved by Google Play. Continue?"
2. On confirm:
   - Show a blocking spinner.
   - Wipe **Room database** (`AppDatabase.getDatabase(ctx).clearAllTables()`).
   - Wipe **DataStore** entries except: consent flags (`onboardingConsentSeen`, `analyticsConsent`, `crashlyticsConsent`, `metaAdsConsent`).
   - Wipe SharedPreferences: `entitlement_prefs`, `satisfaction_prefs`, `telemetry_launch`, but **preserve** `pro_purchased`/`pro_purchase_token` so a paid user does not lose their purchase.
   - `FirebaseAuth.getInstance().signOut()` (no-op if not signed in).
   - Open an `ACTION_SENDTO` email intent pre-filled with `mailto:support@<your-domain>?subject=Delete%20my%20data%20—%20<installId>&body=Please%20remove%20uploaded%20feedback%20samples%20tied%20to%20this%20install%20id.`
   - Telemetry: `delete_data_requested` with `layer="local"`.
3. After spinner: snackbar "Local data deleted. Email request opened — please send it to complete server-side deletion."
4. Navigate user back to `consent_onboarding` only if `onboardingConsentSeen == false` was just set. Otherwise stay on Settings.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/viewmodel/SettingsViewModel.kt`
- `app/src/main/java/com/smsclassifier/app/data/AppDatabase.kt`
- `app/src/main/java/com/smsclassifier/app/data/SettingsRepository.kt`
- `app/src/main/java/com/smsclassifier/app/analytics/ConsentManager.kt`
- `app/src/main/java/com/smsclassifier/app/entitlement/EntitlementManager.kt`

### Files likely to change

- `app/src/main/java/com/smsclassifier/app/ui/viewmodel/SettingsViewModel.kt` — add `deleteLocalData(): Result<Unit>` suspend function.
- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` — replace placeholder dialog with the new confirmation + spinner.
- (Optional) `app/src/main/java/com/smsclassifier/app/data/SettingsRepository.kt` — small helper `clearAllExceptConsent()`.

### Steps

1. Add `SettingsViewModel.deleteLocalData()` that performs all the wipe steps in `Dispatchers.IO`.
2. Replace the `AlertDialog` in `SettingsScreen.kt` with a 3-state machine: confirm → loading → done. Use `LaunchedEffect` to call the VM function.
3. Build the email intent. Read `installId` from `SettingsRepository(context).installId`. Use `Intent.ACTION_SENDTO` with `mailto:` URI. Wrap in `try/catch` so devices without an email app don't crash.
4. Disable the button while the operation is in flight.
5. Confirm `EntitlementManager.isPaidPro()` still returns true after wipe (purchase preserved).

### Verification

- `./gradlew.bat assembleDebug` succeeds.
- Manual:
  - With sample messages and feedback in DB → tap delete → confirm → DB tables empty (verify via `adb shell run-as <pkg> sqlite3 ...` or the Database Inspector).
  - `analyticsConsent` and friends remain on if they were on.
  - On a Pro device: `EntitlementManager.isPaidPro()` still true after wipe.
  - Email intent opens Gmail/Outlook with prefilled subject containing the install id.

### Gotchas

- `clearAllTables()` MUST run on a background thread — it throws on main.
- `FirebaseAuth.signOut()` is sync and safe.
- Do NOT delete the file `entitlement_prefs` wholesale — only the trial/banner keys. Purchase keys must survive.
- If the user is on `onboarding`, do not show this CTA at all (already gated by `currentRoute != "consent_onboarding"` in the bottom bar).

### Reporting template

```
T7 result:
Files changed:
Build result:
DB wipe verified:
Consent flags preserved:
Pro purchase preserved:
Email intent opens:
```

---

## T8 — Delete my data — Layer B (backend wipe)

**Project:** `android_sms_classifier` + `beta backend`  
**Task classification:** medium  
**Effort:** ~2h app + `[BACKEND]` work

### Goal

Replace the email fallback from T7 with a real `DELETE /users/me?installId=X[&uid=Y]` HTTPS call to the backend. After backend confirms (HTTP 200/204), proceed with the local wipe (same as T7).

### Prerequisites

- T7 must be merged.
- `[BACKEND]` (in the `beta backend` project) must implement and deploy the endpoint:
  - `DELETE /api/users/me?installId={anonId}&uid={firebaseUid}` (uid optional)
  - Auth: signed request — for the MVP, accept the `installId` as the bearer (low security; rotate to Firebase ID Token later).
  - Response: 204 on success, 404 if no records, 5xx on error.
  - Side-effects: delete from `feedback`, `satisfaction`, `trial`, `purchase_tokens` tables. Keep an anonymised purchase row for accounting.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/feedback/FeedbackUploader.kt` — reference for the `OkHttpClient` pattern, base URL config, install id header.
- `app/build.gradle.kts` — `SERVER_API_BASE_URL` buildConfigField is already set.
- `app/src/main/java/com/smsclassifier/app/ui/viewmodel/SettingsViewModel.kt` — extend the `deleteLocalData()` from T7.

### Files likely to change

- New: `app/src/main/java/com/smsclassifier/app/data/DeleteAccountClient.kt` — encapsulates the HTTP call.
- `app/src/main/java/com/smsclassifier/app/ui/viewmodel/SettingsViewModel.kt` — change to `suspend fun deleteAllData(): Result<Unit>` that calls the client first, then runs T7 local wipe.
- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` — drop the email intent now that the backend is wired.

### Steps

1. Add `DeleteAccountClient` with a single `suspend fun delete(installId: String, uid: String?): Result<Unit>` that sends a `DELETE` request via `OkHttpClient`. Time out at 10s.
2. In the VM, `client.delete(...)` first. On success (or 404), proceed to local wipe and return `Result.success`. On 5xx, return `Result.failure(...)` and surface a snackbar with retry.
3. Telemetry: log `delete_data_requested(layer="backend", success=true|false)`.
4. Remove the email intent path — keep it only as a recovery option behind a `BuildConfig.DEBUG` debug button (optional).

### Verification

- `./gradlew.bat assembleDebug` succeeds.
- Manual against staging backend: tap Delete → see network request → see 204 → local wipe runs → snackbar "All data deleted."
- Negative path: with backend down, snackbar shows "Couldn't reach server, try again."

### Gotchas

- Coordinate `[BACKEND]` deployment timing. Don't ship the app change before the endpoint is live, or users will see errors.
- Do not block UI for >10s; wrap in a coroutine with `withTimeout`.
- Privacy Policy must reflect that data is deleted server-side. Do NOT release this code path until the policy is updated (Phase 12.1 in the plan).

### Reporting template

```
T8 result:
Files changed:
Files added:
Backend endpoint deployed (Y/N):
Build result:
Happy-path manual test:
Failure-path manual test:
Privacy Policy updated (Y/N):
```

---

## Cross-task delegation plan

| Order | Task | Delegate to | Rationale |
|---|---|---|---|
| 1 | T1, T4 | small/cheap model | mechanical, safe, < 30 min each |
| 2 | T3 | small/cheap model | comment + small connectivity check |
| 3 | T2 | small model | careful Compose edit; verify rendering |
| 4 | T7 | small model | bounded, no external dependencies |
| 5 | T5 | lead model + operator | mostly Play Console; code polish needs care around purchase/recovery flows |
| 6 | T6 | strong model | UI + Firebase + reCAPTCHA edge cases |
| 7 | T8 | strong model + `[BACKEND]` coordination | cross-project, requires deploy timing |

## Final QA pass after all tasks (lead model only)

- Run `./gradlew.bat assembleDebug` and `./gradlew.bat assembleRelease`.
- Smoke-test on a real device using the Section A regression checklist in `MONETIZATION_AND_GROWTH_PLAN.md` (lines ~1246+).
- Manually sweep Logcat for new `paywall_shown`, `purchase_*`, `phone_auth_*`, `delete_data_requested`, `satisfaction_*` events — confirm shape, no PII.
- Bump `versionCode` and `versionName` in `app/build.gradle.kts` for the release candidate.
