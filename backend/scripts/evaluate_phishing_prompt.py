import os
import re
import json
import time
import pandas as pd
import requests
from collections import Counter
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
RAW_DATASETS = {
    "balanced_spam_dataset.csv": ("text_combined", "label", {"spam"}),
    "bangla_smish.csv": ("text", "label", {"smish", "smishing", "spam"}),
    "Hindi.csv": ("message", "label", {"spam"}),
    "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv":
        ("TEXT", "LABEL", {"smishing", "smish", "spam"})
}
SAMPLE_POSITIVE = 80
SAMPLE_NEGATIVE = 20
FEW_SHOT_POS = 4
FEW_SHOT_NEG = 4
MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile"
]


def normalize_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def build_dataset():
    rows = []
    for file_name, (text_col, label_col, positives) in RAW_DATASETS.items():
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            print(f"Warning: {file_name} not found. Skipping.")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"Warning: Could not read {file_name} ({e}). Skipping.")
            continue
        if text_col not in df.columns or label_col not in df.columns:
            print(f"Warning: {file_name} missing columns. Skipping.")
            continue
        for text, label in zip(df[text_col], df[label_col]):
            norm_text = normalize_text(text)
            if not norm_text:
                continue
            is_phish = str(label).strip().lower() in positives
            rows.append({"sms": norm_text, "is_phishing": is_phish, "source": file_name})
    dataset = pd.DataFrame(rows).drop_duplicates("sms")
    return dataset


def select_few_shot_examples(df, exclude_texts):
    filtered = df[~df["sms"].isin(exclude_texts)]
    pos_pool = filtered[filtered["is_phishing"]]
    neg_pool = filtered[~filtered["is_phishing"]]
    positives = pos_pool.sample(n=FEW_SHOT_POS, random_state=123, replace=len(pos_pool) < FEW_SHOT_POS)
    negatives = neg_pool.sample(n=FEW_SHOT_NEG, random_state=456, replace=len(neg_pool) < FEW_SHOT_NEG)
    few_shot = pd.concat([positives, negatives])
    examples = [{"sms": row["sms"], "is_phishing": row["is_phishing"]} for _, row in few_shot.iterrows()]
    examples.extend([
        {"sms": "Dear customer, your account has been suspended. Click http://secure-bank-login.com to verify now or your funds will be frozen.", "is_phishing": True},
        {"sms": "Congratulations! You have won Rs.50000. Reply YES with your bank details to claim your reward immediately.", "is_phishing": True},
        {"sms": "Your OTP is 456987. Do not share this OTP with anyone. - ICICI Bank", "is_phishing": False},
        {"sms": "Dear Customer, Rs. 2,345.50 has been debited from account XX1234 on 12-05-24. If not you, call the number on the back of your card.", "is_phishing": False}
    ])
    return examples


def build_prompt(sms, examples):
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


def call_groq(prompt, api_key, model_name):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
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
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


def evaluate_predictions(results):
    total = len(results)
    mismatches = sum(1 for r in results if r["predicted"] != r["truth"])
    accuracy = (total - mismatches) / total if total else 0
    counts = Counter((r["truth"], r["predicted"]) for r in results)
    return accuracy, mismatches, counts


def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set. Aborting.")
        return

    print("Building labeled dataset from raw sources...")
    dataset = build_dataset()
    if dataset.empty:
        print("No labeled data available. Aborting.")
        return

    positives = dataset[dataset["is_phishing"]]
    negatives = dataset[~dataset["is_phishing"]]
    if len(positives) < SAMPLE_POSITIVE or len(negatives) < SAMPLE_NEGATIVE:
        print("Not enough labeled examples to perform the evaluation with desired split.")
        return

    sample_pos = positives.sample(n=SAMPLE_POSITIVE, random_state=99)
    sample_neg = negatives.sample(n=SAMPLE_NEGATIVE, random_state=99)
    eval_df = pd.concat([sample_pos, sample_neg]).reset_index(drop=True)
    few_shot_examples = select_few_shot_examples(dataset, set(eval_df["sms"]))

    print(f"Evaluating {len(eval_df)} messages: {SAMPLE_POSITIVE} phishing, {SAMPLE_NEGATIVE} non-phishing.")

    for model_name in MODELS:
        print(f"\n=== Testing model: {model_name} ===")
        results = []
        start_time = time.time()
        for _, row in eval_df.iterrows():
            prompt = build_prompt(row["sms"], few_shot_examples)
            classification = call_groq(prompt, api_key, model_name)
            predicted = bool(classification["is_phishing"]) if classification and "is_phishing" in classification else None
            results.append({
                "sms": row["sms"],
                "truth": row["is_phishing"],
                "predicted": predicted
            })
            time.sleep(0.2 if model_name != "llama-3.3-70b-versatile" else 0.3)

        accuracy, mismatches, counts = evaluate_predictions(results)
        elapsed = time.time() - start_time

        print("Evaluation complete.")
        print(f"Accuracy: {accuracy*100:.2f}%")
        print(f"Mismatches: {mismatches}/{len(results)}")
        print("Confusion counts (truth, predicted):", counts)
        print(f"Elapsed time: {elapsed:.1f}s (avg {elapsed/len(results):.2f}s per message)")

        mismatched_examples = [r for r in results if r["predicted"] != r["truth"]]
        if mismatched_examples:
            print("Sample mismatches:")
            for r in mismatched_examples[:5]:
                print(f"- Truth: {r['truth']}, Predicted: {r['predicted']}, SMS: {r['sms'][:120]}")

if __name__ == "__main__":
    main()

