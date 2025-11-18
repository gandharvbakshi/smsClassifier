"""
Generate synthetic OTP SMS samples for underrepresented intent classes
using a local Ollama model (default: llama3.1:latest).

Output columns match the clean training dataset:
    original_index, sms_text, predicted_is_otp, predicted_otp_intent,
    classification_status, batch_number, is_phishing_original
"""

import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_FILE = "classification_results_with_phishing_llm_clean.csv"
OUTPUT_FILE = "synthetic_otp_intents_generated.csv"

MODEL_ID = os.environ.get("OLLAMA_MODEL_ID", "llama3.1:latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
GENERATE_BATCH = 15                      # messages per LLM call
SLEEP_BETWEEN_CALLS = 1.0                # seconds

# Minimum target size per OTP intent; if current count >= target, skip.
TARGET_COUNTS = {
    "APP_ACCOUNT_CHANGE_OTP": 250,
    "UPI_TXN_OR_PIN_OTP": 250,
    "KYC_OR_ESIGN_OTP": 250,
    "FINANCIAL_LOGIN_OTP": 300,
    "APP_LOGIN_OTP": 350,
    "GENERIC_APP_ACTION_OTP": 350,
    "DELIVERY_OR_SERVICE_OTP": 400,
    # NOT_OTP and BANK_OR_CARD_TXN_OTP already have ample coverage.
}

INTENT_GUIDELINES = {
    "APP_ACCOUNT_CHANGE_OTP": {
        "definition": "OTP for account updates such as password reset, profile change, phone/email update in consumer apps.",
        "must_include": [
            "Clear account-change context (e.g., resetting password, updating contact info).",
            "Numeric OTP code (4–8 digits).",
            "Safety line (Do not share / valid for limited time)."
        ]
    },
    "UPI_TXN_OR_PIN_OTP": {
        "definition": "OTP for UPI transfers, PIN setup, or device binding in UPI apps (GPay, PhonePe, Paytm).",
        "must_include": [
            "Explicit UPI context (transaction, PIN setup, linking account).",
            "OTP code and validity.",
            "Safety warning."
        ]
    },
    "KYC_OR_ESIGN_OTP": {
        "definition": "OTP for know-your-customer verification or e-signing documents.",
        "must_include": [
            "Reference to KYC/esign/document signing.",
            "OTP + validity window.",
            "Instruction NOT to share the OTP."
        ]
    },
    "FINANCIAL_LOGIN_OTP": {
        "definition": "OTP for logging into financial platforms (trading, investment, banking portals beyond basic card transactions).",
        "must_include": [
            "Financial platform or trading/investment context.",
            "OTP + validity.",
            "Security reminder."
        ]
    },
    "APP_LOGIN_OTP": {
        "definition": "OTP for logging into consumer apps (social, entertainment, SaaS) that are not primarily financial.",
        "must_include": [
            "Consumer or SaaS login context.",
            "OTP and mentioned app name.",
            "Safety warning."
        ]
    },
    "GENERIC_APP_ACTION_OTP": {
        "definition": "OTP for miscellaneous app actions (two-factor, profile change, device linking) not covered above.",
        "must_include": [
            "Mention of generic app action (e.g., verifying device, enabling 2FA).",
            "OTP code + duration.",
            "Instruction not to share."
        ]
    },
    "DELIVERY_OR_SERVICE_OTP": {
        "definition": "OTP for confirming deliveries, courier drop-offs, service appointments.",
        "must_include": [
            "Delivery/service context (courier, technician visit, food/package drop).",
            "OTP + step (e.g., share with delivery agent).",
            "Safety reminder about not sharing with strangers."
        ]
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_existing_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)
    df["sms_text"] = df["sms_text"].astype(str)
    return df


def message_already_exists(msg: str, existing_texts: set) -> bool:
    normalized = " ".join(msg.strip().split()).lower()
    return normalized in existing_texts


def build_prompt(intent: str,
                 needed: int,
                 seed_examples: List[str]) -> str:
    guidelines = INTENT_GUIDELINES[intent]
    example_block = "\n".join(f"- {ex}" for ex in seed_examples[:5])

    prompt = f"""
You are an expert SMS copywriter for Indian banks and apps. Generate {needed} distinct SMS messages for the intent class "{intent}".

Definition:
{guidelines["definition"]}

Essential requirements for each SMS:
{"".join(f"- {item}\n" for item in guidelines["must_include"])}

General rules:
- Include realistic OTP wording with code (4-8 digits).
- Vary brands/apps, amounts, languages (English + occasional Hindi vernacular lines).
- Avoid personally identifiable info. Invent generic merchants/banks if needed.
- Always include a security warning ("Do not share", "Bank never asks", etc.).
- Keep messages within 160 characters when possible.
- Ensure each SMS is unique (no simple rewrites).

Provide your answer as a JSON array. Each element must be an object with keys:
  "sms": "<the SMS text>"

Example templates (do NOT copy verbatim; just for inspiration):
{example_block}

Return ONLY valid JSON. Do NOT wrap the output in Markdown fences or add commentary.
"""
    return prompt.strip()


def call_ollama(prompt: str) -> str:
    response = requests.post(
        url=f"{OLLAMA_URL.rstrip('/')}/api/generate",
        json={"model": MODEL_ID, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def parse_json_list(response_text: str) -> List[Dict[str, str]]:
    response_text = response_text.strip()
    # Try direct JSON parse
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try to extract JSON array substring
    start = response_text.find("[")
    end = response_text.rfind("]")
    if start != -1 and end != -1 and end > start:
        snippet = response_text[start:end + 1]
        try:
            parsed = json.loads(snippet)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Unable to parse JSON array from response:\n{response_text[:200]}...")


def gather_seed_examples(df: pd.DataFrame, intent: str, n: int = 5) -> List[str]:
    subset = df[df["predicted_otp_intent"] == intent]["sms_text"].head(n)
    if subset.empty:
        return [
            "123456 is OTP for resetting your account password. Do not share this OTP. Valid 10 minutes.",
            "Use OTP 789012 to update contact info in your app. Keep it secret. Valid 5 minutes.",
        ]
    return subset.tolist()


def create_synthetic_rows(intent: str,
                          messages: List[str]) -> List[Dict[str, Any]]:
    rows = []
    for msg in messages:
        msg_clean = " ".join(msg.strip().split())
        row = {
            "original_index": f"synthetic_{intent}_{uuid.uuid4().hex[:8]}",
            "sms_text": msg_clean,
            "predicted_is_otp": True,
            "predicted_otp_intent": intent,
            "classification_status": "synthetic",
            "batch_number": "synthetic",
            "is_phishing_original": False,
        }
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------

def main():
    df = load_existing_dataset(SOURCE_FILE)
    existing_texts = {" ".join(txt.strip().split()).lower() for txt in df["sms_text"].tolist()}

    synthetic_rows = []
    for intent, target in TARGET_COUNTS.items():
        current_count = int((df["predicted_otp_intent"] == intent).sum())
        needed = target - current_count
        if needed <= 0:
            print(f"[SKIP] {intent}: already {current_count} samples (target {target}).")
            continue

        print(f"[INFO] Generating ~{needed} SMS for {intent} (current {current_count}).")
        seed_examples = gather_seed_examples(df, intent)
        remaining = needed
        while remaining > 0:
            batch_size = min(GENERATE_BATCH, remaining)
            prompt = build_prompt(intent, batch_size, seed_examples)
            raw_response = call_ollama(prompt)
            try:
                candidates = parse_json_list(raw_response)
            except ValueError as err:
                print(f"[WARN] Failed to parse LLM output: {err}. Retrying...")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            new_messages = []
            for item in candidates:
                sms = item.get("sms", "")
                if not sms:
                    continue
                if message_already_exists(sms, existing_texts):
                    continue
                existing_texts.add(" ".join(sms.strip().split()).lower())
                new_messages.append(sms)

            if not new_messages:
                print("[WARN] LLM returned no usable messages; retrying...")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            synthetic_rows.extend(create_synthetic_rows(intent, new_messages))
            remaining -= len(new_messages)
            print(f"  +{len(new_messages)} messages added; {remaining} remaining.")
            time.sleep(SLEEP_BETWEEN_CALLS)

    if not synthetic_rows:
        print("No synthetic rows generated. Nothing to write.")
        return

    synthetic_df = pd.DataFrame(synthetic_rows)
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    synthetic_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nSaved {len(synthetic_df)} synthetic rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()