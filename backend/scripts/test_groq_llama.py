import os
import time
import json
import requests
import pandas as pd
from dotenv import load_dotenv


def get_few_shot_examples():
    df = pd.read_csv('merged_standardized_partially_labeled.csv')
    labeled = df[df['otp_intent'].notna()]

    examples = []
    categories_examples = {
        'BANK_OR_CARD_TXN_OTP': 2,
        'NOT_OTP': 3,
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
                is_otp_bool = 'true' if is_otp_val in ['YES', 'TRUE', 'True', 'true'] else 'false'
                examples.append({
                    'sms': sms_text,
                    'is_otp': is_otp_bool,
                    'otp_intent': str(row['otp_intent'])
                })

    return examples


def load_data():
    merged = pd.read_csv('merged_standardized_partially_labeled.csv')
    merged = merged.reset_index().rename(columns={'index': 'original_index'})
    merged['body_str'] = merged['sender'].astype(str)

    results = pd.read_csv('classification_progress_checkpoint.csv')
    classified = merged.merge(results, on='original_index', how='inner')
    classified = classified[classified['classification_status'].isin(['success', 'auto_not_otp'])]

    keyword_mask = classified['body_str'].str.contains(r'one\s*time\s*password|otp|code', case=False, na=False)
    eligible = classified[keyword_mask]

    return eligible


def prepare_prompt(sms, examples):
    examples_text = "\n\n".join([
        f"Example {i+1}:\nSMS: \"{ex['sms']}\"\nOutput: {{\"is_otp\": {ex['is_otp']}, \"otp_intent\": \"{ex['otp_intent']}\"}}"
        for i, ex in enumerate(examples)
    ])

    prompt = f"""You are a classifier for OTP SMS messages. Your task is to identify if an SMS contains an OTP (One-Time Password) and classify its intent.

IMPORTANT RULES:
1. An OTP must contain a numeric code used for verification/authentication (e.g., "123456 is your OTP", "Your OTP is 789012").
2. Transaction notifications, balance updates, payment confirmations, promotional codes, and general alerts are NOT OTPs.
3. Each OTP intent category has a specific meaning:
   - BANK_OR_CARD_TXN_OTP: OTPs for completing a financial transaction using a bank account or card.
   - DELIVERY_OR_SERVICE_OTP: OTPs used by couriers, delivery services, or service providers to confirm delivery/appointments.
   - APP_LOGIN_OTP: OTPs for logging into apps/sites (non-financial).
   - FINANCIAL_LOGIN_OTP: OTPs for logging into banks, trading platforms, or financial accounts.
   - NOT_OTP: any message without a verification OTP.
4. Only return JSON. No explanations, no markdown, no extra text.
5. Do not add additional keys or commentary. The JSON must contain only "is_otp" and "otp_intent".

EXAMPLES:

{examples_text}

Now classify this SMS:
SMS: "{sms}"

Respond ONLY with valid JSON object:
{{"is_otp": true, "otp_intent": "BANK_OR_CARD_TXN_OTP"}}"""

    return prompt


def call_groq(prompt, api_key, model_name):
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': 'You are a precise JSON-only OTP classifier.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.0,
        'max_tokens': 256,
        'response_format': {'type': 'json_object'}
    }

    if model_name == 'openai/gpt-oss-20b':
        payload['max_tokens'] = 400
        payload['top_p'] = 0.1

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def extract_json(response):
    if 'choices' in response:
        try:
            content = response['choices'][0]['message']['content']
        except (KeyError, IndexError):
            return None
    elif 'response' in response:
        content = response['response']
    else:
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start:end+1])
            except json.JSONDecodeError:
                return None
    return None


def normalize_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ['true', 'yes', '1']
    return False


