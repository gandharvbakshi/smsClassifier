import os
import json
import time
import re
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
OTP_SOURCE_FILE = os.path.join(BASE_DIR, "merged_standardized_partially_labeled.csv")
GROUND_TRUTH_OUTPUT = os.path.join(BASE_DIR, "ground_truth_eval_sample_200.csv")
PHISHING_SAMPLE_FILE = os.path.join(BASE_DIR, "eval_sample_is_phishing_100.csv")
OTP_SAMPLE_FILE = os.path.join(BASE_DIR, "eval_sample_otp_intent_100.csv")
BENCHMARK_SUMMARY_OUTPUT = os.path.join(BASE_DIR, "benchmark_llm_accuracy_summary.csv")

BATCH_SIZE = 10
SMOKE_TEST_ROWS = 10
SLEEP_BETWEEN_CALLS = 0.25

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

MODEL_CONFIGS = [
    {"name": "llama-3.1-8b-instant", "provider": "groq", "model_id": "llama-3.1-8b-instant"},
    {"name": "llama-3.3-70b-versatile", "provider": "groq", "model_id": "llama-3.3-70b-versatile"},
    {"name": "deepseek-chat", "provider": "deepseek", "model_id": "deepseek-chat"},
    {"name": "gemini-2.5-flash-lite", "provider": "google", "model_id": "gemini-2.5-flash-lite"},
    {"name": "gemini-2.5-flash", "provider": "google", "model_id": "gemini-2.5-flash"},
    {"name": "gpt-4o-mini", "provider": "openai", "model_id": "gpt-4o-mini"},
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
            is_positive = str(label).strip().lower() in positive_labels
            if is_positive:
                mapping[norm] = True
            else:
                mapping.setdefault(norm, False)
    return mapping


def parse_bool(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    value_str = str(value).strip().lower()
    if value_str in {"true", "yes", "1"}:
        return True
    if value_str in {"false", "no", "0"}:
        return False
    return pd.NA


def build_ground_truth_sample() -> pd.DataFrame:
    if not os.path.exists(PHISHING_SAMPLE_FILE):
        raise FileNotFoundError(
            f"{PHISHING_SAMPLE_FILE} not found. Run prepare_eval_samples.py first."
        )
    if not os.path.exists(OTP_SAMPLE_FILE):
        raise FileNotFoundError(
            f"{OTP_SAMPLE_FILE} not found. Run prepare_eval_samples.py first."
        )

    phishing_df = pd.read_csv(PHISHING_SAMPLE_FILE)
    otp_df = pd.read_csv(OTP_SAMPLE_FILE)

    phishing_df["sms_text"] = phishing_df["sender"].fillna(phishing_df.get("body")).fillna("")
    phishing_df["is_phishing_truth"] = phishing_df["is_phishing_truth"].apply(parse_bool)
    phishing_df = phishing_df.dropna(subset=["is_phishing_truth"])
    phishing_df["eval_id"] = [f"phishing_{i:03d}" for i in range(len(phishing_df))]
    phishing_out = phishing_df.assign(
        source_id=phishing_df["id"].astype(str),
        is_otp_truth=pd.NA,
        otp_intent_truth=pd.NA,
    )[["eval_id", "sms_text", "is_otp_truth", "otp_intent_truth", "is_phishing_truth", "source_id"]]

    otp_df["sms_text"] = otp_df["sender"].fillna(otp_df.get("body")).fillna("")
    otp_df["is_otp_truth"] = otp_df["is_otp"].apply(parse_bool)
    otp_df["otp_intent_truth"] = otp_df["otp_intent"].astype(str)
    otp_df = otp_df[otp_df["otp_intent_truth"].isin(OTP_INTENT_LABELS)]
    otp_df = otp_df.dropna(subset=["is_otp_truth"])
    otp_df["eval_id"] = [f"otp_{i:03d}" for i in range(len(otp_df))]
    otp_out = otp_df.assign(
        source_id=otp_df["id"].astype(str),
        is_phishing_truth=pd.NA,
    )[["eval_id", "sms_text", "is_otp_truth", "otp_intent_truth", "is_phishing_truth", "source_id"]]

    combined = pd.concat([phishing_out, otp_out], ignore_index=True)
    combined["sms_text"] = combined["sms_text"].fillna("").astype(str)
    combined.to_csv(GROUND_TRUTH_OUTPUT, index=False, encoding="utf-8-sig")
    return combined


def load_otp_few_shot_examples() -> List[Dict[str, str]]:
    if not os.path.exists(OTP_SOURCE_FILE):
        return []
    df = pd.read_csv(OTP_SOURCE_FILE)
    labeled = df[df["otp_intent"].notna() & df["is_otp"].notna()]
    categories_examples = {
        "BANK_OR_CARD_TXN_OTP": 2,
        "NOT_OTP": 3,
        "APP_LOGIN_OTP": 1,
        "FINANCIAL_LOGIN_OTP": 1,
        "DELIVERY_OR_SERVICE_OTP": 1,
        "UPI_TXN_OR_PIN_OTP": 1,
        "GENERIC_APP_ACTION_OTP": 1,
        "KYC_OR_ESIGN_OTP": 1,
    }
    examples: List[Dict[str, str]] = []
    for category, count in categories_examples.items():
        subset = labeled[labeled["otp_intent"] == category]
        if subset.empty:
            continue
        sample = subset.sample(n=min(count, len(subset)), random_state=42)
        for _, row in sample.iterrows():
            sms_text = str(row["sender"]) if pd.notna(row["sender"]) else str(row.get("body", ""))
            is_otp_val = parse_bool(row["is_otp"])
            examples.append(
                {
                    "sms": sms_text,
                    "is_otp": "true" if is_otp_val is True else "false",
                    "otp_intent": str(row["otp_intent"]),
                }
            )
    return examples


PHISHING_FEW_SHOTS: List[Dict[str, Any]] = [
    {
        "sms": "Claim your exclusive reward now! Click https://bit.ly/verify-prize and enter your bank details to receive 50,000 cashback.",
        "is_phishing": True,
    },
    {
        "sms": "Final warning: Your account will be suspended. Login at http://secure-update-login.com and confirm your password immediately.",
        "is_phishing": True,
    },
    {
        "sms": "Urgent! Share your OTP with customer support on 9876543210 to unlock your blocked card.",
        "is_phishing": True,
    },
    {
        "sms": "ICICI Bank: Rs. 1,500.00 credited to A/C XX1234 on 12-Feb-25. Avl bal Rs. 48,932. Do not share OTP with anyone.",
        "is_phishing": False,
    },
    {
        "sms": "Your Amazon package will be delivered today. No action needed. Track at amazon.in/track.",
        "is_phishing": False,
    },
    {
        "sms": "123456 is your login OTP for MyFinance app. Do not share this code.",
        "is_phishing": False,
    },
    {
        "sms": "Reminder: Electricity bill of Rs. 850 is due on 15 Feb. Pay via BESCOM app.",
        "is_phishing": False,
    },
]


VERIFICATION_FEW_SHOTS: List[Dict[str, Any]] = [
    {
        "sms": "PLEASE SHARE THIS CODE ONLY WHEN YOUR ORDER IS DELIVERED : 3505. Swiggy Order 217945204638873 from Instamart",
        "provided_is_otp": True,
        "provided_otp_intent": "DELIVERY_OR_SERVICE_OTP",
        "provided_is_phishing": False,
        "expected": {"is_otp_verified": True, "otp_intent_verified": True, "is_phishing_verified": True},
    },
    {
        "sms": "Dear Customer, Min payment Rs.6,756.38/total payment Rs.27,286.51 for AMEX Card **********91009 is due by 06/12/2019.",
        "provided_is_otp": True,
        "provided_otp_intent": "BANK_OR_CARD_TXN_OTP",
        "provided_is_phishing": False,
        "expected": {"is_otp_verified": False, "otp_intent_verified": False, "is_phishing_verified": True},
    },
    {
        "sms": "To DELIVER Achaari order, share OTP 1060. Track@ https://www.delhivery.com -Delhivery",
        "provided_is_otp": True,
        "provided_otp_intent": "BANK_OR_CARD_TXN_OTP",
        "provided_is_phishing": False,
        "expected": {"is_otp_verified": True, "otp_intent_verified": False, "is_phishing_verified": True},
    },
    {
        "sms": "Claim your reward! Click http://fake-rewards.in and login now.",
        "provided_is_otp": False,
        "provided_otp_intent": "NOT_OTP",
        "provided_is_phishing": False,
        "expected": {"is_otp_verified": True, "otp_intent_verified": True, "is_phishing_verified": False},
    },
]


def format_json_value(value: Any) -> str:
    if pd.isna(value):
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    value_str = str(value).strip()
    if value_str.lower() in {"true", "false"}:
        return value_str.lower()
    return json.dumps(value)


def build_prompt(
    batch: pd.DataFrame,
    otp_examples: List[Dict[str, str]],
    phishing_examples: List[Dict[str, Any]],
    verification_examples: List[Dict[str, Any]],
) -> str:
    otp_examples_text = "\n\n".join(
        [
            f"Reference OTP Example {idx + 1}:\nSMS: \"{ex['sms']}\"\nClassification: {{\"is_otp\": {ex['is_otp']}, \"otp_intent\": \"{ex['otp_intent']}\"}}"
            for idx, ex in enumerate(otp_examples)
        ]
    )
    phishing_examples_text = "\n\n".join(
        [
            f"Reference Phishing Example {idx + 1}:\nSMS: \"{ex['sms']}\"\nClassification: {{\"is_phishing\": {str(ex['is_phishing']).lower()} }}"
            for idx, ex in enumerate(phishing_examples)
        ]
    )
    verification_examples_text = "\n\n".join(
        [
            f"Verification Example {idx + 1}:\nSMS: \"{ex['sms']}\"\nProvided labels: "
            f"{{\"is_otp\": {format_json_value(ex['provided_is_otp'])}, \"otp_intent\": \"{ex['provided_otp_intent']}\", "
            f"\"is_phishing\": {format_json_value(ex['provided_is_phishing'])}}}\n"
            f"Output: {json.dumps(ex['expected'])}"
            for idx, ex in enumerate(verification_examples)
        ]
    )

    instructions = f"""You are verifying existing SMS classifications. For each message you will see the SMS text and the previously assigned labels:
- is_otp (true/false)
- otp_intent (from the allowed list)
- is_phishing (true/false)

Your task:
- Decide whether each provided label is correct.
- Return true if the label is correct, false if it is incorrect.
- If a label is missing (null), return null for that field.
- Respond ONLY with JSON: an array of objects each containing id, is_otp_verified, otp_intent_verified, is_phishing_verified.
- Do not add commentary or extra keys.

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
- OTP requires a numeric verification code; alerts without codes are NOT OTP.
- Distinguish between OTP intents carefully using the definitions above.
- Phishing (true) involves suspicious links, unknown contacts, urgent credential/OTP requests, or unrealistic incentives.
- Not phishing (false) covers routine alerts, OTP reminders with safety language, or benign personal messages.

Reference OTP classifications:

{otp_examples_text}

Reference phishing classifications:

{phishing_examples_text}

Verification examples:

{verification_examples_text}
"""
    messages = []
    for _, row in batch.iterrows():
        sms = row["sms_text"].replace("\\", " ").replace('"', '\\"')
        provided_is_otp = format_json_value(row["is_otp_truth"])
        provided_otp_intent = json.dumps(row["otp_intent_truth"]) if pd.notna(row["otp_intent_truth"]) else "null"
        provided_is_phishing = format_json_value(row["is_phishing_truth"])
        messages.append(
            f'{{"id": "{row["eval_id"]}", "sms": "{sms}", '
            f'"provided_is_otp": {provided_is_otp}, '
            f'"provided_otp_intent": {provided_otp_intent}, '
            f'"provided_is_phishing": {provided_is_phishing}}}'
        )
    prompt = (
        instructions
        + "\nMessages to verify:\n["
        + ",\n".join(messages)
        + "]\n\nReturn ONLY the JSON array with objects formatted as "
        + '{"id": "...", "is_otp_verified": true/false/null, "otp_intent_verified": true/false/null, "is_phishing_verified": true/false/null}'
    )
    return prompt


def call_groq(model_id: str, prompt: str, api_key: str) -> str:
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 800,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_deepseek(model_id: str, prompt: str, api_key: str) -> str:
    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 900,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def build_google_schema() -> Dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "is_otp": {"type": "boolean"},
                "otp_intent": {"type": "string"},
                "is_phishing": {"type": "boolean"},
            },
            "required": ["id", "is_otp", "otp_intent", "is_phishing"],
        },
    }


