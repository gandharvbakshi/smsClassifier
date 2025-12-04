# SMS Classifier: Technical Journey and Architecture Decisions

**Document Version:** 1.0  
**Date:** November 2024  
**Project:** SMS Classifier Android Application

---

## Executive Summary

This document outlines the technical evolution of the SMS Classifier application, focusing on the classifier engine architecture decisions. The journey progressed from simple on-device models to a hybrid ensemble approach combining classical machine learning with large language models, ultimately achieving optimal accuracy and performance.

---

## 1. Initial Approach: On-Device Logistic Regression

### 1.1 Motivation
- **Goal:** Complete on-device processing for privacy and offline capability
- **Approach:** Logistic Regression (LR) model trained on TF-IDF features
- **Deployment:** ONNX Runtime Mobile for Android

### 1.2 Implementation
- Feature extraction: TF-IDF vectorization of SMS text
- Model: Binary/multiclass logistic regression
- Inference: ONNX Runtime on Android device
- Latency: <50ms per message

### 1.3 Results
- **Accuracy:** ~65-70% on synthetic test set
- **F1 Score:** 0.68 (OTP detection), 0.72 (Phishing detection)
- **Issues:**
  - Poor generalization to unseen message patterns
  - Limited context understanding
  - High false positive rate for OTP detection
  - Struggled with intent classification (9 classes)

### 1.4 Trade-offs
| Aspect | Pros | Cons |
|--------|------|------|
| Privacy | ✅ Complete on-device, no data transmission | ❌ Limited model capacity |
| Latency | ✅ Very fast (<50ms) | ❌ Poor accuracy negates speed benefit |
| Offline | ✅ Works without internet | ❌ Accuracy too low for production |
| Maintenance | ✅ No server costs | ❌ Model updates require app updates |

**Decision:** Rejected due to insufficient accuracy for production use.

---

## 2. LightGBM: Gradient Boosting Approach

### 2.1 Motivation
- Improve accuracy while maintaining reasonable model size
- Leverage gradient boosting for better feature interactions
- Still consider on-device deployment

### 2.2 Implementation
- **Features:**
  - TF-IDF vectors (sparse, high-dimensional)
  - Heuristic features (23 hand-crafted features):
    - OTP keywords ("OTP", "verification code", etc.)
    - Phishing indicators ("click here", "urgent", etc.)
    - URL patterns, phone number patterns
    - Message length, sender patterns
- **Models:**
  - Binary classifier for `is_otp`
  - Binary classifier for `is_phishing`
  - Multiclass classifier for `otp_intent` (9 classes)
- **Training:**
  - LightGBM with hyperparameter tuning
  - Cross-validation on synthetic test set
  - Model size: ~0.68MB per model

### 2.3 Results
- **Accuracy:** 
  - OTP Detection: 87%
  - Phishing Detection: 91%
  - OTP Intent Classification: 78% (9 classes)
- **F1 Scores:**
  - OTP: 0.89
  - Phishing: 0.93
  - Intent: 0.76
- **Performance:**
  - Inference time: ~80-120ms on Android
  - Model size: Acceptable for mobile (3 models × 0.68MB)

### 2.4 Trade-offs
| Aspect | Pros | Cons |
|--------|------|------|
| Accuracy | ✅ Significant improvement over LR | ⚠️ Intent classification still suboptimal |
| Model Size | ✅ Reasonable for mobile (~2MB total) | ⚠️ Larger than LR but acceptable |
| Latency | ✅ Fast enough for real-time use | ⚠️ Slightly slower than LR |
| Features | ✅ Hand-crafted features add value | ❌ Requires domain expertise |

**Decision:** Adopted for OTP and Phishing detection. Intent classification needed improvement.

---

## 3. LoRA Fine-Tuning: Small LLM Approach

### 3.1 Motivation
- Improve intent classification accuracy (9 classes)
- Leverage pre-trained language model understanding
- Keep model size manageable with LoRA (Low-Rank Adaptation)

### 3.2 Implementation
- **Base Model:** `Qwen/Qwen2.5-1.5B-Instruct`
  - 1.5 billion parameter instruction-tuned language model
  - Pre-trained by Alibaba Cloud's Qwen team
  - Instruction-tuned variant optimized for following instructions
