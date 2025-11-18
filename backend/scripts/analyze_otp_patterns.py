import pandas as pd
import re
import sys

# Set UTF-8 encoding for stdout to handle Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read the labeled data
print("Reading merged_standardized_partially_labeled.csv...")
df = pd.read_csv('merged_standardized_partially_labeled.csv')

# Filter labeled data
labeled = df[df['otp_intent'].notna()]
otp_rows = labeled[labeled['is_otp'].isin(['YES', 'Yes', True, 'true', 'True'])]
not_otp_rows = labeled[labeled['is_otp'].isin(['NO', 'No', False, 'false', 'False'])]

print("\n" + "="*80)
print("ANALYSIS OF CORRECTLY LABELED OTP MESSAGES")
print("="*80)

print(f"\nTotal labeled OTP messages: {len(otp_rows)}")
print(f"Total labeled NOT_OTP messages: {len(not_otp_rows)}")

# Check for "OTP" word presence
print("\n" + "-"*80)
print("PATTERN ANALYSIS FOR OTP MESSAGES:")
print("-"*80)

patterns = {
    'contains_otp_word': 0,
    'has_4_6_digit_code': 0,
    'has_6_8_digit_code': 0,
    'has_verification_words': 0,
    'has_pin_password_code': 0
}

for idx, row in otp_rows.iterrows():
    sms = str(row['sender'])
    sms_upper = sms.upper()
    
    # Check for OTP word
    if re.search(r'\bOTP\b', sms_upper):
        patterns['contains_otp_word'] += 1
    
    # Check for 4-6 digit codes
    if re.search(r'\b\d{4,6}\b', sms):
        patterns['has_4_6_digit_code'] += 1
    
    # Check for 6-8 digit codes
    if re.search(r'\b\d{6,8}\b', sms):
        patterns['has_6_8_digit_code'] += 1
    
    # Check for verification words
    verification_words = ['VERIFY', 'VERIFICATION', 'AUTHENTICATE', 'AUTHENTICATION']
    if any(word in sms_upper for word in verification_words):
        patterns['has_verification_words'] += 1
    
    # Check for PIN/PASSWORD/CODE
    pin_words = ['PIN', 'PASSWORD', 'CODE', 'SECRET', 'DO NOT SHARE']
    if any(word in sms_upper for word in pin_words):
        patterns['has_pin_password_code'] += 1

print(f"\nTotal OTP messages analyzed: {len(otp_rows)}")
for key, val in patterns.items():
    pct = (val / len(otp_rows) * 100) if len(otp_rows) > 0 else 0
    print(f"  {key}: {val} ({pct:.1f}%)")

# Show samples of OTP messages
print("\n" + "-"*80)
print("SAMPLE OTP MESSAGES:")
print("-"*80)

for idx, row in otp_rows.head(10).iterrows():
    sms = str(row['sender'])
    print(f"\nSMS: {sms}")
    print(f"  Contains 'OTP' word: {bool(re.search(r'\bOTP\b', sms, re.IGNORECASE))}")
    print(f"  Has numeric code (4-8 digits): {bool(re.search(r'\b\d{4,8}\b', sms))}")
    print(f"  is_otp: {row['is_otp']}, otp_intent: {row['otp_intent']}")

# Check for OTP messages without "OTP" word
print("\n" + "-"*80)
print("OTP MESSAGES WITHOUT 'OTP' WORD:")
print("-"*80)

non_otp_word = otp_rows[~otp_rows['sender'].str.contains('OTP', case=False, na=False)]
print(f"\nFound {len(non_otp_word)} OTP messages without the word 'OTP'")
if len(non_otp_word) > 0:
    for idx, row in non_otp_word.head(5).iterrows():
        print(f"\n  {row['sender'][:200]}...")
        print(f"    Intent: {row['otp_intent']}")

# Analyze misclassified entries from test
print("\n" + "="*80)
print("ANALYSIS OF MISCLASSIFIED ENTRIES FROM TEST")
print("="*80)

try:
    test_df = pd.read_csv('test_classifications_100_samples.csv')
    
    # False positives - marked as OTP but should be NOT_OTP
    print("\nFalse Positives (Marked as OTP but are transaction notifications):")
    print("-"*80)
    
    false_positives = test_df[test_df['predicted_is_otp'] == 'True']
    
    # Check for common false positive patterns
    transaction_keywords = ['transaction', 'spent', 'successful', 'payment', 'debited', 'credited', 'due', 'receipt']
    
    fp_count = 0
    for idx, row in false_positives.iterrows():
        sms = str(row['sms_text']).lower()
        if any(keyword in sms for keyword in transaction_keywords):
            if 'otp' not in sms.lower():
                print(f"\n  {row['sms_text'][:200]}...")
                print(f"    Contains 'OTP' word: {'OTP' in row['sms_text'].upper()}")
                print(f"    Has numeric code: {bool(re.search(r'\\b\\d{4,8}\\b', row['sms_text']))}")
                print(f"    Predicted: is_otp={row['predicted_is_otp']}, intent={row['predicted_otp_intent']}")
                fp_count += 1
                if fp_count >= 10:
                    break
    
    print(f"\nTotal potential false positives found: {fp_count}")
    
except Exception as e:
    print(f"Could not analyze test file: {e}")

# Suggest regex patterns
print("\n" + "="*80)
print("RECOMMENDED REGEX PATTERNS FOR OTP DETECTION")
print("="*80)

print("""
Based on analysis, here are suggested regex patterns:

1. Has OTP word + numeric code:
   Pattern: (?:OTP|otp|One.?Time.?Password).*?\\b\\d{4,8}\\b
   
2. Has verification words + numeric code:
   Pattern: (?:verify|verification|code|password|pin).*?\\b\\d{4,8}\\b
   
3. Numeric code at start + OTP context:
   Pattern: ^\\b\\d{4,8}\\b.*?(?:OTP|otp|verify|verification|code)
   
4. Common OTP phrases:
   Pattern: (?:is.*?OTP|your.*?OTP|OTP.*?is|use.*?OTP|enter.*?OTP|OTP.*?for)
""")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("""
A hybrid approach might work best:
1. Use regex to catch obvious OTP patterns (high precision)
2. Use LLM for ambiguous cases (broader coverage)
3. If regex matches OTP pattern + has numeric code -> likely OTP
4. If transaction notification keywords present without OTP -> likely NOT_OTP
""")

