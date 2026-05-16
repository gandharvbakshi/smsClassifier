"""Check which original datasets have sender columns."""

import pandas as pd
from pathlib import Path

# Original (non-standardized) datasets to check
ORIGINAL_DATASETS = [
    "Gandharv personal all_conversations_03_11_2025_13h56h59.csv",
    "balanced_spam_dataset.csv",
    "Hindi.csv",
    "bangla_smish.csv",
    "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv",
]

# Also check standardized versions
STANDARDIZED_DATASETS = [
    "Gandharv personal all_conversations_03_11_2025_13h56h59_standardized.csv",
    "balanced_spam_dataset_standardized.csv",
    "Hindi_standardized.csv",
    "bangla_smish_standardized.csv",
    "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971_standardized.csv",
    "merged_standardized.csv",
]

print("=" * 80)
print("CHECKING ORIGINAL DATASETS FOR SENDER COLUMNS")
print("=" * 80)

def check_dataset(filepath: str, is_standardized: bool = False):
    """Check a dataset for sender column."""
    if not Path(filepath).exists():
        return None
    
    try:
        # Read first few rows to check structure
        df_sample = pd.read_csv(filepath, nrows=100, low_memory=False)
        
        # Check for sender-related columns
        sender_cols = [col for col in df_sample.columns if 'sender' in col.lower() or 'from' in col.lower() or 'phone' in col.lower() or 'address' in col.lower()]
        
        result = {
            "file": filepath,
            "exists": True,
            "columns": df_sample.columns.tolist(),
            "sender_columns": sender_cols,
            "total_rows": None,
            "sample_sender_values": None,
        }
        
        # Try to get total row count (might be slow for large files)
        try:
            df_full = pd.read_csv(filepath, low_memory=False)
            result["total_rows"] = len(df_full)
            
            # Sample sender values if sender column exists
            if sender_cols:
                sender_col = sender_cols[0]
                if sender_col in df_full.columns:
                    non_null = df_full[sender_col].dropna()
                    if len(non_null) > 0:
                        result["sample_sender_values"] = non_null.head(10).tolist()
                        result["unique_senders"] = df_full[sender_col].nunique()
                        result["null_count"] = df_full[sender_col].isna().sum()
        except Exception as e:
            result["error"] = str(e)
        
        return result
    except Exception as e:
        return {
            "file": filepath,
            "exists": True,
            "error": str(e)
        }

print("\n" + "-" * 80)
print("ORIGINAL (NON-STANDARDIZED) DATASETS")
print("-" * 80)

for dataset in ORIGINAL_DATASETS:
    result = check_dataset(dataset, is_standardized=False)
    if result:
        print(f"\n{dataset}:")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Columns: {result['columns']}")
            if result['sender_columns']:
                print(f"  ✓ Sender columns found: {result['sender_columns']}")
                if result.get('total_rows'):
                    print(f"  Total rows: {result['total_rows']:,}")
                    print(f"  Unique senders: {result.get('unique_senders', 'N/A')}")
                    print(f"  Null senders: {result.get('null_count', 'N/A'):,}")
                if result.get('sample_sender_values'):
                    print(f"  Sample sender values:")
                    for idx, val in enumerate(result['sample_sender_values'][:5], 1):
                        print(f"    {idx}. {str(val)[:80]}")
            else:
                print(f"  ✗ No sender columns found")
    else:
        print(f"\n{dataset}: File not found")

print("\n" + "-" * 80)
print("STANDARDIZED DATASETS")
print("-" * 80)

for dataset in STANDARDIZED_DATASETS:
    result = check_dataset(dataset, is_standardized=True)
    if result:
        print(f"\n{dataset}:")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Columns: {result['columns']}")
            if result['sender_columns']:
                print(f"  ✓ Sender columns found: {result['sender_columns']}")
                if result.get('total_rows'):
                    print(f"  Total rows: {result['total_rows']:,}")
                    print(f"  Unique senders: {result.get('unique_senders', 'N/A')}")
                    print(f"  Null senders: {result.get('null_count', 'N/A'):,}")
                if result.get('sample_sender_values'):
                    print(f"  Sample sender values:")
                    for idx, val in enumerate(result['sample_sender_values'][:5], 1):
                        print(f"    {idx}. {str(val)[:80]}")
            else:
                print(f"  ✗ No sender columns found")
    else:
        print(f"\n{dataset}: File not found")

