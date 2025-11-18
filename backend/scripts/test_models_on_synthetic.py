"""
Test both Logistic Regression and LightGBM models on the verified synthetic test set.

This script:
1. Loads the trained models (or trains them if not found)
2. Loads the synthetic test set
3. Evaluates both models
4. Compares accuracy, precision, recall, F1 for all three tasks
"""

import json
import pickle
import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("WARNING: lightgbm not installed. Will only test Logistic Regression.")

RANDOM_SEED = 2025
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
TRAIN_FILE = DATA_DIR / "classification_results_with_phishing_llm_balanced_with_sender.csv"
TEST_FILE = DATA_DIR / "synthetic_test_set_200_verified.csv"
OUTPUT_DIR = ROOT_DIR / "synthetic_test_results"


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: str) -> pd.DataFrame:
    """Load dataset."""
    df = pd.read_csv(path, low_memory=False)
    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    
    # Handle boolean columns
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
    
    # Handle optional sender
    if "sender" in df.columns:
        df["sender"] = df["sender"].astype(str).fillna("")
    else:
        df["sender"] = ""
    
    return df


def vectorize(train_text: pd.Series, test_text: pd.Series, vectorizer: TfidfVectorizer = None) -> Tuple[csr_matrix, csr_matrix, TfidfVectorizer]:
    """Create TF-IDF vectors."""
    if vectorizer is None:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=3,
            max_df=0.95,
            strip_accents="unicode",
        )
        X_train = vectorizer.fit_transform(train_text)
    else:
        X_train = None
    
    X_test = vectorizer.transform(test_text)
    return X_train, X_test, vectorizer


def build_heuristic_features(text_series: pd.Series, sender_series: pd.Series = None) -> csr_matrix:
    """Build enhanced heuristic features."""
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
        
        # Add sender-based features if available
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


def load_or_train_models(train_df: pd.DataFrame, model_dir: Path = None):
    """Load pre-trained models if available, otherwise train new ones."""
    if model_dir is None:
        model_dir = Path("trained_models")
    
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if models exist
    model_files = {
        "vectorizer": model_dir / "tfidf_vectorizer.pkl",
        "lr_phishing": model_dir / "model_phishing.pkl",
        "lr_isotp": model_dir / "model_isotp.pkl",
        "lr_intent": model_dir / "model_intent.pkl",
        "le_intent": model_dir / "label_encoder_intent.pkl",
    }
    
    if HAS_LIGHTGBM:
        model_files.update({
            "lgb_phishing": model_dir / "model_phishing_lgb.pkl",
            "lgb_isotp": model_dir / "model_isotp_lgb.pkl",
        })
    
    # Try to load existing models
    all_exist = all(f.exists() for f in model_files.values())
    
    if all_exist:
        print("Loading pre-trained models...")
        import pickle
        
        models = {}
        with open(model_files["vectorizer"], "rb") as f:
            models["vectorizer"] = pickle.load(f)
        with open(model_files["lr_phishing"], "rb") as f:
            models["lr_phishing"] = pickle.load(f)
        with open(model_files["lr_isotp"], "rb") as f:
            models["lr_isotp"] = pickle.load(f)
        with open(model_files["lr_intent"], "rb") as f:
            models["lr_intent"] = pickle.load(f)
        with open(model_files["le_intent"], "rb") as f:
            models["le_intent"] = pickle.load(f)
        
        if HAS_LIGHTGBM:
            try:
                with open(model_files["lgb_phishing"], "rb") as f:
                    models["lgb_phishing"] = pickle.load(f)
                with open(model_files["lgb_isotp"], "rb") as f:
                    models["lgb_isotp"] = pickle.load(f)
            except FileNotFoundError:
                print("  LightGBM models not found, will skip")
        
        print("  ✓ Loaded pre-trained models")
        return models
    
    # Train new models
    print("Training new models (this may take a few minutes)...")
    models = train_models(train_df)
    
    # Save models
    print("\nSaving trained models...")
    import pickle
    
    with open(model_files["vectorizer"], "wb") as f:
        pickle.dump(models["vectorizer"], f)
    with open(model_files["lr_phishing"], "wb") as f:
        pickle.dump(models["lr_phishing"], f)
    with open(model_files["lr_isotp"], "wb") as f:
        pickle.dump(models["lr_isotp"], f)
    with open(model_files["lr_intent"], "wb") as f:
        pickle.dump(models["lr_intent"], f)
    with open(model_files["le_intent"], "wb") as f:
        pickle.dump(models["le_intent"], f)
    
    if HAS_LIGHTGBM and "lgb_phishing" in models:
        with open(model_files["lgb_phishing"], "wb") as f:
            pickle.dump(models["lgb_phishing"], f)
        with open(model_files["lgb_isotp"], "wb") as f:
            pickle.dump(models["lgb_isotp"], f)
    
    print(f"  ✓ Saved models to {model_dir}/")
    return models


