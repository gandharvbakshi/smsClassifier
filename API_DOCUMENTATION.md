# SMS Classification API Documentation

## Base URL

```
https://sms-ensemble-hhpimusmbq-el.a.run.app/api
```

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

---

## Endpoints

### 1. Health Check

Check if the backend service is running and models are loaded.

**Endpoint:** `GET /health`

**Request:**
```bash
curl https://sms-ensemble-hhpimusmbq-el.a.run.app/api/health
```

**Response:**
```json
{
  "status": "ok",
  "modelsLoaded": true,
  "groqModel": "llama-3.1-8b-instant"
}
```

**Response Fields:**
- `status` (string): Service status, typically `"ok"`
- `modelsLoaded` (boolean): Whether all ML models are successfully loaded
- `groqModel` (string): The Groq LLM model being used for intent classification

**Status Codes:**
- `200 OK`: Service is healthy
- `500 Internal Server Error`: Service error or models not loaded

---

### 2. Classify SMS

Classify an SMS message to determine if it contains an OTP, its intent, and if it's phishing.

**Endpoint:** `POST /classify`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "123456 is your OTP for login. Do not share.",
  "sender": "BANK"
}
```

**Request Fields:**
- `text` (string, **required**): The SMS message text to classify
- `sender` (string, optional): The sender ID or phone number (e.g., "BANK", "ICICI", "+919876543210")

**Example Request (cURL):**
```bash
curl -X POST https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "123456 is your OTP for login. Do not share.",
    "sender": "BANK"
  }'
```

**Example Request (Python):**
```python
import requests

url = "https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify"
payload = {
    "text": "123456 is your OTP for login. Do not share.",
    "sender": "BANK"
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers)
result = response.json()
print(result)
```

**Example Request (JavaScript/Node.js):**
```javascript
const fetch = require('node-fetch');

const url = 'https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify';
const payload = {
    text: '123456 is your OTP for login. Do not share.',
    sender: 'BANK'
};

fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
})
.then(response => response.json())
.then(data => console.log(data));
```

**Response:**
```json
{
  "isOtp": true,
  "otpIntent": "APP_LOGIN_OTP",
  "isPhishing": false,
  "phishScore": 0.123,
  "reasons": [
    "OTP detected by heuristics (confidence: 0.95)",
    "Code at start pattern matched",
    "is_phishing LightGBM prob=0.123 (threshold=0.5)",
    "Groq intent=APP_LOGIN_OTP (450 ms)"
  ]
}
```

**Response Fields:**
- `isOtp` (boolean): Whether the message contains an OTP code
- `otpIntent` (string): The classification intent (see [Intent Types](#intent-types) below)
- `isPhishing` (boolean): Whether the message is classified as phishing
- `phishScore` (float): Phishing probability score (0.0 to 1.0)
- `reasons` (array of strings): Detailed explanation of the classification decision

**Status Codes:**
- `200 OK`: Classification successful
- `400 Bad Request`: Invalid request (e.g., empty text field)
- `500 Internal Server Error`: Server error during classification
- `503 Service Unavailable`: Service temporarily unavailable

**Error Response:**
```json
{
  "detail": "Request text must not be empty."
}
```

---

## Intent Types

The `otpIntent` field can have one of the following values:

| Intent | Description |
|--------|-------------|
| `NOT_OTP` | Message does not contain an OTP code |
| `APP_ACCOUNT_CHANGE_OTP` | OTP for changing account details (password, email, phone, etc.) |
| `APP_LOGIN_OTP` | OTP for non-financial app login/verification |
| `BANK_OR_CARD_TXN_OTP` | OTP for bank/card transaction approval |
| `DELIVERY_OR_SERVICE_OTP` | OTP for delivery/service verification |
| `FINANCIAL_LOGIN_OTP` | OTP for banking or trading platform login |
| `GENERIC_APP_ACTION_OTP` | OTP for generic in-app actions |
| `KYC_OR_ESIGN_OTP` | OTP for KYC/e-signature/document signing |
| `UPI_TXN_OR_PIN_OTP` | OTP for UPI transfers, PIN changes, or device binding |

---

## Classification Logic

The backend uses an ensemble approach combining:

1. **Heuristic Classifier**: Pattern-based rules for fast OTP detection
2. **LightGBM Models**: Machine learning models for OTP and phishing detection
3. **Groq LLM**: Large language model for intent classification (only when OTP is detected)

**Classification Flow:**
1. Heuristics are checked first for high-confidence OTP detection
2. If heuristics don't match with high confidence, ML models are used
3. If an OTP is detected, Groq LLM classifies the intent
4. Phishing detection always uses ML models

---

## Rate Limits

Currently, there are no explicit rate limits, but please use the API responsibly. For high-volume usage, consider implementing client-side rate limiting or caching.

---

## Timeouts

- **Connection Timeout**: 10 seconds
- **Read Timeout**: 10 seconds
- **Groq API Timeout**: 45 seconds (for intent classification)

---

## Examples

### Example 1: Bank Transaction OTP
```bash
curl -X POST https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your OTP for transaction of INR 5000.00 is 789012. Valid for 10 minutes. Do not share.",
    "sender": "ICICIB"
  }'
