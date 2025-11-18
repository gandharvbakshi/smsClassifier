import json
import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

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

    categories_examples = {
        'BANK_OR_CARD_TXN_OTP': 2,
        'NOT_OTP': 3,
        'APP_LOGIN_OTP': 1,
        'FINANCIAL_LOGIN_OTP': 1,
        'DELIVERY_OR_SERVICE_OTP': 1,
        'UPI_TXN_OR_PIN_OTP': 1,
        'GENERIC_APP_ACTION_OTP': 1,
        'KYC_OR_ESIGN_OTP': 1
    }

    for category, count in categories_examples.items():
        category_df = labeled[labeled['otp_intent'] == category]
        if len(category_df) > 0:
            sample = category_df.sample(n=min(count, len(category_df)), random_state=42)
            for _, row in sample.iterrows():
                sms_text = str(row['sender']) if pd.notna(row['sender']) else str(row['body'])
                is_otp_val = str(row['is_otp']).upper() if pd.notna(row['is_otp']) else 'NO'
                is_otp_bool = 'true' if is_otp_val in ['YES', 'TRUE', 'True', 'true'] else 'false'
                examples.append({
                    'sms': sms_text,
                    'is_otp': is_otp_bool,
                    'otp_intent': str(row['otp_intent'])
                })

    return examples

def normalize_text(text):
    if pd.isna(text):
        return ''
    return re.sub(r'\s+', ' ', str(text)).strip().lower()

def get_phishing_mapping():
    mapping = {}

    def update_mapping(texts, labels, positive_labels):
        for text, label in zip(texts, labels):
            norm = normalize_text(text)
            if not norm:
                continue
            label_norm = str(label).strip().lower()
            if label_norm in positive_labels:
                mapping[norm] = True
            else:
                mapping.setdefault(norm, False)

    try:
        df_balanced = pd.read_csv('balanced_spam_dataset.csv')
        update_mapping(df_balanced['text_combined'], df_balanced['label'], {'spam'})
    except Exception as e:
        print(f"Warning: Could not read balanced_spam_dataset.csv ({e})")

    try:
        df_bangla = pd.read_csv('bangla_smish.csv')
        update_mapping(df_bangla['text'], df_bangla['label'], {'smish', 'smishing', 'spam'})
    except Exception as e:
        print(f"Warning: Could not read bangla_smish.csv ({e})")

    try:
        df_hindi = pd.read_csv('Hindi.csv')
        update_mapping(df_hindi['message'], df_hindi['label'], {'spam'})
    except Exception as e:
        print(f"Warning: Could not read Hindi.csv ({e})")

    try:
        df_sms = pd.read_csv('SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv')
        update_mapping(df_sms['TEXT'], df_sms['LABEL'], {'smishing', 'smish', 'spam'})
    except Exception as e:
        print(f"Warning: Could not read SMS PHISHING dataset ({e})")

    return mapping

