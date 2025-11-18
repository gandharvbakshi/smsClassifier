# Android Deployment Plan for SMS Classification Models

## Overview
Deploy Logistic Regression models (TF-IDF + heuristics) to Android SMS app for real-time classification.

---

## November 2025 Update – Hybrid Ensemble

We now recommend a hybrid pipeline:

- **LightGBM (on-device or server)** handles `is_otp` and `is_phishing`. These models already ship as ONNX (`model_isotp.onnx`, `model_phishing.onnx`) and keep the low-latency, offline guarantees.
- **Groq `llama-3.1-8b-instant` (cloud)** only runs when the LightGBM `is_otp` classifier fires true, and returns the OTP intent label. This replaces the lower-accuracy intent ONNX model.
- **FastAPI backend** (`backend/scripts/android_backend_server.py`) exposes the ensemble via `/api/classify`, so Android’s existing `ServerClassifier` can test the new logic without changing the app UI.

### Current vs Previous Logic

| Task              | Previous Version                              | Current Ensemble                                            |
|-------------------|-----------------------------------------------|-------------------------------------------------------------|
| `is_phishing`     | Logistic Regression ONNX                      | LightGBM ONNX or Python (same exported weights)             |
| `is_otp`          | Logistic Regression ONNX + heuristics fallback| LightGBM ONNX or Python (same exported weights)             |
| `otp_intent`      | Logistic Regression ONNX                      | Groq `llama-3.1-8b-instant` via backend API (OTP-only gate) |
| Android workflow  | Pure on-device ONNX                           | On-device by default; optional server mode hits new API     |

This change boosts intent accuracy from ~0.70/0.43 (acc/macro-F1) to 0.97/0.90 on the verified synthetic set while preserving the strong on-device phishing/OTP performance.

### Running the Android Backend Server

1. Ensure `trained_models` contains the latest LightGBM artifacts (run `export_models_for_android.py` or `test_models_on_synthetic.py` if needed).
2. Set your Groq key in `.env`: `GROQ_API_KEY=...`.
3. Start the server:
   ```bash
   uvicorn backend.scripts.android_backend_server:app --host 0.0.0.0 --port 8001 --reload
   ```
4. Point `ServerClassifier` to `http://10.0.2.2:8001/api` (Android emulator) or the LAN URL of the machine running the server.
5. Toggle `InferenceMode.SERVER` in the app to send SMS samples to the backend and observe ensemble outputs (LightGBM scores + Groq intent reason strings).

The FastAPI endpoint mirrors the Kotlin `ServerResponse` schema (`isOtp`, `otpIntent`, `isPhishing`, `phishScore`, `reasons`) so no additional Android code changes are required beyond updating the base URL.

### Observing Backend Decisions

- Every `/api/classify` call is logged to stdout with the LightGBM probabilities, predicted labels, and (optionally) the SMS text. Run the server with `LOG_RAW_MESSAGES=true` to log the full body instead of the first 32 characters.
- In Docker: `docker run --rm -e GROQ_API_KEY=... -e LOG_RAW_MESSAGES=true -p 8001:8000 sms-ensemble`
- Check the container logs (`docker logs <container_id>`) or the local `uvicorn` console to verify what the backend saw vs. what it predicted when debugging Android results.

## Model Performance Summary
- **Phishing**: F1 = 0.95 (Logistic Regression)
- **Is OTP**: F1 = 0.998 (Logistic Regression)
- **OTP Intent**: Macro F1 = 0.91 (Logistic Regression)

**Recommendation**: Use Logistic Regression for all three tasks (performs best).

---

## Deployment Options

### Option 1: ONNX Runtime Mobile (Recommended)
**Pros:**
- ✅ Good Android support (ONNX Runtime Mobile)
- ✅ Can convert scikit-learn models directly
- ✅ Reasonable performance
- ✅ Smaller model size than full TensorFlow

**Cons:**
- ⚠️ Requires ONNX Runtime Mobile dependency (~10-15 MB)
- ⚠️ Slightly slower than TFLite

**Implementation:**
1. Export models to ONNX format (done by `export_models_for_android.py`)
2. Add ONNX Runtime Mobile to Android project
3. Load ONNX models in Android app
4. Preprocess SMS text → extract features → run inference

**Model Files:**
- `model_phishing.onnx` (~500 KB)
- `model_isotp.onnx` (~500 KB)
- `model_intent.onnx` (~1 MB)
- `tfidf_vectorizer.pkl` (needs Python runtime or port to Java)

---

### Option 2: TFLite (Best Performance)
**Pros:**
- ✅ Native Android support (built into Android ML Kit)
- ✅ Fastest inference
- ✅ Small model size
- ✅ No external dependencies

**Cons:**
- ⚠️ Requires converting scikit-learn pipeline to TensorFlow
- ⚠️ More complex implementation
- ⚠️ TF-IDF vectorization needs to be ported to TensorFlow

