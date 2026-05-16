"""
Join sender column from original Gandharv file back to the balanced dataset.

This script:
1. Loads the balanced dataset
2. Loads the original Gandharv file (which has Phone column with sender info)
3. Matches by SMS text content (normalized) - only when text matches exactly
4. Saves the enhanced dataset with sender column

Output: classification_results_with_phishing_llm_balanced_with_sender.csv
"""

import pandas as pd
from pathlib import Path
from collections import Counter

SOURCE_FILE = "classification_results_with_phishing_llm_balanced.csv"
GANDHARV_ORIGINAL_FILE = "Gandharv personal all_conversations_03_11_2025_13h56h59.csv"
OUTPUT_FILE = "classification_results_with_phishing_llm_balanced_with_sender.csv"


def normalize_text(text: str) -> str:
    """Normalize text for matching - removes extra whitespace, lowercases."""
    if pd.isna(text):
        return ""
    # Normalize: strip, collapse whitespace, lowercase
    normalized = " ".join(str(text).strip().split()).lower()
    return normalized


def load_gandharv_sender_data(filepath: str) -> pd.DataFrame:
    """Load Gandharv file and extract Phone (sender) and Content (SMS text)."""
    print(f"   Reading {filepath}...")
    
    # Read CSV, skipping first 3 lines (header info)
    df = pd.read_csv(filepath, skiprows=3, low_memory=False)
    
    # Expected columns: Date, Time, Direction, Contact, Phone, Content, Type
    required_cols = ["Phone", "Content"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {filepath}: {missing}")
    
    # Extract only Phone and Content columns
    df_clean = df[["Phone", "Content"]].copy()
    df_clean["Phone"] = df_clean["Phone"].astype(str)
    df_clean["Content"] = df_clean["Content"].astype(str)
    
    # Remove rows where Phone or Content is missing/invalid
    df_clean = df_clean[
        (df_clean["Phone"] != "nan") & 
        (df_clean["Phone"].str.strip() != "") &
        (df_clean["Content"] != "nan") &
        (df_clean["Content"].str.strip() != "")
    ].copy()
    
    # Normalize Content for matching
    df_clean["Content_normalized"] = df_clean["Content"].apply(normalize_text)
    
    print(f"   Loaded {len(df_clean)} valid rows with Phone and Content")
    return df_clean


def main():
    print("=" * 80)
    print("JOINING SENDER DATA FROM ORIGINAL GANDHARV FILE")
    print("=" * 80)
    
    # Load balanced dataset
    print(f"\n1. Loading {SOURCE_FILE}...")
    df_balanced = pd.read_csv(SOURCE_FILE)
    print(f"   Loaded {len(df_balanced)} rows")
    print(f"   Columns: {df_balanced.columns.tolist()}")
    
    # Load Gandharv original file
    print(f"\n2. Loading {GANDHARV_ORIGINAL_FILE}...")
    if not Path(GANDHARV_ORIGINAL_FILE).exists():
        raise FileNotFoundError(f"{GANDHARV_ORIGINAL_FILE} not found.")
    
    df_gandharv = load_gandharv_sender_data(GANDHARV_ORIGINAL_FILE)
    
    # Normalize SMS text in balanced dataset
    print("\n3. Normalizing SMS text for matching...")
    df_balanced["sms_text_normalized"] = df_balanced["sms_text"].apply(normalize_text)
    
    # Create lookup dictionary: normalized_content -> phone (sender)
    # If multiple rows have same content, keep the most common sender
    print("\n4. Building sender lookup dictionary from Gandharv file...")
    sender_lookup = {}
    content_to_senders = {}
    
    for _, row in df_gandharv.iterrows():
        normalized_content = row["Content_normalized"]
        phone = row["Phone"]
        
        if normalized_content and phone:
            if normalized_content not in content_to_senders:
                content_to_senders[normalized_content] = []
            content_to_senders[normalized_content].append(phone)
    
    # For each normalized content, use the most common sender
    for content, senders in content_to_senders.items():
        # Count sender frequencies
        sender_counts = Counter(senders)
        most_common_sender = sender_counts.most_common(1)[0][0]
        sender_lookup[content] = most_common_sender
    
    print(f"   Built lookup dictionary with {len(sender_lookup):,} unique SMS texts")
    
    # Match balanced dataset SMS texts to senders
    print("\n5. Matching SMS texts to senders...")
    df_balanced["sender"] = None
    
    matched_count = 0
    for idx, row in df_balanced.iterrows():
        normalized_sms = row["sms_text_normalized"]
        if normalized_sms in sender_lookup:
            df_balanced.loc[idx, "sender"] = sender_lookup[normalized_sms]
            matched_count += 1
    
    print(f"   Matched {matched_count:,} rows by SMS text ({100*matched_count/len(df_balanced):.1f}%)")
    
    # Clean up temporary columns
    df_balanced = df_balanced.drop(columns=["sms_text_normalized"], errors="ignore")
    
    # Final stats
    total_with_sender = df_balanced["sender"].notna().sum()
    print(f"\n6. Final results:")
    print(f"   Total rows: {len(df_balanced):,}")
    print(f"   Rows with sender: {total_with_sender:,} ({100 * total_with_sender / len(df_balanced):.1f}%)")
    print(f"   Rows without sender: {len(df_balanced) - total_with_sender:,}")
    
    # Save
    df_balanced.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✓ Saved enhanced dataset to {OUTPUT_FILE}")
    
    # Show sample of sender values
    print("\n7. Sample sender values:")
    valid_senders = df_balanced[df_balanced["sender"].notna()]["sender"]
    if len(valid_senders) > 0:
        sender_counts = valid_senders.value_counts().head(10)
        for sender, count in sender_counts.items():
            print(f"   {sender}: {count:,}")
    else:
        print("   No sender values found")


if __name__ == "__main__":
    main()