def call_google(model_id: str, prompt: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        params={"key": api_key},
        json={
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 900,
                "responseMimeType": "application/json",
                "responseSchema": build_google_schema(),
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUAL_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_MISINFORMATION", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_VIOLENCE", "threshold": "BLOCK_NONE"},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    candidates = payload.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        parts = content.get("parts") if isinstance(content, dict) else None
        if parts:
            text = parts[0].get("text")
            if text:
                return text
    prompt_feedback = payload.get("promptFeedback", {})
    if prompt_feedback:
        raise ValueError(f"Gemini prompt feedback: {prompt_feedback}")
    raise ValueError("No usable text returned from Gemini API.")


def build_response_schema() -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sms_classification_results",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "is_otp": {"type": "boolean"},
                        "otp_intent": {"type": "string"},
                        "is_phishing": {"type": "boolean"},
                    },
                    "required": ["id", "is_otp", "otp_intent", "is_phishing"],
                    "additionalProperties": False,
                },
            },
        },
    }


def call_openai(model_id: str, prompt: str, api_key: str) -> str:
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_id,
            "input": [
                {"role": "system", "content": [{"type": "text", "text": "Respond with JSON only."}]},
                {"role": "user", "content": [{"type": "text", "text": prompt}]},
            ],
            "temperature": 0.0,
            "max_output_tokens": 900,
            "response_format": build_response_schema(),
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    outputs = payload.get("output", [])
    for item in outputs:
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                text = part.get("text", "")
                if text:
                    return text
    raise ValueError("No text returned from OpenAI Responses API.")


