import os
import random
import re
from typing import Dict, Tuple

import pandas as pd

from benchmark_llm_accuracy import (
    OTP_SOURCE_FILE,
    PHISHING_MAPPING_FILES,
    normalize_text,
)

BASE_DIR = os.path.dirname(__file__)

PHISHING_SAMPLE_SIZE = 100
OTP_INTENT_SAMPLE_SIZE = 100

PHISHING_SAMPLE_OUTPUT = os.path.join(
    BASE_DIR, "eval_sample_is_phishing_100.csv"
)
OTP_INTENT_SAMPLE_OUTPUT = os.path.join(
    BASE_DIR, "eval_sample_otp_intent_100.csv"
)


def load_phishing_truth() -> Dict[str, bool]:
    """Rebuild a normalized phishing truth map using relaxed normalization.

    The legacy datasets do not always preserve punctuation/whitespace exactly.
    To maximise overlap with our standardized CSV, we normalise the mapping
    keys with the same regex that is subsequently applied to the SMS text.
    """

    def relaxed_normalise(text: str) -> str:
        base = normalize_text(text)
        return re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()

    truth_map: Dict[str, bool] = {}
    for file_name, (text_col, label_col, positive_labels) in PHISHING_MAPPING_FILES.items():
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if text_col not in df.columns or label_col not in df.columns:
            continue

        for text, label in zip(df[text_col], df[label_col]):
            norm = relaxed_normalise(text)
            if not norm:
                continue
            is_positive = str(label).strip().lower() in positive_labels
            if is_positive:
                truth_map[norm] = True
            else:
                truth_map.setdefault(norm, False)

    return truth_map


def prepare_samples() -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(OTP_SOURCE_FILE):
        raise FileNotFoundError(f"{OTP_SOURCE_FILE} not found.")

    df = pd.read_csv(OTP_SOURCE_FILE)
    required_cols = {"id", "sender", "body", "is_otp", "otp_intent"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in source CSV: {missing}")

    # ---------------------------------------------------------
    # Phishing sample (100 rows with high-confidence truth)
    # ---------------------------------------------------------
    phishing_truth = load_phishing_truth()
    if not phishing_truth:
        raise ValueError("No phishing ground-truth entries found.")

    def relaxed_normalise(text: str) -> str:
        base = normalize_text(text)
        return re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()

    df["sms_text"] = df["sender"].fillna(df["body"]).fillna("")
    df["sms_text_relaxed"] = df["sms_text"].apply(relaxed_normalise)
    phishing_mask = df["sms_text_relaxed"].isin(phishing_truth.keys())
    phishing_pool = df.loc[phishing_mask].copy()
    phishing_pool["is_phishing_truth"] = phishing_pool["sms_text_relaxed"].map(phishing_truth)
    phishing_pool = phishing_pool.dropna(subset=["is_phishing_truth"])

    if len(phishing_pool) < PHISHING_SAMPLE_SIZE:
        raise ValueError(
            f"Only {len(phishing_pool)} phishing-labelled rows available; need {PHISHING_SAMPLE_SIZE}."
        )

    phishing_sample = phishing_pool.sample(
        n=PHISHING_SAMPLE_SIZE, random_state=1234
    ).reset_index(drop=True)

    phishing_sample = phishing_sample[
        ["id", "sender", "body", "is_phishing_truth", "sms_text_relaxed"]
    ]
    phishing_sample = phishing_sample.rename(
        columns={
            "sms_text_relaxed": "normalized_sms_text",
        }
    )

    # ---------------------------------------------------------
    # OTP intent sample (100 rows with manual labels)
    # ---------------------------------------------------------
    otp_pool = df[
        df["otp_intent"].notna() & df["is_otp"].notna()
    ].copy()

    # Ensure disjoint samples by excluding any IDs already used
    used_ids = set(phishing_sample["id"])
    otp_pool = otp_pool[~otp_pool["id"].isin(used_ids)]

    if len(otp_pool) < OTP_INTENT_SAMPLE_SIZE:
        raise ValueError(
            f"Only {len(otp_pool)} OTP-labelled rows available after exclusions; need {OTP_INTENT_SAMPLE_SIZE}."
        )

    otp_sample = otp_pool.sample(
        n=OTP_INTENT_SAMPLE_SIZE, random_state=5678
    ).reset_index(drop=True)

    otp_sample = otp_sample[
        ["id", "sender", "body", "is_otp", "otp_intent"]
    ]

    return phishing_sample, otp_sample


def main() -> None:
    phishing_sample, otp_sample = prepare_samples()

    phishing_sample.to_csv(
        PHISHING_SAMPLE_OUTPUT, index=False, encoding="utf-8-sig"
    )
    otp_sample.to_csv(
        OTP_INTENT_SAMPLE_OUTPUT, index=False, encoding="utf-8-sig"
    )

    print(
        f"Saved {len(phishing_sample)} phishing ground-truth rows to "
        f"{os.path.basename(PHISHING_SAMPLE_OUTPUT)}"
    )
    print(
        f"Saved {len(otp_sample)} OTP intent ground-truth rows to "
        f"{os.path.basename(OTP_INTENT_SAMPLE_OUTPUT)}"
    )


if __name__ == "__main__":
    main()


