# Deploying the Groq Ensemble Backend to Google Cloud

## 1. Build and tag the image
```bash
cd "D:\Projects\SMS datasets and project"
docker build -t sms-ensemble .
docker tag sms-ensemble gcr.io/smsclassifier-478611/sms-ensemble:latest
```

## 2. Authenticate Docker with Artifact Registry
```bash
gcloud auth login
gcloud config set project smsclassifier-478611
gcloud auth configure-docker
```

## 3. Push the image
```bash
docker push gcr.io/smsclassifier-478611/sms-ensemble:latest
```

## 4. Deploy to Cloud Run

**Recommended region for India:** `asia-south1` (Mumbai)

**Important:** never paste the actual `GROQ_API_KEY` value into this file (it would leak to git). Either reference an environment variable or use Secret Manager — see below.

```bash
# Option A — env var passthrough (set GROQ_API_KEY in your shell first)
gcloud run deploy sms-ensemble \
    --image gcr.io/smsclassifier-478611/sms-ensemble:latest \
    --region asia-south1 \
    --port 8000 \
    --set-env-vars "GROQ_API_KEY=$GROQ_API_KEY" \
    --platform managed \
    --allow-unauthenticated

# Option B (recommended) — store in Secret Manager and mount it at deploy time
gcloud run deploy sms-ensemble \
    --image gcr.io/smsclassifier-478611/sms-ensemble:latest \
    --region asia-south1 \
    --port 8000 \
    --set-secrets "GROQ_API_KEY=projects/smsclassifier-478611/secrets/groq-api-key:latest" \
    --platform managed \
    --allow-unauthenticated
```

### Setting the region in the Cloud Console

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click **"Create Service"**
3. In the **"Location"** dropdown, select **"asia-south1 (Mumbai)"**
4. Alternatively, set a default region for all Cloud Run commands:
   ```bash
   gcloud config set run/region asia-south1
   ```
   After this, you can omit `--region` from deploy commands.

### Service URL

After deployment, your service will be available at:
- **Service URL:** `https://sms-ensemble-hhpimusmbq-el.a.run.app`
- **API Endpoint:** `https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify`

### Update Android App to Use Cloud Run

Update the Android app's `BuildConfig` to point to the Cloud Run service:

1. Open `android_sms_classifier/app/build.gradle.kts`
2. Update the `SERVER_API_BASE_URL` field:
   ```kotlin
   buildConfigField(
       "String",
       "SERVER_API_BASE_URL",
       "\"https://sms-ensemble-hhpimusmbq-el.a.run.app/api\""
   )
   ```
3. Rebuild and reinstall the Android app

**Note:** Since Cloud Run uses HTTPS, you can remove the network security config that allows cleartext traffic to `10.0.2.2` if you're no longer testing locally.

### Optional settings
- **Private ingress**: add `--ingress internal` if only the Android app should reach it through a VPC.
- **Secrets**: store `GROQ_API_KEY` in Secret Manager and mount via `--set-secrets GROQ_API_KEY=projects/.../secrets/...:latest`.
- **Custom domain**: after deployment run `gcloud run domain-mappings create ...` to map a friendly HTTPS domain.

### Optional admin entitlement API

The backend has a protected admin API for occasional gift grants and entitlement
checks. It is disabled unless `ADMIN_API_TOKEN` is set.

Store a long random token in Secret Manager and mount it into Cloud Run:

```bash
gcloud secrets create sms-admin-token --replication-policy=automatic
gcloud secrets versions add sms-admin-token --data-file=-

gcloud run services update sms-ensemble \
    --region asia-south1 \
    --set-secrets "ADMIN_API_TOKEN=projects/smsclassifier-478611/secrets/sms-admin-token:latest"
```

Local operator commands:

```powershell
$env:SMS_ADMIN_TOKEN = "<same token>"
$env:SMS_ADMIN_BASE_URL = "https://sms-ensemble-hhpimusmbq-el.a.run.app/api"

# Gift Pro for one year by Firebase UID or app installId
python scripts/admin_entitlements.py grant-pro --firebase-uid "<firebase uid>" --days 365 --reason "gift"
python scripts/admin_entitlements.py grant-pro --install-id "<install id>" --days 365 --reason "gift"

# Check one user's entitlement
python scripts/admin_entitlements.py lookup --firebase-uid "<firebase uid>"

# Backend entitlement counts and recent gift grants
python scripts/admin_entitlements.py stats
```

Phone numbers can be used only after the user has linked phone auth in the app:
look up the phone number in Firebase Authentication, copy the Firebase UID, then
grant by UID. Gmail/Android account lookup is not supported unless Google/email
sign-in is added later.

Important stats caveats:

- The admin `stats` command counts entitlement records known to the backend.
- Play Console remains the source of truth for paid subscriber/revenue reports.
- GA4/Firebase Analytics remains the source of truth for app usage events.
- Per-user classification usage is not available yet because `/api/classify`
  does not currently receive `installId` or `firebaseUid`.

Purchase validation still requires Android Publisher credentials on the backend.
For Cloud Run, mount the existing publisher service-account JSON through Secret
Manager as `ANDROID_PUBLISHER_CREDENTIALS_JSON`, or set
`ANDROID_PUBLISHER_CREDENTIALS_FILE` for local testing. Keep
`PLAY_PACKAGE_NAME=com.smsclassifier.app`.

## 5. Monitoring
- Cloud Run automatically streams logs to Cloud Logging; filter by service name to confirm `/api/classify` traffic.
- Enable Cloud Monitoring dashboards (Latency, Errors) for proactive alerts.
