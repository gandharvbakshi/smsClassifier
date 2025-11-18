"""
Combine the original OTP dataset with synthetic rows and optionally balance
underrepresented intent classes by oversampling them to a target count.

Inputs:
    - classification_results_with_phishing_llm_clean.csv
    - synthetic_otp_intents_generated.csv   (optional; skipped if missing)

Outputs:
    - classification_results_with_phishing_llm_balanced.csv
    - A quick summary printed to stdout (class counts before/after balancing)

Balancing strategy:
    - For each OTP intent, if the count is below TARGET_COUNTS, randomly
      oversample (with replacement) existing rows (real + synthetic) until
      the threshold is reached.
    - Leaves NOT_OTP untouched (no oversampling).
"""

import random
from pathlib import Path

import pandas as pd

BASE_FILE = "classification_results_with_phishing_llm_clean.csv"
SYNTHETIC_FILE = "synthetic_otp_intents_generated.csv"
OUTPUT_FILE = "classification_results_with_phishing_llm_balanced.csv"

# Minimum desired count per intent class
TARGET_COUNTS = {
    "APP_ACCOUNT_CHANGE_OTP": 300,
    "UPI_TXN_OR_PIN_OTP": 350,
    "KYC_OR_ESIGN_OTP": 350,
    "FINANCIAL_LOGIN_OTP": 350,
    "APP_LOGIN_OTP": 400,
    "GENERIC_APP_ACTION_OTP": 400,
    "DELIVERY_OR_SERVICE_OTP": 450,
    # NOT_OTP and BANK_OR_CARD_TXN_OTP are already abundant; no target needed.
}

RANDOM_SEED = 2025


def oversample(df: pd.DataFrame, intent: str, target: int) -> pd.DataFrame:
    subset = df[df["predicted_otp_intent"] == intent]
    if len(subset) == 0:
        return df  # Nothing to oversample from
    rows_needed = target - len(subset)
    if rows_needed <= 0:
        return df
    # Sample with replacement from the subset
    sampled = subset.sample(n=rows_needed, replace=True, random_state=RANDOM_SEED)
    return pd.concat([df, sampled], ignore_index=True)


def main():
    random.seed(RANDOM_SEED)
    base_df = pd.read_csv(BASE_FILE)
    if Path(SYNTHETIC_FILE).exists():
        synthetic_df = pd.read_csv(SYNTHETIC_FILE)
        combined_df = pd.concat([base_df, synthetic_df], ignore_index=True)
        print(f"Loaded {len(base_df)} base rows and {len(synthetic_df)} synthetic rows.")
    else:
        combined_df = base_df.copy()
        print(f"Loaded {len(base_df)} base rows. No synthetic file found.")

    # Drop ERROR intents if any remain
    combined_df = combined_df[combined_df["predicted_otp_intent"] != "ERROR"].reset_index(drop=True)

    print("\nCounts before balancing:")
    print(combined_df["predicted_otp_intent"].value_counts())

    balanced_df = combined_df.copy()
    for intent, target in TARGET_COUNTS.items():
        balanced_df = oversample(balanced_df, intent, target)

    print("\nCounts after balancing:")
    print(balanced_df["predicted_otp_intent"].value_counts())

    balanced_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nSaved balanced dataset to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