- **Fine-tuning Method:** LoRA (Low-Rank Adaptation)
  - **LoRA Rank (r):** 8
  - **LoRA Alpha:** 16
  - **LoRA Dropout:** 0.05
  - **Target Modules:** q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
  - Reduces trainable parameters by 90%+ (only adapter weights trained)
  - Faster training, smaller adapter size (~few MB)
- **Training Configuration:**
  - **Quantization:** 4-bit (bitsandbytes) for memory efficiency
  - **Sequence Length:** 512 tokens (max)
  - **Learning Rate:** 2e-4
  - **Batch Size:** 2 per device
  - **Gradient Accumulation:** 32 steps
  - **Epochs:** 3
  - **Precision:** FP16 or BF16 (if supported)
- **Training Data:** Synthetic SMS dataset with labeled intents (JSONL format)
- **Deployment:** ONNX conversion attempted for mobile inference

### 3.3 Results
- **Accuracy:**
  - Intent Classification: 82% (improvement over LightGBM)
  - OTP Detection: Similar to LightGBM
  - Phishing Detection: Similar to LightGBM
- **Model Size:** ~3-5MB (larger than LightGBM)
- **Latency:** 150-200ms (slower than LightGBM)
- **Issues:**
  - Still not reaching desired accuracy (>90%)
  - Model complexity increased significantly
  - Training time and computational cost higher
  - Edge cases still problematic

### 3.4 Trade-offs
| Aspect | Pros | Cons |
|--------|------|------|
| Accuracy | ✅ Better intent classification | ⚠️ Still below target (90%+) |
| Model Size | ⚠️ Larger than LightGBM | ❌ 3-5MB per model |
| Latency | ⚠️ Acceptable but slower | ❌ 150-200ms per inference |
| Complexity | ❌ More complex training pipeline | ❌ Requires GPU for training |
| Generalization | ✅ Better language understanding | ⚠️ Still struggles with edge cases |

**Decision:** Partially adopted. Better than LightGBM for intent, but not sufficient for production quality.

---

## 4. Classical Models: Final Baseline

### 4.1 Motivation
- LightGBM showed strong performance for binary classification
- Classical ML models are interpretable and reliable
- Good balance of accuracy, speed, and model size
- Proven track record in production systems

### 4.2 Final Architecture
- **OTP Detection:** LightGBM binary classifier
  - Accuracy: 87%
  - F1: 0.89
  - Model: `model_isotp.onnx` (~0.68MB)
- **Phishing Detection:** LightGBM binary classifier
  - Accuracy: 91%
  - F1: 0.93
  - Model: `model_phishing.onnx` (~0.68MB)
- **Intent Classification:** LightGBM multiclass classifier
  - Accuracy: 78%
  - F1: 0.76
  - Model: `model_intent.onnx` (~3MB)
  - Classes: 9 OTP intent categories

### 4.3 Production Deployment
- **On-Device:** All three models deployed via ONNX Runtime
- **Features:** TF-IDF + 23 heuristic features
- **Inference:** ~100ms total for all three models
- **Fallback:** Heuristic rules for edge cases

### 4.4 Trade-offs
| Aspect | Pros | Cons |
|--------|------|------|
| Accuracy | ✅ Good for binary tasks | ⚠️ Intent classification (78%) needs improvement |
| Speed | ✅ Fast inference (~100ms) | ✅ Acceptable for real-time |
| Model Size | ✅ Reasonable (~4.4MB total) | ✅ Fits in mobile app |
| Interpretability | ✅ Feature importance available | ✅ Can debug misclassifications |
| Maintenance | ✅ Simple retraining pipeline | ✅ No GPU required |

**Decision:** Adopted as baseline. Intent classification identified as improvement area.

---

## 5. Hybrid Ensemble: GROQ + Large Model + Classical Models

### 5.1 Motivation
- LightGBM intent classifier accuracy (78%) insufficient
- Large language models excel at understanding context and intent
- GROQ provides high-throughput, low-latency LLM inference
- Hybrid approach: Use best tool for each task

### 5.2 Architecture Design

#### 5.2.1 Two-Stage Pipeline
```
Stage 1: LightGBM (On-Device or Server)
  ├─ OTP Detection (is_otp) → LightGBM
  └─ Phishing Detection (is_phishing) → LightGBM

Stage 2: GROQ LLM (Cloud, Conditional)
  └─ OTP Intent Classification → Only if is_otp = true
```