def build_batch_prompt(chunk_rows, otp_examples, phishing_examples):
    otp_examples_text = "\n\n".join([
        f"OTP Example {i + 1}:\nSMS: \"{ex['sms']}\"\nOutput: {{\"is_otp\": {ex['is_otp']}, \"otp_intent\": \"{ex['otp_intent']}\"}}"
        for i, ex in enumerate(otp_examples)
    ])

    phishing_examples_text = "\n\n".join([
        f"Phishing Example {i + 1}:\nSMS: \"{ex['sms']}\"\nOutput: {{\"is_phishing\": {str(ex['is_phishing']).lower()} }}"
        for i, ex in enumerate(phishing_examples)
    ])

    instructions = f"""You are an SMS classification assistant. For each message, determine:
1. is_otp (true/false)
2. otp_intent (choose one from the allowed list)
3. is_phishing (true/false)

OTP intent options:
- APP_LOGIN_OTP
- FINANCIAL_LOGIN_OTP
- APP_ACCOUNT_CHANGE_OTP
- BANK_OR_CARD_TXN_OTP
- UPI_TXN_OR_PIN_OTP
- DELIVERY_OR_SERVICE_OTP
- KYC_OR_ESIGN_OTP
- PROMO_OR_REWARD_OTP
- GENERIC_APP_ACTION_OTP
- NOT_OTP

Guidelines:
- OTP requires a numeric verification code. Alerts without codes are NOT OTP.
- Distinguish OTP intents carefully:
  * BANK_OR_CARD_TXN_OTP: numeric code for card/bank transaction authorisation.
  * APP_LOGIN_OTP: OTP for logging into a consumer/non-financial app.
  * FINANCIAL_LOGIN_OTP: OTP for logging into banks, trading, lending, or wallet platforms.
  * APP_ACCOUNT_CHANGE_OTP: OTP for account/profile changes like password reset.
  * UPI_TXN_OR_PIN_OTP: OTP for UPI transfers, PIN setup, or UPI device binding.
  * DELIVERY_OR_SERVICE_OTP: code handed to courier/service staff to confirm delivery/visit.
  * PROMO_OR_REWARD_OTP: codes tied to offers, rewards, promos, or contests.
  * KYC_OR_ESIGN_OTP: identity verification, e-signature, or KYC compliance.
  * GENERIC_APP_ACTION_OTP: miscellaneous in-app actions not covered above.
- Phishing (true) looks for suspicious links, unknown phone numbers, urgent credential/OTP requests, or unrealistic rewards.
- Not phishing (false) covers routine alerts, benign OTP reminders with clear safety warnings, or personal/conversational texts without malicious intent.
- Respond ONLY with JSON: an array of objects with keys id, is_otp, otp_intent, is_phishing.
- Do not include explanations or extra keys anywhere.

Few-shot OTP guidance:

{otp_examples_text}

Few-shot phishing guidance:

{phishing_examples_text}
"""

    messages = []
    for row in chunk_rows:
        sms_clean = row["sms_text"].replace("\\", " ").replace('"', '\\"')
        messages.append(f'{{"id": "{row["row_id"]}", "sms": "{sms_clean}"}}')

    prompt = instructions + "\nMessages:\n[" + ",\n".join(messages) + "]\n\nReturn a JSON array in the same ID order."
    return prompt

