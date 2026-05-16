"""
Analyze OTP messages that were missed by heuristics to identify improvement opportunities.
"""

import pandas as pd
import re
from pathlib import Path
from collections import Counter

def analyze_missed_otps(results_csv_path: str, sample_size: int = 100):
    """Analyze false negative OTP messages."""
    
    print("Loading heuristic classification results...")
    df = pd.read_csv(results_csv_path)
    
    # Filter for false negatives: ground truth is OTP but heuristic said no (or confidence 0)
    # Also filter out messages where intent is NOT_OTP (those are correctly identified as not OTPs)
    false_negatives = df[
        (df['ground_truth_is_otp'] == True) & 
        (df['heuristic_confidence'] == 0.0) &
        (df['ground_truth_intent'] != 'NOT_OTP')
    ].copy()
    
    print(f"\n{'='*80}")
    print(f"FALSE NEGATIVE ANALYSIS")
    print(f"{'='*80}")
    print(f"\nTotal false negatives: {len(false_negatives)}")
    print(f"Percentage of total OTPs missed: {len(false_negatives) / len(df[df['ground_truth_is_otp'] == True]) * 100:.2f}%")
    
    if len(false_negatives) == 0:
        print("\nNo false negatives found!")
        return
    
    # Sample for analysis
    sample_df = false_negatives.head(min(sample_size, len(false_negatives)))
    
    # Analyze patterns in missed OTPs
    print(f"\n{'='*80}")
    print(f"PATTERN ANALYSIS (analyzing {len(sample_df)} samples)")
    print(f"{'='*80}")
    
    patterns = {
        'has_code': 0,
        'has_otp_keyword': 0,
        'has_verification_words': 0,
        'has_otp_phrases': 0,
        'has_sender_pattern': 0,
        'short_message': 0,
        'numeric_code_at_start': 0,
        'numeric_code_in_middle': 0,
        'has_security_warnings': 0,
        'has_validity_period': 0,
        'has_no_code': 0,
        'code_length_4': 0,
        'code_length_5': 0,
        'code_length_6': 0,
        'code_length_7_8': 0,
    }
    
    otp_keywords = [
        "otp", "verification code", "authentication code", "your code",
        "one time password", "verification pin", "access code", "security code",
        "password code", "login code"
    ]
    
    verification_words = ["verify", "verification", "authenticate", "authentication", 
                         "login", "sign in", "access"]
    
    otp_phrases = [
        "is your", "code is", "verify with", "use code", "enter code",
        "use otp", "your otp", "otp is", "code to", "verification code is"
    ]
    
    security_warnings = ["do not share", "don't share", "keep secret", "confidential", 
                        "never share", "do not disclose"]
    
    validity_words = ["valid", "validity", "expires", "expiry", "minutes", "min", 
                     "seconds", "sec"]
    
    code_pattern = re.compile(r"\b\d{4,8}\b")
    
    sample_texts = []
    
    for idx, row in sample_df.iterrows():
        text = str(row['text']).lower() if pd.notna(row['text']) else ""
        sender = str(row['sender']).upper() if pd.notna(row['sender']) else ""
        sender_upper = sender.upper()
        
        has_code = bool(code_pattern.search(text))
        patterns['has_code'] += has_code
        
        if not has_code:
            patterns['has_no_code'] += 1
            sample_texts.append({
                'text': row['text'][:150] if pd.notna(row['text']) else '',
                'reason': 'No numeric code',
                'intent': row.get('ground_truth_intent', 'Unknown')
            })
        
        # Check for code patterns
        if has_code:
            code_matches = code_pattern.findall(text)
            if code_matches:
                code = code_matches[0]
                code_len = len(code)
                if code_len == 4:
                    patterns['code_length_4'] += 1
                elif code_len == 5:
                    patterns['code_length_5'] += 1
                elif code_len == 6:
                    patterns['code_length_6'] += 1
                elif code_len >= 7:
                    patterns['code_length_7_8'] += 1
                
                # Check code position
                code_pos = text.find(code)
                if code_pos < 20:
                    patterns['numeric_code_at_start'] += 1
                else:
                    patterns['numeric_code_in_middle'] += 1
        
        # Check for OTP keywords
        has_otp_keyword = any(keyword in text for keyword in otp_keywords)
        patterns['has_otp_keyword'] += has_otp_keyword
        
        # Check for verification words
        has_verification = any(word in text for word in verification_words)
        patterns['has_verification_words'] += has_verification
        
        # Check for OTP phrases
        has_phrase = any(phrase in text for phrase in otp_phrases)
        patterns['has_otp_phrases'] += has_phrase
        
        # Check sender patterns
        sender_patterns = ["BANK", "PAYTM", "PHONEPE", "GPAY", "SWIGGY", "ZOMATO",
                          "AMAZON", "FLIPKART", "ICICI", "HDFC", "SBI", "AXIS",
                          "OTP", "VERIFY", "CODE", "AUTH"]
        has_sender = any(pattern in sender_upper for pattern in sender_patterns)
        patterns['has_sender_pattern'] += has_sender
        
        # Check message length
        if len(text) < 150:
            patterns['short_message'] += 1
        
        # Check for security warnings
        has_security = any(warning in text for warning in security_warnings)
        patterns['has_security_warnings'] += has_security
        
        # Check for validity period
        has_validity = any(word in text for word in validity_words)
        patterns['has_validity_period'] += has_validity
        
        # Collect interesting samples
        if has_code and not has_otp_keyword and not has_phrase and len(sample_texts) < 20:
            sample_texts.append({
                'text': row['text'][:200] if pd.notna(row['text']) else '',
                'reason': 'Has code but no OTP keywords',
                'intent': row.get('ground_truth_intent', 'Unknown'),
                'sender': sender[:30]
            })
    
    # Print pattern statistics
    print(f"\nPattern Frequency (out of {len(sample_df)} samples):")
    print("-" * 80)
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(sample_df) * 100) if len(sample_df) > 0 else 0
        print(f"  {pattern}: {count} ({percentage:.1f}%)")
    
    # Show sample missed OTPs
    print(f"\n{'='*80}")
    print(f"SAMPLE MISSED OTP MESSAGES")
    print(f"{'='*80}")
    
    for i, sample in enumerate(sample_texts[:15], 1):
        print(f"\n{i}. [{sample['reason']}] Intent: {sample.get('intent', 'Unknown')}")
        if 'sender' in sample:
            print(f"   Sender: {sample['sender']}")
        print(f"   Text: {sample['text']}")
    
    # Analyze common patterns in missed messages
    print(f"\n{'='*80}")
    print(f"RECOMMENDATIONS FOR IMPROVING HEURISTICS")
    print(f"{'='*80}")
    
    recommendations = []
    
    if patterns['has_code'] > len(sample_df) * 0.8:
        recommendations.append("[OK] Most missed OTPs have numeric codes - good!")
    
    if patterns['has_no_code'] > 0:
        recommendations.append(f"[INFO] {patterns['has_no_code']} missed OTPs have no numeric code - these need ML")
    
    if patterns['numeric_code_at_start'] > len(sample_df) * 0.3:
        recommendations.append(f"[TIP] {patterns['numeric_code_at_start']} missed OTPs have code at start - add pattern: '^\\d{{4,8}}\\s+(?:is|for|your|use)'")
    
    if patterns['has_verification_words'] > len(sample_df) * 0.4:
        recommendations.append(f"[TIP] {patterns['has_verification_words']} missed OTPs have verification words - expand keyword list")
    
    if patterns['has_validity_period'] > len(sample_df) * 0.2:
        recommendations.append(f"[TIP] {patterns['has_validity_period']} missed OTPs mention validity - add as indicator")
    
    if patterns['has_security_warnings'] > len(sample_df) * 0.3:
        recommendations.append(f"[TIP] {patterns['has_security_warnings']} missed OTPs have security warnings - add as indicator")
    
    if patterns['short_message'] > len(sample_df) * 0.5:
        recommendations.append(f"[TIP] {patterns['short_message']} missed OTPs are short messages - consider lowering length threshold")
    
    if patterns['has_sender_pattern'] > len(sample_df) * 0.3:
        recommendations.append(f"[TIP] {patterns['has_sender_pattern']} missed OTPs have known sender patterns - verify sender matching logic")
    
    if patterns['code_length_6'] > len(sample_df) * 0.3:
        recommendations.append(f"[TIP] Most codes are 6 digits - verify pattern matches correctly")
    
    for rec in recommendations:
        print(f"\n{rec}")
    
    # Suggest new patterns
    print(f"\n{'='*80}")
    print(f"SUGGESTED NEW PATTERNS")
    print(f"{'='*80}")
    
    print("""
1. Code at start pattern:
   Pattern: ^\\b\\d{4,8}\\b.*?(?:is|for|your|use|enter|verification|code)
   
2. Verification + code pattern:
   Pattern: (?:verify|verification|authenticate|login).*?\\b\\d{4,8}\\b
   
3. Short message with code:
   If message < 100 chars + has code + no transaction keywords → likely OTP
   
4. Validity period indicator:
   If contains "valid", "minutes", "expires" + code → likely OTP
   
5. Security warning indicator:
   If contains "don't share", "confidential" + code → likely OTP
   
6. Numeric code without context:
   If message has isolated 4-8 digit code (not part of date/amount) → possible OTP
    """)
    
    return sample_df

def main():
    results_file = Path(__file__).parent.parent / "heuristic_test_results" / "heuristic_classification_results.csv"
    
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        return
    
    analyze_missed_otps(str(results_file), sample_size=500)

if __name__ == "__main__":
    main()
