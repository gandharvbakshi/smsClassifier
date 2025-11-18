"""
Baseline TF-IDF + Logistic Regression models for OTP/phishing classification.

This script trains three independent models on
`classification_results_with_phishing_llm_clean.csv`:
    1. is_phishing_original (binary)
    2. predicted_is_otp (binary)
    3. predicted_otp_intent (multi-class)

Outputs:
    - Prints metrics to stdout.
    - Saves classification reports and metrics to `baseline_results/`.
Heuristic binary features (URLs, OTP keywords, etc.) are appended to the TF-IDF
vectors to capture rule-based hints. Training uses CPU-bound scikit-learn; GPU
hardware is not required (or leveraged)."""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import re

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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

RANDOM_SEED = 2025
SOURCE_FILE = "classification_results_with_phishing_llm_balanced.csv"
OUTPUT_DIR = Path("baseline_results")


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected_cols = [
        "original_index",
        "sms_text",
        "predicted_is_otp",
        "predicted_otp_intent",
        "classification_status",
        "batch_number",
        "is_phishing_original",
    ]
    missing = [col for col in expected_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    df["sms_text"] = df["sms_text"].astype(str).fillna("")
    df["predicted_is_otp"] = df["predicted_is_otp"].astype(str).str.lower().map({"true": 1, "false": 0})
    df["is_phishing_original"] = df["is_phishing_original"].astype(str).str.lower().map({"true": 1, "false": 0})
    df = df.dropna(subset=["predicted_is_otp", "is_phishing_original"])
    df["predicted_is_otp"] = df["predicted_is_otp"].astype(int)
    df["is_phishing_original"] = df["is_phishing_original"].astype(int)
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)
    df.loc[df["predicted_is_otp"] == 0, "predicted_otp_intent"] = "NOT_OTP"
    return df


def vectorize(train_text: pd.Series, test_text: pd.Series) -> Tuple[np.ndarray, np.ndarray, TfidfVectorizer]:
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


def build_heuristic_features(text_series: pd.Series) -> csr_matrix:
    patterns = {
        "has_digits": r"\d",
        "has_otp_word": r"\botp\b",
        "has_do_not_share": r"do not share|never share",
        "has_url": r"https?://|www\.",
        "has_request": r"\blogin\b|\bverify\b|\bupdate\b|\bclick\b|\bcall\b|\bshare\b",
        "mentions_bank_safe": r"bank never asks|otp is secret|do not disclose",
        "icici_sms_block": r"sms block 7007",
        "has_reward": r"reward|win|cashback|lottery|prize|gift",
    }
    rows = []
    for text in text_series:
        rows.append(
            [
                bool(re.search(pattern, text, flags=re.IGNORECASE))
                for pattern in patterns.values()
            ]
        )
    return csr_matrix(np.array(rows, dtype=np.float32))


def train_binary_model(X_train, y_train) -> LogisticRegression:
    model = LogisticRegression(
        class_weight="balanced",
        solver="lbfgs",
        max_iter=2000,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)
    return model


def train_multiclass_model(X_train, y_train) -> LogisticRegression:
    model = LogisticRegression(
        class_weight="balanced",
        solver="saga",
        max_iter=2000,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


def evaluate_binary(y_true, y_pred) -> Dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def evaluate_multiclass(y_true, y_pred, labels: List[str]) -> Dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
    }


