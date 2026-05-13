# Settings Cleanup — Handoff Doc

> **Audience:** delegate model (Composer 2.0). Stay strictly inside the scope below. Diff Discipline from `AGENTS.md` applies — do not refactor or rename anything not listed in **Files likely to change** for each task. If a task feels ambiguous, STOP and surface in your final report rather than guessing.
>
> **Why this doc exists:** the current settings UI carries vestiges from earlier phases (Meta Ads, server-only inference mode, backend status diagnostics) that confuse normal users and contradict the production product (Google Ads only — no Meta SDK in use). It also has redundancy across the main Settings page, the sub-screens, and the onboarding consent screen.
>
> **Lead orchestrator (Claude) handles:** anything tagged `[LEAD]`. Composer 2.0 handles everything else.

---

## Production reality check (read first, do not change)

- **Meta SDK is not used.** `META_APP_ID` and `META_CLIENT_TOKEN` are empty `BuildConfig` fields, `MetaInit.init` returns at line 10 when `META_APP_ID.isBlank()`, the `AD_ID` permission is stripped via `tools:node="remove"`, and the published privacy policy and Play Data Safety form both declare we do not collect the advertising ID.
- **Inference mode is fixed:** server ensemble during the 7-day trial and Pro; heuristic-on-device after the trial. There is no user-facing knob for this.
- **Misclassification feedback** is uploaded to `gs://sms-classifier-feedback/misclassification/<received_at>_<id>.json` only when the user opts in via "Help improve classification".
- **`paywall_shown` is owned by `PaywallScreen`.** Settings rows must NOT log it again.

---

## Task index

| ID | Title | Effort | Risk |
|---|---|---|---|
| C1 | Remove Meta Ads toggle from onboarding + settings + ConsentManager (UI only — no Firebase Analytics changes) | S | low |
| C2 | Reorganize main Settings: collapse "Classifier" + drop redundant rows | S | low |
| C3 | Move Diagnostics & self-test out of "Help" into an "Advanced" section gated behind a long-press / hidden tap | S | low |
| C4 | Trim Notification sub-screen to one user-facing toggle row + one "Open system settings" button | S | low |
| C5 | Trim Export sub-screen to a single "Export my data" action that emits a zip with all three CSVs | M | medium |
| C6 | Tighten copy across Settings (every subtitle ≤ 60 chars, no jargon, no PII references) | S | low |
| C7 `[LEAD]` | Drop Facebook SDK dependency + delete `MetaInit.kt` (after C1 lands) | S | medium |
| C8 `[LEAD]` | Verify build, run a manual smoke pass, bump version, rebuild AAB | S | low |

> **Composer 2.0 should execute C1–C6 sequentially in that order.** Each task ends with `./gradlew.bat assembleDebug` and a one-line "build green" report before moving to the next.

---

## C1 — Remove Meta Ads toggle (UI only)

### Why

Two user-visible places mention Meta Ads but the Meta SDK is not actually doing anything in production. Worse, asking the user about "Ad campaign measurement (Meta)" when we don't run Meta ads creates trust friction and contradicts the Play Data Safety declaration ("No data collected" / "No data shared with third parties" — see public store listing).

### Goal

