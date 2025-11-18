"""
Validate synthetic OTP SMS data quality.

This script checks:
1. Count per intent (should match targets)
2. Message length (should be reasonable for SMS)
3. OTP code presence and format (4-8 digits)
4. Security warnings presence
5. Duplicate detection
6. Language distribution
7. Format compliance (CSV structure, column values)
8. Uniqueness vs existing dataset

Usage:
    python validate_synthetic_data.py [synthetic_file.csv]
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import pandas as pd

# Default files
DEFAULT_SYNTHETIC_FILE = "synthetic_financial_app_login_full.csv"
EXISTING_DATASET = "classification_results_with_phishing_llm_balanced.csv"

# Expected targets
TARGET_COUNTS = {
    "FINANCIAL_LOGIN_OTP": 800,
    "APP_LOGIN_OTP": 800,
}

# Validation patterns
OTP_PATTERN = r"\b\d{4,8}\b"  # 4-8 digit OTP codes
SECURITY_WARNING_PATTERNS = [
    r"do not share|never share|don't share",
    r"bank never asks|bank.*never.*ask",
    r"otp.*secret|secret.*code|keep.*secret|keep.*confidential",
    r"do not disclose|never disclose|don't disclose",
    r"kisi ko.*share|kisi ko.*batayein|mat batayein",
]

FINANCIAL_KEYWORDS = [
    r"\b(trading|investment|portfolio|demat|mutual fund|stocks|NSE|BSE|Zerodha|Groww|Upstox|broker|equity|Angel One|Kotak Securities|ICICI Direct|HDFC Securities)\b",
]

APP_KEYWORDS = [
    r"\b(Netflix|Spotify|Amazon|Zomato|Hotstar|Instagram|Flipkart|Gaana|Disney|YouTube|social|entertainment|streaming|gaming|shopping)\b",
]


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    if pd.isna(text):
        return ""
    return " ".join(str(text).strip().split()).lower()


def check_otp_presence(text: str) -> bool:
    """Check if message contains an OTP code."""
    return bool(re.search(OTP_PATTERN, text))


def check_security_warning(text: str) -> bool:
    """Check if message contains security warnings."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in SECURITY_WARNING_PATTERNS)


def check_financial_context(text: str) -> bool:
    """Check if message contains financial keywords."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in FINANCIAL_KEYWORDS)


def check_app_context(text: str) -> bool:
    """Check if message contains app keywords."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in APP_KEYWORDS)


def detect_language(text: str) -> str:
    """Simple language detection (English vs Hindi mix)."""
    hindi_chars = re.search(r"[\u0900-\u097F]", text)
    if hindi_chars:
        return "hindi_mixed"
    return "english"


