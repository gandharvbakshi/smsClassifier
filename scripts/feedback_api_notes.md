# `POST …/feedback` backend (implement on Cloud Run / FastAPI)

The Android client posts JSON to:

`${SERVER_API_BASE_URL}/feedback`

With `SERVER_API_BASE_URL` = `https://sms-ensemble-hhpimusmbq-el.a.run.app/api`

So the path is **`https://sms-ensemble-hhpimusmbq-el.a.run.app/api/feedback`**.

## Request schema (mirror `FeedbackRequest`)

- `installId` (string, UUID per install)
- `appVersionCode` (int)
- `appVersionName` (string)
- `sender` (string)
- `body` (string; client truncates to 4000 chars)
- `predictedIsOtp`, `predictedOtpIntent`, `predictedIsPhishing`, `predictedPhishScore` (nullable)
- `userCorrection` (string or null — same content as Android `MisclassificationLogEntity.userNote`)
- `userNote` (reserved; Android sends null for now)
- `clientCreatedAt` (epoch ms)

## Responses

Return **HTTP 200** with JSON **`{"ok": true, "id": "<stored-row-id-or-uuid>"}`** when accepted.

Cheap bot filter suggested in plan: reject `POST` bodies when `User-Agent` does not contain `okhttp` (OkHttp’s default UA includes `"okhttp/"`).

## Storage

Persist at least payload + server receive time + request IP (masked if desired). Prefer BigQuery or Firestore/Firestore via Cloud Logging pipeline.