def call_deepseek(prompt, api_key, model_name):
    url = 'https://api.deepseek.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model_name,
        'messages': [
            {'role': 'system', 'content': 'You are a precise JSON-only OTP classifier.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.0,
        'max_tokens': 400,
        'response_format': {'type': 'json_object'}
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def run_test(model_name, sample, examples, api_key, provider='groq'):
    print(f"\n=== Testing model: {model_name} ===")

    successes = 0
    failures = 0
    mismatches = 0
    records = []

    start_time = time.time()

    for idx, row in sample.iterrows():
        sms = row['body_str']
        prompt = prepare_prompt(sms, examples)

        try:
            if provider == 'groq':
                response = call_groq(prompt, api_key, model_name)
            else:
                response = call_deepseek(prompt, api_key, model_name)
        except Exception as e:
            failures += 1
            records.append({
                'original_index': row['original_index'],
                'model': model_name,
                'error': str(e)
            })
            continue

        parsed = extract_json(response)
        if not parsed:
            failures += 1
            records.append({
                'original_index': row['original_index'],
                'model': model_name,
                'error': 'JSON parse failed',
                'raw_response': response
            })
            continue

        predicted_is_otp = normalize_bool(parsed.get('is_otp'))
        predicted_intent = parsed.get('otp_intent', '')

        true_is_otp = normalize_bool(row['predicted_is_otp'])
        true_intent = str(row.get('predicted_otp_intent', '')).strip()

        intent_match = (true_intent == '' or predicted_intent == true_intent)
        is_match = (predicted_is_otp == true_is_otp) and intent_match

        if is_match:
            successes += 1
        else:
            mismatches += 1

        records.append({
            'original_index': row['original_index'],
            'model': model_name,
            'sms': sms[:160],
            'predicted_is_otp': predicted_is_otp,
            'predicted_otp_intent': predicted_intent,
            'true_is_otp': true_is_otp,
            'true_otp_intent': true_intent,
            'intent_match': intent_match,
            'match': is_match
        })

    duration = time.time() - start_time
    total_processed = successes + failures + mismatches

    print('--- Summary ---')
    print(f'Total processed: {total_processed}')
    print(f'Successful matches: {successes}')
    print(f'Mismatches: {mismatches}')
    print(f'Failures (API/parse): {failures}')
    accuracy = successes / total_processed if total_processed else 0
    print(f'Accuracy: {accuracy*100:.2f}%')
    print(f'Total time: {duration:.2f}s (avg {duration/max(total_processed,1):.2f}s per message)')

    if mismatches or failures:
        print('Sample issues:')
        shown = 0
        for rec in records:
            if not rec.get('match', True) or 'error' in rec:
                print(rec)
                shown += 1
            if shown >= 5:
                break


def run_deepseek_local(sample, examples):
    successes = 0
    failures = 0
    mismatches = 0
    records = []

    start_time = time.time()

    for _, row in sample.iterrows():
        sms = row['body_str']
        prompt = prepare_prompt(sms, examples)

        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={'model': 'deepseek-r1:8b', 'prompt': prompt, 'stream': False},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            failures += 1
            records.append({
                'original_index': row['original_index'],
                'model': 'deepseek-r1:8b',
                'error': str(e)
            })
            continue

        parsed = extract_json(data)
        if not parsed:
            failures += 1
            records.append({
                'original_index': row['original_index'],
                'model': 'deepseek-r1:8b',
                'error': 'JSON parse failed',
                'raw_response': data
            })
            continue

        predicted_is_otp = normalize_bool(parsed.get('is_otp'))
        predicted_intent = parsed.get('otp_intent', '')

        true_is_otp = normalize_bool(row['predicted_is_otp'])
        true_intent = str(row.get('predicted_otp_intent', '')).strip()

        intent_match = (true_intent == '' or predicted_intent == true_intent)
        is_match = (predicted_is_otp == true_is_otp) and intent_match

        if is_match:
            successes += 1
        else:
            mismatches += 1

        records.append({
            'original_index': row['original_index'],
            'model': 'deepseek-r1:8b',
            'sms': sms[:160],
            'predicted_is_otp': predicted_is_otp,
            'predicted_otp_intent': predicted_intent,
            'true_is_otp': true_is_otp,
            'true_otp_intent': true_intent,
            'intent_match': intent_match,
            'match': is_match
        })

    duration = time.time() - start_time
    total_processed = successes + failures + mismatches

    print('--- Summary ---')
    print(f'Total processed: {total_processed}')
    print(f'Successful matches: {successes}')
    print(f'Mismatches: {mismatches}')
    print(f'Failures (API/parse): {failures}')
    accuracy = successes / total_processed if total_processed else 0
    print(f'Accuracy: {accuracy*100:.2f}%')
    print(f'Total time: {duration:.2f}s (avg {duration/max(total_processed,1):.2f}s per message)')

    if mismatches or failures:
        print('Sample issues:')
        shown = 0
        for rec in records:
            if not rec.get('match', True) or 'error' in rec:
                print(rec)
                shown += 1
            if shown >= 5:
                break


def main():
    load_dotenv()
    groq_key = os.getenv('GROQ_API_KEY')
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')

    if not deepseek_key:
        print('DEEPSEEK_API_KEY not found in environment.')
        return

    eligible = load_data()
    if eligible.empty:
        print('No eligible rows found for testing.')
        return

    otp_mask = eligible['predicted_is_otp'].astype(str).str.lower() == 'true'
    eligible = eligible[otp_mask]
    if eligible.empty:
        print('No rows with confirmed OTP labels available for testing.')
        return

    sample_size = min(50, len(eligible))
    sample_size = min(20, sample_size)
    sample = eligible.sample(n=sample_size, random_state=42).reset_index(drop=True)
    few_shot_examples = get_few_shot_examples()
    print(f'Using {len(few_shot_examples)} few-shot examples')
    print(f'Sample size (true OTP rows): {sample_size}')

    if groq_key:
        run_test('llama-3.3-70b-versatile', sample, few_shot_examples, groq_key, provider='groq')
    else:
        print('GROQ_API_KEY not set; skipping llama-3.3-70b-versatile test.')

    run_deepseek_local(sample, few_shot_examples)
    run_test('deepseek-chat', sample, few_shot_examples, deepseek_key, provider='deepseek')
    run_test('deepseek-reasoner', sample, few_shot_examples, deepseek_key, provider='deepseek')


if __name__ == '__main__':
    main()

