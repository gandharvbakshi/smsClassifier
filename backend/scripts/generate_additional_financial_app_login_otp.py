"""
Generate additional synthetic OTP SMS samples for FINANCIAL_LOGIN_OTP and APP_LOGIN_OTP
using Deepseek API (from .env file).

This script:
1. Generates a small test batch (10 samples) first for inspection
2. Then generates full batches to reach target counts

Output format matches the training dataset:
    original_index, sms_text, predicted_is_otp, predicted_otp_intent,
    classification_status, batch_number, is_phishing_original
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_FILE = "classification_results_with_phishing_llm_balanced.csv"
TEST_OUTPUT_FILE = "synthetic_financial_app_login_test_10.csv"
FULL_OUTPUT_FILE = "synthetic_financial_app_login_full.csv"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

GENERATE_BATCH = 15  # messages per API call
SLEEP_BETWEEN_CALLS = 1.0  # seconds

# Target counts (current + additional needed)
TARGET_COUNTS = {
    "FINANCIAL_LOGIN_OTP": 800,  # Increase from ~300-400 to 800
    "APP_LOGIN_OTP": 800,  # Increase from ~300-400 to 800
}

INTENT_GUIDELINES = {
    "FINANCIAL_LOGIN_OTP": {
        "definition": "OTP for logging into financial platforms like trading apps (Zerodha, Groww, Upstox), investment platforms, banking portals, or financial services apps. These are HIGH RISK - users should NEVER share these OTPs.",
        "must_include": [
            "Explicit mention of financial platform (trading, investment, banking portal, demat account, mutual fund, stocks, NSE, BSE).",
            "Keywords: trading, investment, portfolio, demat, mutual fund, stocks, broker, equity, Zerodha, Groww, Upstox, Angel One, Kotak Securities, ICICI Direct, HDFC Securities.",
            "OTP code (4-8 digits) and validity period.",
            "Strong security warning (Do not share, Bank never asks, OTP is secret).",
        ],
        "examples": [
            "Your OTP for Zerodha login is 456789. Valid for 10 minutes. Do not share this OTP with anyone. Bank never asks for OTP.",
            "Groww: Your login OTP is 123456. Use it to access your investment portfolio. Never share this code.",
            "Upstox: 789012 is your OTP for trading account login. Valid for 5 minutes. Keep it confidential.",
            "ICICI Direct: OTP 345678 for demat account access. Do not disclose this code to anyone.",
            "HDFC Securities: Your login verification code is 901234. Valid for 10 minutes. Bank never asks for OTP.",
        ],
    },
    "APP_LOGIN_OTP": {
        "definition": "OTP for logging into consumer apps (social media, entertainment, streaming, gaming, shopping apps) that are NOT primarily financial. These are lower risk than financial logins but still should not be shared.",
        "must_include": [
            "EXPLICIT mention of a specific app name (Netflix, Spotify, Instagram, Facebook, Amazon, Flipkart, Zomato, Swiggy, Hotstar, Disney+, YouTube, Gaana, JioSaavn, Prime Video, etc.).",
            "MUST include the app name at the start or clearly in the message (e.g., 'Netflix:', 'Spotify login OTP:', 'Your Instagram code').",
            "Keywords: app login, account login, social media, entertainment, streaming, gaming, shopping (non-financial context).",
            "OTP code (4-8 digits) and validity period.",
            "Security reminder (Do not share, Keep it secret).",
        ],
        "examples": [
            "Netflix: Your login OTP is 567890. Use it to sign in to your account. Valid for 10 minutes.",
            "Instagram: 234567 is your verification code for account login. Do not share this code.",
            "Spotify: Your login verification code is 890123. Valid for 5 minutes. Keep it confidential.",
            "Amazon: OTP 456789 for account login. Use this code to access your account. Do not share.",
            "Facebook: Your login code is 123456. Enter this to sign in. Valid for 10 minutes.",
            "Zomato: Your login OTP is 789012. Valid for 5 minutes. Do not share with anyone.",
            "Hotstar: 345678 is your verification code for account login. Keep it confidential.",
            "Flipkart: OTP 901234 for app login. Valid for 10 minutes. Do not disclose.",
        ],
        "app_names": [
            "Netflix", "Spotify", "Instagram", "Facebook", "Amazon", "Flipkart", "Zomato", "Swiggy",
            "Hotstar", "Disney+", "YouTube", "Gaana", "JioSaavn", "Prime Video", "Voot", "SonyLIV",
            "MX Player", "TikTok", "Twitter", "LinkedIn", "Snapchat", "Telegram", "WhatsApp",
            "Pinterest", "Reddit", "Discord", "Twitch", "Steam", "Epic Games", "Uber", "Ola",
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_existing_dataset(path: str) -> pd.DataFrame:
    """Load the balanced dataset to check current counts."""
    df = pd.read_csv(path)
    df["predicted_otp_intent"] = df["predicted_otp_intent"].astype(str)
    return df


def message_already_exists(msg: str, existing_texts: set) -> bool:
    """Check if a normalized message already exists."""
    normalized = " ".join(msg.strip().split()).lower()
    return normalized in existing_texts


def has_app_keywords(text: str) -> bool:
    """Check if APP_LOGIN_OTP message contains app-related keywords."""
    text_upper = text.upper()
    app_names = INTENT_GUIDELINES["APP_LOGIN_OTP"].get("app_names", [])
    
    # Check for explicit app names
    for app_name in app_names:
        if app_name.upper() in text_upper:
            return True
    
    # Check for generic app keywords
    app_keywords = [
        "APP LOGIN", "ACCOUNT LOGIN", "SOCIAL MEDIA", "ENTERTAINMENT",
        "STREAMING", "GAMING", "SHOPPING APP", "SIGN IN", "LOG IN",
    ]
    for keyword in app_keywords:
        if keyword in text_upper:
            return True
    
    return False


def build_prompt(intent: str, needed: int, seed_examples: List[str]) -> str:
    """Build a detailed prompt for Deepseek to generate OTP SMS."""
    guidelines = INTENT_GUIDELINES[intent]
    example_block = "\n".join(f"- {ex}" for ex in seed_examples[:5])
    
    # Add app names list for APP_LOGIN_OTP
    app_names_section = ""
    if intent == "APP_LOGIN_OTP" and "app_names" in guidelines:
        app_names_list = ", ".join(guidelines["app_names"][:20])  # Show first 20
        app_names_section = f"\n\nIMPORTANT: You MUST use explicit app names from this list: {app_names_list}\nEach message MUST start with or clearly mention the app name (e.g., 'Netflix:', 'Spotify login OTP:', 'Your Instagram code')."

    prompt = f"""You are an expert SMS copywriter for Indian banks and apps. Generate {needed} distinct, realistic SMS messages for the intent class "{intent}".

