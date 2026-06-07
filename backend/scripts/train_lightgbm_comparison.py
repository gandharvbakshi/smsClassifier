"""
Train and compare multiple models (Logistic Regression, LightGBM, optional XGBoost)
for OTP / phishing classification, combining TF‑IDF features with handcrafted
heuristics. Also evaluates the trained models on the synthetic hold-out set
`synthetic_test_set_200_verified.csv` (never used for training).

Usage:
    pip install -r requirements (needs lightgbm; xgboost is optional)
    python backend/scripts/train_lightgbm_comparison.py
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("WARNING: lightgbm not installed. Install with: pip install lightgbm")

try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("INFO: xgboost not installed. Install with: pip install xgboost (optional baseline).")

RANDOM_SEED = 2025
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DEFAULT_SOURCE = DATA_DIR / "classification_results_with_phishing_llm_balanced_with_sender.csv"
SYNTHETIC_EVAL_FILE = DATA_DIR / "synthetic_test_set_200_verified.csv"
OUTPUT_DIR = ROOT_DIR / "model_comparison_results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: str) -> pd.DataFrame:
    """Load dataset and normalize key columns."""
    df = pd.read_csv(path, low_memory=False)
    required_cols = [
        "original_index",
        "sms_text",
        "predicted_is_otp",
        "predicted_otp_intent",
        "classification_status",
        "batch_number",
        "is_phishing_original",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")

    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    df["predicted_is_otp"] = (
        df["predicted_is_otp"].astype(str).str.lower().map({"true": 1, "false": 0})
    )
    df["is_phishing_original"] = (
        df["is_phishing_original"].astype(str).str.lower().map({"true": 1, "false": 0})
    )
    df = df.dropna(subset=["predicted_is_otp", "is_phishing_original"])
    df["predicted_is_otp"] = df["predicted_is_otp"].astype(int)
    df["is_phishing_original"] = df["is_phishing_original"].astype(int)
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)
    df.loc[df["predicted_is_otp"] == 0, "predicted_otp_intent"] = "NOT_OTP"
    if "sender" not in df.columns:
        df["sender"] = ""
    else:
        df["sender"] = df["sender"].astype(str).fillna("")
    return df


def vectorize(train_text: pd.Series, test_text: pd.Series) -> Tuple[csr_matrix, csr_matrix, TfidfVectorizer]:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.95,
        strip_accents="unicode",
    )
    X_train = vectorizer.fit_transform(train_text)
    X_test = vectorizer.transform(test_text)
    return X_train, X_test, vectorizer


def build_heuristic_features(text_series: pd.Series, sender_series: pd.Series = None) -> csr_matrix:
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
            feature_row.extend(
                [
                    bool(re.search(r"\b(ICICI|HDFC|SBI|AXIS|KOTAK|ZERODHA|GROWW|UPSTOX|PAYTM|PHONEPE|GPAY)\b", sender)),
                    bool(re.search(r"\b(SWIGGY|ZOMATO|AMAZON|FLIPKART|DELHIVERY|BLUEDART)\b", sender)),
                    bool(re.search(r"\b(NETFLIX|SPOTIFY|INSTAGRAM|FACEBOOK|TWITTER)\b", sender)),
                    bool(re.search(r"^\d{10,12}$", sender)),
                ]
            )
        else:
            feature_row.extend([False, False, False, False])
        rows.append(feature_row)
    return csr_matrix(np.array(rows, dtype=np.float32))


def train_binary_lr(X_train, y_train) -> LogisticRegression:
    model = LogisticRegression(
        class_weight="balanced",
        solver="lbfgs",
        max_iter=3000,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)
    return model


def train_multiclass_lr(X_train, y_train, intent_labels: List[str]) -> Tuple[LogisticRegression, Dict[str, float]]:
    class_weights = {}
    for i, label in enumerate(intent_labels):
        if label == "FINANCIAL_LOGIN_OTP":
            class_weights[i] = 3.0
        elif label == "APP_LOGIN_OTP":
            class_weights[i] = 1.5
        else:
            class_weights[i] = 1.0

    model = LogisticRegression(
        class_weight=class_weights,
        solver="saga",
        max_iter=3000,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model, class_weights


def ensure_dense(X):
    """Dense float32 array — only use for models that cannot take CSR (XGBoost)."""
    if hasattr(X, "toarray"):
        return X.toarray().astype(np.float32, copy=False)
    return np.asarray(X, dtype=np.float32)


def _matrix_too_large_for_dense(n_rows: int, n_cols: int, max_elements: int = 25_000_000) -> bool:
    """Avoid allocating multi-GB dense matrices on merged 70k+ × 60k+ TF-IDF stacks."""
    return n_rows * n_cols > max_elements


def train_binary_lightgbm(X_train, y_train) -> "lgb.LGBMClassifier":
    if not HAS_LIGHTGBM:
        raise ImportError("lightgbm not installed")
    model = lgb.LGBMClassifier(
        objective="binary",
        class_weight="balanced",
        random_state=RANDOM_SEED,
        verbose=-1,
        n_estimators=200,
        learning_rate=0.08,
    )
    # scipy.sparse.csr_matrix hstack(TFIDF, heuristics) — LightGBM accepts CSR
    model.fit(X_train, y_train)
    return model


def train_multiclass_lightgbm(X_train, y_train, intent_labels: List[str]) -> "lgb.LGBMClassifier":
    if not HAS_LIGHTGBM:
        raise ImportError("lightgbm not installed")
    class_weights = {}
    for i, label in enumerate(intent_labels):
        if label == "FINANCIAL_LOGIN_OTP":
            class_weights[i] = 3.0
        elif label == "APP_LOGIN_OTP":
            class_weights[i] = 1.5
        else:
            class_weights[i] = 1.0
    model = lgb.LGBMClassifier(
        objective="multiclass",
        class_weight=class_weights,
        random_state=RANDOM_SEED,
        verbose=-1,
        n_estimators=200,
        learning_rate=0.08,
        num_class=len(intent_labels),
    )
    model.fit(X_train, y_train)
    return model


def compute_scale_pos_weight(y: np.ndarray) -> float:
    positives = max(np.sum(y == 1), 1)
    negatives = max(len(y) - positives, 1)
    return negatives / positives


def train_binary_xgboost(X_train_dense, y_train) -> "xgb.XGBClassifier":
    if not HAS_XGBOOST:
        raise ImportError("xgboost not installed")
    model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=350,
        learning_rate=0.07,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        reg_alpha=0.2,
        random_state=RANDOM_SEED,
        scale_pos_weight=compute_scale_pos_weight(y_train),
        n_jobs=-1,
    )
    model.fit(X_train_dense, y_train)
    return model


def train_multiclass_xgboost(X_train_dense, y_train, num_classes: int) -> "xgb.XGBClassifier":
    if not HAS_XGBOOST:
        raise ImportError("xgboost not installed")
    model = xgb.XGBClassifier(
        objective="multi:softmax",
        num_class=num_classes,
        eval_metric="mlogloss",
        n_estimators=400,
        learning_rate=0.07,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train_dense, y_train)
    return model


def evaluate_model(y_true, y_pred, labels=None) -> Dict:
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)
    rec = recall_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)
    base = {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
    }
    if labels is not None and len(labels) > 2:
        base.update(
            {
                "precision_macro": precision_score(
                    y_true, y_pred, average="macro", zero_division=0, labels=labels
                ),
                "recall_macro": recall_score(
                    y_true, y_pred, average="macro", zero_division=0, labels=labels
                ),
                "f1_macro": f1_score(
                    y_true, y_pred, average="macro", zero_division=0, labels=labels
                ),
                "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
                "labels": labels,
            }
        )
    else:
        base["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    return base


@dataclass
class ModelBundle:
    model: object
    requires_dense: bool


def add_model(store: Dict[str, ModelBundle], key: str, model_obj, needs_dense: bool):
    store[key] = ModelBundle(model=model_obj, requires_dense=needs_dense)


def predict_and_evaluate(
    models: Dict[str, ModelBundle],
    X_sparse,
    X_dense,
    y_true,
    labels=None,
    return_preds: bool = False,
):
    metrics = {}
    preds = {} if return_preds else None
    for name, bundle in models.items():
        if bundle.requires_dense:
            if X_dense is None:
                continue
            X_mat = X_dense
        else:
            X_mat = X_sparse
        y_pred = np.asarray(bundle.model.predict(X_mat)).ravel()
        if y_pred.dtype.kind == "f":
            y_pred = np.rint(y_pred)
        y_pred = y_pred.astype(int)
        metrics[name] = evaluate_model(y_true, y_pred, labels=labels)
        if preds is not None:
            preds[name] = y_pred
    return (metrics, preds) if return_preds else metrics


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def main():
    import argparse

    ap = argparse.ArgumentParser(description="Train/eval LR + LightGBM (+optional XGB) on SMS corpus.")
    ap.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Training CSV path (classification_results*_with_sender schema).",
    )
    args = ap.parse_args()
    SOURCE_FILE = args.source

    if not HAS_LIGHTGBM:
        print("ERROR: lightgbm not installed. Install with: pip install lightgbm")
        return

    ensure_output_dir()
    print(f"Loading training dataset: {SOURCE_FILE} ...")
    df = load_dataset(SOURCE_FILE)

    stratify_key = df["predicted_otp_intent"] + "_" + df["is_phishing_original"].astype(str)
    counts = stratify_key.value_counts()
    rare = counts[counts < 2].index
    if len(rare) > 0:
        stratify_key = stratify_key.where(~stratify_key.isin(rare), other="fallback_" + df["predicted_otp_intent"])
        counts = stratify_key.value_counts()
        if (counts < 2).any():
            stratify_key = stratify_key.where(counts[stratify_key].ge(2), other="global_fallback")

    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=stratify_key,
    )
    print(f"Train: {len(train_df)}, Test: {len(test_df)}")

    X_train_tfidf, X_test_tfidf, vectorizer = vectorize(train_df["sms_text"], test_df["sms_text"])
    heur_train = build_heuristic_features(train_df["sms_text"], train_df["sender"])
    heur_test = build_heuristic_features(test_df["sms_text"], test_df["sender"])

    X_train_full = hstack([X_train_tfidf, heur_train])
    X_test_full = hstack([X_test_tfidf, heur_test])
    n_rows, n_cols = X_train_full.shape
    skip_xgb_dense = _matrix_too_large_for_dense(n_rows, n_cols)
    if skip_xgb_dense and HAS_XGBOOST:
        print(
            f"[train] Skipping XGBoost (design matrix {n_rows}×{n_cols} too large for dense RAM). "
            "LightGBM + LR run on sparse CSR."
        )
    X_train_dense = None if skip_xgb_dense else ensure_dense(X_train_full)
    X_test_dense = None if skip_xgb_dense else ensure_dense(X_test_full)

    y_train_phishing = train_df["is_phishing_original"].values
    y_test_phishing = test_df["is_phishing_original"].values

    y_train_isotp = train_df["predicted_is_otp"].values
    y_test_isotp = test_df["predicted_is_otp"].values

    le_intent = LabelEncoder()
    y_train_intent = le_intent.fit_transform(train_df["predicted_otp_intent"])
    y_test_intent = le_intent.transform(test_df["predicted_otp_intent"])
    intent_labels = list(range(len(le_intent.classes_)))

    results: Dict[str, Dict[str, Dict]] = {}

    # --- Phishing models ----------------------------------------------------
    print("\n" + "=" * 80)
    print("TASK 1: is_phishing_original")
    print("=" * 80)
    models_phishing: Dict[str, ModelBundle] = {}
    add_model(models_phishing, "logistic_regression", train_binary_lr(X_train_full, y_train_phishing), False)
    add_model(models_phishing, "lightgbm", train_binary_lightgbm(X_train_full, y_train_phishing), False)
    if HAS_XGBOOST and not skip_xgb_dense:
        add_model(models_phishing, "xgboost", train_binary_xgboost(X_train_dense, y_train_phishing), True)

    phishing_metrics, phishing_preds = predict_and_evaluate(
        models_phishing, X_test_full, X_test_dense, y_test_phishing, return_preds=True
    )
    print(json.dumps(phishing_metrics, indent=2))
    results["phishing"] = phishing_metrics

    # --- is_otp models ------------------------------------------------------
    print("\n" + "=" * 80)
    print("TASK 2: predicted_is_otp")
    print("=" * 80)
    models_isotp: Dict[str, ModelBundle] = {}
    add_model(models_isotp, "logistic_regression", train_binary_lr(X_train_full, y_train_isotp), False)
    add_model(models_isotp, "lightgbm", train_binary_lightgbm(X_train_full, y_train_isotp), False)
    if HAS_XGBOOST and not skip_xgb_dense:
        add_model(models_isotp, "xgboost", train_binary_xgboost(X_train_dense, y_train_isotp), True)

    isotp_metrics, isotp_preds = predict_and_evaluate(
        models_isotp, X_test_full, X_test_dense, y_test_isotp, return_preds=True
    )
    print(json.dumps(isotp_metrics, indent=2))
    results["is_otp"] = isotp_metrics

    # --- Intent models ------------------------------------------------------
    print("\n" + "=" * 80)
    print("TASK 3: predicted_otp_intent")
    print("=" * 80)
    models_intent: Dict[str, ModelBundle] = {}
    lr_intent_model, _ = train_multiclass_lr(X_train_full, y_train_intent, le_intent.classes_.tolist())
    add_model(models_intent, "logistic_regression", lr_intent_model, False)
    add_model(
        models_intent,
        "lightgbm",
        train_multiclass_lightgbm(X_train_full, y_train_intent, le_intent.classes_),
        False,
    )
    if HAS_XGBOOST and not skip_xgb_dense:
        add_model(
            models_intent,
            "xgboost",
            train_multiclass_xgboost(X_train_dense, y_train_intent, len(le_intent.classes_)),
            True,
        )

    intent_metrics, intent_preds = predict_and_evaluate(
        models_intent,
        X_test_full,
        X_test_dense,
        y_test_intent,
        labels=intent_labels,
        return_preds=True,
    )
    print(json.dumps(intent_metrics, indent=2))
    results["intent"] = intent_metrics

    # --- External synthetic evaluation -------------------------------------
    print("\nLoading synthetic evaluation set (never trained on)...")
    synthetic_df = load_dataset(SYNTHETIC_EVAL_FILE)
    X_eval_tfidf = vectorizer.transform(synthetic_df["sms_text"])
    heur_eval = build_heuristic_features(synthetic_df["sms_text"], synthetic_df["sender"])
    X_eval_full = hstack([X_eval_tfidf, heur_eval])
    X_eval_dense = None if skip_xgb_dense else ensure_dense(X_eval_full)

    y_eval_phishing = synthetic_df["is_phishing_original"].values
    y_eval_isotp = synthetic_df["predicted_is_otp"].values
    y_eval_intent = le_intent.transform(synthetic_df["predicted_otp_intent"])

    synthetic_metrics = {
        "phishing": predict_and_evaluate(models_phishing, X_eval_full, X_eval_dense, y_eval_phishing),
        "is_otp": predict_and_evaluate(models_isotp, X_eval_full, X_eval_dense, y_eval_isotp),
        "intent": predict_and_evaluate(
            models_intent, X_eval_full, X_eval_dense, y_eval_intent, labels=intent_labels
        ),
    }

    # --- Persist metrics/predictions ---------------------------------------
    with open(OUTPUT_DIR / "comparison_metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    with open(OUTPUT_DIR / "synthetic_eval_metrics.json", "w") as f:
        json.dump(synthetic_metrics, f, indent=2)

    predictions_payload = {
        "original_index": test_df["original_index"].values,
        "sms_text": test_df["sms_text"].values,
        "true_phishing": y_test_phishing,
        "true_is_otp": y_test_isotp,
        "true_intent": le_intent.inverse_transform(y_test_intent),
    }
    for name, preds in phishing_preds.items():
        predictions_payload[f"{name}_pred_phishing"] = preds
    for name, preds in isotp_preds.items():
        predictions_payload[f"{name}_pred_is_otp"] = preds
    for name, preds in intent_preds.items():
        predictions_payload[f"{name}_pred_intent"] = le_intent.inverse_transform(preds)
    pd.DataFrame(predictions_payload).to_csv(OUTPUT_DIR / "comparison_predictions.csv", index=False)

    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY (Internal Test F1)")
    print("=" * 80)
    for task, task_metrics in results.items():
        metric_key = "f1_macro" if task == "intent" else "f1"
        print(f"\n{task.upper()}:")
        for model_name, metrics in task_metrics.items():
            if metric_key in metrics:
                print(f"  {model_name:20s} {metrics[metric_key]:.4f}")

    print("\nSynthetic hold-out metrics:")
    print(json.dumps(synthetic_metrics, indent=2))
    print(f"\n✓ Results saved to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()

