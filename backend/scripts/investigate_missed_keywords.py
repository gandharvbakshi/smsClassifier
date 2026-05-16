"""
Investigate why messages with OTP keywords are being missed by heuristics.
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict

def investigate_missed_keywords(results_csv_path: str):
    """Find messages that have OTP keywords but were missed."""
    
    print("Loading heuristic classification results...")
    df = pd.read_csv(results_csv_path)
    
    # Filter for false negatives that are actual OTPs
    false_negatives = df[
        (df['ground_truth_is_otp'] == True) & 
        (df['heuristic_confidence'] == 0.0) &
        (df['ground_truth_intent'] != 'NOT_OTP')
    ].copy()
    
    print(f"\nTotal false negatives (actual OTPs): {len(false_negatives)}")
    
    # OTP keywords from classifier
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
    
    # Find messages with keywords/phrases but still missed
    missed_with_keywords = []
    
    for idx, row in false_negatives.iterrows():
        text = str(row['text']).lower() if pd.notna(row['text']) else ""
        
        # Check for keywords
        found_keywords = []
        for keyword in OTP_KEYWORDS:
            if len(keyword.split()) == 1:
                # Single word - check with word boundary
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                if pattern.search(str(row['text'])):
                    found_keywords.append(keyword)
            else:
                # Phrase - substring match
                if keyword in text:
                    found_keywords.append(keyword)
        
        # Check for phrases
        found_phrases = []
        for phrase in OTP_PHRASES:
            if phrase in text:
                found_phrases.append(phrase)
        
        if found_keywords or found_phrases:
            missed_with_keywords.append({
                'index': idx,
                'text': row['text'][:300] if pd.notna(row['text']) else '',
                'sender': row.get('sender', ''),
                'ground_truth_intent': row.get('ground_truth_intent', ''),
                'found_keywords': found_keywords,
                'found_phrases': found_phrases,
                'has_code': bool(re.search(r"\b\d{4,8}\b", str(row['text']) if pd.notna(row['text']) else "")),
                'text_length': len(str(row['text']) if pd.notna(row['text']) else "")
            })
    
    print(f"\n{'='*80}")
    print(f"MESSAGES WITH OTP KEYWORDS/PHRASES BUT STILL MISSED: {len(missed_with_keywords)}")
    print(f"{'='*80}")
    
    if len(missed_with_keywords) == 0:
        print("\nNo messages with OTP keywords were missed - all keyword matches are being caught!")
        return
    
    # Analyze patterns
    print(f"\nAnalysis of {len(missed_with_keywords)} missed messages with keywords:")
    print("-" * 80)
    
    no_code_count = sum(1 for m in missed_with_keywords if not m['has_code'])
    has_code_count = len(missed_with_keywords) - no_code_count
    
    print(f"Messages with code: {has_code_count} ({has_code_count/len(missed_with_keywords)*100:.1f}%)")
    print(f"Messages without code: {no_code_count} ({no_code_count/len(missed_with_keywords)*100:.1f}%)")
    
    # Show examples
    print(f"\n{'='*80}")
    print("SAMPLE MISSED MESSAGES WITH KEYWORDS:")
    print(f"{'='*80}")
    
    for i, msg in enumerate(missed_with_keywords[:20], 1):
        print(f"\n{i}. Keywords found: {', '.join(msg['found_keywords'][:3])}")
        if msg['found_phrases']:
            print(f"   Phrases found: {', '.join(msg['found_phrases'][:2])}")
        print(f"   Intent: {msg['ground_truth_intent']}")
        print(f"   Has code: {msg['has_code']}, Length: {msg['text_length']}")
        print(f"   Text: {msg['text'][:200]}...")
        
        # Analyze why it was missed
        text = msg['text'].lower()
        has_code = msg['has_code']
        
        reasons = []
        if not has_code:
            reasons.append("No numeric code - correctly rejected")
        else:
            # Check if keywords are in context with code
            code_match = re.search(r"\b\d{4,8}\b", msg['text'])
            if code_match:
                code_pos = code_match.start()
                keyword_positions = []
                for keyword in msg['found_keywords']:
                    if keyword in text:
                        keyword_positions.append(text.find(keyword))
                
                if keyword_positions:
                    min_keyword_pos = min(keyword_positions)
                    distance = abs(code_pos - min_keyword_pos)
                    if distance > 50:
                        reasons.append(f"Keyword and code far apart ({distance} chars)")
                    else:
                        reasons.append("Keyword and code close - should have matched!")
                
                # Check for transaction keywords that might suppress
                transaction_words = ["spent", "transaction", "payment", "debited", "credited", "balance"]
                if any(word in text for word in transaction_words):
                    reasons.append("Contains transaction keywords - may need filtering")
        
        if reasons:
            print(f"   Analysis: {'; '.join(reasons)}")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS:")
    print(f"{'='*80}")
    
    if no_code_count > 0:
        print(f"\n1. {no_code_count} messages have keywords but no code - these need ML (correct behavior)")
    
    if has_code_count > 0:
        print(f"\n2. {has_code_count} messages have both keywords and code but were missed:")
        print("   - Verify keyword matching logic")
        print("   - Check if transaction keywords are suppressing matches")
        print("   - Consider lowering code-keyword distance threshold")
        print("   - Review if any keywords are being filtered out")
    
    # Save detailed results
    output_dir = Path(__file__).parent.parent / "heuristic_test_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_df = pd.DataFrame(missed_with_keywords)
    output_file = output_dir / "missed_keywords_analysis.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\nSaved detailed analysis to: {output_file}")
    
    return missed_with_keywords

def test_keyword_matching():
    """Test keyword matching logic to identify issues."""
    
    print("\n" + "="*80)
    print("TESTING KEYWORD MATCHING LOGIC")
    print("="*80)
    
    OTP_KEYWORDS = [
        "otp", "verification code", "authentication code", "your code",
        "one time password", "verification pin", "access code", "security code",
        "password code", "login code", "verification", "authenticate"
    ]
    
    test_cases = [
        ("Your OTP is 123456", ["otp"]),
        ("123456 is your OTP", ["otp"]),
        ("OTP: 123456", ["otp"]),
        ("Your verification code is 123456", ["verification code", "verification"]),
        ("Please verify with code 123456", ["verification"]),
        ("Authentication code: 123456", ["authentication code", "authenticate"]),
        ("Your login code is 123456", ["login code"]),
        ("Use code 123456 to verify", ["code"]),
        ("OTP123456", ["otp"]),  # No space
        ("Your OTPfor transaction is 123456", ["otp"]),  # No space
    ]
    
    print("\nTesting keyword detection:")
    for text, expected in test_cases:
        text_lower = text.lower()
        found = []
        
        for keyword in OTP_KEYWORDS:
            if len(keyword.split()) == 1:
                # Single word
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                if pattern.search(text):
                    found.append(keyword)
            else:
                # Phrase
                if keyword in text_lower:
                    found.append(keyword)
        
        match_status = "✓" if found else "✗"
        print(f"{match_status} Text: '{text}'")
        print(f"  Found: {found}")
        print(f"  Expected: {expected}")
        if found != expected:
            print(f"  ⚠ MISMATCH!")
        print()

def main():
    results_file = Path(__file__).parent.parent / "heuristic_test_results" / "heuristic_classification_results.csv"
    
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        return
    
    # Test keyword matching logic
    test_keyword_matching()
    
    # Investigate missed keywords
    investigate_missed_keywords(str(results_file))

if __name__ == "__main__":
    main()
