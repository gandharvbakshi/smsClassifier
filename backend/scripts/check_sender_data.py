"""Quick script to check sender data in the training dataset."""

import pandas as pd

FILE = "classification_results_with_phishing_llm_balanced_with_sender.csv"

print("=" * 80)
print("CHECKING SENDER DATA")
print("=" * 80)

df = pd.read_csv(FILE)
print(f"\nTotal rows: {len(df):,}")
print(f"Columns: {df.columns.tolist()}")

if 'sender' not in df.columns:
    print("\nERROR: 'sender' column not found!")
else:
    # Count non-null and non-empty senders
    df['sender'] = df['sender'].astype(str)
    non_empty = (df['sender'] != 'nan') & (df['sender'].str.strip() != '')
    empty = ~non_empty
    
    print(f"\nRows with sender: {non_empty.sum():,} ({100*non_empty.sum()/len(df):.2f}%)")
    print(f"Rows without sender: {empty.sum():,} ({100*empty.sum()/len(df):.2f}%)")
    
    # Show sample sender values
    if non_empty.sum() > 0:
        print("\nSample sender values (first 20):")
        valid_senders = df[non_empty]['sender'].head(20)
        for idx, sender in enumerate(valid_senders, 1):
            print(f"  {idx}. {sender}")
        
        # Top sender values
        print("\nTop 20 sender values (by frequency):")
        sender_counts = df[non_empty]['sender'].value_counts().head(20)
        for sender, count in sender_counts.items():
            print(f"  {sender}: {count:,}")
    else:
        print("\n⚠ No sender values found - all rows have empty sender column")
    
    # Check by intent
    print("\n" + "=" * 80)
    print("SENDER COVERAGE BY INTENT")
    print("=" * 80)
    if 'predicted_otp_intent' in df.columns:
        for intent in sorted(df['predicted_otp_intent'].unique()):
            intent_df = df[df['predicted_otp_intent'] == intent]
            sender_mask = (intent_df['sender'] != 'nan') & (intent_df['sender'].str.strip() != '')
            with_sender = sender_mask.sum()
            total = len(intent_df)
            pct = 100 * with_sender / total if total > 0 else 0
            print(f"  {intent:30s}: {with_sender:6,}/{total:6,} ({pct:5.1f}%)")