def train_models(train_df: pd.DataFrame):
    """Train models on training data."""
    # Vectorize
    X_train_tfidf, _, vectorizer = vectorize(train_df["sms_text"], train_df["sms_text"])
    
    # Heuristic features
    sender_train = train_df["sender"] if "sender" in train_df.columns else None
    heur_train = build_heuristic_features(train_df["sms_text"], sender_train)
    X_train_full = hstack([X_train_tfidf, heur_train])
    
    # Labels
    y_train_phishing = train_df["is_phishing_original"].values
    y_train_isotp = train_df["predicted_is_otp"].values
    
    le_intent = LabelEncoder()
    y_train_intent = le_intent.fit_transform(train_df["predicted_otp_intent"])
    intent_labels = le_intent.classes_.tolist()
    
    # Train models
    models = {}
    
    # Phishing - LR
    print("  Training LR for phishing...")
    lr_phishing = LogisticRegression(
        class_weight="balanced",
        solver="lbfgs",
        max_iter=3000,
        random_state=RANDOM_SEED,
    )
    lr_phishing.fit(X_train_full, y_train_phishing)
    models["lr_phishing"] = lr_phishing
    
    # Phishing - LightGBM
    if HAS_LIGHTGBM:
        print("  Training LightGBM for phishing...")
        lgb_phishing = lgb.LGBMClassifier(
            objective="binary",
            class_weight="balanced",
            random_state=RANDOM_SEED,
            verbose=-1,
            n_estimators=100,
            learning_rate=0.1,
        )
        lgb_phishing.fit(X_train_full.toarray(), y_train_phishing)
        models["lgb_phishing"] = lgb_phishing
    
    # Is OTP - LR
    print("  Training LR for is_otp...")
    lr_isotp = LogisticRegression(
        class_weight="balanced",
        solver="lbfgs",
        max_iter=3000,
        random_state=RANDOM_SEED,
    )
    lr_isotp.fit(X_train_full, y_train_isotp)
    models["lr_isotp"] = lr_isotp
    
    # Is OTP - LightGBM
    if HAS_LIGHTGBM:
        print("  Training LightGBM for is_otp...")
        lgb_isotp = lgb.LGBMClassifier(
            objective="binary",
            class_weight="balanced",
            random_state=RANDOM_SEED,
            verbose=-1,
            n_estimators=100,
            learning_rate=0.1,
        )
        lgb_isotp.fit(X_train_full.toarray(), y_train_isotp)
        models["lgb_isotp"] = lgb_isotp
    
    # Intent - LR
    print("  Training LR for otp_intent...")
    class_weights = {}
    for i, label in enumerate(intent_labels):
        if label == "FINANCIAL_LOGIN_OTP":
            class_weights[i] = 3.0
        elif label == "APP_LOGIN_OTP":
            class_weights[i] = 1.5
        else:
            class_weights[i] = 1.0
    
    lr_intent = LogisticRegression(
        class_weight=class_weights,
        solver="saga",
        max_iter=3000,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    lr_intent.fit(X_train_full, y_train_intent)
    models["lr_intent"] = lr_intent
    models["le_intent"] = le_intent
    
    models["vectorizer"] = vectorizer
    
    return models


def evaluate_model(y_true, y_pred, labels=None, task_name=""):
    """Evaluate model."""
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)
    rec = recall_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)
    
    if labels and len(labels) > 2:
        prec_macro = precision_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)
        rec_macro = recall_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)
        f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)
        return {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "precision_macro": prec_macro,
            "recall_macro": rec_macro,
            "f1_macro": f1_macro,
            "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
            "labels": labels,
        }
    else:
        return {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        }