def parse_json_array(content: str) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                if isinstance(value, list):
                    return value
            raise ValueError("JSON root is not a list.")
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
    raise ValueError("Failed to parse JSON array response.")


def batch_predictions(
    df: pd.DataFrame,
    model_cfg: Dict[str, str],
    keys: Dict[str, str],
    otp_examples: List[Dict[str, str]],
    phishing_examples: List[Dict[str, Any]],
    verification_examples: List[Dict[str, Any]],
) -> Tuple[pd.DataFrame, float]:
    api_key = keys[model_cfg["provider"]]
    rows: List[Dict[str, Any]] = []
    start = time.time()
    for batch_start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[batch_start : batch_start + BATCH_SIZE]
        prompt = build_prompt(batch, otp_examples, phishing_examples, verification_examples)
        if model_cfg["provider"] == "groq":
            response_text = call_groq(model_cfg["model_id"], prompt, api_key)
        elif model_cfg["provider"] == "deepseek":
            response_text = call_deepseek(model_cfg["model_id"], prompt, api_key)
        elif model_cfg["provider"] == "google":
            response_text = call_google(model_cfg["model_id"], prompt, api_key)
        elif model_cfg["provider"] == "openai":
            response_text = call_openai(model_cfg["model_id"], prompt, api_key)
        else:
            raise ValueError(f"Unsupported provider: {model_cfg['provider']}")

        predictions = parse_json_array(response_text)
        rows.extend(predictions)
        time.sleep(SLEEP_BETWEEN_CALLS)
    elapsed = time.time() - start
    pred_df = pd.DataFrame(rows)
    return pred_df, elapsed


