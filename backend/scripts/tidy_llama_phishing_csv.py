"""
Tidy the existing LLaMA verification CSV by adding clean comparison columns.

Input:  llama_recheck_phishing_sample.csv (already created by previous run)
Output: llama_recheck_phishing_sample_clean.csv with the following columns:
    - original_index
    - sms_text
    - is_phishing_original
    - is_phishing_llama_bool
    - is_phishing_llama_raw
    - raw_response

Usage:
    python tidy_llama_phishing_csv.py
"""

import pandas as pd

SOURCE_FILE = "llama_recheck_phishing_sample.csv"
OUTPUT_FILE = "llama_recheck_phishing_sample_clean.csv"


def to_bool(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    value_str = str(value).strip().lower()
    if value_str in {"true", "1", "yes"}:
        return True
    if value_str in {"false", "0", "no"}:
        return False
    return None


def main():
    df = pd.read_csv(SOURCE_FILE)

    is_phishing_original = df.get("is_phishing_bool", df.get("is_phishing"))
    if is_phishing_original is None:
        raise ValueError("Source CSV lacks 'is_phishing' or 'is_phishing_bool' columns.")

    llama_raw = df.get("is_phishing_llama", df.get("predicted_is_phishing"))
    if llama_raw is None:
        raise ValueError("Source CSV lacks 'is_phishing_llama' or 'predicted_is_phishing' columns.")

    cleaned = pd.DataFrame(
        {
            "original_index": df.get("original_index", df.index).astype(str),
            "sms_text": df.get("sms_text", df.get("body", "")),
            "is_phishing_original": is_phishing_original.apply(to_bool),
            "is_phishing_llama_bool": llama_raw.apply(to_bool),
            "is_phishing_llama_raw": llama_raw,
            "raw_response": df.get("raw_response", ""),
        }
    )

    cleaned.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Wrote tidy comparison to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