def main():
    ensure_output_dir()
    
    print("=" * 80)
    print("TESTING MODELS ON SYNTHETIC TEST SET")
    print("=" * 80)
    
    # Load training data
    print(f"\n1. Loading training data: {TRAIN_FILE}...")
    train_df = load_dataset(TRAIN_FILE)
    print(f"   Loaded {len(train_df)} training rows")
    
    # Load test data
    print(f"\n2. Loading test data: {TEST_FILE}...")
    if not Path(TEST_FILE).exists():
        raise FileNotFoundError(f"{TEST_FILE} not found. Run generate_verified_test_set.py first.")
    
    test_df = load_dataset(TEST_FILE)
    print(f"   Loaded {len(test_df)} test rows")
    
    # Load or train models
    print("\n3. Loading or training models...")
    models = load_or_train_models(train_df)
    
    # Prepare test features
    print("\n4. Preparing test features...")
    _, X_test_tfidf, _ = vectorize(None, test_df["sms_text"], models["vectorizer"])
    sender_test = test_df["sender"] if "sender" in test_df.columns else None
    heur_test = build_heuristic_features(test_df["sms_text"], sender_test)
    X_test_full = hstack([X_test_tfidf, heur_test])
    
    # True labels
    y_test_phishing = test_df["is_phishing_original"].values
    y_test_isotp = test_df["predicted_is_otp"].values
    le_intent = models["le_intent"]
    y_test_intent = le_intent.transform(test_df["predicted_otp_intent"])
    intent_labels = le_intent.classes_.tolist()
    
    results = {}
    
    # Test Phishing
    print("\n" + "=" * 80)
    print("TASK 1: is_phishing_original")
    print("=" * 80)
    
    lr_pred_phishing = models["lr_phishing"].predict(X_test_full)
    lr_metrics_phishing = evaluate_model(y_test_phishing, lr_pred_phishing)
    print("\nLogistic Regression:")
    print(json.dumps(lr_metrics_phishing, indent=2))
    results["phishing"] = {"lr": lr_metrics_phishing}
    
    if HAS_LIGHTGBM:
        lgb_pred_phishing = models["lgb_phishing"].predict(X_test_full.toarray())
        lgb_metrics_phishing = evaluate_model(y_test_phishing, lgb_pred_phishing)
        print("\nLightGBM:")
        print(json.dumps(lgb_metrics_phishing, indent=2))
        results["phishing"]["lightgbm"] = lgb_metrics_phishing
    
    # Test Is OTP
    print("\n" + "=" * 80)
    print("TASK 2: predicted_is_otp")
    print("=" * 80)
    
    lr_pred_isotp = models["lr_isotp"].predict(X_test_full)
    lr_metrics_isotp = evaluate_model(y_test_isotp, lr_pred_isotp)
    print("\nLogistic Regression:")
    print(json.dumps(lr_metrics_isotp, indent=2))
    results["is_otp"] = {"lr": lr_metrics_isotp}
    
    if HAS_LIGHTGBM:
        lgb_pred_isotp = models["lgb_isotp"].predict(X_test_full.toarray())
        lgb_metrics_isotp = evaluate_model(y_test_isotp, lgb_pred_isotp)
        print("\nLightGBM:")
        print(json.dumps(lgb_metrics_isotp, indent=2))
        results["is_otp"]["lightgbm"] = lgb_metrics_isotp
    
    # Test Intent
    print("\n" + "=" * 80)
    print("TASK 3: predicted_otp_intent")
    print("=" * 80)
    
    lr_pred_intent = models["lr_intent"].predict(X_test_full)
    lr_metrics_intent = evaluate_model(y_test_intent, lr_pred_intent, labels=list(range(len(intent_labels))))
    print("\nLogistic Regression:")
    print(json.dumps(lr_metrics_intent, indent=2))
    results["intent"] = {"lr": lr_metrics_intent}
    
    # Save results
    with open(OUTPUT_DIR / "synthetic_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Save predictions
    predictions_df = pd.DataFrame({
        "sms_text": test_df["sms_text"].values,
        "true_phishing": y_test_phishing,
        "lr_pred_phishing": lr_pred_phishing,
        "true_is_otp": y_test_isotp,
        "lr_pred_is_otp": lr_pred_isotp,
        "true_intent": le_intent.inverse_transform(y_test_intent),
        "lr_pred_intent": le_intent.inverse_transform(lr_pred_intent),
    })
    
    if HAS_LIGHTGBM:
        predictions_df["lgb_pred_phishing"] = lgb_pred_phishing
        predictions_df["lgb_pred_is_otp"] = lgb_pred_isotp
    
    predictions_df.to_csv(OUTPUT_DIR / "synthetic_test_predictions.csv", index=False)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nPhishing (F1):")
    print(f"  Logistic Regression: {lr_metrics_phishing['f1']:.4f}")
    if HAS_LIGHTGBM:
        print(f"  LightGBM:            {lgb_metrics_phishing['f1']:.4f}")
    
    print("\nIs OTP (F1):")
    print(f"  Logistic Regression: {lr_metrics_isotp['f1']:.4f}")
    if HAS_LIGHTGBM:
        print(f"  LightGBM:            {lgb_metrics_isotp['f1']:.4f}")
    
    print("\nOTP Intent (Macro F1):")
    print(f"  Logistic Regression: {lr_metrics_intent['f1_macro']:.4f}")
    
    print(f"\n✓ Results saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

