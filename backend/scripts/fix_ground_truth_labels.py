"""
Review and fix ground truth labels.
Identifies messages marked as OTP (is_otp=True) but with intent='NOT_OTP'
These should be corrected to is_otp=False.
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, List

def identify_label_issues(dataset_path: str) -> pd.DataFrame:
    """Identify messages with conflicting labels."""
    
    print(f"Loading dataset: {dataset_path}")
    df = pd.read_csv(dataset_path)
    
    print(f"Total rows: {len(df)}")
    
    # Find text and label columns
    text_col = None
    sender_col = None
    is_otp_col = None
    intent_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if "body" in col_lower or "text" in col_lower or "sms" in col_lower or "message" in col_lower:
            text_col = col
        if "sender" in col_lower or "from" in col_lower or "address" in col_lower:
            sender_col = col
        if "is_otp" in col_lower or "predicted_is_otp" in col_lower or "isotp" in col_lower:
            is_otp_col = col
        if "intent" in col_lower or "otp_intent" in col_lower:
            intent_col = col
    
    if not text_col:
        raise ValueError("Could not find SMS text column")
    
    print(f"\nUsing columns:")
    print(f"  Text: {text_col}")
    print(f"  Sender: {sender_col}")
    print(f"  Is OTP: {is_otp_col}")
    print(f"  Intent: {intent_col}")
    
    # Find conflicting labels
    if is_otp_col and intent_col:
        # Messages marked as OTP but intent is NOT_OTP
        conflicting = df[
            (df[is_otp_col].notna()) &
            (df[intent_col].notna()) &
            (df[is_otp_col].astype(str).str.lower().isin(['true', 'yes', '1', '1.0'])) &
            (df[intent_col].astype(str).str.upper() == 'NOT_OTP')
        ].copy()
        
        print(f"\n{'='*80}")
        print(f"CONFLICTING LABELS FOUND: {len(conflicting)}")
        print(f"{'='*80}")
        print(f"\nThese messages are marked as is_otp=True but intent='NOT_OTP'")
        print("They should be corrected to is_otp=False")
        
        return conflicting, text_col, sender_col, is_otp_col, intent_col
    else:
        print("\nWarning: Could not find is_otp or intent columns")
        return pd.DataFrame(), text_col, sender_col, is_otp_col, intent_col

def analyze_conflicting_labels(conflicting_df: pd.DataFrame, text_col: str, sender_col: str):
    """Analyze patterns in conflicting labels."""
    
    if len(conflicting_df) == 0:
        return
    
    print(f"\n{'='*80}")
    print("ANALYZING CONFLICTING LABELS")
    print(f"{'='*80}")
    
    # Transaction notification keywords
    transaction_keywords = [
        "spent", "transaction", "payment", "debited", "credited", 
        "balance", "limit", "due", "bill", "recharge", "toll"
    ]
    
    # Payment confirmation keywords
    payment_keywords = [
        "successfully processed", "payment of", "to be debited",
        "received", "transferred", "paid"
    ]
    
    # Analyze patterns
    patterns = {
        'transaction_notifications': 0,
        'payment_confirmations': 0,
        'balance_updates': 0,
        'delivery_notifications': 0,
        'bill_reminders': 0,
        'other': 0
    }
    
    samples_by_pattern = {
        'transaction_notifications': [],
        'payment_confirmations': [],
        'balance_updates': [],
        'delivery_notifications': [],
        'bill_reminders': [],
        'other': []
    }
    
    for idx, row in conflicting_df.iterrows():
        text = str(row[text_col]).lower() if pd.notna(row[text_col]) else ""
        
        # Categorize
        if any(kw in text for kw in ["spent", "using", "card", "on"]):
            patterns['transaction_notifications'] += 1
            if len(samples_by_pattern['transaction_notifications']) < 5:
                samples_by_pattern['transaction_notifications'].append({
                    'index': idx,
                    'text': row[text_col][:150] if pd.notna(row[text_col]) else ''
                })
        elif any(kw in text for kw in ["successfully processed", "payment of", "to be debited"]):
            patterns['payment_confirmations'] += 1
            if len(samples_by_pattern['payment_confirmations']) < 5:
                samples_by_pattern['payment_confirmations'].append({
                    'index': idx,
                    'text': row[text_col][:150] if pd.notna(row[text_col]) else ''
                })
        elif any(kw in text for kw in ["avl limit", "available balance", "balance"]):
            patterns['balance_updates'] += 1
            if len(samples_by_pattern['balance_updates']) < 5:
                samples_by_pattern['balance_updates'].append({
                    'index': idx,
                    'text': row[text_col][:150] if pd.notna(row[text_col]) else ''
                })
        elif any(kw in text for kw in ["delivery", "order", "shipment"]):
            patterns['delivery_notifications'] += 1
            if len(samples_by_pattern['delivery_notifications']) < 5:
                samples_by_pattern['delivery_notifications'].append({
                    'index': idx,
                    'text': row[text_col][:150] if pd.notna(row[text_col]) else ''
                })
        elif any(kw in text for kw in ["bill", "due", "payment due"]):
            patterns['bill_reminders'] += 1
            if len(samples_by_pattern['bill_reminders']) < 5:
                samples_by_pattern['bill_reminders'].append({
                    'index': idx,
                    'text': row[text_col][:150] if pd.notna(row[text_col]) else ''
                })
        else:
            patterns['other'] += 1
            if len(samples_by_pattern['other']) < 3:
                samples_by_pattern['other'].append({
                    'index': idx,
                    'text': row[text_col][:150] if pd.notna(row[text_col]) else ''
                })
    
    # Print analysis
    print("\nPattern Distribution:")
    print("-" * 80)
    total = len(conflicting_df)
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {pattern}: {count} ({pct:.1f}%)")
    
    # Show samples
    print(f"\n{'='*80}")
    print("SAMPLE MESSAGES BY CATEGORY")
    print(f"{'='*80}")
    
    for category, samples in samples_by_pattern.items():
        if samples:
            print(f"\n{category.upper().replace('_', ' ')}:")
            print("-" * 80)
            for i, sample in enumerate(samples, 1):
                print(f"{i}. {sample['text']}")
    
    return patterns

def create_fixed_dataset(original_df: pd.DataFrame, conflicting_df: pd.DataFrame, 
                        is_otp_col: str, output_path: str, dry_run: bool = True):
    """Create corrected dataset with fixed labels."""
    
    if len(conflicting_df) == 0:
        print("\nNo conflicting labels to fix.")
        return original_df
    
    print(f"\n{'='*80}")
    if dry_run:
        print("DRY RUN - No changes will be saved")
    else:
        print("CREATING FIXED DATASET")
    print(f"{'='*80}")
    
    fixed_df = original_df.copy()
    
    # Fix labels: change is_otp to False for conflicting messages
    conflicting_indices = conflicting_df.index
    
    print(f"\nWill fix {len(conflicting_indices)} labels:")
    print(f"  - Change is_otp from True to False for {len(conflicting_indices)} messages")
    
    if not dry_run:
        # Convert to appropriate type
        if fixed_df[is_otp_col].dtype == 'object':
            # String type
            fixed_df.loc[conflicting_indices, is_otp_col] = 'False'
        elif fixed_df[is_otp_col].dtype == 'bool':
            # Boolean type
            fixed_df.loc[conflicting_indices, is_otp_col] = False
        else:
            # Numeric type
            fixed_df.loc[conflicting_indices, is_otp_col] = 0
        
        print(f"\nFixed labels in dataset")
        print(f"Saving to: {output_path}")
        fixed_df.to_csv(output_path, index=False)
        print(f"Saved!")
    else:
        print(f"\nDry run complete. Run with --apply to actually fix the labels.")
        print(f"Output would be saved to: {output_path}")
    
    return fixed_df

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix ground truth labels')
    parser.add_argument('dataset', nargs='?', default='classification_results_full.csv',
                       help='Dataset file name (default: classification_results_full.csv)')
    parser.add_argument('--apply', action='store_true',
                       help='Actually apply fixes (default: dry run)')
    parser.add_argument('--output', type=str,
                       help='Output file name (default: adds _fixed suffix)')
    
    args = parser.parse_args()
    
    # Find dataset
    dataset_path = Path(__file__).parent.parent / "data" / args.dataset
    
    if not dataset_path.exists():
        print(f"Error: Dataset file not found: {dataset_path}")
        print("Available files:")
        data_dir = Path(__file__).parent.parent / "data"
        for f in sorted(data_dir.glob("*.csv")):
            print(f"  - {f.name}")
        return
    
    # Load original dataset
    print(f"Loading original dataset...")
    original_df = pd.read_csv(dataset_path)
    
    # Identify issues
    conflicting_df, text_col, sender_col, is_otp_col, intent_col = identify_label_issues(str(dataset_path))
    
    if len(conflicting_df) == 0:
        print("\nNo conflicting labels found. Dataset labels are consistent!")
        return
    
    # Analyze patterns
    analyze_conflicting_labels(conflicting_df, text_col, sender_col)
    
    # Create fixed dataset
    if args.output:
        output_path = Path(__file__).parent.parent / "data" / args.output
    else:
        output_path = dataset_path.parent / f"{dataset_path.stem}_fixed.csv"
    
    fixed_df = create_fixed_dataset(
        original_df, 
        conflicting_df, 
        is_otp_col,
        str(output_path),
        dry_run=not args.apply
    )
    
    # Save conflicting labels for review
    review_file = Path(__file__).parent.parent / "heuristic_test_results" / "conflicting_labels_review.csv"
    review_file.parent.mkdir(parents=True, exist_ok=True)
    conflicting_df.to_csv(review_file, index=False)
    print(f"\nSaved conflicting labels for review to: {review_file}")

if __name__ == "__main__":
    main()
