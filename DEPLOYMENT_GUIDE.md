# Backend Deployment Guide

## Current Status

✅ **Improved heuristics are already integrated in the backend!**
- Backend uses `backend/classification/heuristic_classifier.py` which has all the improvements
- The Android app's Kotlin version has been updated to match
- Both now use the same enhanced patterns and logic

## Deploying to Google Cloud Run

### Prerequisites
1. Google Cloud SDK installed (`gcloud` CLI)
2. Docker installed
3. Authenticated with Google Cloud: `gcloud auth login`
4. Project set: `gcloud config set project smsclassifier-478611`

### Step-by-Step Deployment

#### 1. Build Docker Image
```bash
cd "D:\Projects\SMS datasets and project"
docker build -t sms-ensemble .
```

#### 2. Tag for Google Container Registry
```bash
docker tag sms-ensemble gcr.io/smsclassifier-478611/sms-ensemble:latest
```

#### 3. Authenticate Docker with GCR
```bash
gcloud auth configure-docker
```

#### 4. Push Image to GCR
```bash
docker push gcr.io/smsclassifier-478611/sms-ensemble:latest
```

#### 5. Deploy to Cloud Run
```bash
gcloud run deploy sms-ensemble \
  --image gcr.io/smsclassifier-478611/sms-ensemble:latest \
  --region asia-south1 \
  --port 8000 \
  --set-env-vars GROQ_API_KEY=YOUR_GROQ_API_KEY \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10
```

**Note:** Replace `YOUR_GROQ_API_KEY` with your actual Groq API key.

#### 6. Get Service URL
After deployment, get the service URL:
```bash
gcloud run services describe sms-ensemble --region asia-south1 --format 'value(status.url)'
```

The service will be available at something like:
- **Service URL:** `https://sms-ensemble-xxxxx-xx.a.run.app`
- **API Endpoint:** `https://sms-ensemble-xxxxx-xx.a.run.app/api/classify`
- **Health Check:** `https://sms-ensemble-xxxxx-xx.a.run.app/api/health`

### Using Secret Manager (Recommended for Production)

Instead of passing API key directly, use Secret Manager:

#### 1. Create Secret
```bash
echo -n "YOUR_GROQ_API_KEY" | gcloud secrets create groq-api-key --data-file=-
```

#### 2. Grant Cloud Run Access
```bash
PROJECT_NUMBER=$(gcloud projects describe smsclassifier-478611 --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding groq-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 3. Deploy with Secret
```bash
gcloud run deploy sms-ensemble \
  --image gcr.io/smsclassifier-478611/sms-ensemble:latest \
  --region asia-south1 \
  --port 8000 \
  --set-secrets GROQ_API_KEY=groq-api-key:latest \
  --platform managed \
  --allow-unauthenticated
```

### Update Android App

After deployment, update the Android app to use the new URL:

1. Open `android_sms_classifier/app/build.gradle.kts`
2. Update `SERVER_API_BASE_URL`:
```kotlin
buildConfigField(
    "String",
    "SERVER_API_BASE_URL",
    "\"https://sms-ensemble-xxxxx-xx.a.run.app/api\""
)
```

3. Rebuild and reinstall the app

### Testing the Deployment

#### Test Health Endpoint
```bash
curl https://sms-ensemble-xxxxx-xx.a.run.app/api/health
```

Expected response:
```json
{
  "status": "ok",
  "modelsLoaded": true,
  "groqModel": "llama-3.1-8b-instant"
}
```

#### Test Classification Endpoint
```bash
curl -X POST https://sms-ensemble-xxxxx-xx.a.run.app/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "123456 is your OTP for login. Do not share.",
    "sender": "BANK"
  }'
```

### Monitoring

1. **View Logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sms-ensemble" --limit 50
   ```

2. **Cloud Console:**
   - Go to [Cloud Run Console](https://console.cloud.google.com/run)
   - Click on `sms-ensemble` service
   - View logs, metrics, and revisions

3. **Set Up Alerts:**
   - Enable Cloud Monitoring
   - Create alerts for high latency or error rates

### Troubleshooting

#### Image Build Fails
- Ensure `trained_models/` directory contains required model files
- Check `.env` file exists (or set env vars in Dockerfile)

#### Deployment Fails
- Verify `GROQ_API_KEY` is set correctly
- Check service account has necessary permissions
- Ensure Docker image pushed successfully

#### Service Not Responding
- Check service logs: `gcloud run services logs read sms-ensemble --region asia-south1`
- Verify health endpoint: `curl https://your-service-url/api/health`
- Check quota limits in Cloud Console

## Next Steps

1. ✅ Deploy to Cloud Run
2. ✅ Update Android app with new URL
3. ✅ Test with real SMS messages
4. 📊 Monitor performance and costs
5. 🔄 Set up CI/CD for automated deployments
6. 📈 Scale based on usage patterns

