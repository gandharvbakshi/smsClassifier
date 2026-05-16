import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "classification_results_full.csv"
OUTPUT_FILE = BASE_DIR / "classification_results_with_phishing.csv"

RAW_DATASETS = {
    "balanced_spam_dataset.csv": {
        "text_column": "text_combined",
        "label_column": "label",
        "positive_labels": {"spam"}
    },
    "bangla_smish.csv": {
        "text_column": "text",
        "label_column": "label",
        "positive_labels": {"smish", "smishing", "spam"}
    },
    "Hindi.csv": {
        "text_column": "message",
        "label_column": "label",
        "positive_labels": {"spam"}
    },
    "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv": {
        "text_column": "TEXT",
        "label_column": "LABEL",
        "positive_labels": {"smishing", "smish", "spam"}
    }
}

def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().lower()

def build_mapping():
    mapping = {}
    for file_name, cfg in RAW_DATASETS.items():
        path = BASE_DIR / file_name
        if not path.exists():
            print(f"Warning: {file_name} not found. Skipping.")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"Warning: Could not read {file_name} ({e}). Skipping.")
            continue
        if cfg["text_column"] not in df.columns or cfg["label_column"] not in df.columns:
            print(f"Warning: {file_name} missing columns. Skipping.")
            continue
        for text, label in zip(df[cfg["text_column"]], df[cfg["label_column"]]):
            norm = normalize_text(text)
            if not norm:
                continue
            label_norm = str(label).strip().lower()
            if label_norm in cfg["positive_labels"]:
                mapping[norm] = True
            elif norm not in mapping:
                mapping[norm] = False
    return mapping

def main():
    if not INPUT_FILE.exists():
        print(f"{INPUT_FILE.name} not found. Please run the classifier first.")
        return

    print("Reading existing classification results...")
    df = pd.read_csv(INPUT_FILE)
    if "sms_text" not in df.columns:
        print("sms_text column not found in input file; cannot match messages.")
        return

    print("Building phishing label mapping from raw datasets...")
    mapping = build_mapping()
    print(f"Mapping built for {len(mapping)} unique messages.")

    safe_words = [
        "bank", "otp", "do not share", "authorized", "transaction", "payment",
        "limit", "debit", "credit", "account", "rs", "inr", "dear customer"
    ]
    suspicious_words = [
        "click", "login", "log in", "verify", "update", "confirm", "activate", "register",
        "reply", "respond", "call", "whatsapp", "message", "contact", "link", "visit",
        "win", "winner", "prize", "lottery", "jackpot", "reward", "cashback", "bonus",
        "offer", "free", "claim"
    ]
    url_pattern = re.compile(r"(https?://|www\\.|\\b[a-zA-Z0-9.-]+\\.(com|in|net|org|info|biz|co)(/|\\b))", re.IGNORECASE)
    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
    phone_pattern = re.compile(r"(\\+?\\d{1,3}[- ]?)?(\\d{10}|\\d{3}[- ]\\d{3}[- ]\\d{4}|\\d{4}[- ]\\d{6})")

    def looks_definitely_not_phishing(text: str) -> bool:
        norm = normalize_text(text)
        if not norm:
            return False
        if url_pattern.search(norm):
            return False
        if email_pattern.search(norm):
            return False
        if phone_pattern.search(norm):
            return False
        if any(word in norm for word in suspicious_words):
            return False
        if "otp" in norm:
            if "do not share" not in norm and "don't share" not in norm:
                return False
        if len(norm) < 200 and any(word in norm for word in safe_words):
            return True
        return False

    print("Applying phishing labels...")
    df["normalized_sms"] = df["sms_text"].apply(normalize_text)
    df["is_phishing"] = df["normalized_sms"].map(mapping)
    mask_unlabeled = df["is_phishing"].isna()
    df.loc[mask_unlabeled & df["sms_text"].apply(looks_definitely_not_phishing), "is_phishing"] = False

    df = df.drop(columns=["normalized_sms"])

    print(f"Writing updated results to {OUTPUT_FILE.name}...")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print("Done.")

if __name__ == "__main__":
    main()

