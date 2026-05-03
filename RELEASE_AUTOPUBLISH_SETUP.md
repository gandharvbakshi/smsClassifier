# Auto-publishing to the Play Store

This repo is wired up to publish signed AABs to Google Play in two ways:

1. **Locally** via Gradle Play Publisher (GPP):
   `./gradlew publishReleaseBundle`
2. **On CI** via the `Release to Play Store` workflow in
   `.github/workflows/release.yml`, triggered by either:
   - pushing a `v*` tag (e.g. `git tag v1.0.12 && git push --tags`), or
   - clicking "Run workflow" in the GitHub Actions UI (lets you pick the track).

You only need to do the one-time setup below once. After that, releases are
either a single Gradle command or a single tag push.

---

## One-time setup

### Step 1 — Create a Google Cloud service account

1. Open [Google Cloud Console](https://console.cloud.google.com/) → pick the
   `smsclassifier-478611` project (or any project you control).
2. **IAM & Admin → Service Accounts → Create service account**
   - Service account name: `play-publisher`
   - Skip the "Grant this service account access to project" step.
3. After creation, open the service account → **Keys → Add key → Create new
   key → JSON**. A file like `smsclassifier-478611-xxxxx.json` downloads.
4. Save that file in this repo under **`app/`**. Either name it
   **`play-publisher.json`** (recommended) or keep the Cloud Console download
   name (e.g. `smsclassifier-478611-9782f504fc81.json`) — Gradle detects any
   `.json` file in `app/` whose contents look like a service account. The
   `.gitignore` excludes these paths; **never commit the key.**

### Step 1b — Enable the Google Play Android Developer API (required)

The service account's **Cloud project** must have the Android Publisher API
turned on — inviting the user in Play Console alone is not enough.

1. In [Google Cloud Console](https://console.cloud.google.com/), open the
   **same project** the service account belongs to (pick it from the project
   dropdown at the top).
2. **APIs & services → Library →** search **"Google Play Android Developer
   API" → Enable**.

If you skip this, local commands like `bootstrapReleaseListing` or
`publishReleaseBundle` fail with `403` / `SERVICE_DISABLED` /
`accessNotConfigured`. Google often prints a direct enable link in the error
message, e.g.:

`https://console.developers.google.com/apis/api/androidpublisher.googleapis.com/overview?project=YOUR_PROJECT_NUMBER`

After enabling, wait **a few minutes** and retry.

### Step 2 — Grant the service account Play Console access

1. Open [Play Console](https://play.google.com/console/) → **Users and
   permissions** → **Invite new users**.
2. Email: paste the service account email from step 1
   (looks like `something@PROJECT_ID.iam.gserviceaccount.com`).
3. **App permissions** → add this app, grant **Release manager** (or
   **Admin** if you want it to manage the listing too).
4. Save. **Wait up to 24 hours** the very first time — Google's permission
   propagation for new service accounts can be slow.

**Play Console linking:** under **Setup → API access**, ensure your Play
developer account is linked to a Google Cloud project (the same one where you
created the service account is typical).

### Step 3 — Verify locally

```powershell
.\gradlew bundleRelease
.\gradlew publishReleaseBundle
```

- `bundleRelease` should succeed without calling Play (the project uses
  `resolutionStrategy = IGNORE` so **release builds do not pull version codes
  from the store** — you bump `versionCode` in `app/build.gradle.kts` yourself).
- `publishReleaseBundle` **does** call the Android Publisher API — it will
  fail until step 1b is done and credentials are valid.

Successful `publishReleaseBundle` uploads to the **beta** track by default,
which matches **Open testing** in Play Console. Use `--track=internal` for
internal testers only, or `--track=production` when you are ready for prod.

If you get `PERMISSION_DENIED` right after inviting the service account, wait
for the propagation window. If you get `SERVICE_DISABLED` / `accessNotConfigured`,
finish step 1b.

## CI setup — GitHub Actions

You need to add **5 GitHub repository secrets** to enable the
`Release to Play Store` workflow.

In the GitHub UI: **Settings → Secrets and variables → Actions →
New repository secret**.

| Secret name | What to put in it |
|---|---|
| `RELEASE_KEYSTORE_BASE64` | Output of `[Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\release-keystore.jks"))` (PowerShell) or `base64 -w 0 release-keystore.jks` (bash). One long single-line string. |
| `RELEASE_KEYSTORE_PASSWORD` | The store password from your local `keystore.properties`. |
| `RELEASE_KEY_ALIAS` | The key alias from your local `keystore.properties`. |
| `RELEASE_KEY_PASSWORD` | The key password from your local `keystore.properties`. |
| `PLAY_SERVICE_ACCOUNT_JSON` | The **entire contents** of the `play-publisher.json` file from step 1 above (paste the raw JSON; GitHub stores it as-is). |

### How to base64 the keystore in PowerShell

```powershell
$bytes = [IO.File]::ReadAllBytes("D:\path\to\release-keystore.jks")
[Convert]::ToBase64String($bytes) | Set-Clipboard
# Then paste from clipboard into the GitHub secret value field.
```

---

## Daily release workflow

### Option A — local, single command

```powershell
# 1. Bump versionCode (+ versionName) in app/build.gradle.kts if Play already has that code.
#    (resolutionStrategy is IGNORE — no silent auto-bump from the store.)
# 2. Update app/src/main/play/release-notes/en-US/default.txt
# 3. Build + upload (default track = beta = Open testing):
.\gradlew publishReleaseBundle

# Internal testers only:
.\gradlew publishReleaseBundle --track=internal

# Promote without rebuilding:
.\gradlew promoteArtifact --from-track beta --promote-track production --user-fraction 0.10
```

### Option B — CI, push a tag

```powershell
# 1. Bump versionName, commit, push.
# 2. Tag and push the tag — CI takes over:
git tag v1.0.12
git push origin v1.0.12
```

Tag-triggered runs ship to the **beta** track (Open testing); use **Run workflow**
→ choose another track when you want internal-only or production.

---

## Track strategy (recommended)

1. **Tag push or local publish** → default **beta** (= Open testing).
2. Watch crashes / Play Console pre-launch reports.
3. Promote to **production** via Play Console UI or:
   ```powershell
   .\gradlew promoteArtifact --from-track beta --promote-track production --user-fraction 0.10
   ```
   The `--user-fraction 0.10` flag rolls out to 10% of users first; you can
   bump it to 0.50 then 1.00 over a few days. Saves you from a bad release
   reaching everyone at once.

---

## Things to know

- **First release on a new app must be uploaded manually** via the Play
  Console UI. Since v1.0.11 is already on Play, you're past that gate.
- This project uses `resolutionStrategy = IGNORE`: release builds do **not**
  call Play to compute `versionCode`; bump `versionCode` yourself before each
  upload when needed. Optional: switch to `AUTO` in `app/build.gradle.kts`
  **after** step 1b — then every release build contacts Play to align version
  codes (requires the Android Publisher API enabled).
- The `play-publisher.json` and `release-keystore.jks` are **never** stored
  in git. They live on your local machine and inside GitHub Secrets only.
- The CI workflow scrubs them off the runner disk in a `cleanup` step at
  the end of every run (defense in depth — GitHub-hosted runners are
  ephemeral but the principle is right).
