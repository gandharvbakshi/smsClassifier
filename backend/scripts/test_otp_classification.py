import pandas as pd
import requests
import json
import random
import sys

# Set UTF-8 encoding for stdout to handle Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def get_few_shot_examples():
    """
    Get few-shot examples from labeled data
    """
    df = pd.read_csv('merged_standardized_partially_labeled.csv')
    labeled = df[df['otp_intent'].notna()]
    
    examples = []
    
    # Get examples for different categories
    categories_examples = {
        'BANK_OR_CARD_TXN_OTP': 2,
        'NOT_OTP': 3,  # More examples for NOT_OTP to help distinguish
        'APP_LOGIN_OTP': 1,
        'FINANCIAL_LOGIN_OTP': 1,
        'DELIVERY_OR_SERVICE_OTP': 1
    }
    
    for category, count in categories_examples.items():
        category_df = labeled[labeled['otp_intent'] == category]
        if len(category_df) > 0:
            sample = category_df.sample(n=min(count, len(category_df)), random_state=42)
            for _, row in sample.iterrows():
                sms_text = str(row['sender']) if pd.notna(row['sender']) else str(row['body'])
                is_otp_val = str(row['is_otp']).upper() if pd.notna(row['is_otp']) else 'NO'
                # Convert YES/NO to true/false for JSON
                is_otp_bool = 'true' if is_otp_val in ['YES', 'TRUE', 'True', 'true'] else 'false'
                examples.append({
                    'sms': sms_text,
                    'is_otp': is_otp_bool,
                    'otp_intent': str(row['otp_intent'])
                })
    
    return examples

