"""
Test heuristic OTP classification on dataset.
Evaluates what percentage of OTPs are caught by heuristics vs requiring ML.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

# Heuristic classifier implementation (Python version matching Kotlin)
# Improved version with enhanced patterns and indicators
class HeuristicOtpClassifier:
    OTP_KEYWORDS = [
        "otp", "verification code", "authentication code", "your code",
        "one time password", "verification pin", "access code", "security code",
        "password code", "login code", "verification", "authenticate"
    ]
    
    OTP_PHRASES = [
        "is your", "code is", "verify with", "use code", "enter code",
        "use otp", "your otp", "otp is", "code to", "verification code is",
        "your verification", "verification code", "login code is"
    ]
    
    OTP_SENDER_PATTERNS = [
        "BANK", "PAYTM", "PHONEPE", "GPAY", "SWIGGY", "ZOMATO",
        "AMAZON", "FLIPKART", "ICICI", "HDFC", "SBI", "AXIS",
        "OTP", "VERIFY", "CODE", "AUTH"
    ]
    
    # Security warning indicators
    SECURITY_WARNINGS = [
        "do not share", "don't share", "don't share", "keep secret", 
        "confidential", "never share", "do not disclose", "keep it safe",
        "don't reveal", "never reveal"
    ]
    
    # Validity period indicators
    VALIDITY_WORDS = [
        "valid", "validity", "expires", "expiry", "minutes", "min", 
        "seconds", "sec", "valid for", "expires in"
    ]
    
    # Verification words
    VERIFICATION_WORDS = [
        "verify", "verification", "authenticate", "authentication", 
        "login", "sign in", "access", "confirm"
    ]
    
    CODE_PATTERN = re.compile(r"\b\d{4,8}\b")
    
    STRONG_OTP_PATTERNS = [
        re.compile(r"\b(otp|one.?time.?password)\b.*?\b\d{4,8}\b", re.IGNORECASE),
        re.compile(r"\b\d{4,8}\b.*?(otp|code|verification)", re.IGNORECASE),
        re.compile(r"(your|use|enter).*?(otp|code).*?\b\d{4,8}\b", re.IGNORECASE),
        re.compile(r"\b\d{4,8}\b.*?(is|as).*?(your|the).*?(otp|code|password)", re.IGNORECASE)
    ]
    
    # NEW: Code at start pattern
    START_CODE_PATTERN = re.compile(
        r"^\b\d{4,8}\b\s*(?:is|for|your|use|enter|verification|code|otp|password)",
        re.IGNORECASE
    )
    
    # NEW: Verification words with code pattern
    VERIFICATION_CODE_PATTERN = re.compile(
        r"(?:verify|verification|authenticate|login|sign.?in).*?\b\d{4,8}\b",
        re.IGNORECASE
    )
    
    # NEW: Security warning with code pattern
    SECURITY_CODE_PATTERN = re.compile(
        r"(?:do\s+not\s+share|don'?t\s+share|keep\s+secret|confidential|never\s+share).*?\b\d{4,8}\b",
        re.IGNORECASE
    )
    
    @staticmethod
    def classify(text: str, sender: str = None) -> Dict:
        text_lower = text.lower()
        sender_upper = (sender or "").upper()
        reasons = []
        confidence = 0.0
        is_otp = False
        suggested_intent = None
        
        # Check for numeric code (required for OTP)
        has_code = bool(HeuristicOtpClassifier.CODE_PATTERN.search(text))
        if not has_code:
            return {
                "isOtp": False,
                "confidence": 0.0,
                "suggestedIntent": None,
                "reasons": ["No numeric code found (4-8 digits required)"]
            }
        reasons.append("Numeric code found (4-8 digits)")
        
        # Check for strong OTP patterns (high confidence)
        strong_match = any(pattern.search(text) for pattern in HeuristicOtpClassifier.STRONG_OTP_PATTERNS)
        if strong_match:
            is_otp = True
            confidence = 0.95
            reasons.append("Strong OTP pattern detected")
        
        # NEW: Check for code at start pattern
        start_code_match = HeuristicOtpClassifier.START_CODE_PATTERN.search(text)
        if start_code_match:
            is_otp = True
            confidence = max(confidence, 0.90)
            reasons.append("Code at start with OTP context")
        
        # Check for OTP keywords (improved: use word boundaries)
        has_otp_keyword = False
        for keyword in HeuristicOtpClassifier.OTP_KEYWORDS:
            # Use word boundary for single words, substring for phrases
            if len(keyword.split()) == 1:
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                if pattern.search(text):
                    has_otp_keyword = True
                    break
            elif keyword in text_lower:
                has_otp_keyword = True
                break
        
        if has_otp_keyword:
            is_otp = True
            confidence = max(confidence, 0.85)
            reasons.append("OTP keyword found")
        
        # Check for OTP phrases
        has_otp_phrase = any(phrase in text_lower for phrase in HeuristicOtpClassifier.OTP_PHRASES)
        if has_otp_phrase and has_code:
            is_otp = True
            confidence = max(confidence, 0.80)
            reasons.append("OTP phrase found")
        
        # NEW: Check for verification words with code
        verification_match = HeuristicOtpClassifier.VERIFICATION_CODE_PATTERN.search(text)
        if verification_match:
            is_otp = True
            confidence = max(confidence, 0.80)
            reasons.append("Verification word with code detected")
        
        # NEW: Check for security warnings with code
        security_match = HeuristicOtpClassifier.SECURITY_CODE_PATTERN.search(text)
        if security_match:
            is_otp = True
            confidence = max(confidence, 0.75)
            reasons.append("Security warning with code detected")
        
        # Check sender patterns
        sender_matches = any(pattern in sender_upper for pattern in HeuristicOtpClassifier.OTP_SENDER_PATTERNS)
        if sender_matches and has_code:
            is_otp = True
            confidence = max(confidence, 0.75)
            reasons.append("Known OTP sender pattern")
        
        # NEW: Check for validity period indicators
        has_validity = any(word in text_lower for word in HeuristicOtpClassifier.VALIDITY_WORDS)
        if has_validity and has_code and not is_otp:
            is_otp = True
            confidence = max(confidence, 0.70)
            reasons.append("Validity period mentioned")
        
        # NEW: Check for security warnings as additional indicator
        has_security_warning = any(warning in text_lower for warning in HeuristicOtpClassifier.SECURITY_WARNINGS)
        if has_security_warning and has_code and not is_otp:
            is_otp = True
            confidence = max(confidence, 0.75)
            reasons.append("Security warning present")
        
        # Additional confidence boost if multiple indicators present
        indicator_count = sum([
            strong_match, 
            bool(start_code_match), 
            has_otp_keyword, 
            has_otp_phrase, 
            sender_matches,
            bool(verification_match),
            bool(security_match),
            has_validity,
            has_security_warning
        ])
        if indicator_count >= 2:
            confidence = min(confidence + 0.05, 0.98)
            reasons.append(f"Multiple OTP indicators ({indicator_count})")
        
        # If we have code but low confidence indicators, still classify as OTP but with lower confidence
        if has_code and not is_otp:
            # Check if message is short (typical for OTPs) - lowered threshold
            if len(text) < 100:
                is_otp = True
                confidence = 0.60
                reasons.append("Short message with numeric code (possible OTP)")
            elif len(text) < 150:
                is_otp = True
                confidence = 0.55
                reasons.append("Medium-length message with numeric code (possible OTP)")
        
        # Determine intent if it's an OTP
        if is_otp:
            suggested_intent = HeuristicOtpClassifier._detect_intent(text, sender_upper, reasons)
        
        return {
            "isOtp": is_otp,
            "confidence": confidence,
            "suggestedIntent": suggested_intent,
            "reasons": reasons
        }
    
    @staticmethod
    def _detect_intent(text: str, sender_upper: str, reasons: List[str]) -> str:
        if (re.search(r"\b(delivery|deliver|courier|package|order|shipment|tracking|logistics)\b", text, re.IGNORECASE) or
            any(s in sender_upper for s in ["SWIGGY", "ZOMATO", "DELHIVERY", "BLUEDART"])):
            reasons.append("Intent: DELIVERY_OR_SERVICE_OTP")
            return "DELIVERY_OR_SERVICE_OTP"
        
        if (re.search(r"\b(bank|card|transaction|payment|transfer|upi|debit|credit)\b", text, re.IGNORECASE) or
            any(s in sender_upper for s in ["BANK", "ICICI", "HDFC", "SBI", "AXIS"])):
            reasons.append("Intent: BANK_OR_CARD_TXN_OTP")
            return "BANK_OR_CARD_TXN_OTP"
        
        if (re.search(r"\b(upi|unified payments|pin|device.*link|link.*device)\b", text, re.IGNORECASE) or
            any(s in sender_upper for s in ["UPI", "PHONEPE", "GPAY", "PAYTM"])):
            reasons.append("Intent: UPI_TXN_OR_PIN_OTP")
            return "UPI_TXN_OR_PIN_OTP"
        
        if re.search(r"\b(password.*reset|change.*password|update.*profile|change.*phone|change.*email|account.*change)\b", text, re.IGNORECASE):
            reasons.append("Intent: APP_ACCOUNT_CHANGE_OTP")
            return "APP_ACCOUNT_CHANGE_OTP"
        
        if re.search(r"\b(login|sign.?in|access|verify.?account|authenticate)\b", text, re.IGNORECASE):
            reasons.append("Intent: APP_LOGIN_OTP")
            return "APP_LOGIN_OTP"
        
        if re.search(r"\b(kyc|know.*customer|e.?sign|esign|document.*sign)\b", text, re.IGNORECASE):
            reasons.append("Intent: KYC_OR_ESIGN_OTP")
            return "KYC_OR_ESIGN_OTP"
        
        reasons.append("Intent: GENERIC_APP_ACTION_OTP (default)")
        return "GENERIC_APP_ACTION_OTP"


def load_dataset(file_path: str) -> pd.DataFrame:
    """Load dataset CSV file."""
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} rows from {file_path}")
    return df


def test_heuristic_classification(df: pd.DataFrame) -> Dict:
    """Test heuristic classifier on dataset."""
    
    # Determine which columns contain SMS text and labels
    text_col = None
    sender_col = None
    is_otp_col = None
    otp_intent_col = None
    
    # Try common column names
    for col in df.columns:
        col_lower = col.lower()
        if "body" in col_lower or "text" in col_lower or "sms" in col_lower or "message" in col_lower:
            text_col = col
        if "sender" in col_lower or "from" in col_lower or "address" in col_lower:
            sender_col = col
        if "is_otp" in col_lower or "predicted_is_otp" in col_lower or "isotp" in col_lower:
            is_otp_col = col
        if "intent" in col_lower or "otp_intent" in col_lower:
            otp_intent_col = col
    
    if not text_col:
        raise ValueError("Could not find SMS text column in dataset")
    
    print(f"Using columns: text={text_col}, sender={sender_col}, is_otp={is_otp_col}, intent={otp_intent_col}")
    
    # Filter rows where we have ground truth
    if is_otp_col:
        df_filtered = df[df[is_otp_col].notna()].copy()
        print(f"Filtered to {len(df_filtered)} rows with is_otp labels")
    else:
        df_filtered = df.copy()
        print("Warning: No is_otp column found, will only compute predictions")
    
    # Apply heuristic classifier
    results = []
    high_confidence_count = 0
    medium_confidence_count = 0
    low_confidence_count = 0
    ml_needed_count = 0
    
    for idx, row in df_filtered.iterrows():
        text = str(row[text_col]) if pd.notna(row[text_col]) else ""
        sender = str(row[sender_col]) if sender_col and pd.notna(row.get(sender_col, None)) else None
        
        heuristic_result = HeuristicOtpClassifier.classify(text, sender)
        
        # Count by confidence level
        if heuristic_result["confidence"] > 0.8:
            high_confidence_count += 1
        elif heuristic_result["confidence"] > 0.5:
            medium_confidence_count += 1
        elif heuristic_result["confidence"] > 0.0:
            low_confidence_count += 1
        else:
            ml_needed_count += 1
        
        results.append({
            "index": idx,
            "text": text[:100],  # Truncate for readability
            "sender": sender,
            "heuristic_is_otp": heuristic_result["isOtp"],
            "heuristic_confidence": heuristic_result["confidence"],
            "heuristic_intent": heuristic_result["suggestedIntent"],
            "ground_truth_is_otp": bool(row[is_otp_col]) if is_otp_col and pd.notna(row[is_otp_col]) else None,
            "ground_truth_intent": row[otp_intent_col] if otp_intent_col and pd.notna(row.get(otp_intent_col, None)) else None,
            "reasons": " | ".join(heuristic_result["reasons"][:3])  # First 3 reasons
        })
    
    results_df = pd.DataFrame(results)
    
    # Calculate metrics
    metrics = {}
    
    if is_otp_col:
        y_true = results_df["ground_truth_is_otp"].fillna(False).astype(bool)
        y_pred = results_df["heuristic_is_otp"].astype(bool)
        
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1_score": f1_score(y_true, y_pred, zero_division=0),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist()
        }
        
        # Calculate percentage caught by heuristics
        total_otps = y_true.sum()
        caught_by_heuristics = (y_true & y_pred).sum()
        percentage_caught = (caught_by_heuristics / total_otps * 100) if total_otps > 0 else 0
        
        metrics["total_otps"] = int(total_otps)
        metrics["caught_by_heuristics"] = int(caught_by_heuristics)
        metrics["percentage_caught"] = float(percentage_caught)
        
        # High confidence catch rate
        high_conf_caught = ((results_df["heuristic_is_otp"] == True) & 
                           (results_df["heuristic_confidence"] > 0.8) & 
                           (y_true == True)).sum()
        metrics["high_confidence_caught"] = int(high_conf_caught)
        metrics["high_confidence_percentage"] = float(high_conf_caught / total_otps * 100) if total_otps > 0 else 0
    
    # Confidence distribution
    metrics["confidence_distribution"] = {
        "high_confidence_gt_80": int(high_confidence_count),
        "medium_confidence_50_80": int(medium_confidence_count),
        "low_confidence_0_50": int(low_confidence_count),
        "ml_needed_0": int(ml_needed_count)
    }
    
    metrics["total_messages"] = len(results_df)
    
    return metrics, results_df


def main():
    import sys
    
    # Default dataset file
    dataset_file = "classification_results_full.csv"
    
    if len(sys.argv) > 1:
        dataset_file = sys.argv[1]
    
    dataset_path = Path(__file__).parent.parent / "data" / dataset_file
    
    if not dataset_path.exists():
        print(f"Error: Dataset file not found: {dataset_path}")
        print("Available files:")
        data_dir = Path(__file__).parent.parent / "data"
        for f in sorted(data_dir.glob("*.csv")):
            print(f"  - {f.name}")
        return
    
    print(f"Testing heuristic classification on: {dataset_path}")
    print("=" * 80)
    
    # Load dataset
    df = load_dataset(str(dataset_path))
    
    # Test heuristic classifier
    metrics, results_df = test_heuristic_classification(df)
    
    # Print results
    print("\n" + "=" * 80)
    print("HEURISTIC CLASSIFICATION RESULTS")
    print("=" * 80)
    
    if "accuracy" in metrics:
        print(f"\nAccuracy: {metrics['accuracy']:.4f}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1-Score: {metrics['f1_score']:.4f}")
        print(f"\nTotal OTPs in dataset: {metrics['total_otps']}")
        print(f"Caught by heuristics: {metrics['caught_by_heuristics']}")
        print(f"Percentage caught: {metrics['percentage_caught']:.2f}%")
        print(f"\nHigh confidence (>0.8) catches: {metrics['high_confidence_caught']}")
        print(f"High confidence percentage: {metrics['high_confidence_percentage']:.2f}%")
        print(f"\nConfusion Matrix:")
        cm = metrics['confusion_matrix']
        print(f"  True Negatives: {cm[0][0]}, False Positives: {cm[0][1]}")
        print(f"  False Negatives: {cm[1][0]}, True Positives: {cm[1][1]}")
    
    print(f"\nConfidence Distribution:")
    dist = metrics['confidence_distribution']
    print(f"  High confidence (>0.8): {dist['high_confidence_gt_80']} messages")
    print(f"  Medium confidence (0.5-0.8): {dist['medium_confidence_50_80']} messages")
    print(f"  Low confidence (0.0-0.5): {dist['low_confidence_0_50']} messages")
    print(f"  ML needed (0.0): {dist['ml_needed_0']} messages")
    
    # Save results
    output_dir = Path(__file__).parent.parent / "heuristic_test_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metrics_file = output_dir / "heuristic_performance_report.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved metrics to: {metrics_file}")
    
    results_file = output_dir / "heuristic_classification_results.csv"
    results_df.to_csv(results_file, index=False)
    print(f"Saved detailed results to: {results_file}")


if __name__ == "__main__":
    main()

