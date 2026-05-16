import os
import re
import time
import json
import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
INPUT_FILE = os.path.join(BASE_DIR, "classification_results_with_phishing.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "classification_results_with_phishing_llm.csv")
MAX_RETRIES = 3
SLEEP_BETWEEN_CALLS = 0.2

RAW_DATASETS = {
    "balanced_spam_dataset.csv": ("text_combined", "label", {"spam"}),
    "bangla_smish.csv": ("text", "label", {"smish", "smishing", "spam"}),
    "Hindi.csv": ("message", "label", {"spam"}),
    "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv": ("TEXT", "LABEL", {"smishing", "smish", "spam"})
}
FEW_SHOT_POS = 4
FEW_SHOT_NEG = 4


def normalize_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def build_mapping():
    mapping = {}
    for file_name, (text_col, label_col, positives) in RAW_DATASETS.items():
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if text_col not in df.columns or label_col not in df.columns:
            continue
        for text, label in zip(df[text_col], df[label_col]):
            norm = normalize_text(text)
            if not norm:
                continue
            label_norm = str(label).strip().lower()
            if label_norm in positives:
                mapping[norm] = True
            else:
                mapping.setdefault(norm, False)
    return mapping


def select_few_shot_examples(mapping, exclude_texts):
    remaining = {k: v for k, v in mapping.items() if k not in exclude_texts}
    pos_examples = [k for k, v in remaining.items() if v]
    neg_examples = [k for k, v in remaining.items() if not v]

    few_shot = []
    for texts, label, count, seed in [
        (pos_examples, True, FEW_SHOT_POS, 123),
        (neg_examples, False, FEW_SHOT_NEG, 456)
    ]:
        if not texts:
            continue
        df = pd.DataFrame({"sms": texts})
        sample = df.sample(n=min(count, len(df)), random_state=seed)
        few_shot.extend({"sms": row.sms, "is_phishing": label} for row in sample.itertuples())

    few_shot.extend([
        {"sms": "Dear customer, your account has been suspended. Click http://secure-bank-login.com to verify now or your funds will be frozen.", "is_phishing": True},
        {"sms": "Congratulations! You have won Rs.50000. Reply YES with your bank details to claim your reward immediately.", "is_phishing": True},
        {"sms": "Your OTP is 456987. Do not share this OTP with anyone. - ICICI Bank", "is_phishing": False},
        {"sms": "Dear Customer, Rs. 2,345.50 has been debited from account XX1234 on 12-05-24. If not you, call the number on the back of your card.", "is_phishing": False}
    ])
    return few_shot


def build_prompt(sms: str, examples):
    example_text = "\n\n".join(
        f"Example {i+1}:\nSMS: \"{ex['sms']}\"\nOutput: {{\"is_phishing\": {str(ex['is_phishing']).lower()}}}"
        for i, ex in enumerate(examples)
    )
    prompt = f"""You are an SMS phishing detector. Decide if a message is phishing (true/false) and respond in JSON only.

Definitions:
- phishing (true): messages that try to steal information or money, urge the user to click suspicious links, share OTPs, call unknown numbers, or promise fake rewards.
- not phishing (false): routine bank alerts, OTP notices that explicitly warn \"do not share\", delivery updates, personal or conversational texts without suspicious elements.

High-risk indicators:
• URLs or domains (http://, https://, www., .com, .in, etc.)
• Requests to click, login, verify, update, activate, reply, call, share OTP, send details, or contact unknown numbers.
• Promises of rewards, winnings, lotteries, cashback, bonuses, free offers.

Safe indicators:
• Simple OTP alerts that say \"do not share\".
• Standard transaction/balance notifications from known banks without links or urgent commands.
• Personal reminders or informational messages.

Respond ONLY with JSON {{\"is_phishing\": true}} or {{\"is_phishing\": false}}.

{example_text}

Classify this SMS:
SMS: \"{sms}\"

Respond ONLY with JSON containing the single key \"is_phishing\".
"""
    return prompt


def call_groq(prompt, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a precise JSON-only classifier."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 200,
        "response_format": {"type": "json_object"}
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start:end+1])
            except json.JSONDecodeError:
                return None
    return None


def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set. Aborting.")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} not found. Run add_phishing_labels.py first.")
        return

    print("Loading classification results...")
    df = pd.read_csv(INPUT_FILE)
    if "sms_text" not in df.columns or "is_phishing" not in df.columns:
        print("Missing required columns in classification results.")
        return

    unresolved_mask = df["is_phishing"].isna()
    unresolved = df[unresolved_mask].copy()
    if unresolved.empty:
        print("No rows with unlabeled phishing status. Nothing to do.")
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        return

    total_unlabeled = len(unresolved)
    print(f"Unlabeled rows to process: {total_unlabeled}.")

    mapping = build_mapping()
    few_shot_examples = select_few_shot_examples(mapping, {normalize_text(t) for t in unresolved["sms_text"]})
    print(f"Few-shot examples prepared: {len(few_shot_examples)}")

    start_time = time.time()
    for idx, (row_index, row) in enumerate(unresolved.iterrows(), 1):
        sms = row["sms_text"]
        prompt = build_prompt(sms, few_shot_examples)
        classification = None
        error_msg = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                classification = call_groq(prompt, api_key)
            except Exception as e:
                classification = None
                error_msg = str(e)
            if classification and "is_phishing" in classification:
                break
            if attempt < MAX_RETRIES:
                time.sleep(0.2)
            else:
                print(f"Failed to classify row {row_index}: {error_msg or 'Unknown error'}")
        if classification and "is_phishing" in classification:
            df.at[row_index, "is_phishing"] = bool(classification["is_phishing"])
        time.sleep(0.2)
        if idx % 100 == 0:
            elapsed = time.time() - start_time
            print(f"Processed {idx} messages. Elapsed {elapsed:.1f}s")

    print(f"Writing updated file to {OUTPUT_FILE} ...")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print("Done.")

if __name__ == "__main__":
    main()

