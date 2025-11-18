import os
import json
import time
import re
from typing import List, Dict, Any

import pandas as pd
import requests
from dotenv import load_dotenv

# Configuration
BASE_DIR = os.path.dirname(__file__)
OTP_SOURCE_FILE = os.path.join(BASE_DIR, "merged_standardized_partially_labeled.csv")
PHISHING_MAPPING_FILES = {
    "balanced_spam_dataset.csv": ("text_combined", "label", {"spam"}),
    "bangla_smish.csv": ("text", "label", {"smish", "smishing", "spam"}),
    "Hindi.csv": ("message", "label", {"spam"}),
    "SMS PHISHING DATASET FOR MACHINE LEARNING AND PATTERN RECOGNITION Dataset_5971.csv": (
        "TEXT",
        "LABEL",
        {"smishing", "smish", "spam"},
    ),
}

TARGET_SAMPLE_SIZE = 100
TARGET_POSITIVE_RATIO = 0.8  # proportion of phishing positives in evaluation sample
BATCH_SIZE = 10
MODEL_PROVIDER = "groq"  # "groq" or "deepseek"
MODEL_NAME_GROQ = "llama-3.1-8b-instant"
MODEL_NAME_DEEPSEEK = "deepseek-chat"
OUTPUT_FILE = os.path.join(BASE_DIR, "llm_verification_results.csv")
SLEEP_BETWEEN_CALLS = 0.2

OTP_INTENT_LABELS = [
    "APP_LOGIN_OTP",
    "FINANCIAL_LOGIN_OTP",
    "APP_ACCOUNT_CHANGE_OTP",
    "BANK_OR_CARD_TXN_OTP",
    "UPI_TXN_OR_PIN_OTP",
    "DELIVERY_OR_SERVICE_OTP",
    "KYC_OR_ESIGN_OTP",
    "PROMO_OR_REWARD_OTP",
    "GENERIC_APP_ACTION_OTP",
    "NOT_OTP",
]


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def load_phishing_mapping() -> Dict[str, bool]:
    mapping: Dict[str, bool] = {}
    for file_name, (text_col, label_col, positive_labels) in PHISHING_MAPPING_FILES.items():
        path = os.path.join(BASE_DIR, file_name)
        if not os.path.exists(path):
            print(f"Warning: {file_name} not found; skipping.")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            print(f"Warning: could not read {file_name} ({exc}); skipping.")
            continue
        if text_col not in df.columns or label_col not in df.columns:
            print(f"Warning: {file_name} missing required columns; skipping.")
            continue
        for text, label in zip(df[text_col], df[label_col]):
            norm = normalize_text(text)
            if not norm:
                continue
            is_positive = str(label).strip().lower() in positive_labels
            if is_positive:
                mapping[norm] = True
            else:
                mapping.setdefault(norm, False)
    return mapping


def prepare_evaluation_sample(mapping: Dict[str, bool]) -> pd.DataFrame:
    if not os.path.exists(OTP_SOURCE_FILE):
        raise FileNotFoundError(f"{OTP_SOURCE_FILE} not found.")

    df = pd.read_csv(OTP_SOURCE_FILE)
    df["sms_text"] = df["body"].fillna("")
    df["sms_text_norm"] = df["sms_text"].apply(normalize_text)

    df = df[df["sms_text_norm"].notna() & df["sms_text_norm"].ne("")]
    df = df[df["sms_text_norm"].isin(mapping.keys())]

    # Ensure OTP labels present
    df = df[df["is_otp"].notna() & df["otp_intent"].notna()]

    df["is_otp_truth"] = df["is_otp"].astype(str).str.lower().isin({"true", "1", "yes"})
    df["otp_intent_truth"] = df["otp_intent"].astype(str)
    df["is_phishing_truth"] = df["sms_text_norm"].map(mapping)

    df = df[df["otp_intent_truth"].isin(OTP_INTENT_LABELS)]

    positives = df[df["is_phishing_truth"] == True]
    negatives = df[df["is_phishing_truth"] == False]

    if positives.empty or negatives.empty:
        raise ValueError("Not enough labeled positives/negatives for evaluation sample.")

    target_pos = min(len(positives), int(TARGET_SAMPLE_SIZE * TARGET_POSITIVE_RATIO))
    target_neg = min(len(negatives), TARGET_SAMPLE_SIZE - target_pos)

    if target_pos + target_neg < TARGET_SAMPLE_SIZE:
        # fill remaining from whichever pool has more data
        remaining = TARGET_SAMPLE_SIZE - (target_pos + target_neg)
        if len(positives) - target_pos > len(negatives) - target_neg:
            target_pos = min(len(positives), target_pos + remaining)
        else:
            target_neg = min(len(negatives), target_neg + remaining)

    sample_pos = positives.sample(n=target_pos, random_state=42)
    sample_neg = negatives.sample(n=target_neg, random_state=42)

    eval_df = pd.concat([sample_pos, sample_neg]).sample(frac=1, random_state=1337).reset_index(drop=True)
    eval_df["source_file"] = "merged_standardized_partially_labeled.csv"

    print(f"Prepared evaluation sample with {len(eval_df)} rows "
          f"({eval_df['is_phishing_truth'].sum()} phishing, {len(eval_df) - eval_df['is_phishing_truth'].sum()} non-phishing).")
    return eval_df


