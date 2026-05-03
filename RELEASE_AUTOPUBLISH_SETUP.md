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
4. Save that file locally as `app/play-publisher.json` in this repo. The
   `.gitignore` already excludes it; **never commit it.**

### Step 2 — Grant the service account Play Console access

1. Open [Play Console](https://play.google.com/console/) → **Users and
   permissions** → **Invite new users**.
2. Email: paste the service account email from step 1
   (looks like `play-publisher@smsclassifier-478611.iam.gserviceaccount.com`).
3. **App permissions** → add this app, grant **Release manager** (or
   **Admin** if you want it to manage the listing too).
4. Save. **Wait up to 24 hours** the very first time — Google's permission
   propagation for new service accounts is famously slow.

### Step 3 — Verify locally

```powershell
.\gradlew publishReleaseBundle
```

If it succeeds, you'll see `BUILD SUCCESSFUL` and a new release on the
**internal** track in Play Console within a minute. (If you get
`PERMISSION_DENIED`, you're inside the 24-hour propagation window — wait.)

---

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
# 1. Bump versionName in app/build.gradle.kts (versionCode auto-bumps via GPP)
# 2. Update app/src/main/play/release-notes/en-US/default.txt
# 3. Build, sign, upload to internal track:
.\gradlew publishReleaseBundle

# To upload to a different track:
.\gradlew publishReleaseBundle --track=beta

# To promote an existing artifact between tracks (no rebuild):
.\gradlew promoteArtifact --from-track internal --promote-track production --user-fraction 0.10
```

### Option B — CI, push a tag

```powershell
# 1. Bump versionName, commit, push.
# 2. Tag and push the tag — CI takes over:
git tag v1.0.12
git push origin v1.0.12
```

The workflow always ships a tag-triggered release to **internal** track.
To ship directly to a different track, use the **Run workflow** button on the
`Release to Play Store` workflow page in the GitHub Actions UI and pick the
track from the dropdown.

---

## Track strategy (recommended)

1. **Tag push or local publish** → goes to **internal** track. Safe — only
   testers you've added can install it.
2. Live with it for a day or two. Watch crashes / Play Console pre-launch
   reports.
3. When happy, promote to **production** via Play Console UI or:
   ```powershell
   .\gradlew promoteArtifact --from-track internal --promote-track production --user-fraction 0.10
   ```
   The `--user-fraction 0.10` flag rolls out to 10% of users first; you can
   bump it to 0.50 then 1.00 over a few days. Saves you from a bad release
   reaching everyone at once.

---

## Things to know

- **First release on a new app must be uploaded manually** via the Play
  Console UI. Since v1.0.11 is already on Play, you're past that gate.
- GPP `resolutionStrategy.AUTO` means: if you forget to bump `versionCode`
  in `build.gradle.kts` and the existing one is already taken on Play, GPP
  silently bumps it for you so the upload succeeds. Convenient, but it does
  mask the "I forgot to bump" mistake. If you'd rather it fail loudly, change
  the value to `FAIL` in `app/build.gradle.kts`.
- The `play-publisher.json` and `release-keystore.jks` are **never** stored
  in git. They live on your local machine and inside GitHub Secrets only.
- The CI workflow scrubs them off the runner disk in a `cleanup` step at
  the end of every run (defense in depth — GitHub-hosted runners are
  ephemeral but the principle is right).