def validate_synthetic_file(synthetic_file: str, existing_file: str = None) -> Dict:
    """Validate synthetic data file."""
    print("=" * 80)
    print(f"VALIDATING: {synthetic_file}")
    print("=" * 80)
    
    # Load synthetic data
    try:
        df_synth = pd.read_csv(synthetic_file)
    except FileNotFoundError:
        print(f"ERROR: File not found: {synthetic_file}")
        return {}
    
    print(f"\n✓ Loaded {len(df_synth)} rows")
    
    # Check required columns
    required_cols = [
        "original_index",
        "sms_text",
        "predicted_is_otp",
        "predicted_otp_intent",
        "classification_status",
        "batch_number",
        "is_phishing_original",
    ]
    missing_cols = [col for col in required_cols if col not in df_synth.columns]
    if missing_cols:
        print(f"ERROR: Missing columns: {missing_cols}")
        return {}
    
    print("✓ All required columns present")
    
    # Initialize results
    results = {
        "total_rows": len(df_synth),
        "intent_counts": {},
        "issues": [],
        "warnings": [],
        "stats": {},
    }
    
    # 1. Check intent distribution
    print("\n" + "-" * 80)
    print("1. INTENT DISTRIBUTION")
    print("-" * 80)
    intent_counts = df_synth["predicted_otp_intent"].value_counts()
    results["intent_counts"] = intent_counts.to_dict()
    
    for intent, target in TARGET_COUNTS.items():
        actual = intent_counts.get(intent, 0)
        print(f"  {intent}:")
        print(f"    Target: {target}")
        print(f"    Actual: {actual}")
        if actual < target * 0.9:  # Allow 10% tolerance
            results["warnings"].append(f"{intent}: Only {actual}/{target} samples (expected at least {int(target * 0.9)})")
            print(f"    ⚠ WARNING: Below target")
        elif actual > target * 1.1:
            results["warnings"].append(f"{intent}: {actual} samples (exceeded target of {target})")
            print(f"    ⚠ WARNING: Exceeded target")
        else:
            print(f"    ✓ Within target range")
    
    # 2. Check for duplicates within synthetic data
    print("\n" + "-" * 80)
    print("2. DUPLICATE DETECTION (within synthetic data)")
    print("-" * 80)
    normalized_texts = df_synth["sms_text"].apply(normalize_text)
    duplicates = normalized_texts.duplicated()
    dup_count = duplicates.sum()
    results["stats"]["internal_duplicates"] = dup_count
    
    if dup_count > 0:
        results["issues"].append(f"Found {dup_count} duplicate messages within synthetic data")
        print(f"  ⚠ Found {dup_count} duplicate messages")
        print("  Sample duplicates:")
        dup_indices = df_synth[duplicates].index[:5]
        for idx in dup_indices:
            print(f"    - {df_synth.loc[idx, 'sms_text'][:80]}...")
    else:
        print("  ✓ No duplicates found")
    
    # 3. Check against existing dataset
    if existing_file and Path(existing_file).exists():
        print("\n" + "-" * 80)
        print("3. DUPLICATE DETECTION (vs existing dataset)")
        print("-" * 80)
        try:
            df_existing = pd.read_csv(existing_file)
            existing_texts = {
                normalize_text(txt) 
                for txt in df_existing["sms_text"].tolist() 
                if pd.notna(txt)
            }
            
            synth_texts = {normalize_text(txt) for txt in df_synth["sms_text"].tolist() if pd.notna(txt)}
            overlap = synth_texts & existing_texts
            results["stats"]["overlap_with_existing"] = len(overlap)
            
            if overlap:
                results["warnings"].append(f"Found {len(overlap)} messages that already exist in existing dataset")
                print(f"  ⚠ Found {len(overlap)} messages that already exist")
                print("  Sample overlapping messages:")
                for txt in list(overlap)[:3]:
                    print(f"    - {txt[:80]}...")
            else:
                print("  ✓ No overlap with existing dataset")
        except Exception as e:
            print(f"  ⚠ Could not check against existing dataset: {e}")
    
    # 4. Message quality checks
    print("\n" + "-" * 80)
    print("4. MESSAGE QUALITY CHECKS")
    print("-" * 80)
    
    # OTP presence
    has_otp = df_synth["sms_text"].apply(check_otp_presence)
    otp_count = has_otp.sum()
    results["stats"]["messages_with_otp"] = otp_count
    print(f"  Messages with OTP code: {otp_count}/{len(df_synth)} ({100*otp_count/len(df_synth):.1f}%)")
    if otp_count < len(df_synth) * 0.95:
        results["issues"].append(f"Only {otp_count}/{len(df_synth)} messages contain OTP codes")
    
    # Security warnings
    has_warning = df_synth["sms_text"].apply(check_security_warning)
    warning_count = has_warning.sum()
    results["stats"]["messages_with_warning"] = warning_count
    print(f"  Messages with security warning: {warning_count}/{len(df_synth)} ({100*warning_count/len(df_synth):.1f}%)")
    if warning_count < len(df_synth) * 0.90:
        results["warnings"].append(f"Only {warning_count}/{len(df_synth)} messages contain security warnings")
    
    # Message length
    lengths = df_synth["sms_text"].str.len()
    results["stats"]["avg_length"] = lengths.mean()
    results["stats"]["min_length"] = lengths.min()
    results["stats"]["max_length"] = lengths.max()
    print(f"  Message length: avg={lengths.mean():.1f}, min={lengths.min()}, max={lengths.max()}")
    
    too_long = (lengths > 200).sum()
    if too_long > 0:
        results["warnings"].append(f"{too_long} messages exceed 200 characters (SMS limit)")
        print(f"  ⚠ {too_long} messages exceed 200 characters")
    
    # 5. Context validation
    print("\n" + "-" * 80)
    print("5. CONTEXT VALIDATION")
    print("-" * 80)
    
    financial_rows = df_synth[df_synth["predicted_otp_intent"] == "FINANCIAL_LOGIN_OTP"]
    app_rows = df_synth[df_synth["predicted_otp_intent"] == "APP_LOGIN_OTP"]
    
    if len(financial_rows) > 0:
        financial_context = financial_rows["sms_text"].apply(check_financial_context)
        financial_context_count = financial_context.sum()
        print(f"  FINANCIAL_LOGIN_OTP with financial keywords: {financial_context_count}/{len(financial_rows)} ({100*financial_context_count/len(financial_rows):.1f}%)")
        if financial_context_count < len(financial_rows) * 0.80:
            results["warnings"].append(f"Only {financial_context_count}/{len(financial_rows)} FINANCIAL_LOGIN_OTP messages contain financial keywords")
    
    if len(app_rows) > 0:
        app_context = app_rows["sms_text"].apply(check_app_context)
        app_context_count = app_context.sum()
        print(f"  APP_LOGIN_OTP with app keywords: {app_context_count}/{len(app_rows)} ({100*app_context_count/len(app_rows):.1f}%)")
        if app_context_count < len(app_rows) * 0.80:
            results["warnings"].append(f"Only {app_context_count}/{len(app_rows)} APP_LOGIN_OTP messages contain app keywords")
    
    # 6. Language distribution
    print("\n" + "-" * 80)
    print("6. LANGUAGE DISTRIBUTION")
    print("-" * 80)
    languages = df_synth["sms_text"].apply(detect_language)
    lang_counts = languages.value_counts()
    results["stats"]["language_distribution"] = lang_counts.to_dict()
    for lang, count in lang_counts.items():
        print(f"  {lang}: {count} ({100*count/len(df_synth):.1f}%)")
    
    # 7. Column value validation
    print("\n" + "-" * 80)
    print("7. COLUMN VALUE VALIDATION")
    print("-" * 80)
    
    # Check predicted_is_otp
    is_otp_values = df_synth["predicted_is_otp"].value_counts()
    print(f"  predicted_is_otp: {is_otp_values.to_dict()}")
    if (df_synth["predicted_is_otp"] != True).any():
        results["issues"].append("Some rows have predicted_is_otp != True")
        print("  ⚠ Some rows have predicted_is_otp != True")
    
    # Check is_phishing_original
    is_phishing_values = df_synth["is_phishing_original"].value_counts()
    print(f"  is_phishing_original: {is_phishing_values.to_dict()}")
    if (df_synth["is_phishing_original"] != False).any():
        results["warnings"].append("Some rows have is_phishing_original != False (should all be False for OTP)")
        print("  ⚠ Some rows have is_phishing_original != False")
    
    # Check classification_status
    status_values = df_synth["classification_status"].value_counts()
    print(f"  classification_status: {status_values.to_dict()}")
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if results["issues"]:
        print("\n❌ ISSUES FOUND:")
        for issue in results["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✓ No critical issues found")
    
    if results["warnings"]:
        print("\n⚠ WARNINGS:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
    else:
        print("\n✓ No warnings")
    
    print(f"\nTotal rows: {results['total_rows']}")
    print(f"Intent distribution: {results['intent_counts']}")
    
    return results


def main():
    """Main entry point."""
    synthetic_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SYNTHETIC_FILE
    existing_file = EXISTING_DATASET if Path(EXISTING_DATASET).exists() else None
    
    results = validate_synthetic_file(synthetic_file, existing_file)
    
    # Save results to JSON
    if results:
        import json
        
        # Convert numpy/pandas types to native Python types for JSON serialization
        def convert_to_native(obj):
            if isinstance(obj, (pd.Series, pd.DataFrame)):
                return obj.to_dict()
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_native(item) for item in obj]
            elif isinstance(obj, set):
                return list(obj)
            return obj
        
        results_serializable = convert_to_native(results)
        output_file = Path(synthetic_file).stem + "_validation.json"
        with open(output_file, "w") as f:
            json.dump(results_serializable, f, indent=2)
        print(f"\n✓ Validation results saved to {output_file}")


if __name__ == "__main__":
    main()