def build_batch_prompt(batch: pd.DataFrame) -> str:
    instructions = """You are an SMS classification assistant. For each message, determine:
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
- OTP must include a numeric code used for verification/authentication. Transaction alerts without codes are NOT OTP.
- Phishing involves attempts to steal information/money via suspicious links, OTP requests, urgent demands, fake rewards, etc.
- Legitimate bank/service notifications without suspicious content are not phishing.
- Respond in JSON only with a list of objects matching the format:
  {"id": "...", "is_otp": true/false, "otp_intent": "...", "is_phishing": true/false}
- Do NOT include explanations or extra keys.
"""
    messages_text = []
    for _, row in batch.iterrows():
        msg = f'{{"id": "{row["eval_id"]}", "sms": "{row["sms_text"].replace("\\\\", " ").replace(\'"\', \'\\\\"\')}"}}'
        messages_text.append(msg)
    prompt = instructions + "\nMessages:\n[" + ",\n".join(messages_text) + "]\n\nReturn a JSON array of results in the same order of IDs."
    return prompt


def call_groq(prompt: str, api_key: str) -> Any:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME_GROQ,
        "messages": [
            {"role": "system", "content": "You respond with JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content


def call_deepseek(prompt: str, api_key: str) -> Any:
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME_DEEPSEEK,
        "messages": [
            {"role": "system", "content": "You respond with JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 800,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content


def parse_json_response(content: str) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "results" in parsed:
            parsed = parsed["results"]
        if not isinstance(parsed, list):
            raise ValueError("Parsed content is not a list.")
        return parsed
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start: end + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Unable to parse JSON response: {content[:200]}...")


def evaluate_predictions(results_df: pd.DataFrame) -> None:
    metrics = {}

    metrics["is_otp_accuracy"] = (results_df["is_otp_pred"] == results_df["is_otp_truth"]).mean()
    metrics["is_phishing_accuracy"] = (results_df["is_phishing_pred"] == results_df["is_phishing_truth"]).mean()
    metrics["otp_intent_accuracy"] = (results_df["otp_intent_pred"] == results_df["otp_intent_truth"]).mean()

    print("\n=== Evaluation Summary ===")
    for key, value in metrics.items():
        print(f"{key}: {value:.2%}")

    mismatches = results_df[
        (results_df["is_otp_pred"] != results_df["is_otp_truth"])
        | (results_df["otp_intent_pred"] != results_df["otp_intent_truth"])
        | (results_df["is_phishing_pred"] != results_df["is_phishing_truth"])
    ]
    if not mismatches.empty:
        print(f"\nSample mismatches ({min(5, len(mismatches))} shown):")
        print(
            mismatches[
                [
                    "sms_text",
                    "is_otp_truth",
                    "is_otp_pred",
                    "otp_intent_truth",
                    "otp_intent_pred",
                    "is_phishing_truth",
                    "is_phishing_pred",
                ]
            ]
            .head(5)
            .to_string(index=False)
        )


def main():
    load_dotenv()

    if MODEL_PROVIDER.lower() == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set.")
    elif MODEL_PROVIDER.lower() == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise EnvironmentError("DEEPSEEK_API_KEY not set.")
    else:
        raise ValueError("MODEL_PROVIDER must be 'groq' or 'deepseek'.")

    mapping = load_phishing_mapping()
    eval_df = prepare_evaluation_sample(mapping)
    eval_df = eval_df.reset_index(drop=True)
    eval_df["eval_id"] = eval_df.index.astype(str)

    results: List[Dict[str, Any]] = []
    start_time = time.time()

    for batch_start in range(0, len(eval_df), BATCH_SIZE):
        batch = eval_df.iloc[batch_start: batch_start + BATCH_SIZE]
        prompt = build_batch_prompt(batch)

        try:
            if MODEL_PROVIDER.lower() == "groq":
                raw_content = call_groq(prompt, api_key)
            else:
                raw_content = call_deepseek(prompt, api_key)
            parsed = parse_json_response(raw_content)
        except Exception as exc:
            print(f"Error processing batch starting at index {batch_start}: {exc}")
            continue

        for item in parsed:
            results.append(
                {
                    "eval_id": item.get("id"),
                    "is_otp_pred": bool(item.get("is_otp")) if item.get("is_otp") is not None else None,
                    "otp_intent_pred": item.get("otp_intent"),
                    "is_phishing_pred": bool(item.get("is_phishing")) if item.get("is_phishing") is not None else None,
                }
            )

        time.sleep(SLEEP_BETWEEN_CALLS)

    if not results:
        print("No results obtained from the model.")
        return

    results_df = pd.DataFrame(results)
    merged = eval_df.merge(results_df, on="eval_id", how="left")

    merged.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nWrote detailed results to {OUTPUT_FILE}")

    evaluate_predictions(merged)
    elapsed = time.time() - start_time
    print(f"Total elapsed time: {elapsed:.1f}s ({elapsed / len(eval_df):.2f}s per message)")


if __name__ == "__main__":
    main()