Definition:
{guidelines["definition"]}

Essential requirements for each SMS:
{"".join(f"- {item}\n" for item in guidelines["must_include"])}
{app_names_section}

General rules:
- Include realistic OTP wording with code (4-8 digits).
- Vary brands/apps, amounts, languages (English + occasional Hindi vernacular lines).
- Avoid personally identifiable info. Invent generic merchants/banks if needed.
- Always include a security warning ("Do not share", "Bank never asks", etc.).
- Keep messages within 160 characters when possible.
- Ensure each SMS is unique (no simple rewrites).
- Make messages sound authentic and natural.

Example templates (do NOT copy verbatim; use as inspiration):
{example_block}

Provide your answer as a JSON array. Each element must be an object with keys:
  "sms": "<the SMS text>"

Return ONLY valid JSON. Do NOT wrap the output in Markdown fences or add commentary.
"""
    return prompt.strip()


def call_deepseek(prompt: str) -> str:
    """Call Deepseek API to generate text."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not found in environment variables.")

    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that generates realistic SMS messages. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,  # Slight randomness for variety
            "max_tokens": 2000,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_json_list(response_text: str) -> List[Dict[str, str]]:
    """Parse JSON array from Deepseek response."""
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
    """Gather real examples from the dataset as seed templates."""
    subset = df[df["predicted_otp_intent"] == intent]["sms_text"].head(n)
    if subset.empty:
        # Fallback to guidelines examples
        return INTENT_GUIDELINES[intent]["examples"]
    return subset.tolist()


def create_synthetic_rows(intent: str, messages: List[str]) -> List[Dict[str, Any]]:
    """Create synthetic rows in the expected format."""
    rows = []
    for msg in messages:
        msg_clean = " ".join(msg.strip().split())
        row = {
            "original_index": f"synthetic_{intent}_{uuid.uuid4().hex[:8]}",
            "sms_text": msg_clean,
            "predicted_is_otp": True,
            "predicted_otp_intent": intent,
            "classification_status": "synthetic",
            "batch_number": "synthetic_deepseek",
            "is_phishing_original": False,
        }
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Main generation functions
# ---------------------------------------------------------------------------