**Implementation:**
1. Create TensorFlow model that replicates:
   - TF-IDF vectorization (or pre-compute vocab)
   - Heuristic feature extraction
   - Logistic Regression layers
2. Convert to TFLite
3. Use TensorFlow Lite in Android app

**Challenges:**
- TF-IDF is complex to replicate in TensorFlow (vocabulary lookup, IDF weights)
- May need to pre-compute TF-IDF features or use a simpler text encoding

---

### Option 3: Hybrid Approach (Recommended for MVP)
**Pros:**
- ✅ Fastest to implement
- ✅ Uses native Android features
- ✅ No external ML dependencies

**Cons:**
- ⚠️ Requires porting feature extraction to Java/Kotlin
- ⚠️ Models run on backend server (requires internet)

**Implementation:**
1. **Client-side (Android):**
   - Extract heuristic features (regex patterns - easy to port)
   - Send SMS text + features to backend API

2. **Server-side (Python backend):**
   - Run TF-IDF vectorization
   - Run Logistic Regression models
   - Return predictions

**Alternative:** Run models locally on device using ONNX Runtime Mobile (Option 1)

---

## Recommended Approach: ONNX Runtime Mobile

### Step 1: Export Models
```bash
python export_models_for_android.py
```

This creates:
- `model_phishing.onnx`
- `model_isotp.onnx`
- `model_intent.onnx`
- `model_metadata.json`
- `heuristic_features.json`

### Step 2: Port Feature Extraction to Android

**TF-IDF Vectorization:**
- Option A: Pre-compute TF-IDF vectors on server, send to app
- Option B: Port TF-IDF to Java (use Apache Commons Math or custom implementation)
- Option C: Use simpler text encoding (e.g., word embeddings, character n-grams)

**Heuristic Features:**
- Easy to port - just regex patterns
- See `heuristic_features.json` for list of patterns

### Step 3: Android Integration

**Dependencies (build.gradle):**
```gradle
dependencies {
    implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.16.0'
    // Or use ONNX Runtime Mobile
}
```

**Inference Flow:**
1. Receive SMS → Extract text + sender
2. Preprocess text (normalize, lowercase)
3. Extract heuristic features (regex patterns)
4. Vectorize text (TF-IDF or alternative)
5. Combine features → Run ONNX models
6. Get predictions → Display in app

---

## Model Size Estimates

| Format | Phishing | Is OTP | Intent | Total |
|--------|----------|--------|--------|-------|
| ONNX   | ~500 KB  | ~500 KB| ~1 MB  | ~2 MB |
| TFLite | ~300 KB  | ~300 KB| ~600 KB| ~1.2 MB |
| Pickle | ~2 MB    | ~2 MB  | ~3 MB  | ~7 MB (not suitable) |

---

## Performance Considerations

### Inference Speed (estimated)
- **ONNX Runtime Mobile**: ~5-10 ms per SMS
- **TFLite**: ~2-5 ms per SMS
- **Server API**: ~50-100 ms (network latency)

### Memory Usage
- **ONNX Runtime**: ~50-100 MB RAM
- **TFLite**: ~30-50 MB RAM

---

## Implementation Checklist

### Phase 1: Model Export ✅
- [x] Export models to ONNX format
- [x] Create metadata files
- [x] Document feature extraction

### Phase 2: Android Port
- [ ] Port TF-IDF vectorization to Java/Kotlin
- [ ] Port heuristic feature extraction
- [ ] Integrate ONNX Runtime Mobile
- [ ] Create inference wrapper class

### Phase 3: Testing
- [ ] Test on synthetic test set
- [ ] Test on real SMS samples
- [ ] Benchmark performance
- [ ] Optimize for battery usage

### Phase 4: Deployment
- [ ] Package models in APK
- [ ] Add model versioning
- [ ] Implement model updates (optional)
- [ ] Add error handling

---

## Alternative: Simplified Model for Android

If ONNX/TFLite is too complex, consider:

1. **Use only heuristic features** (no TF-IDF)
   - Simpler, faster
   - Lower accuracy (~85-90% vs 95%)
   - Easy to port to Java

2. **Use pre-trained word embeddings**
   - FastText or Word2Vec
   - Smaller than TF-IDF vocab
   - Better for mobile

3. **Hybrid: Heuristics + Simple ML**
   - Train a smaller model (fewer features)
   - Use only heuristic features + simple text stats
   - Export to TFLite

---

## Next Steps

1. **Test current models** on synthetic test set
2. **Export models** using `export_models_for_android.py`
3. **Evaluate ONNX models** (test inference speed/accuracy)
4. **Port feature extraction** to Java/Kotlin
5. **Integrate into Android app**

---

## Files Created

- `export_models_for_android.py` - Exports models in multiple formats
- `inference_example.py` - Python inference example (reference for Android port)
- `model_metadata.json` - Model information
- `heuristic_features.json` - Feature definitions

