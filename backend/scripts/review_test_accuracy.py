import pandas as pd
import re
import sys

# Set UTF-8 encoding for stdout to handle Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read the test results
df = pd.read_csv('test_classifications_100_samples_deepseek.csv')

# Manual review - I'll go through each SMS and determine if it's actually an OTP
# Key indicators for OTP:
# - Contains numeric code (4-8 digits) + "OTP" word
# - Pattern: "[code] is OTP" or "Your OTP is [code]"
# - Contains verification/authentication language

# Key indicators for NOT_OTP:
# - Transaction notifications ("spent", "debited", "credited", "transaction")
# - Payment confirmations ("successful", "processed", "payment")
# - Balance updates ("Avl Limit", "Available Balance")
# - Delivery notifications
# - Due date reminders
# - General messages without OTP context

def is_actually_otp(sms_text):
    """
    Manually determine if SMS is actually an OTP based on content
    """
    sms = str(sms_text).lower()
    
    # Positive indicators - strong OTP signals
    has_otp_word = bool(re.search(r'\botp\b', sms, re.IGNORECASE))
    has_code_pattern = bool(re.search(r'\b\d{4,8}\b.*?(?:is.*?otp|otp.*?is|otp.*?for|your.*?otp)', sms, re.IGNORECASE))
    has_verification_words = bool(re.search(r'(?:verify|verification|authenticate|code|password).*?\b\d{4,8}\b', sms, re.IGNORECASE))
    
    # Negative indicators - transaction/notification patterns
    is_transaction_notification = bool(re.search(r'(?:spent|spending|transaction.*?of|debited|credited).*?(?:on|at|card|account)', sms, re.IGNORECASE))
    is_payment_confirmation = bool(re.search(r'(?:payment.*?successful|successfully.*?processed|was.*?successful|order.*?placed)', sms, re.IGNORECASE))
    is_balance_update = bool(re.search(r'(?:avl.*?limit|available.*?balance|avl.*?lmt|balance.*?is)', sms, re.IGNORECASE))
    is_due_date = bool(re.search(r'(?:is.*?due|due.*?by|payment.*?due)', sms, re.IGNORECASE))
    is_delivery_notification = bool(re.search(r'(?:delivered|delivery|arriving|shipment|order.*?delivered)', sms, re.IGNORECASE))
    is_receipt = bool(re.search(r'(?:receipt|statement.*?sent)', sms, re.IGNORECASE))
    
    # If has strong OTP indicators
    if (has_otp_word and has_code_pattern) or has_verification_words:
        return True
    
    # If has transaction keywords WITHOUT OTP word
    if (is_transaction_notification or is_payment_confirmation) and not has_otp_word:
        return False
    
    # If has balance/due/delivery indicators without OTP
    if (is_balance_update or is_due_date or is_delivery_notification or is_receipt) and not has_otp_word:
        return False
    
    # Special cases
    # Pattern: "[code] is OTP for transaction" - IS OTP
    if re.search(r'^\d{4,8}\s+is\s+otp\s+for', sms, re.IGNORECASE):
        return True
    
    # Pattern: "Your OTP is [code]" - IS OTP
    if re.search(r'your\s+otp\s+is\s+\d{4,8}', sms, re.IGNORECASE):
        return True
    
    # If it's just a short word like "yes", "no", "ok" - NOT OTP
    if sms.strip().lower() in ['yes', 'no', 'ok', 'okay', 'yeah', 'nope']:
        return False
    
    # If contains transaction amounts but no OTP context
    if re.search(r'(?:rs\.?|inr|₹)\s*\d+.*?(?:spent|debited|credited|transaction)', sms, re.IGNORECASE) and not has_otp_word:
        return False
    
    # Default: if has OTP word, likely OTP; otherwise not
    return has_otp_word

# Evaluate each SMS
results = []
for idx, row in df.iterrows():
    sms_text = row['sms_text']
    predicted_is_otp = str(row['predicted_is_otp']).lower() == 'true'
    predicted_intent = row['predicted_otp_intent']
    
    actual_is_otp = is_actually_otp(sms_text)
    
    # Check consistency: if is_otp=True but intent=NOT_OTP, that's inconsistent
    is_consistent = not (predicted_is_otp == True and predicted_intent == 'NOT_OTP')
    
    is_correct = (predicted_is_otp == actual_is_otp) and is_consistent
    
    results.append({
        'sms': sms_text[:100],
        'predicted_is_otp': predicted_is_otp,
        'predicted_intent': predicted_intent,
        'actual_is_otp': actual_is_otp,
        'is_correct': is_correct,
        'is_consistent': is_consistent,
        'error_type': None if is_correct else ('false_positive' if predicted_is_otp and not actual_is_otp else 'false_negative' if not predicted_is_otp and actual_is_otp else 'inconsistent')
    })

results_df = pd.DataFrame(results)

# Calculate metrics
total = len(results_df)
correct = results_df['is_correct'].sum()
accuracy = (correct / total) * 100

false_positives = results_df[(results_df['predicted_is_otp'] == True) & (results_df['actual_is_otp'] == False)]
false_negatives = results_df[(results_df['predicted_is_otp'] == False) & (results_df['actual_is_otp'] == True)]
inconsistent = results_df[results_df['is_consistent'] == False]

print("="*80)
print("MANUAL ACCURACY ASSESSMENT")
print("="*80)
print(f"\nTotal SMSes reviewed: {total}")
print(f"Correct: {correct}")
print(f"Accuracy: {accuracy:.2f}%")
print(f"\nFalse Positives (predicted OTP but not OTP): {len(false_positives)}")
print(f"False Negatives (predicted NOT_OTP but is OTP): {len(false_negatives)}")
print(f"Inconsistent (is_otp=True but intent=NOT_OTP): {len(inconsistent)}")

print("\n" + "="*80)
print("FALSE POSITIVES (Predicted as OTP but are NOT)")
print("="*80)
for idx, row in false_positives.head(20).iterrows():
    print(f"\n{idx+1}. {row['sms']}...")
    print(f"   Predicted: is_otp={row['predicted_is_otp']}, intent={row['predicted_intent']}")

print("\n" + "="*80)
print("FALSE NEGATIVES (Predicted as NOT_OTP but ARE OTP)")
print("="*80)
for idx, row in false_negatives.head(10).iterrows():
    print(f"\n{idx+1}. {row['sms']}...")
    print(f"   Predicted: is_otp={row['predicted_is_otp']}, intent={row['predicted_intent']}")

print("\n" + "="*80)
print("INCONSISTENT PREDICTIONS (is_otp=True but intent=NOT_OTP)")
print("="*80)
for idx, row in inconsistent.head(10).iterrows():
    print(f"\n{idx+1}. {row['sms']}...")
    print(f"   Predicted: is_otp={row['predicted_is_otp']}, intent={row['predicted_intent']}")

# Save detailed results
results_df.to_csv('test_classifications_100_samples_deepseek_reviewed.csv', index=False)
print(f"\n\nDetailed review saved to: test_classifications_100_samples_deepseek_reviewed.csv")