def extract_json_from_content(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(content[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                return None
    return None


def call_groq_llama(prompt: str, api_key: str):
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'llama-3.3-70b-versatile',
        'messages': [
            {'role': 'system', 'content': 'You are a precise JSON-only OTP classifier.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.0,
        'max_tokens': 800
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get('choices', [{}])[0].get('message', {}).get('content', '')

def load_progress():
    """Load existing progress from checkpoint file"""
    checkpoint_file = 'classification_progress_checkpoint.csv'
    if os.path.exists(checkpoint_file):
        try:
            df = pd.read_csv(checkpoint_file)
            processed_indices = set(df['original_index'].values)
            return processed_indices, df
        except:
            return set(), pd.DataFrame()
    return set(), pd.DataFrame()

def save_progress(results_df, checkpoint_file='classification_progress_checkpoint.csv'):
    """Save progress to checkpoint file"""
    results_df.to_csv(checkpoint_file, index=False, encoding='utf-8-sig')

BATCH_SIZE = 500
PROMPT_CHUNK_SIZE = 10
MAX_ROWS_PER_RUN = 40000
MAX_RETRIES_PER_CHUNK = 3
VERIFICATION_BADGE_LLM = 'VERIFIED_llama-3.3-70b-versatile'
VERIFICATION_BADGE_HEURISTIC = 'HEURISTIC_AUTO_NOT_OTP'

def main():
    load_dotenv()
    print("="*80)
    print("PHASE 2: FULL DATASET CLASSIFICATION")
    print("Model: llama-3.3-70b-versatile (Groq)")
    print(f"Batch size (rows per checkpoint save): {BATCH_SIZE}")
    print(f"Requests per prompt: {PROMPT_CHUNK_SIZE} messages")
    print(f"Maximum rows per run: {MAX_ROWS_PER_RUN}")
    print(f"Retry attempts per chunk: {MAX_RETRIES_PER_CHUNK}")
    print("="*80)
    
    # Read the merged CSV file
    print("\nReading merged_standardized_partially_labeled.csv...")
    df = pd.read_csv('merged_standardized_partially_labeled.csv')
    
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        print("GROQ_API_KEY not set in environment. Cannot proceed.")
        return

    # Filter rows where otp_intent is missing
    missing_labels = df[df['otp_intent'].isna()].copy()
    total_unlabeled_initial = len(missing_labels)
    print(f"Found {total_unlabeled_initial} rows with missing otp_intent labels")
    
    # Load progress
    processed_indices, existing_results = load_progress()
    processed_prev_count = len(existing_results)
    if len(processed_indices) > 0:
        print(f"Found existing progress: {processed_prev_count} rows already processed")
        missing_labels = missing_labels[~missing_labels.index.isin(processed_indices)]
        remaining_rows = len(missing_labels)
        print(f"Remaining rows to process: {remaining_rows}")
    else:
        remaining_rows = len(missing_labels)
    
    if remaining_rows == 0:
        print("\nAll rows have been processed!")
        return

    rows_to_process = min(remaining_rows, MAX_ROWS_PER_RUN)
    if rows_to_process < remaining_rows:
        print(f"\nLimiting this run to {rows_to_process} rows out of {remaining_rows} pending")
    else:
        print("\nProcessing all remaining rows in this run")
    
    missing_labels_to_process = missing_labels.iloc[:rows_to_process].copy()
    
    # Load few-shot examples
    print("\nLoading few-shot examples...")
    few_shot_examples = get_few_shot_examples()
    print(f"Loaded {len(few_shot_examples)} few-shot examples")
    phishing_map = get_phishing_mapping()
    print(f"Loaded phishing labels for {len(phishing_map)} messages")

    phishing_examples = [
        {
            'sms': 'Claim your reward now! Click http://fake-bank-login.com and enter your password within 1 hour to avoid penalties.',
            'is_phishing': True
        },
        {
            'sms': 'Your account will be blocked today. Call 9876543210 and share your OTP immediately.',
            'is_phishing': True
        },
        {
            'sms': 'HDFC Bank: Rs.450.00 debited from A/C XX1234 on 14-Feb. Avl bal Rs. 23,981. Never share OTP with anyone.',
            'is_phishing': False
        },
        {
            'sms': 'BlueDart: Package out for delivery today. Driver will call upon arrival. No action required.',
            'is_phishing': False
        }
    ]
    
    # Configuration
    output_file = 'classification_results_with_phishing.csv'
    checkpoint_file = 'classification_progress_checkpoint.csv'
    
    # Calculate batches
    total_rows = len(missing_labels_to_process)
    total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE
    overall_pending_before = total_unlabeled_initial - processed_prev_count
    
    print(f"\nProcessing configuration:")
    print(f"  Rows to process this run: {total_rows:,}")
    print(f"  Batch size: {BATCH_SIZE:,}")
    print(f"  Total batches this run: {total_batches}")
    print(f"  Already classified overall: {processed_prev_count:,}")
    print(f"  Pending overall before this run: {overall_pending_before:,}")
    print(f"  Progress checkpoint: {checkpoint_file}")
    print(f"  Final output: {output_file}")
    
    # Initialize results
    all_results = existing_results.copy()
    if not all_results.empty and 'is_phishing' not in all_results.columns:
        if 'sms_text' in all_results.columns:
            all_results['is_phishing'] = all_results['sms_text'].apply(lambda x: phishing_map.get(normalize_text(x), False))
        else:
            all_results['is_phishing'] = False
    if 'verification_badge' not in all_results.columns:
        all_results['verification_badge'] = None
    
    # Process in batches
    start_time = time.time()
    
    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min((batch_num + 1) * BATCH_SIZE, total_rows)
        batch_df = missing_labels_to_process.iloc[batch_start:batch_end].copy()
        
        print("\n" + "="*80)
        print(f"BATCH {batch_num + 1}/{total_batches}")
        print(f"Processing rows {batch_start + 1:,} to {batch_end:,} ({len(batch_df)} rows)")
        print("="*80)
        
        batch_results = []
        batch_start_time = time.time()
        
        progress_interval = max(1, len(batch_df) // 5)
        keyword_pattern = re.compile(r"one\s*time\s*password|otp|code", re.IGNORECASE)
        current_chunk = []
        chunk_lookup = {}

        def flush_chunk():
            nonlocal current_chunk, chunk_lookup, batch_results
            if not current_chunk:
                return
            for attempt in range(1, MAX_RETRIES_PER_CHUNK + 1):
                prompt = build_batch_prompt(current_chunk, few_shot_examples, phishing_examples)
                try:
                    response_text = call_groq_llama(prompt, groq_api_key)
                    parsed = extract_json_from_content(response_text)
                    if isinstance(parsed, list) and len(parsed) == len(current_chunk):
                    if isinstance(parsed, dict):
                        if 'results' in parsed and isinstance(parsed['results'], list):
                            parsed = parsed['results']
                        elif 'data' in parsed and isinstance(parsed['data'], list):
                            parsed = parsed['data']
                    if not isinstance(parsed, list):
                        raise ValueError("Parsed response did not return a list")

                    for item in parsed:
                            row_id = item.get('id')
                            linked = chunk_lookup.get(row_id)
                            if not linked:
                                continue
                            phishing_value = item.get('is_phishing')
                            if phishing_value is None:
                                phishing_value = linked['mapped_phish']
                            batch_results.append({
                                'original_index': linked['original_index'],
                                'sms_text': linked['sms_text'],
                                'predicted_is_otp': item.get('is_otp'),
                                'predicted_otp_intent': item.get('otp_intent'),
                                'classification_status': 'success',
                                'is_phishing': phishing_value,
                                'batch_number': batch_num + 1,
                                'verification_badge': VERIFICATION_BADGE_LLM
                            })
                        current_chunk = []
                        chunk_lookup = {}
                        return
                    else:
                        raise ValueError("Parsed response size mismatch or invalid format")
                except Exception as e:
                    if attempt < MAX_RETRIES_PER_CHUNK:
                        print(f"    Chunk attempt {attempt} failed ({e}). Retrying...")
                        time.sleep(0.5)
                        continue
                    else:
                        print(f"    Chunk attempt {attempt} failed ({e}). Marking rows as failed.")
                        for row in current_chunk:
                            batch_results.append({
                                'original_index': row['original_index'],
                                'sms_text': row['sms_text'],
                                'predicted_is_otp': 'ERROR',
                                'predicted_otp_intent': 'ERROR',
                                'classification_status': 'failed',
                                'is_phishing': phishing_map.get(normalize_text(row['sms_text']), False),
                                'batch_number': batch_num + 1,
                                'verification_badge': None
                            })
                        current_chunk = []
                        chunk_lookup = {}
                        return

        for idx, (original_idx, row) in enumerate(batch_df.iterrows(), 1):
            sms_text = str(row['sender']) if pd.notna(row['sender']) else str(row['body'])

            if idx % progress_interval == 0 or idx == len(batch_df):
                elapsed = time.time() - batch_start_time
                rate = idx / elapsed if elapsed > 0 else 0
                remaining_in_batch = len(batch_df) - idx
                eta_seconds = remaining_in_batch / rate if rate > 0 else 0
                print(f"  Progress: {idx}/{len(batch_df)} ({idx/len(batch_df)*100:.1f}%) | "
                      f"Rate: {rate:.2f} rows/sec | ETA: {eta_seconds:.0f}s")

            normalized_text = normalize_text(sms_text)
            mapped_phish = phishing_map.get(normalized_text, False)

            if not keyword_pattern.search(sms_text or ""):
                batch_results.append({
                    'original_index': original_idx,
                    'sms_text': sms_text,
                    'predicted_is_otp': False,
                    'predicted_otp_intent': 'NOT_OTP',
                    'classification_status': 'auto_not_otp',
                    'is_phishing': mapped_phish,
                    'batch_number': batch_num + 1,
                    'verification_badge': VERIFICATION_BADGE_HEURISTIC
                })
                continue

            row_id = f"{original_idx}"
            chunk_lookup[row_id] = {
                'original_index': original_idx,
                'sms_text': sms_text,
                'mapped_phish': mapped_phish
            }
            current_chunk.append({
                'row_id': row_id,
                'sms_text': sms_text
            })

            if len(current_chunk) >= PROMPT_CHUNK_SIZE:
                flush_chunk()

        flush_chunk()
        
        # Convert batch results to DataFrame
        batch_results_df = pd.DataFrame(batch_results)
        
        # Append to all results
        if len(all_results) == 0:
            all_results = batch_results_df
        else:
            all_results = pd.concat([all_results, batch_results_df], ignore_index=True)
        
        # Save checkpoint after each batch
        save_progress(all_results, checkpoint_file)
        
        # Calculate statistics
        batch_time = time.time() - batch_start_time
        total_time = time.time() - start_time
        avg_time_per_row = batch_time / len(batch_df)
        rows_per_second = len(batch_df) / batch_time
        processed_in_run = batch_end
        processed_overall = processed_prev_count + processed_in_run
        overall_pending = max(total_unlabeled_initial - processed_overall, 0)
        remaining_in_run = total_rows - batch_end
        estimated_remaining_time = (remaining_in_run / rows_per_second) if rows_per_second > 0 else 0
        
        print(f"\nBatch {batch_num + 1} completed:")
        print(f"  Time: {batch_time:.1f}s ({avg_time_per_row:.2f}s per row, {rows_per_second:.2f} rows/sec)")
        print(f"  Successful: {len(batch_results_df[batch_results_df['classification_status'] == 'success'])}")
        print(f"  Failed: {len(batch_results_df[batch_results_df['classification_status'] == 'failed'])}")
        print(f"\nProgress summary:")
        print(f"  This run processed: {processed_in_run:,} / {total_rows:,} ({processed_in_run/total_rows*100:.1f}%)")
        print(f"  Overall processed: {processed_overall:,} / {total_unlabeled_initial:,}")
        print(f"  Overall pending: {overall_pending:,}")
        print(f"  Total time elapsed this run: {total_time/60:.1f} minutes")
        print(f"  Estimated remaining this run: {estimated_remaining_time/60:.1f} minutes")
        print(f"  Checkpoint saved to: {checkpoint_file}")
    
    # Final save
    print("\n" + "="*80)
    print("CLASSIFICATION COMPLETE!")
    print("="*80)
    
    all_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nFinal results saved to: {output_file}")
    total_processed_overall = len(all_results)
    overall_pending_after = max(total_unlabeled_initial - total_processed_overall, 0)
    print(f"Rows processed in this run: {total_rows:,}")
    print(f"Total rows classified overall: {total_processed_overall:,}")
    print(f"Successful (overall): {len(all_results[all_results['classification_status'] == 'success']):,}")
    print(f"Failed (overall): {len(all_results[all_results['classification_status'] == 'failed']):,}")
    print(f"Rows pending overall: {overall_pending_after:,}")
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print("\nPredicted is_otp distribution:")
    print(all_results['predicted_is_otp'].value_counts())
    print("\nPredicted otp_intent distribution:")
    print(all_results['predicted_otp_intent'].value_counts(dropna=False))
    print("\nPhishing flag distribution:")
    print(all_results['is_phishing'].value_counts(dropna=False))

if __name__ == "__main__":
    main()

