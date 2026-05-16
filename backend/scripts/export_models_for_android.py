"""
Export ML models for Android deployment.

This script creates multiple export formats:
1. Pickle files (TF-IDF vectorizer + models) - for Python/backend use
2. ONNX format - can run on Android via ONNX Runtime Mobile
3. TFLite format - native Android support (requires TensorFlow conversion)
4. JSON metadata - model info, feature names, etc.

For Android SMS app:
- TFLite is preferred (native, fast, small)
- ONNX Runtime Mobile is alternative (good performance)
- Pickle is NOT suitable (requires Python runtime)

Usage:
    python export_models_for_android.py
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

try:
    import onnx
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    print("WARNING: skl2onnx not installed. Install with: pip install skl2onnx onnx")

try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    print("WARNING: tensorflow not installed. TFLite export will be skipped.")

RANDOM_SEED = 2025
TRAIN_FILE = "classification_results_with_phishing_llm_balanced_with_sender.csv"
TRAINED_MODELS_DIR = Path("trained_models")
EXPORT_DIR = Path("android_model_exports")


def ensure_export_dir():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: str) -> pd.DataFrame:
    """Load and prepare dataset."""
    df = pd.read_csv(path, low_memory=False)
    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    
    if "predicted_is_otp" in df.columns:
        if df["predicted_is_otp"].dtype == "bool":
            df["predicted_is_otp"] = df["predicted_is_otp"].astype(int)
        else:
            df["predicted_is_otp"] = df["predicted_is_otp"].astype(str).str.lower().map({"true": 1, "false": 0})
    
    if "is_phishing_original" in df.columns:
        if df["is_phishing_original"].dtype == "bool":
            df["is_phishing_original"] = df["is_phishing_original"].astype(int)
        else:
            df["is_phishing_original"] = df["is_phishing_original"].astype(str).str.lower().map({"true": 1, "false": 0})
    
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)
    df.loc[df["predicted_is_otp"] == 0, "predicted_otp_intent"] = "NOT_OTP"
    
    if "sender" in df.columns:
        df["sender"] = df["sender"].astype(str).fillna("")
    else:
        df["sender"] = ""
    
    return df


def build_heuristic_features(text_series: pd.Series, sender_series: pd.Series = None) -> csr_matrix:
    """Build heuristic features (same as training script)."""
    import re
    
    patterns = {
        "has_digits": r"\d",
        "has_otp_word": r"\botp\b",
        "has_do_not_share": r"do not share|never share",
        "has_url": r"https?://|www\.",
        "has_request": r"\blogin\b|\bverify\b|\bupdate\b|\bclick\b|\bcall\b|\bshare\b",
        "mentions_bank_safe": r"bank never asks|otp is secret|do not disclose",
        "icici_sms_block": r"sms block 7007",
        "has_reward": r"reward|win|cashback|lottery|prize|gift",
        "has_financial_context": r"\b(trading|investment|portfolio|demat|mutual fund|stocks|NSE|BSE|Zerodha|Groww|Upstox|broker|equity|Angel One|Kotak Securities|ICICI Direct|HDFC Securities)\b",
        "has_app_context": r"\b(social|entertainment|streaming|gaming|shopping|app login|account login)\b",
        "has_delivery_context": r"\b(delivery|deliver|courier|package|order|shipment|tracking|OTP.*delivery|share.*code.*delivery)\b",
        "has_upi_context": r"\b(UPI|unified payments|PIN|device.*link|link.*device|bind.*device)\b",
        "has_kyc_context": r"\b(KYC|know your customer|e-sign|esign|document.*sign|verification.*document)\b",
        "has_account_change": r"\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|update.*contact)\b",
        "has_otp_phrase": r"\b(one time password|OTP|verification code|authentication code|this is your.*code|your.*code is|give.*code|share.*code|delivery code)\b",
        "has_amount_pattern": r"\b(INR|Rs\.?|₹)\s*\d+[.,]?\d*\b",
        "has_card_mask": r"\b(XX\d+|xxxx\d+|card.*XX|account.*XX)\b",
        "has_urgent_language": r"\b(urgent|immediately|act now|expires.*soon|limited time|verify now)\b",
        "has_suspicious_link": r"\b(bit\.ly|tinyurl|short\.link|click.*here|verify.*link)\b",
    }
    
    rows = []
    for idx, text in enumerate(text_series):
        feature_row = [
            bool(re.search(pattern, text, flags=re.IGNORECASE))
            for pattern in patterns.values()
        ]
        
        if sender_series is not None and len(sender_series) > idx:
            sender = str(sender_series.iloc[idx]).upper()
            feature_row.extend([
                bool(re.search(r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY)\b", sender)),
                bool(re.search(r"\b(SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART)\b", sender)),
                bool(re.search(r"\b(NETFLIX|SPOTIFY|INSTAGRAM|FACEBOOK|TWITTER)\b", sender)),
                bool(re.search(r"^\d{10,12}$", sender)),
            ])
        else:
            feature_row.extend([False, False, False, False])
        
        rows.append(feature_row)
    
    return csr_matrix(np.array(rows, dtype=np.float32))


def load_trained_models():
    """Load pre-trained models from trained_models directory."""
    print("Loading pre-trained models...")
    
    model_files = {
        "vectorizer": TRAINED_MODELS_DIR / "tfidf_vectorizer.pkl",
        "model_phishing": TRAINED_MODELS_DIR / "model_phishing.pkl",
        "model_isotp": TRAINED_MODELS_DIR / "model_isotp.pkl",
        "model_intent": TRAINED_MODELS_DIR / "model_intent.pkl",
        "le_intent": TRAINED_MODELS_DIR / "label_encoder_intent.pkl",
    }
    
    # Check if all models exist
    missing = [k for k, v in model_files.items() if not v.exists()]
    if missing:
        raise FileNotFoundError(
            f"Pre-trained models not found. Missing: {missing}\n"
            f"Please run train_lightgbm_comparison.py or test_models_on_synthetic.py first."
        )
    
    models = {}
    for name, path in model_files.items():
        with open(path, "rb") as f:
            models[name] = pickle.load(f)
        print(f"  ✓ Loaded {name}")
    
    return models


def train_and_export_models():
    """Load pre-trained models and export in multiple formats."""
    print("=" * 80)
    print("EXPORTING MODELS FOR ANDROID")
    print("=" * 80)
    
    # Load pre-trained models
    print("\n1. Loading pre-trained models...")
    try:
        models = load_trained_models()
        vectorizer = models["vectorizer"]
        model_phishing = models["model_phishing"]
        model_isotp = models["model_isotp"]
        model_intent = models["model_intent"]
        le_intent = models["le_intent"]
        intent_labels = le_intent.classes_.tolist()
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("\nTraining new models instead...")
        # Fallback: train new models
        return train_and_export_models_fallback()
    
    # Load a small sample to get feature dimensions (needed for ONNX)
    print("\n2. Loading sample data for feature extraction...")
    df_sample = load_dataset(TRAIN_FILE)
    df_sample = df_sample.head(100)  # Just need a small sample
    
    # Extract features to get dimensions
    X_sample_tfidf = vectorizer.transform(df_sample["sms_text"])
    sender_sample = df_sample["sender"] if "sender" in df_sample.columns else None
    heur_sample = build_heuristic_features(df_sample["sms_text"], sender_sample)
    X_sample_full = hstack([X_sample_tfidf, heur_sample])
    
    print(f"   Feature dimensions: {X_sample_full.shape[1]}")
    
    # Export metadata
    print("\n3. Exporting metadata...")
    metadata = {
        "models": {
            "phishing": {
                "type": "binary",
                "classes": [0, 1],
                "class_names": ["not_phishing", "phishing"],
            },
            "is_otp": {
                "type": "binary",
                "classes": [0, 1],
                "class_names": ["not_otp", "is_otp"],
            },
            "otp_intent": {
                "type": "multiclass",
                "classes": list(range(len(intent_labels))),
                "class_names": intent_labels,
            },
        },
        "features": {
            "tfidf_vocab_size": len(vectorizer.vocabulary_),
            "heuristic_features": 23,  # 19 patterns + 4 sender features
            "total_features": X_sample_full.shape[1],
        },
        "preprocessing": {
            "normalize_text": True,
            "lowercase": True,
            "ngram_range": [1, 2],
        },
    }
    
    ensure_export_dir()
    with open(EXPORT_DIR / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Export 1: Pickle files (for Python/backend)
    print("\n4. Exporting Pickle files...")
    pickle.dump(vectorizer, open(EXPORT_DIR / "tfidf_vectorizer.pkl", "wb"))
    pickle.dump(model_phishing, open(EXPORT_DIR / "model_phishing.pkl", "wb"))
    pickle.dump(model_isotp, open(EXPORT_DIR / "model_isotp.pkl", "wb"))
    pickle.dump(model_intent, open(EXPORT_DIR / "model_intent.pkl", "wb"))
    pickle.dump(le_intent, open(EXPORT_DIR / "label_encoder_intent.pkl", "wb"))
    
    # Save heuristic feature function info
    heuristic_info = {
        "patterns": [
            "has_digits", "has_otp_word", "has_do_not_share", "has_url", "has_request",
            "mentions_bank_safe", "icici_sms_block", "has_reward", "has_financial_context",
            "has_app_context", "has_delivery_context", "has_upi_context", "has_kyc_context",
            "has_account_change", "has_otp_phrase", "has_amount_pattern", "has_card_mask",
            "has_urgent_language", "has_suspicious_link",
        ],
        "sender_patterns": [
            "has_financial_sender", "has_delivery_sender", "has_app_sender", "is_phone_number",
        ],
    }
    with open(EXPORT_DIR / "heuristic_features.json", "w") as f:
        json.dump(heuristic_info, f, indent=2)
    
    print("   ✓ Saved pickle files")
    
    # Export 2: ONNX format (for Android via ONNX Runtime Mobile)
    if HAS_ONNX:
        print("\n5. Exporting ONNX models...")
        try:
            n_features = X_sample_full.shape[1]
            
            # Define input type
            initial_type = [('float_input', FloatTensorType([None, n_features]))]
            
            # Convert phishing model
            print("  Converting phishing model...")
            onnx_phishing = convert_sklearn(
                model_phishing,
                initial_types=initial_type,
                target_opset=12,
            )
            with open(EXPORT_DIR / "model_phishing.onnx", "wb") as f:
                f.write(onnx_phishing.SerializeToString())
            
            # Convert is_otp model
            print("  Converting is_otp model...")
            onnx_isotp = convert_sklearn(
                model_isotp,
                initial_types=initial_type,
                target_opset=12,
            )
            with open(EXPORT_DIR / "model_isotp.onnx", "wb") as f:
                f.write(onnx_isotp.SerializeToString())
            
            # Convert intent model
            print("  Converting otp_intent model...")
            onnx_intent = convert_sklearn(
                model_intent,
                initial_types=initial_type,
                target_opset=12,
            )
            with open(EXPORT_DIR / "model_intent.onnx", "wb") as f:
                f.write(onnx_intent.SerializeToString())
            
            print("   ✓ Saved ONNX files")
        except Exception as e:
            print(f"   ✗ ONNX export failed: {e}")
    else:
        print("\n5. Skipping ONNX export (skl2onnx not installed)")
    
    # Export 3: Create inference example
    print("\n6. Creating inference example...")
    create_inference_example(vectorizer, model_phishing, model_isotp, model_intent, le_intent)
    
    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"\nExported files are in: {EXPORT_DIR}/")
    print("\nFiles created:")
    print("  - tfidf_vectorizer.pkl (TF-IDF vectorizer)")
    print("  - model_phishing.pkl (Phishing classifier)")
    print("  - model_isotp.pkl (Is OTP classifier)")
    print("  - model_intent.pkl (OTP Intent classifier)")
    print("  - label_encoder_intent.pkl (Intent label encoder)")
    if HAS_ONNX:
        print("  - model_phishing.onnx (ONNX format)")
        print("  - model_isotp.onnx (ONNX format)")
        print("  - model_intent.onnx (ONNX format)")
    print("  - model_metadata.json (Model metadata)")
    print("  - heuristic_features.json (Feature definitions)")
    print("  - inference_example.py (Reference implementation)")
    print("\nFor Android deployment, use the ONNX files with ONNX Runtime Mobile.")


def train_and_export_models_fallback():
    """Fallback: Train models from scratch if pre-trained models not found."""
    print("=" * 80)
    print("TRAINING AND EXPORTING MODELS FOR ANDROID")
    print("=" * 80)
    
    # Load data
    print(f"\n1. Loading training data: {TRAIN_FILE}...")
    df = load_dataset(TRAIN_FILE)
    print(f"   Loaded {len(df)} rows")
    
    # Prepare features
    print("\n2. Preparing features...")
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.95,
        strip_accents="unicode",
    )
    X_tfidf = vectorizer.fit_transform(df["sms_text"])
    
    sender_series = df["sender"] if "sender" in df.columns else None
    X_heuristic = build_heuristic_features(df["sms_text"], sender_series)
    X_full = hstack([X_tfidf, X_heuristic])
    
    # Prepare labels
    y_phishing = df["is_phishing_original"].values
    y_isotp = df["predicted_is_otp"].values
    
    le_intent = LabelEncoder()
    y_intent = le_intent.fit_transform(df["predicted_otp_intent"])
    intent_labels = le_intent.classes_.tolist()
    
    # Train models
    print("\n3. Training models...")
    
    # Phishing model
    print("   Training phishing model...")
    model_phishing = LogisticRegression(
        class_weight="balanced",
        solver="lbfgs",
        max_iter=3000,
        random_state=RANDOM_SEED,
    )
    model_phishing.fit(X_full, y_phishing)
    
    # Is OTP model
    print("   Training is_otp model...")
    model_isotp = LogisticRegression(
        class_weight="balanced",
        solver="lbfgs",
        max_iter=3000,
        random_state=RANDOM_SEED,
    )
    model_isotp.fit(X_full, y_isotp)
    
    # Intent model
    print("   Training otp_intent model...")
    class_weights = {}
    for i, label in enumerate(intent_labels):
        if label == "FINANCIAL_LOGIN_OTP":
            class_weights[i] = 3.0
        elif label == "APP_LOGIN_OTP":
            class_weights[i] = 1.5
        else:
            class_weights[i] = 1.0
    
    model_intent = LogisticRegression(
        class_weight=class_weights,
        solver="saga",
        max_iter=3000,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model_intent.fit(X_full, y_intent)
    
    # Export metadata
    print("\n4. Exporting metadata...")
    metadata = {
        "models": {
            "phishing": {
                "type": "binary",
                "classes": [0, 1],
                "class_names": ["not_phishing", "phishing"],
            },
            "is_otp": {
                "type": "binary",
                "classes": [0, 1],
                "class_names": ["not_otp", "is_otp"],
            },
            "otp_intent": {
                "type": "multiclass",
                "classes": list(range(len(intent_labels))),
                "class_names": intent_labels,
            },
        },
        "features": {
            "tfidf_vocab_size": len(vectorizer.vocabulary_),
            "heuristic_features": 23,  # 19 patterns + 4 sender features
            "total_features": X_full.shape[1],
        },
        "preprocessing": {
            "normalize_text": True,
            "lowercase": True,
            "ngram_range": [1, 2],
        },
    }
    
    with open(EXPORT_DIR / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Export 1: Pickle files (for Python/backend)
    print("\n5. Exporting Pickle files...")
    pickle.dump(vectorizer, open(EXPORT_DIR / "tfidf_vectorizer.pkl", "wb"))
    pickle.dump(model_phishing, open(EXPORT_DIR / "model_phishing.pkl", "wb"))
    pickle.dump(model_isotp, open(EXPORT_DIR / "model_isotp.pkl", "wb"))
    pickle.dump(model_intent, open(EXPORT_DIR / "model_intent.pkl", "wb"))
    pickle.dump(le_intent, open(EXPORT_DIR / "label_encoder_intent.pkl", "wb"))
    
    # Save heuristic feature function info
    heuristic_info = {
        "patterns": [
            "has_digits", "has_otp_word", "has_do_not_share", "has_url", "has_request",
            "mentions_bank_safe", "icici_sms_block", "has_reward", "has_financial_context",
            "has_app_context", "has_delivery_context", "has_upi_context", "has_kyc_context",
            "has_account_change", "has_otp_phrase", "has_amount_pattern", "has_card_mask",
            "has_urgent_language", "has_suspicious_link",
        ],
        "sender_patterns": [
            "has_financial_sender", "has_delivery_sender", "has_app_sender", "is_phone_number",
        ],
    }
    with open(EXPORT_DIR / "heuristic_features.json", "w") as f:
        json.dump(heuristic_info, f, indent=2)
    
    print("   ✓ Saved pickle files")
    
    # Export 2: ONNX format (for Android via ONNX Runtime Mobile)
    if HAS_ONNX:
        print("\n6. Exporting ONNX models...")
        try:
            # Convert to dense for ONNX (ONNX doesn't support sparse)
            X_full_dense = X_full.toarray()
            n_features = X_full_dense.shape[1]
            
            # Define input type
            initial_type = [('float_input', FloatTensorType([None, n_features]))]
            
            # Convert phishing model
            onnx_phishing = convert_sklearn(
                model_phishing,
                initial_types=initial_type,
                target_opset=12,
            )
            with open(EXPORT_DIR / "model_phishing.onnx", "wb") as f:
                f.write(onnx_phishing.SerializeToString())
            
            # Convert is_otp model
            onnx_isotp = convert_sklearn(
                model_isotp,
                initial_types=initial_type,
                target_opset=12,
            )
            with open(EXPORT_DIR / "model_isotp.onnx", "wb") as f:
                f.write(onnx_isotp.SerializeToString())
            
            # Convert intent model
            onnx_intent = convert_sklearn(
                model_intent,
                initial_types=initial_type,
                target_opset=12,
            )
            with open(EXPORT_DIR / "model_intent.onnx", "wb") as f:
                f.write(onnx_intent.SerializeToString())
            
            print("   ✓ Saved ONNX models")
        except Exception as e:
            print(f"   ✗ ONNX export failed: {e}")
    else:
        print("\n6. Skipping ONNX export (skl2onnx not installed)")
    
    # Export 3: TFLite format (requires TensorFlow conversion)
    # Note: This is more complex - we need to create a TensorFlow model that replicates
    # the TF-IDF + heuristic features + Logistic Regression pipeline
    print("\n7. TFLite export...")
    print("   NOTE: TFLite export requires creating a TensorFlow model that replicates")
    print("   the TF-IDF + heuristic pipeline. This is complex and may require a custom")
    print("   TensorFlow model. Consider using ONNX Runtime Mobile instead for Android.")
    
    # Create a simple inference example script
    print("\n8. Creating inference example script...")
    create_inference_example(vectorizer, model_phishing, model_isotp, model_intent, le_intent)
    
    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"\nExported files saved to: {EXPORT_DIR}/")
    print("\nFiles created:")
    print("  - tfidf_vectorizer.pkl (TF-IDF vectorizer)")
    print("  - model_phishing.pkl (Phishing classifier)")
    print("  - model_isotp.pkl (Is OTP classifier)")
    print("  - model_intent.pkl (OTP Intent classifier)")
    print("  - label_encoder_intent.pkl (Intent label encoder)")
    print("  - model_metadata.json (Model metadata)")
    print("  - heuristic_features.json (Heuristic feature definitions)")
    if HAS_ONNX:
        print("  - model_phishing.onnx (ONNX format)")
        print("  - model_isotp.onnx (ONNX format)")
        print("  - model_intent.onnx (ONNX format)")
    print("  - inference_example.py (Python inference example)")


def create_inference_example(vectorizer, model_phishing, model_isotp, model_intent, le_intent):
    """Create a simple inference example script."""
    example_code = '''"""