After this task, the user never sees the words "Meta", "Ad campaign", or "advertising" anywhere in the app. The boolean still exists in `ConsentManager` for now (so DataStore migrations don't break) but is internal-only and defaults to `false`. C7 will physically remove the SDK dep and `MetaInit.kt`.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` — the "Ad campaign measurement (Meta)" `ToggleRow` (currently around lines 229–239).
- `app/src/main/java/com/smsclassifier/app/ui/screens/ConsentOnboardingScreen.kt` — the "Ad campaign measurement (Meta)" `ConsentToggleRow` (lines 82–87) and the `metaOn` state (lines 46, 86, 101).
- `app/src/main/java/com/smsclassifier/app/analytics/ConsentManager.kt` — keep `KEY_META`, `setMetaAdsConsent`, `metaAdsEnabledNow`, `metaAdsConsent` exactly as they are. Do NOT delete them in this task.

### Files likely to change

- `SettingsScreen.kt` — delete the Meta `ToggleRow` and the preceding `SectionDivider`. Delete the `metaConsent` `collectAsState` that becomes unused. Leave the `KEY_META` machinery alone.
- `ConsentOnboardingScreen.kt` — delete the `metaOn` mutable state, the `ConsentToggleRow` for it, the trailing `Spacer`, and the `consent.setMetaAdsConsent(metaOn)` call.

### Steps

1. In `SettingsScreen.kt`, delete the entire `ToggleRow(title = "Ad campaign measurement (Meta)", ...)` block AND the `SectionDivider()` that immediately precedes it (so we don't end up with two consecutive dividers).
2. Delete the unused `metaConsent` `val` introduced via `AppContainer.consentManager.metaAdsConsent.collectAsState(...)`.
3. In `ConsentOnboardingScreen.kt`, delete the `var metaOn by ...`, the `ConsentToggleRow` for Meta, the `Spacer` immediately before it, and the `consent.setMetaAdsConsent(metaOn)` call inside the `onClick`.
4. Run `./gradlew.bat assembleDebug` and confirm zero new warnings related to unused state.

### Hard rules

- DO NOT touch `ConsentManager.kt`.
- DO NOT remove the `META_APP_ID` / `META_CLIENT_TOKEN` `BuildConfig` fields.
- DO NOT touch `MetaInit.kt`, `AppContainer.kt`, or `app/build.gradle.kts` in this task — that is C7.

### Verification

- Build green.
- Open the app on a fresh install: onboarding shows exactly two toggles (Anonymous usage analytics + Crash reports).
- Open Settings → Privacy & data: there is no Meta row.
- Search the codebase for the literal string "Meta" inside `app/src/main/java/com/smsclassifier/app/ui/`. The only remaining hit must be in non-user-visible code (none expected after this task).

### Reporting

```
C1 result:
Files changed:
Build result:
Onboarding visual check (Y/N):
Settings visual check (Y/N):
```

---

## C2 — Reorganize main Settings

### Current layout (problem)

The main Settings screen currently has these top-level sections in this order: **General**, **Classifier**, **Privacy & data**, **Help**.

Inside **Classifier** there are four rows: `Inference mode (Server ensemble (fixed))`, `Backend status`, `Misclassification logs`, `Help improve classification`. Of these:

- "Inference mode" with no toggle is decorative noise.
- "Backend status" is engineering telemetry, not a user setting.
- "Misclassification logs" overlaps with the Export sub-screen's "Misclassification reports" row.
- "Help improve classification" is the one row that genuinely belongs in Settings, but it's a privacy-impacting toggle, so it should live under Privacy & data, not under a section called "Classifier".

In **Help** the "Diagnostics & self-test" row links to a page full of dev tooling that confuses normal users (latency stats, OTP self-test, default-SMS subscription IDs, provider authority, etc.).

### Goal layout (after this task)

```
General
  Default SMS app
  Notifications
Privacy & data
  Anonymous usage analytics
  Crash reports
  Help improve classification         ← MOVED from Classifier
  Privacy policy
  Export my data
  Delete my data
Pro
  Upgrade to Pro                       ← was in Help; renamed section
Help
  Contact developer
  About
```

Diagnostics & self-test moves out of "Help" entirely — see C3.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt`

### Files likely to change

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` only.

### Steps

1. Delete the entire `ClassifierSection` composable AND its call site. Move the "Help improve classification" `Switch` row into the existing `Privacy & data` section, immediately below the "Crash reports" `ToggleRow`. Use a `SettingsRow` with a trailing `Switch` (mirroring the current shape from `ClassifierSection`). Reuse `feedbackUploadEnabled`, `onFeedbackToggleOff`, `onFeedbackToggleOnConsentNeeded`, `onFeedbackToggleOnGranted` from the parent — do NOT change `SettingsViewModel`.
2. Delete the "Inference mode" row and the "Backend status" row entirely. They are not user-facing decisions.
3. Delete the parent's "Misclassification logs" row from the (now removed) Classifier section. The Export sub-screen already exposes the same data via "Misclassification reports".
4. Rename the `SettingsSection(title = "Help")` to remain "Help" but split off "Upgrade to Pro" into a NEW `SettingsSection(title = "Pro")` placed BETWEEN `Privacy & data` and `Help`.
5. Remove the `onOpenMisclassificationLogs` parameter from `SettingsScreen` (no longer used). Update the call site in `MainActivity.kt` (the only caller) to drop the `onOpenMisclassificationLogs = ...` argument. Do NOT delete the `logs` route or `LogsScreen` itself — Diagnostics will surface it (see C3).

### Hard rules

- DO NOT touch `SettingsViewModel`.
- DO NOT touch `LogsScreen.kt`.
- DO NOT change navigation routes other than removing the now-unused `onOpenMisclassificationLogs` callback param.
- DO NOT change icons unless an icon is genuinely orphaned.

### Verification

- Build green.
- Visual sweep on emulator: all four sections present in the new order; no "Inference mode", no "Backend status", no "Misclassification logs" row at top level; the "Help improve classification" switch toggles correctly and still triggers the existing consent dialog.

### Reporting

```
C2 result:
Files changed:
Section order after change:
Build result:
Toggle still works (Y/N):
```

---

## C3 — Move Diagnostics into a hidden "Advanced" entry

### Why

Diagnostics & self-test exposes provider authority, default-SMS subscription IDs, OTP self-test plumbing, performance latency stats, and a "Notification debug" entry. Normal users do not need any of this and the technical jargon is a Play review risk ("complicated UX" remarks). But power users and the developer DO need it for support tickets.

### Goal

- Remove the "Diagnostics & self-test" row from the visible "Help" section.
- Keep the same `DiagnosticsSubScreen` and route (`settings_diagnostics`).
- Surface entry by long-pressing the "About" row, OR by tapping the version line in About 5 times in a row. Either is acceptable. Prefer the version-tap pattern (Android-standard, used by AOSP "Build number → Developer options").

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt` — the existing "Diagnostics & self-test" row in the Help section.
- `app/src/main/java/com/smsclassifier/app/ui/screens/AboutSubScreen.kt` — currently shows version only.
- `app/src/main/java/com/smsclassifier/app/MainActivity.kt` — the route registrations for `settings_diagnostics` and `settings_about`.

### Files likely to change

- `SettingsScreen.kt` — delete the "Diagnostics & self-test" row from the Help section. Drop the now-unused `onNavigateToDiagnostics` parameter; update the `MainActivity.kt` call site to drop the argument.
- `AboutSubScreen.kt` — implement the 5-tap counter on the "Version" row. Show a `Snackbar` "Diagnostics enabled" on the 5th tap, then call a new `onUnlockDiagnostics()` callback added as a new optional param. The About screen also gets a trailing `SettingsRow` "Diagnostics & self-test" that becomes visible only after unlock (kept-in-state — does not need to persist across navigations for now).
- `MainActivity.kt` — pass `onUnlockDiagnostics = { navController.navigate("settings_diagnostics") }` to `AboutSubScreen`. Remove the diagnostics arg from `SettingsScreen`.

### Hard rules

- DO NOT remove the `settings_diagnostics` route from the NavHost.
- DO NOT remove the `settings_diagnostics` composable destination.
- DO NOT remove `DiagnosticsSubScreen` or any of its supporting view-model code in `SettingsViewModel`.

### Verification

- Build green.
- Settings → Help no longer shows Diagnostics.
- Settings → Help → About → tap version 5 times → snackbar shows → diagnostics row appears → tapping it opens the existing Diagnostics screen unchanged.

### Reporting

```
C3 result:
Files changed:
Hidden gesture chosen (5-tap version / long-press):
Build result:
Diagnostics still reachable (Y/N):
```

---

## C4 — Trim Notifications sub-screen

### Why

`NotificationSettingsSubScreen` has: System notifications status row, Sound toggle, Vibration toggle, "App notifications" button, "Channels" button. Sound + Vibration duplicate what Android already exposes per channel; the "Channels" button is power-user-only.

### Goal

After this task, the screen has exactly:

```
Notifications
  System notifications              ← keep (status + Enable button if disabled)
  Open system notification settings ← single button replacing the two buttons
```

The two custom toggles (Sound + Vibration) are deleted. They are misleading anyway — Android's per-channel sound/vibration already overrides our app-level switch on most OEMs, so the toggles set users up for confusion when their OEM ignores them.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/NotificationSettingsSubScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/viewmodel/SettingsViewModel.kt` — confirm `notificationSoundEnabled`, `notificationVibrationEnabled`, `setNotificationSoundEnabled`, `setNotificationVibrationEnabled` are referenced only here.
- `app/src/main/java/com/smsclassifier/app/util/NotificationHelper.kt` — confirm whether the toggles are wired into actual notification building.

### Files likely to change

- `NotificationSettingsSubScreen.kt` — delete the two `ToggleRow`s and merge the two `OutlinedButton`s into a single full-width "Open system settings" button that calls `viewModel.openNotificationSettings()`.
- DO NOT delete the methods on `SettingsViewModel` or `NotificationHelper.kt` in THIS task — orphan removal is a separate cleanup. Just stop calling them from the UI.

### Hard rules

- DO NOT change Android channel definitions.
- DO NOT remove the `Channels` API call from `NotificationHelper.kt`. Channels still need to exist; we are only hiding the user-facing button to them.

### Verification

- Build green.
- Settings → Notifications shows two rows total. Tapping the button opens the system Notifications page for the app.

### Reporting

```
C4 result:
Files changed:
Rows visible after change:
Build result:
```

---

## C5 — Collapse Export sub-screen into a single action

### Why

The Export sub-screen has three buttons: "Full classification data", "Labels only", "Misclassification reports". Most users will not understand which to pick. Privacy regulators (GDPR Article 15 — right to access) want one obvious "give me all my data" button.

### Goal

Single primary action "Export my data" that produces a single share intent containing all three artifacts. Keep the three discrete buttons internally for QA/debug, but hide them in release builds.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/ExportSubScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/viewmodel/SettingsViewModel.kt` — find `exportFullClassificationData`, `exportLabels`, `exportMisclassificationLogs`.
- Reuse `startShareIntent` from `SettingsShared.kt`.

### Files likely to change

- `ExportSubScreen.kt` — keep only the primary "Export my data" `FilledTonalButton`. The three discrete rows become visible ONLY when `BuildConfig.DEBUG` is true.
- `SettingsViewModel.kt` — add a new `suspend fun exportAllToZip(onResult: (Uri?) -> Unit)` that orchestrates the three existing exports into a single ZIP and emits a single `Uri`. Place the helper near the existing export functions; do NOT refactor them.

### Hard rules

- DO NOT change the underlying CSV schemas. They are referenced by external tooling (`scripts/download_feedback.ps1` and the `feedback_corpus/` analysis flow).
- DO NOT remove the three existing export functions even if the release UI no longer calls two of them.
- The ZIP file MUST contain three files at the root, named exactly: `classifications.csv`, `labels.csv`, `misclassifications.csv`. Empty CSVs (with header rows only) are acceptable when there is nothing to export.
- Use `java.util.zip.ZipOutputStream` against the existing `FileProvider` cache dir. Do NOT pull in a new dependency.

### Verification

- Build green.
- Release build: only one button visible. Tapping it produces a share sheet with `your_data.zip`. The zip extracts to the three named CSVs.
- Debug build: the three legacy buttons remain so QA can validate each.

### Reporting

```
C5 result:
Files changed:
Files added (helper if any):
Zip contents verified (Y/N + names):
Build result:
```

---

## C6 — Copy & jargon pass

### Why

Several subtitles are too long, too technical, or reveal implementation. Examples (do not assume these are exhaustive — sweep the whole `SettingsScreen.kt` + sub-screens):

- "Server ensemble (fixed)" → delete (row removed in C2 anyway).
- "Helps us understand which features are used (no SMS content)." → fine but trim trailing parenthetical to "(no message content)".
- "When this is on, each time you tap \"Report as wrong\" we send the SMS text, sender, predicted labels, your note, app version, and an anonymous install id over HTTPS so we can improve the classifier." → too long. Split the consent dialog into a one-line summary plus a "Learn more" link to the privacy policy.
- "Server-side deletion tied to your anonymous install id will be available in a future update." → STALE — server-side deletion shipped in `DELETE /api/users/me`. If you find this string anywhere, delete it.

### Files to inspect

- `app/src/main/java/com/smsclassifier/app/ui/screens/SettingsScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/ConsentOnboardingScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/NotificationSettingsSubScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/ExportSubScreen.kt`
- `app/src/main/java/com/smsclassifier/app/ui/screens/AboutSubScreen.kt`

### Files likely to change

Same as inspection list. Copy-only changes.

### Steps

1. Sweep every `subtitle = "..."` in those files. Hard targets:
    - ≤ 60 characters where possible.
    - No words: "ensemble", "inference", "ML", "telemetry", "Crashlytics", "DataStore", "SharedPreferences", "Firebase", "okhttp", "JSONL", "CSR", "Cloud Run", "BigQuery".
    - Allowed words for Privacy & data: "anonymous", "encrypted", "private", "your data".
2. For the Help-improve-classification consent dialog, replace the giant block of text with:
    > "Send the text and sender of misclassified messages over HTTPS so we can improve the classifier. Stored on our servers — see Privacy policy. Off by default."
    Keep the "Turn on" / "Cancel" buttons.
3. Delete any references to "future update" or "coming soon" in dialog copy.

### Hard rules

- DO NOT change anything outside string literals + minor `Text(...)` arrangements required to fit the new copy.
- DO NOT remove or rename `R.string.*` resources unless one becomes truly unused; if so, surface in the report — do not delete in this task.

### Verification

- Build green.
- Visual: subtitles fit on one or two lines on a Pixel 5 size screen at default font scale.

### Reporting

```
C6 result:
Files changed:
Strings shortened (count):
Stale strings removed (count):
Build result:
```

---

## C7 `[LEAD]` — Drop Facebook SDK + delete `MetaInit.kt`

> Lead orchestrator only. Composer 2.0 must NOT touch C7.

### Steps

1. After C1 lands, remove `implementation("com.facebook.android:facebook-android-sdk:17.0.2")` from `app/build.gradle.kts`.
2. Delete `app/src/main/java/com/smsclassifier/app/analytics/MetaInit.kt`.
3. Remove the `MetaInit.init(...)` call from `AppContainer.init` and the import.
4. Remove the `META_APP_ID` and `META_CLIENT_TOKEN` `BuildConfig` fields. Keep the `AD_ID` `tools:node="remove"` line in `AndroidManifest.xml` regardless — `firebase-analytics` may auto-merge it on future BoM bumps.
5. Confirm `assembleRelease` still passes with R8 enabled. If R8 complains about a missing Coil/FB rule that was previously masked, add a single targeted `-keep` line to `proguard-rules.pro`.

---

## C8 `[LEAD]` — Verification, version bump, AAB upload

> Lead orchestrator only.

1. Manual sweep on a real device or emulator across: onboarding (no Meta), Settings (new layout), Diagnostics (only via 5-tap), Notifications (one button), Export (single button release / three buttons debug), Privacy policy link, Delete my data.
2. Run the QA section A from `MONETIZATION_AND_GROWTH_PLAN.md` (lines ~1246+).
3. Bump `versionName` to `1.1.0` and `versionCode` to `20` in `app/build.gradle.kts`.
4. `./gradlew.bat bundleRelease publishReleaseBundle --track=internal`.

---

## Hard global rules for Composer 2.0

1. Run tasks **C1 → C2 → C3 → C4 → C5 → C6** in that order. Do not skip ahead.
2. `./gradlew.bat assembleDebug` must be green at the end of every task. If a task fails to compile, fix only the compile errors caused by your own edits and STOP rather than continue.
3. Do NOT touch any file under `app/src/main/java/com/smsclassifier/app/billing/`, `auth/`, `entitlement/`, `analytics/Telemetry.kt`, `feedback/`, `data/DeleteAccountClient.kt`, `work/`, or any `*ViewModel.kt`.
4. Do NOT modify `MainActivity.kt` beyond removing/renaming the two callback args called out in C2 and C3.
5. Do NOT change navigation routes, deep links, or `Manifest` files.
6. Do NOT bump `versionCode` or `versionName`. Lead handles that in C8.
7. Do NOT commit, push, or run `git` commands. Lead reviews and commits.
8. Surface in the final report any TODOs, stale strings, or orphan code you spotted but did NOT fix per scope.

---

## Final report format (copy at end of session)

```
Tasks completed: C1 / C2 / C3 / C4 / C5 / C6 (mark which finished)
Files touched (deduped):
Net LOC delta:
Build result (last `./gradlew.bat assembleDebug`):
Manual visual checks performed (list):
Stale or orphan items spotted (list — DO NOT FIX):
Open questions for the lead:
```