#### 5.2.2 Rationale
- **OTP/Phishing Detection:** LightGBM already achieves 87-91% accuracy
- **Intent Classification:** LLM needed for 90%+ accuracy
- **Cost Optimization:** Only call GROQ when OTP detected (~30% of messages)
- **Latency Optimization:** LightGBM runs first (fast), LLM only when needed

### 5.3 Implementation

#### 5.3.1 LightGBM Models (Stage 1)
- **Deployment Options:**
  - On-device: ONNX Runtime Mobile (privacy-first)
  - Server: FastAPI backend (better accuracy, requires internet)
- **Models:**
  - `model_isotp.onnx`: OTP detection
  - `model_phishing.onnx`: Phishing detection
- **Features:** TF-IDF + 23 heuristic features

#### 5.3.2 GROQ LLM (Stage 2)
- **Model:** `llama-3.1-8b-instant` via GROQ API
- **Trigger:** Only when `is_otp = true` (from LightGBM)
- **Input:** SMS text + sender (optional)
- **Output:** OTP intent label (9 classes)
- **Latency:** ~229ms average per message (measured on 200 test messages, range: ~150-400ms)
- **Cost:** Pay-per-request (cost-effective due to conditional execution)

#### 5.3.3 System Prompt
```
You are an SMS security classifier. Classify OTP messages into one of these categories:
- NOT_OTP
- APP_ACCOUNT_CHANGE_OTP
- APP_LOGIN_OTP
- BANK_OR_CARD_TXN_OTP
- DELIVERY_OR_SERVICE_OTP
- FINANCIAL_LOGIN_OTP
- GENERIC_APP_ACTION_OTP
- KYC_OR_ESIGN_OTP
- UPI_TXN_OR_PIN_OTP

Consider context, sender, and message content.
```

### 5.4 Results

#### 5.4.1 Accuracy Metrics (Synthetic Test Set)
| Task | Model | Accuracy | F1 Score |
|------|-------|----------|----------|
| OTP Detection | LightGBM | 87% | 0.89 |
| Phishing Detection | LightGBM | 91% | 0.93 |
| Intent Classification | GROQ (llama-3.1-8b) | **92%** | **0.91** |
| Intent Classification | LightGBM (baseline) | 78% | 0.76 |

**Improvement:** Intent classification accuracy increased from 78% to 92% (+14 percentage points).

#### 5.4.2 Performance Metrics
- **LightGBM Inference:** ~80-120ms (on-device or server)
- **GROQ API Latency:** ~229ms average per message (measured on 200 test messages, range: ~150-400ms)
- **Total Latency:** 
  - Non-OTP messages: ~100ms (LightGBM only)
  - OTP messages: ~300-350ms average (LightGBM + GROQ)
- **Cost:** ~$0.0001 per OTP message (GROQ pricing)

### 5.5 Trade-offs

| Aspect | Pros | Cons |
|--------|------|------|
| **Accuracy** | ✅ Best overall (92% intent) | ✅ Acceptable trade-off |
| **Latency** | ✅ Fast for non-OTP (100ms) | ⚠️ Slower for OTP (~300-350ms avg) |
| **Cost** | ✅ Only pay for OTP messages | ⚠️ Requires internet for GROQ |
| **Privacy** | ⚠️ OTP content sent to GROQ | ✅ Non-OTP stays on-device |
| **Reliability** | ⚠️ Depends on GROQ availability | ✅ LightGBM fallback possible |
| **Scalability** | ✅ GROQ handles scale | ✅ No server management |

### 5.6 Final Architecture Decision

**Hybrid Ensemble Approach:**
1. **LightGBM** for OTP and Phishing detection (fast, accurate, on-device capable)
2. **GROQ LLM** for OTP intent classification (high accuracy, conditional execution)
3. **FastAPI Backend** to orchestrate the ensemble
4. **Android App** can use on-device LightGBM or server-based ensemble

**Rationale:**
- Optimal accuracy (92% intent) while maintaining reasonable latency
- Cost-effective (only pay for OTP classification)
- Flexible deployment (on-device or cloud)
- Best-of-both-worlds: classical ML speed + LLM understanding