def evaluate_predictions(ground_truth: pd.DataFrame, predictions: pd.DataFrame) -> Tuple[float, float, float]:
    if "eval_id" not in predictions.columns:
        raise ValueError("Predictions missing 'eval_id' column.")
    merged = ground_truth.merge(predictions, on="eval_id", how="left")
    merged["is_otp_verified_pred"] = merged["is_otp_verified"].apply(parse_bool)
    merged["is_phishing_verified_pred"] = merged["is_phishing_verified"].apply(parse_bool)
    merged["otp_intent_verified_pred"] = merged["otp_intent_verified"].apply(parse_bool)

    def compute_verification_accuracy(truth_col: str, pred_col: str) -> float:
        mask = merged[truth_col].notna()
        if not mask.any():
            return np.nan
        preds = merged.loc[mask, pred_col].map(parse_bool).dropna()
        if preds.empty:
            return np.nan
        return preds.astype(bool).mean()

    is_otp_acc = compute_verification_accuracy("is_otp_truth", "is_otp_verified_pred")
    is_phishing_acc = compute_verification_accuracy("is_phishing_truth", "is_phishing_verified_pred")
    otp_intent_acc = compute_verification_accuracy("otp_intent_truth", "otp_intent_verified_pred")
    return is_otp_acc, otp_intent_acc, is_phishing_acc


