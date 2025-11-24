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

```bash
gcloud run deploy sms-ensemble   --image gcr.io/smsclassifier-478611/sms-ensemble:latest   --region asia-south1   --port 8000   --set-env-vars GROQ_API_KEY=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   --platform managed --allow-unauthenticated
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

## 5. Monitoring
- Cloud Run automatically streams logs to Cloud Logging; filter by service name to confirm `/api/classify` traffic.
- Enable Cloud Monitoring dashboards (Latency, Errors) for proactive alerts.