---

## 6. Production Architecture

### 6.1 Deployment Model

```
┌─────────────────────────────────────────────────────────┐
│                    Android App                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Option A: On-Device (Privacy-First)              │  │
│  │  - LightGBM (ONNX) for OTP/Phishing               │  │
│  │  - Falls back to server for intent                │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Option B: Server-Based (Best Accuracy)         │  │
│  │  - FastAPI backend                               │  │
│  │  - LightGBM for OTP/Phishing                     │  │
│  │  - GROQ for intent (conditional)                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Cloud Run)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ LightGBM     │  │ LightGBM     │  │ GROQ API     │ │
│  │ (is_otp)     │  │ (is_phishing)│  │ (otp_intent) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Key Design Decisions

1. **Conditional LLM Execution:** Only call GROQ when OTP detected
   - Reduces cost by ~70% (only 30% of messages are OTPs)
   - Reduces latency for non-OTP messages
   - Maintains privacy (non-OTP messages never leave device/server)

2. **LightGBM for Binary Tasks:** Proven accuracy and speed
   - OTP detection: 87% accuracy, <100ms
   - Phishing detection: 91% accuracy, <100ms
   - No need for LLM for these tasks

3. **GROQ for Intent:** Best accuracy for complex classification
   - 92% accuracy vs 78% with LightGBM
   - Understands context and nuances
   - Worth the additional latency for OTP messages

4. **Flexible Deployment:** Support both on-device and server
   - Privacy-conscious users: On-device LightGBM
   - Best accuracy: Server-based ensemble
   - User choice in app settings

---

## 7. Lessons Learned

### 7.1 Model Selection
- **Simple models (LR)** insufficient for complex NLP tasks
- **Classical ML (LightGBM)** excellent for binary classification
- **Small LLMs (LoRA)** better but not production-ready
- **Large LLMs (GROQ)** best for complex intent understanding

### 7.2 Architecture Patterns
- **Hybrid approaches** often outperform single-model solutions
- **Conditional execution** optimizes cost and latency
- **Right tool for the job:** Use classical ML for simple tasks, LLM for complex ones

### 7.3 Production Considerations
- **Accuracy vs. Latency:** Balance based on use case
- **Cost optimization:** Conditional LLM execution reduces costs significantly
- **Privacy:** On-device option important for sensitive data
- **Reliability:** Fallback mechanisms essential

### 7.4 Future Improvements
- Fine-tune smaller LLM specifically for SMS intent (reduce latency)
- Explore quantization for on-device LLM deployment
- Continuous learning from user feedback
- A/B testing different model combinations

---

## 8. Technical Specifications

### 8.1 Models
| Model | Type | Size | Accuracy | Latency |
|-------|------|------|----------|---------|
| `model_isotp.onnx` | LightGBM | 0.68MB | 87% | ~40ms |
| `model_phishing.onnx` | LightGBM | 0.68MB | 91% | ~40ms |
| `model_intent.onnx` | LightGBM | 3MB | 78% | ~80ms |
| GROQ (llama-3.1-8b) | LLM | N/A | 92% | ~229ms avg |

### 8.2 Features
- **TF-IDF Vectors:** Sparse representation of SMS text
- **Heuristic Features (23):**
  - OTP keywords (5 features)
  - Phishing indicators (8 features)
  - URL patterns (3 features)
  - Phone number patterns (2 features)
  - Message characteristics (5 features)

### 8.3 Infrastructure
- **Backend:** FastAPI on Google Cloud Run
- **LLM Provider:** GROQ API
- **Model Storage:** ONNX format for mobile, Pickle for server
- **Database:** Room (Android), PostgreSQL (optional for analytics)

---

## 9. Conclusion

The SMS Classifier evolved from simple on-device models to a sophisticated hybrid ensemble combining classical machine learning with large language models. The final architecture achieves:

- **High Accuracy:** 87% (OTP), 91% (Phishing), 92% (Intent)
- **Reasonable Latency:** 100-500ms depending on message type
- **Cost-Effective:** Conditional LLM execution minimizes costs
- **Privacy-First:** On-device option available
- **Production-Ready:** Reliable, scalable, maintainable

The key insight: **Use the right tool for each task.** LightGBM excels at binary classification, while LLMs excel at understanding context and intent. Combining them in a conditional pipeline provides the best of both worlds.

---

## Appendix A: Feature Engineering by Model Approach

This appendix documents the exact features used for each model approach in our journey.

---

### A.1 Logistic Regression (LR) Features

#### Feature Set
- **Primary Features:** TF-IDF word embeddings only
- **Feature Count:** ~5,000-10,000 dimensions (vocabulary size)
- **Feature Type:** Sparse vector representation

#### Implementation Details
- **TF-IDF Vectorization:**
  - Vocabulary built from training corpus
  - Term Frequency (TF): Count of word occurrences in message
  - Inverse Document Frequency (IDF): Log of inverse document frequency
  - Normalized to unit length (L2 normalization)
- **Preprocessing:**
  - Lowercase conversion
  - Whitespace tokenization
  - No stemming or lemmatization
  - No stop word removal

#### Feature Vector Structure
```
[TF-IDF(word_1), TF-IDF(word_2), ..., TF-IDF(word_n)]
```
- **Dimensions:** Variable (depends on vocabulary size)
- **Sparsity:** High (most values are 0)
- **Normalization:** L2 normalized

#### Limitations
- No contextual features
- No domain-specific knowledge
- No sender information
- Limited to word-level patterns

**Result:** Insufficient for complex classification tasks (65-70% accuracy).

---

### A.2 LightGBM Features

#### Feature Set
- **Primary Features:** TF-IDF vectors + 23 heuristic features
- **Total Dimensions:** TF-IDF vocabulary size + 23
- **Feature Types:** Mixed (sparse vectors + binary indicators)

#### A.2.1 TF-IDF Features
- **Vocabulary Size:** ~5,000-10,000 terms (from training corpus)
- **Vectorization Method:** Same as LR approach
- **Normalization:** Term frequency normalized by message length
- **Storage:** Sparse representation for efficiency

#### A.2.2 Heuristic Features (23 Total)

**Category 1: Basic Text Patterns (4 features)**
1. **Contains digits:** Binary (1 if message contains any digit, 0 otherwise)
2. **Contains "OTP" keyword:** Binary (case-insensitive match)
3. **Contains security warnings:** Binary (matches "do not share", "never share")
4. **Contains URLs:** Binary (matches "http://", "https://", "www.")

**Category 2: Phishing Indicators (5 features)**
5. **Action words:** Binary (matches "login", "verify", "update", "click", "call", "share")
6. **Bank security phrases:** Binary (matches "bank never asks", "otp is secret", "do not disclose")
7. **SMS blocking reference:** Binary (matches "sms block 7007")
8. **Reward/lottery keywords:** Binary (matches "reward", "win", "cashback", "lottery", "prize", "gift")
9. **Trading/investment keywords:** Binary (matches trading platforms, broker names, stock market terms)

**Category 3: OTP Context Indicators (6 features)**
10. **Social/entertainment apps:** Binary (matches app login contexts)
11. **Delivery/courier keywords:** Binary (matches delivery, courier, package, order, shipment, tracking)
12. **UPI/PIN keywords:** Binary (matches UPI, unified payments, PIN, device linking)
13. **KYC/e-sign keywords:** Binary (matches KYC, know your customer, e-sign, document signing)
14. **Account change keywords:** Binary (matches password reset, change password, update profile, change phone/email)
15. **OTP phrases:** Binary (matches "one time password", "verification code", "authentication code", "your code is")

**Category 4: Financial Patterns (3 features)**
16. **Currency amounts:** Binary (matches INR, Rs., ₹ followed by numbers)
17. **Masked card/account:** Binary (matches "XX1234", "xxxx1234", "card XX", "account XX")
18. **Urgency indicators:** Binary (matches "urgent", "immediately", "act now", "expires soon", "limited time")

**Category 5: Suspicious Links (1 feature)**
19. **Shortened URLs:** Binary (matches "bit.ly", "tinyurl", "short.link", "click here", "verify link")

**Category 6: Sender-Based Features (4 features)**
20. **Financial institutions:** Binary (matches ICICI, HDFC, SBI, AXIS, KOTAK, ZERODHA, GROWW, UPSTOX, PAYTM, PHONEPE, GPAY in sender)
21. **E-commerce/delivery:** Binary (matches SWIGGY, ZOMATO, AMAZON, FLIPKART, DELHIVERY, BLUEDART in sender)
22. **Social/streaming apps:** Binary (matches NETFLIX, SPOTIFY, INSTAGRAM, FACEBOOK, TWITTER in sender)
23. **Numeric sender:** Binary (matches 10-12 digit phone numbers)

#### Feature Vector Structure
```
[TF-IDF(word_1), ..., TF-IDF(word_n), heuristic_1, ..., heuristic_23]
```
- **Dimensions:** ~5,000-10,000 (TF-IDF) + 23 (heuristics) = ~5,023-10,023
- **Sparsity:** High for TF-IDF portion, dense for heuristic portion
- **Feature Importance:** LightGBM provides feature importance scores

#### Feature Engineering Process
1. **TF-IDF Extraction:**
   - Load vocabulary from `feature_map.json`
   - Tokenize message text
   - Compute term frequencies
   - Normalize by message length

2. **Heuristic Feature Extraction:**
   - Apply regex patterns to message text
   - Apply regex patterns to sender (if available)
   - Binary encoding (1 if pattern matches, 0 otherwise)

3. **Feature Combination:**
   - Concatenate TF-IDF vector with heuristic features
   - Single feature vector for model input

#### Advantages
- **Domain Knowledge:** Heuristic features encode SMS-specific patterns
- **Interpretability:** Can understand which patterns trigger classifications
- **Robustness:** Multiple feature types provide redundancy
- **Efficiency:** Binary features are fast to compute

**Result:** Significant accuracy improvement (87% OTP, 91% Phishing, 78% Intent).

---

### A.3 LoRA Fine-Tuning (Small LLM) Features

#### Feature Set
- **Primary Features:** Raw text tokens (tokenized input)
- **Feature Type:** Token embeddings (learned during pre-training)
- **No explicit feature engineering:** Model learns features from text
- **Model Used:** `Qwen/Qwen2.5-1.5B-Instruct`

#### Implementation Details
- **Input Format:** Instruction-following format with structured prompt
  - Template: `"{instruction}\n\nInput:\n{input}\n\nJSON:"`
  - Output: JSON object with classification labels
- **Tokenization:**
  - **Tokenizer:** Qwen tokenizer (SentencePiece-based, BPE subword tokenization)
  - **Special Tokens:** Qwen-specific tokens (e.g., `<|im_start|>`, `<|im_end|>`, `<|endoftext|>`)
  - **Padding Token:** Uses EOS token as padding token
- **Sequence Length:** 512 tokens (max, truncated/padded)
- **Embeddings:**
  - Pre-trained token embeddings (from Qwen2.5-1.5B base model)
  - Contextual embeddings from transformer decoder layers
  - Fine-tuned with LoRA adapters (rank=8, alpha=16)
- **Model Architecture:**
  - **Base Model:** Qwen2.5-1.5B-Instruct (decoder-only transformer)
  - **Hidden Size:** ~2048 dimensions (Qwen2.5 architecture)
  - **Quantization:** 4-bit quantization (bitsandbytes) for training efficiency

#### Feature Vector Structure
```
[token_embedding_1, token_embedding_2, ..., token_embedding_512]
```
- **Dimensions:** Hidden size of Qwen2.5-1.5B (~2048)
- **Sequence Length:** Up to 512 tokens
- **Total Dimensions:** Sequence length × Hidden size (e.g., 512 × 2048 = 1,048,576)

#### Preprocessing
- **Text Cleaning:** Minimal (Qwen tokenizer handles normalization)
- **Input Format:** Structured instruction-following format
- **Format:** Instruction prompt + SMS text + expected JSON output

#### Advantages
- **Contextual Understanding:** Model understands word relationships
- **No Manual Features:** Learns relevant patterns automatically
- **Transfer Learning:** Benefits from pre-training on large text corpora

#### Limitations
- **Model Size:** Larger than classical ML models
- **Latency:** Slower inference (150-200ms)
- **Training Complexity:** Requires GPU and fine-tuning expertise

**Result:** Better intent classification (82%) but still below target, higher complexity.

---

### A.4 Hybrid Ensemble Features

#### A.4.1 LightGBM Component Features

**Same as Section A.2:**
- TF-IDF vectors (~5,000-10,000 dimensions)
- 23 heuristic features
- **Total:** ~5,023-10,023 dimensions

**Used For:**
- OTP Detection (`is_otp`)
- Phishing Detection (`is_phishing`)

#### A.4.2 GROQ LLM Component Features

**Input Format:**
- **Primary:** Raw SMS text (string)
- **Optional:** Sender phone number (for context)
- **System Prompt:** Classification instructions and label definitions

#### Feature Processing
- **Tokenization:** Handled by GROQ's `llama-3.1-8b-instant` model
- **No Explicit Features:** Model uses learned representations
- **Context:** Full message text + sender (if provided) + system prompt

#### Input Structure
```
System Prompt:
"You are an SMS security classifier. Classify OTP messages into one of these categories:
- NOT_OTP
- APP_ACCOUNT_CHANGE_OTP
- APP_LOGIN_OTP
- BANK_OR_CARD_TXN_OTP
- DELIVERY_OR_SERVICE_OTP
- FINANCIAL_LOGIN_OTP
- GENERIC_APP_ACTION_OTP
- KYC_OR_ESIGN_OTP
- UPI_TXN_OR_PIN_OTP"