def main():
    load_dotenv()
    api_keys = {
        "groq": os.getenv("GROQ_API_KEY"),
        "deepseek": os.getenv("DEEPSEEK_API_KEY"),
        "google": os.getenv("GOOGLE_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
    }
    for provider, key in api_keys.items():
        if any(cfg["provider"] == provider for cfg in MODEL_CONFIGS) and not key:
            raise EnvironmentError(f"Missing API key for provider '{provider}'.")

    ground_truth = build_ground_truth_sample()
    otp_examples = load_otp_few_shot_examples()
    phishing_examples = PHISHING_FEW_SHOTS
    verification_examples = VERIFICATION_FEW_SHOTS
    smoke_df = ground_truth.iloc[: min(SMOKE_TEST_ROWS, len(ground_truth))]

    print(
        f"Prepared ground truth sample with {len(ground_truth)} rows and saved to {GROUND_TRUTH_OUTPUT}."
    )

    summary_rows: List[Dict[str, Any]] = []
    for cfg in MODEL_CONFIGS:
        try:
            if not smoke_df.empty:
                batch_predictions(
                    smoke_df,
                    cfg,
                    api_keys,
                    otp_examples,
                    phishing_examples,
                    verification_examples,
                )
                print(
                    f"[SMOKE TEST] Model '{cfg['name']}' succeeded on {len(smoke_df)} messages."
                )
        except Exception as exc:
            summary_rows.append(
                {
                    "model": cfg["name"],
                    "provider": cfg["provider"],
                    "status": f"smoke test error: {exc}",
                    "is_otp_acc": np.nan,
                    "otp_intent_acc": np.nan,
                    "is_phishing_acc": np.nan,
                    "elapsed_seconds": np.nan,
                }
            )
            continue

        try:
            pred_df, elapsed = batch_predictions(
                ground_truth,
                cfg,
                api_keys,
                otp_examples,
                phishing_examples,
                verification_examples,
            )
        except Exception as exc:
            summary_rows.append(
                {
                    "model": cfg["name"],
                    "provider": cfg["provider"],
                    "status": f"error: {exc}",
                    "is_otp_acc": np.nan,
                    "otp_intent_acc": np.nan,
                    "is_phishing_acc": np.nan,
                    "elapsed_seconds": np.nan,
                }
            )
            continue

        pred_df = pred_df.rename(
            columns={
                "id": "eval_id",
            }
        )
        is_otp_acc, otp_intent_acc, is_phishing_acc = evaluate_predictions(ground_truth, pred_df)
        summary_rows.append(
            {
                "model": cfg["name"],
                "provider": cfg["provider"],
                "status": "ok",
                "is_otp_acc": round(is_otp_acc * 100, 2),
                "otp_intent_acc": round(otp_intent_acc * 100, 2),
                "is_phishing_acc": round(is_phishing_acc * 100, 2),
                "elapsed_seconds": round(elapsed, 2),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(BENCHMARK_SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nBenchmark summary saved to {BENCHMARK_SUMMARY_OUTPUT}")
    print("\nBenchmark summary (% accuracy and total seconds per model):")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()