Simple inference example for Android SMS classification.

This shows how to use the exported models for inference.
For Android, you'll need to port this logic to Java/Kotlin.
"""

import pickle
import re
import numpy as np
from scipy.sparse import csr_matrix, hstack

# Load models
with open("android_model_exports/tfidf_vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

with open("android_model_exports/model_phishing.pkl", "rb") as f:
    model_phishing = pickle.load(f)

with open("android_model_exports/model_isotp.pkl", "rb") as f:
    model_isotp = pickle.load(f)

with open("android_model_exports/model_intent.pkl", "rb") as f:
    model_intent = pickle.load(f)

with open("android_model_exports/label_encoder_intent.pkl", "rb") as f:
    le_intent = pickle.load(f)


def extract_heuristic_features(sms_text: str, sender: str = "") -> np.ndarray:
    """Extract heuristic features from SMS text."""
    patterns = {
        "has_digits": r"\d",
        "has_otp_word": r"\botp\b",
        "has_do_not_share": r"do not share|never share",
        "has_url": r"https?://|www\.",
        "has_request": r"\blogin\b|\bverify\b|\bupdate\b|\bclick\b|\bcall\b|\bshare\b",
        "mentions_bank_safe": r"bank never asks|otp is secret|do not disclose",
        "icici_sms_block": r"sms block 7007",
        "has_reward": r"reward|win|cashback|lottery|prize|gift",
        "has_financial_context": r"\b(trading|investment|portfolio|demat|mutual fund|stocks|NSE|BSE|Zerodha|Groww|Upstox|broker|equity|Angel One|Kotak Securities|ICICI Direct|HDFC Securities)\b",
        "has_app_context": r"\b(social|entertainment|streaming|gaming|shopping|app login|account login)\b",
        "has_delivery_context": r"\b(delivery|deliver|courier|package|order|shipment|tracking|OTP.*delivery|share.*code.*delivery)\b",
        "has_upi_context": r"\b(UPI|unified payments|PIN|device.*link|link.*device|bind.*device)\b",
        "has_kyc_context": r"\b(KYC|know your customer|e-sign|esign|document.*sign|verification.*document)\b",
        "has_account_change": r"\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|update.*contact)\b",
        "has_otp_phrase": r"\b(one time password|OTP|verification code|authentication code|this is your.*code|your.*code is|give.*code|share.*code|delivery code)\b",
        "has_amount_pattern": r"\b(INR|Rs\.?|₹)\s*\d+[.,]?\d*\b",
        "has_card_mask": r"\b(XX\d+|xxxx\d+|card.*XX|account.*XX)\b",
        "has_urgent_language": r"\b(urgent|immediately|act now|expires.*soon|limited time|verify now)\b",
        "has_suspicious_link": r"\b(bit\.ly|tinyurl|short\.link|click.*here|verify.*link)\b",
    }
    
    feature_row = [
        bool(re.search(pattern, sms_text, flags=re.IGNORECASE))
        for pattern in patterns.values()
    ]
    
    # Sender features
    sender_upper = sender.upper()
    feature_row.extend([
        bool(re.search(r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY)\b", sender_upper)),
        bool(re.search(r"\b(SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART)\b", sender_upper)),
        bool(re.search(r"\b(NETFLIX|SPOTIFY|INSTAGRAM|FACEBOOK|TWITTER)\b", sender_upper)),
        bool(re.search(r"^\d{10,12}$", sender_upper)),
    ])
    
    return np.array(feature_row, dtype=np.float32)


def classify_sms(sms_text: str, sender: str = "") -> dict:
    """
    Classify an SMS message.
    
    Returns:
        {
            "is_phishing": bool,
            "is_otp": bool,
            "otp_intent": str,
            "probabilities": {
                "phishing": float,
                "is_otp": float,
                "intent": dict[str, float]
            }
        }
    """
    # Preprocess
    sms_normalized = " ".join(sms_text.strip().split()).lower()
    
    # Extract features
    X_tfidf = vectorizer.transform([sms_normalized])
    X_heuristic = csr_matrix(extract_heuristic_features(sms_text, sender).reshape(1, -1))
    X_full = hstack([X_tfidf, X_heuristic])
    
    # Predict
    is_phishing = bool(model_phishing.predict(X_full)[0])
    is_otp = bool(model_isotp.predict(X_full)[0])
    
    # Intent (only if is_otp)
    if is_otp:
        intent_idx = model_intent.predict(X_full)[0]
        otp_intent = le_intent.inverse_transform([intent_idx])[0]
    else:
        otp_intent = "NOT_OTP"
    
    # Probabilities
    prob_phishing = model_phishing.predict_proba(X_full)[0][1]
    prob_isotp = model_isotp.predict_proba(X_full)[0][1]
    
    intent_probs = {}
    if is_otp:
        intent_probs_raw = model_intent.predict_proba(X_full)[0]
        for idx, label in enumerate(le_intent.classes_):
            intent_probs[label] = float(intent_probs_raw[idx])
    else:
        intent_probs["NOT_OTP"] = 1.0
    
    return {
        "is_phishing": is_phishing,
        "is_otp": is_otp,
        "otp_intent": otp_intent,
        "probabilities": {
            "phishing": float(prob_phishing),
            "is_otp": float(prob_isotp),
            "intent": intent_probs,
        },
    }


# Example usage
if __name__ == "__main__":
    test_sms = "Your OTP for ICICI Bank Card transaction is 456789. Valid for 10 minutes. Do not share."
    result = classify_sms(test_sms, sender="VM-ICICIT-S")
    print("SMS:", test_sms)
    print("Result:", json.dumps(result, indent=2))
'''
    
    with open(EXPORT_DIR / "inference_example.py", "w", encoding="utf-8") as f:
        f.write(example_code)
    
    print("   ✓ Created inference_example.py")


if __name__ == "__main__":
    ensure_export_dir()
    train_and_export_models()