```

**Expected Response:**
```json
{
  "isOtp": true,
  "otpIntent": "BANK_OR_CARD_TXN_OTP",
  "isPhishing": false,
  "phishScore": 0.089,
  "reasons": [
    "OTP detected by heuristics (confidence: 0.92)",
    "is_phishing LightGBM prob=0.089 (threshold=0.5)",
    "Groq intent=BANK_OR_CARD_TXN_OTP (420 ms)",
    "Bank/card OTP – approve only if you just initiated the transaction. Never share this code."
  ]
}
```

### Example 2: Delivery OTP
```bash
curl -X POST https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your OTP for delivery is 456789. Share this code with the delivery agent.",
    "sender": "AMAZON"
  }'
```

**Expected Response:**
```json
{
  "isOtp": true,
  "otpIntent": "DELIVERY_OR_SERVICE_OTP",
  "isPhishing": false,
  "phishScore": 0.156,
  "reasons": [
    "OTP detected by heuristics (confidence: 0.88)",
    "is_phishing LightGBM prob=0.156 (threshold=0.5)",
    "Groq intent=DELIVERY_OR_SERVICE_OTP (380 ms)",
    "Delivery OTP – share only with the delivery agent in person."
  ]
}
```

### Example 3: Phishing Attempt
```bash
curl -X POST https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "URGENT: Your account will be blocked. Click here to verify: bit.ly/suspicious-link",
    "sender": "BANK-ALERT"
  }'
```

**Expected Response:**
```json
{
  "isOtp": false,
  "otpIntent": "NOT_OTP",
  "isPhishing": true,
  "phishScore": 0.876,
  "reasons": [
    "is_otp LightGBM prob=0.234 (threshold=0.5)",
    "is_phishing LightGBM prob=0.876 (threshold=0.5)",
    "Intent skipped because message classified as NOT_OTP"
  ]
}
```

### Example 4: Regular Transaction Notification (Not OTP)
```bash
curl -X POST https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "INR 5000.00 debited from A/c XX1234 on 15-Jan-24. Avl Bal: INR 45000.00",
    "sender": "HDFCB"
  }'
```

**Expected Response:**
```json
{
  "isOtp": false,
  "otpIntent": "NOT_OTP",
  "isPhishing": false,
  "phishScore": 0.234,
  "reasons": [
    "is_otp LightGBM prob=0.123 (threshold=0.5)",
    "is_phishing LightGBM prob=0.234 (threshold=0.5)",
    "Intent skipped because message classified as NOT_OTP"
  ]
}
```

---

## Best Practices

1. **Always include sender information** when available - it improves classification accuracy
2. **Handle errors gracefully** - implement retry logic with exponential backoff
3. **Cache results** when appropriate - classification results for the same message don't change
4. **Monitor response times** - the service may take 1-3 seconds for classification
5. **Check health endpoint** before making classification requests if you need to verify service availability

---

## Support

For issues or questions:
- Check the health endpoint first to verify service status
- Review the `reasons` field in responses for detailed classification explanations
- Check service logs if deployed on Google Cloud Run

---

## Version

- **API Version**: 0.1.0
- **Last Updated**: 2024
- **Service**: SMS Ensemble Backend (FastAPI)