def main() -> None:
    ensure_output_dir()
    df = load_dataset(SOURCE_FILE)

    stratify_key = df["predicted_otp_intent"] + "_" + df["is_phishing_original"].astype(str)
    key_counts = stratify_key.value_counts()
    rare_keys = key_counts[key_counts < 2].index
    if len(rare_keys) > 0:
        stratify_key = stratify_key.where(~stratify_key.isin(rare_keys), other="fallback_" + df["predicted_otp_intent"])
    fallback_counts = stratify_key.value_counts()
    if (fallback_counts < 2).any():
        stratify_key = stratify_key.where(fallback_counts[stratify_key].ge(2), other="global_fallback")
    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=stratify_key,
    )

    X_train, X_test, vectorizer = vectorize(train_df["sms_text"], test_df["sms_text"])
    heur_train = build_heuristic_features(train_df["sms_text"])
    heur_test = build_heuristic_features(test_df["sms_text"])
    X_train_full = hstack([X_train, heur_train])
    X_test_full = hstack([X_test, heur_test])

    y_train_phishing = train_df["is_phishing_original"].values
    y_test_phishing = test_df["is_phishing_original"].values

    y_train_isotp = train_df["predicted_is_otp"].values
    y_test_isotp = test_df["predicted_is_otp"].values

    intent_encoder = LabelEncoder()
    y_train_intent = intent_encoder.fit_transform(train_df["predicted_otp_intent"])
    y_test_intent = intent_encoder.transform(test_df["predicted_otp_intent"])
    intent_labels = intent_encoder.classes_.tolist()

    print("Training baseline models...")
    model_phishing = train_binary_model(X_train_full, y_train_phishing)
    model_isotp = train_binary_model(X_train_full, y_train_isotp)
    model_intent = train_multiclass_model(X_train_full, y_train_intent)

    print("Evaluating on test split...\n")
    phishing_pred = model_phishing.predict(X_test_full)
    isotp_pred = model_isotp.predict(X_test_full)
    intent_pred = model_intent.predict(X_test_full)

    phishing_metrics = evaluate_binary(y_test_phishing, phishing_pred)
    isotp_metrics = evaluate_binary(y_test_isotp, isotp_pred)
    intent_metrics = evaluate_multiclass(y_test_intent, intent_pred, labels=list(range(len(intent_labels))))

    print("is_phishing_original metrics:")
    print(json.dumps(phishing_metrics, indent=2))
    print("\nclassification_report:\n", classification_report(y_test_phishing, phishing_pred, zero_division=0))

    print("\npredicted_is_otp metrics:")
    print(json.dumps(isotp_metrics, indent=2))
    print("\nclassification_report:\n", classification_report(y_test_isotp, isotp_pred, zero_division=0))

    print("\npredicted_otp_intent metrics:")
    print(json.dumps(intent_metrics, indent=2))
    print(
        "\nclassification_report:\n",
        classification_report(
            y_test_intent,
            intent_pred,
            labels=list(range(len(intent_labels))),
            target_names=intent_labels,
            zero_division=0,
        ),
    )

    # Save metrics
    summary = {
        "is_phishing_original": phishing_metrics,
        "predicted_is_otp": isotp_metrics,
        "predicted_otp_intent": {
            **intent_metrics,
            "label_names": intent_labels,
        },
    }
    (OUTPUT_DIR / "metrics_summary.json").write_text(json.dumps(summary, indent=2))

    reports = [
        "=== is_phishing_original ===\n",
        classification_report(y_test_phishing, phishing_pred, zero_division=0),
        "\n=== predicted_is_otp ===\n",
        classification_report(y_test_isotp, isotp_pred, zero_division=0),
        "\n=== predicted_otp_intent ===\n",
        classification_report(
            y_test_intent,
            intent_pred,
            target_names=intent_labels,
            zero_division=0,
        ),
    ]
    (OUTPUT_DIR / "classification_reports.txt").write_text("\n".join(reports))

    # Save per-row predictions for further analysis
    results_df = test_df[
        ["original_index", "sms_text", "is_phishing_original", "predicted_is_otp", "predicted_otp_intent"]
    ].copy()
    results_df["is_phishing_pred"] = phishing_pred
    results_df["is_otp_pred"] = isotp_pred
    results_df["otp_intent_pred"] = intent_encoder.inverse_transform(intent_pred)
    results_df.to_csv(OUTPUT_DIR / "test_predictions.csv", index=False, encoding="utf-8-sig")

    print(f"\nSaved metrics and predictions under {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()