def classify_otp_locally(body: str, few_shot_examples=None, model_name='deepseek-r1:8b'):
    """
    Classify an SMS message using Ollama API with few-shot examples
    """
    # Build few-shot examples string
    examples_text = ""
    if few_shot_examples:
        examples_text = "\n\nExamples:\n"
        for i, ex in enumerate(few_shot_examples, 1):
            examples_text += f"\nExample {i}:\n"
            examples_text += f'SMS: "{ex["sms"]}"\n'
            examples_text += f'Output: {{"is_otp": {ex["is_otp"]}, "otp_intent": "{ex["otp_intent"]}"}}\n'
    
    prompt = f"""You are a classifier for OTP SMS messages. Your task is to identify if an SMS contains an OTP (One-Time Password) and classify its intent.

IMPORTANT RULES:
1. An OTP is ONLY a message that contains a numeric code used for verification/authentication (e.g., "123456 is your OTP", "Your OTP is 789012")
2. Transaction notifications, balance updates, payment confirmations, and account alerts are NOT OTPs - they are NOT_OTP
3. Only classify as OTP if the message explicitly contains an OTP code and asks you to use it for verification

Label the SMS with:

- is_otp: true if the SMS contains an OTP code for verification, false otherwise
- otp_intent: one of these categories:
  * "BANK_OR_CARD_TXN_OTP" - OTP for bank/card transactions (e.g., "123456 is OTP for transaction")
  * "APP_LOGIN_OTP" - OTP for app login/verification
  * "FINANCIAL_LOGIN_OTP" - OTP for financial platform login
  * "APP_ACCOUNT_CHANGE_OTP" - OTP for account changes
  * "UPI_TXN_OR_PIN_OTP" - OTP for UPI transactions
  * "DELIVERY_OR_SERVICE_OTP" - OTP for delivery/service verification
  * "KYC_OR_ESIGN_OTP" - OTP for KYC/e-signature
  * "PROMO_OR_REWARD_OTP" - OTP for promotional/reward purposes
  * "GENERIC_APP_ACTION_OTP" - OTP for generic app actions
  * "NOT_OTP" - Not an OTP (transaction notifications, balance updates, payment confirmations, alerts, etc.){examples_text}

Now classify this SMS:
SMS: "{body}"

Respond ONLY with valid JSON object (no explanation, no markdown):
{{"is_otp": true, "otp_intent": "BANK_OR_CARD_TXN_OTP"}}""".strip()
    
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': model_name,
                'prompt': prompt,
                'stream': False
            },
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '')
        else:
            return f"Error: HTTP {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def extract_json_from_response(response_text: str):
    """
    Extract JSON from the model response, handling cases where response might have extra text
    """
    try:
        # Try to parse as-is first
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        import re
        json_match = re.search(r'\{[^{}]*"is_otp"[^{}]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object boundaries
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(response_text[start_idx:end_idx+1])
            except json.JSONDecodeError:
                pass
        
        return None

# Read the merged CSV file
print("Reading merged_standardized_partially_labeled.csv...")
df = pd.read_csv('merged_standardized_partially_labeled.csv')

# Filter rows where otp_intent is missing
missing_labels = df[df['otp_intent'].isna()].copy()
print(f"Found {len(missing_labels)} rows with missing otp_intent labels")
print(f"Selecting 100 random rows for testing...\n")

# Select 100 random rows
random.seed(42)  # For reproducibility
test_indices = random.sample(range(len(missing_labels)), min(100, len(missing_labels)))
test_rows = missing_labels.iloc[test_indices].copy()

# Load few-shot examples
print("Loading few-shot examples from labeled data...")
few_shot_examples = get_few_shot_examples()
print(f"Loaded {len(few_shot_examples)} few-shot examples")
print("\nFew-shot examples preview:")
for i, ex in enumerate(few_shot_examples[:3], 1):
    print(f"  {i}. {ex['sms'][:80]}... -> is_otp={ex['is_otp']}, otp_intent={ex['otp_intent']}")
print()

print("="*80)
print("TESTING CLASSIFICATION ON 100 RANDOM SMSes")
print("USING MODEL: deepseek-r1:8b")
print("="*80)
print()

results = []

model_name = 'deepseek-r1:8b'

for idx, (i, row) in enumerate(test_rows.iterrows(), 1):
    sms_text = str(row['sender']) if pd.notna(row['sender']) else str(row['body'])
    
    # Show full details for first 10, then just progress updates
    show_details = idx <= 10
    
    if show_details:
        print("="*80)
        print(f"TEST {idx}/100")
        print("="*80)
        print("\nSMS TEXT:")
        print("-"*80)
        print(sms_text)
        print("-"*80)
        print(f"\nCalling {model_name} model (with few-shot examples)...")
    elif idx % 10 == 0:
        print(f"\n[Progress: {idx}/100 completed - {idx}% done]")
    
    # Get classification with few-shot examples
    response = classify_otp_locally(sms_text, few_shot_examples, model_name=model_name)
    
    # Try to extract JSON
    classification = extract_json_from_response(response)
    
    if classification:
        is_otp = classification.get('is_otp', 'N/A')
        otp_intent = classification.get('otp_intent', 'N/A')
        
        if show_details:
            print("\nCLASSIFICATION RESULTS:")
            print(f"  is_otp: {is_otp}")
            print(f"  otp_intent: {otp_intent}")
            print("\n")
        
        # Store SMS text safely
        try:
            sms_stored = sms_text
        except:
            sms_stored = repr(sms_text)
        
        results.append({
            'sms': sms_stored,
            'is_otp': is_otp,
            'otp_intent': otp_intent,
            'status': 'success'
        })
    else:
        if show_details:
            print(f"\nERROR: Could not parse JSON from response")
            print(f"Raw response: {response}")
        else:
            print(f"  [ERROR on test {idx}: Could not parse JSON]")
        
        # Store SMS text safely
        try:
            sms_stored = sms_text
        except:
            sms_stored = repr(sms_text)
        
        results.append({
            'sms': sms_stored,
            'is_otp': 'ERROR',
            'otp_intent': 'ERROR',
            'status': 'failed',
            'error': response[:500] if isinstance(response, str) else str(response)
        })

# Summary
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Total tested: {len(results)}")
print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
print(f"Failed: {sum(1 for r in results if r['status'] == 'failed')}")

# Save results to CSV
print("\n" + "="*80)
print("SAVING RESULTS TO CSV")
print("="*80)

if results:
    # Create DataFrame from results
    results_df = pd.DataFrame(results)
    
    # Prepare data for CSV
    csv_data = []
    for r in results:
        csv_data.append({
            'sms_text': r['sms'],
            'predicted_is_otp': r['is_otp'],
            'predicted_otp_intent': r['otp_intent'],
            'classification_status': r['status']
        })
    
    results_csv = pd.DataFrame(csv_data)
    output_filename = 'test_classifications_100_samples_deepseek.csv'
    results_csv.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"\nResults saved to: {output_filename}")
    print(f"Total rows saved: {len(results_csv)}")
    
    # Print summary table (first 20 for display)
    print("\n" + "="*80)
    print("SUMMARY TABLE (First 20 entries - see CSV for full results)")
    print("="*80)
    
    print("\n")
    print(f"{'SMS Preview':<60} | {'is_otp':<10} | {'otp_intent':<30}")
    print("-"*110)
    
    for i, r in enumerate(results[:20], 1):
        # Truncate SMS for table display
        sms_preview = r['sms'][:55] + ('...' if len(r['sms']) > 55 else '')
        sms_preview = sms_preview.replace('\n', ' ').replace('\r', ' ')
        
        print(f"{sms_preview:<60} | {str(r['is_otp']):<10} | {str(r['otp_intent']):<30}")
    
    print(f"\n... (see {output_filename} for all {len(results)} results)")
    print("\n")