def generate_test_batch() -> pd.DataFrame:
    """Generate a small test batch (10 samples) for inspection."""
    print("=" * 80)
    print("GENERATING TEST BATCH (10 samples per intent)")
    print("=" * 80)
    
    df = load_existing_dataset(SOURCE_FILE)
    existing_texts = {
        " ".join(str(txt).strip().split()).lower() 
        for txt in df["sms_text"].tolist() 
        if pd.notna(txt)
    }
    
    synthetic_rows = []
    for intent in ["FINANCIAL_LOGIN_OTP", "APP_LOGIN_OTP"]:
        print(f"\n[TEST] Generating 10 samples for {intent}...")
        seed_examples = gather_seed_examples(df, intent)
        prompt = build_prompt(intent, 10, seed_examples)
        
        try:
            raw_response = call_deepseek(prompt)
            candidates = parse_json_list(raw_response)
            
            new_messages = []
            for item in candidates[:10]:  # Limit to 10 for test
                sms = item.get("sms", "")
                if not sms:
                    continue
                if message_already_exists(sms, existing_texts):
                    continue
                
                # For APP_LOGIN_OTP, filter out messages without app keywords
                if intent == "APP_LOGIN_OTP" and not has_app_keywords(sms):
                    continue
                
                existing_texts.add(" ".join(sms.strip().split()).lower())
                new_messages.append(sms)
            
            synthetic_rows.extend(create_synthetic_rows(intent, new_messages))
            print(f"  +{len(new_messages)} messages added.")
            time.sleep(SLEEP_BETWEEN_CALLS)
        except Exception as e:
            print(f"  [ERROR] Failed to generate: {e}")
    
    if not synthetic_rows:
        print("No synthetic rows generated in test batch.")
        return pd.DataFrame()
    
    test_df = pd.DataFrame(synthetic_rows)
    test_df.to_csv(TEST_OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✓ Test batch saved to {TEST_OUTPUT_FILE}")
    print(f"  Total rows: {len(test_df)}")
    print(f"\nPlease inspect {TEST_OUTPUT_FILE} before running the full generation.")
    return test_df


def generate_full_batch() -> pd.DataFrame:
    """Generate full batches to reach target counts."""
    print("=" * 80)
    print("GENERATING FULL BATCH")
    print("=" * 80)
    
    df = load_existing_dataset(SOURCE_FILE)
    existing_texts = {
        " ".join(str(txt).strip().split()).lower() 
        for txt in df["sms_text"].tolist() 
        if pd.notna(txt)
    }
    
    synthetic_rows = []
    for intent, target in TARGET_COUNTS.items():
        current_count = int((df["predicted_otp_intent"] == intent).sum())
        needed = max(0, target - current_count)
        
        if needed <= 0:
            print(f"[SKIP] {intent}: already {current_count} samples (target {target}).")
            continue
        
        print(f"\n[INFO] Generating ~{needed} SMS for {intent} (current {current_count}, target {target}).")
        if intent == "APP_LOGIN_OTP":
            print("  [NOTE] Filtering enabled: Only messages with explicit app names/keywords will be kept.")
        seed_examples = gather_seed_examples(df, intent)
        remaining = needed
        regeneration_attempts = 0
        max_regeneration_attempts = 3  # Max times to retry if too many filtered out
        
        while remaining > 0:
            batch_size = min(GENERATE_BATCH, remaining)
            prompt = build_prompt(intent, batch_size, seed_examples)
            
            try:
                raw_response = call_deepseek(prompt)
                candidates = parse_json_list(raw_response)
                
                new_messages = []
                filtered_out = 0
                for item in candidates:
                    sms = item.get("sms", "")
                    if not sms:
                        continue
                    if message_already_exists(sms, existing_texts):
                        filtered_out += 1
                        continue
                    
                    # For APP_LOGIN_OTP, filter out messages without app keywords
                    if intent == "APP_LOGIN_OTP" and not has_app_keywords(sms):
                        filtered_out += 1
                        continue
                    
                    existing_texts.add(" ".join(sms.strip().split()).lower())
                    new_messages.append(sms)
                
                if filtered_out > 0:
                    print(f"    (Filtered out {filtered_out} messages: duplicates or missing keywords)")
                
                if not new_messages:
                    print("  [WARN] No usable messages in this batch; retrying...")
                    time.sleep(SLEEP_BETWEEN_CALLS)
                    continue
                
                synthetic_rows.extend(create_synthetic_rows(intent, new_messages))
                remaining -= len(new_messages)
                print(f"  +{len(new_messages)} messages added; {remaining} remaining.")
                
                # If we got very few messages (high filter rate), try regenerating
                if intent == "APP_LOGIN_OTP" and len(new_messages) < batch_size * 0.3 and regeneration_attempts < max_regeneration_attempts:
                    regeneration_attempts += 1
                    print(f"  [RETRY] Low acceptance rate, regenerating batch (attempt {regeneration_attempts}/{max_regeneration_attempts})...")
                    time.sleep(SLEEP_BETWEEN_CALLS)
                    continue
                
                regeneration_attempts = 0  # Reset on success
                time.sleep(SLEEP_BETWEEN_CALLS)
            except Exception as e:
                print(f"  [ERROR] Failed: {e}. Retrying...")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue
    
    if not synthetic_rows:
        print("No synthetic rows generated.")
        return pd.DataFrame()
    
    full_df = pd.DataFrame(synthetic_rows)
    full_df.to_csv(FULL_OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✓ Full batch saved to {FULL_OUTPUT_FILE}")
    print(f"  Total rows: {len(full_df)}")
    return full_df


def main():
    """Main entry point."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not found in .env file. Please add it.")
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        # Generate full batch
        generate_full_batch()
    else:
        # Generate test batch first
        generate_test_batch()
        print("\n" + "=" * 80)
        print("To generate the full batch, run:")
        print(f"  python {__file__} full")
        print("=" * 80)


if __name__ == "__main__":
    main()