User Message:
"[SENDER] message text"
```

#### Feature Advantages
- **Full Context:** Model sees entire message
- **Semantic Understanding:** Understands intent beyond keywords
- **Flexible:** Can handle variations and edge cases
- **No Feature Engineering:** Model learns relevant patterns

**Result:** Best intent classification accuracy (92%).

---

### A.5 Feature Comparison Summary

| Approach | Feature Types | Dimensions | Manual Engineering | Context Understanding |
|----------|---------------|------------|-------------------|----------------------|
| **LR** | TF-IDF only | ~5,000-10,000 | Low | None |
| **LightGBM** | TF-IDF + 23 heuristics | ~5,023-10,023 | High | Limited (heuristics) |
| **LoRA/Qwen2.5-1.5B** | Token embeddings | ~1,048,576 | None | High (learned) |
| **GROQ LLM** | Token embeddings | ~98,304 | None | Very High (pre-trained) |

#### Key Insights

1. **TF-IDF Alone Insufficient:**
   - Word frequencies don't capture context
   - No domain-specific knowledge
   - Result: 65-70% accuracy

2. **Heuristic Features Add Value:**
   - Domain expertise encoded as features
   - Significant accuracy boost (87-91% for binary tasks)
   - Interpretable and debuggable

3. **LLM Features Superior for Intent:**
   - Contextual understanding crucial for intent classification
   - Pre-trained knowledge helps with edge cases
   - Result: 92% accuracy vs 78% with LightGBM

4. **Hybrid Approach Optimal:**
   - Use simple features (TF-IDF + heuristics) for binary tasks
   - Use rich features (LLM embeddings) for complex classification
   - Best accuracy with reasonable cost/latency

---

### A.6 Feature Extraction Code Reference

The feature extraction implementation is in:
- **File:** `android_sms_classifier/app/src/main/java/com/smsclassifier/app/classification/FeatureExtractor.kt`
- **Methods:**
  - `extractTfIdfVector()`: Computes TF-IDF vector from vocabulary
  - `extractHeuristicFeatures()`: Computes 23 heuristic features
  - `extractFeatures()`: Combines both feature types

**Vocabulary File:**
- `android_sms_classifier/app/src/main/assets/feature_map.json`
- Contains: Vocabulary mapping (word → index) and heuristic feature count

---

## Appendix B: Evaluation Metrics

### Synthetic Test Set Results

**LightGBM Baseline:**
- OTP Detection: 87% accuracy, F1=0.89
- Phishing Detection: 91% accuracy, F1=0.93
- Intent Classification: 78% accuracy, F1=0.76

**Hybrid Ensemble (LightGBM + GROQ):**
- OTP Detection: 87% accuracy, F1=0.89 (unchanged)
- Phishing Detection: 91% accuracy, F1=0.93 (unchanged)
- Intent Classification: **92% accuracy, F1=0.91** (+14% improvement)

**Test Set Size:** 1000 synthetic SMS messages  
**Evaluation Date:** November 2024

---

*Document prepared for: SMS Classifier Project*  
*Last Updated: November 18, 2024*

