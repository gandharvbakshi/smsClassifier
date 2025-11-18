"""
Build a clean copy of the original LLM-labeled dataset, retaining only the
columns generated during the initial run (no verification metadata).

Input:  classification_results_with_phishing_llm.csv
Output: classification_results_with_phishing_llm_clean.csv
Columns kept:
    - original_index
    - sms_text
    - predicted_is_otp
    - predicted_otp_intent
    - classification_status
    - batch_number
    - is_phishing (renamed to is_phishing_original)

Usage:
    python extract_phishing_original.py
"""

import pandas as pd

SOURCE_FILE = "classification_results_with_phishing_llm.csv"
OUTPUT_FILE = "classification_results_with_phishing_llm_clean.csv"


def main() -> None:
    df = pd.read_csv(SOURCE_FILE)
    required_cols = [
        "original_index",
        "sms_text",
        "predicted_is_otp",
        "predicted_otp_intent",
        "classification_status",
        "batch_number",
        "is_phishing",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Source file missing expected columns: {missing}")

    cleaned = df[required_cols].rename(columns={"is_phishing": "is_phishing_original"})
    cleaned.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(cleaned)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


