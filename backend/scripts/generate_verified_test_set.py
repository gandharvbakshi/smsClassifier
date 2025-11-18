"""
Generate a verified synthetic test set using DeepSeek + local LLaMA validation.

Usage:
    python backend/scripts/generate_verified_test_set.py \
        --target_total 500 \
        --output_file backend/data/synthetic_test_set_500_verified.csv

The script scales the original 200-sample distribution up to the requested size,
ensuring balanced coverage of OTP intents and phishing labels.
"""

import argparse
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = os.getenv("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

BASE_COUNTS = {
    "is_otp": {"True": 100, "False": 100},
    "is_phishing": {"True": 100, "False": 100},
    "otp_intent": {
        "NOT_OTP": 25,
        "BANK_OR_CARD_TXN_OTP": 20,
        "DELIVERY_OR_SERVICE_OTP": 20,
        "GENERIC_APP_ACTION_OTP": 20,
        "APP_LOGIN_OTP": 20,
        "FINANCIAL_LOGIN_OTP": 20,
        "UPI_TXN_OR_PIN_OTP": 20,
        "KYC_OR_ESIGN_OTP": 20,
        "APP_ACCOUNT_CHANGE_OTP": 15,
    },
}

INTENT_EXAMPLES = {
    "NOT_OTP": [
        "INR 1,091.00 spent using ICICI Bank Card XX7007 on 11-May-25 on Swiggy. Avl Limit: INR 2,82,727.46.",
        "Your payment of INR 5000 for Netflix is due by 15/07/2025.",
    ],
    "BANK_OR_CARD_TXN_OTP": [
        "Your OTP for ICICI Bank Card transaction is 456789. Valid for 10 minutes. Do not share.",
        "123456 is OTP for txn of INR 914.77 at SWIGGY LIMI on ICICI Bank Credit Card XX1326.",
    ],
    "DELIVERY_OR_SERVICE_OTP": [
        "PLEASE SHARE THIS CODE ONLY WHEN YOUR ORDER IS DELIVERED : 3505. Swiggy Order 217945204638873",
        "Your delivery OTP is 789012. Share with delivery agent. Valid 5 minutes.",
    ],
    "GENERIC_APP_ACTION_OTP": [
        "Your verification code is 345678. Use it to verify your device. Valid 10 minutes.",
        "OTP 901234 for app verification. Do not share this code.",
    ],
    "APP_LOGIN_OTP": [
        "Netflix: Your login OTP is 567890. Use it to sign in. Valid for 10 minutes.",
        "Instagram: 234567 is your verification code for account login.",
    ],
    "FINANCIAL_LOGIN_OTP": [
        "Zerodha: Your login OTP is 456789. Valid for 10 minutes. Bank never asks for OTP.",
        "Groww: 789012 is your OTP for trading account login. Keep it confidential.",
    ],
    "UPI_TXN_OR_PIN_OTP": [
        "Your UPI PIN setup OTP is 123456. Valid for 5 minutes. Do not share.",
        "GPay: OTP 654321 for UPI transaction. Keep it secret.",
    ],
    "KYC_OR_ESIGN_OTP": [
        "Your KYC verification OTP is 789012. Valid for 10 minutes. Do not disclose.",
        "eSign OTP: 345678. Use for document signing. Valid 5 minutes.",
    ],
    "APP_ACCOUNT_CHANGE_OTP": [
        "Your password reset OTP is 567890. Valid for 10 minutes. Do not share.",
        "Account update verification code: 123456. Valid 5 minutes.",
    ],
}

PHISHING_EXAMPLES = {
    "True": [
        "URGENT: Your account will be suspended. Click here to verify: bit.ly/suspicious123",
        "Congratulations! You won Rs. 50,000. Call 9876543210 to claim your prize.",
        "Your ICICI card is blocked. Verify immediately: icici-fake.com/verify",
    ],
    "False": [
        "INR 1,091.00 spent using ICICI Bank Card XX7007 on 11-May-25 on Swiggy.",
        "Your OTP for ICICI Bank Card transaction is 456789. Valid for 10 minutes.",
    ],
}


def scale_counts(base: Dict[str, int], target_total: int) -> Dict[str, int]:
    base_total = sum(base.values())
    ratios = {k: v / base_total for k, v in base.items()}
    scaled = {k: max(1, int(round(ratios[k] * target_total))) for k in base}
    diff = target_total - sum(scaled.values())
    keys = list(scaled.keys())
    idx = 0
    while diff != 0:
        key = keys[idx % len(keys)]
        adjustment = 1 if diff > 0 else -1
        if scaled[key] + adjustment >= 1:
            scaled[key] += adjustment
            diff = target_total - sum(scaled.values())
        idx += 1
    return scaled


def build_targets(target_total: int) -> Dict[str, Dict[str, int]]:
    base_total = sum(BASE_COUNTS["is_otp"].values())
    scale = target_total / base_total
    targets = {
        "is_otp": scale_counts(BASE_COUNTS["is_otp"], target_total),
        "is_phishing": scale_counts(BASE_COUNTS["is_phishing"], target_total),
    }
    intent_total = int(sum(BASE_COUNTS["otp_intent"].values()) * scale)
    targets["otp_intent"] = scale_counts(BASE_COUNTS["otp_intent"], max(intent_total, target_total // 2))
    return targets


def call_deepseek(prompt: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not configured")
    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You generate realistic Indian SMS content and always reply with JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def generate_candidate(is_otp: bool, otp_intent: str, is_phishing: bool) -> Optional[Dict[str, Any]]:
    examples_intent = INTENT_EXAMPLES.get(otp_intent, [])
    examples_phish = PHISHING_EXAMPLES.get("True" if is_phishing else "False", [])
    prompt = f"""Generate ONE SMS with:
- is_otp: {is_otp}
- otp_intent: {otp_intent}
- is_phishing: {is_phishing}

Guidelines:
- Include a 4-8 digit OTP only if is_otp is true.
- Keep tone aligned with the intent.
- Phishing=True should sound suspicious (urgent language, fake links).
- Phishing=False must sound legitimate.
- Stay under 160 characters and mention Indian brands/apps where relevant.

Examples (do NOT copy):
{chr(10).join(f"- {e}" for e in examples_intent[:3])}

Return ONLY JSON:
{{
  "sms": "...",
  "is_otp": {str(is_otp).lower()},
  "otp_intent": "{otp_intent}",
  "is_phishing": {str(is_phishing).lower()}
}}"""
    raw = call_deepseek(prompt)
    parsed = parse_json_block(raw)
    if parsed and "sms" in parsed:
        return parsed
    return None


def verify_labels(sms: str) -> Optional[Dict[str, Any]]:
    prompt = f"""Classify the SMS and return JSON with keys is_otp, otp_intent, is_phishing.
SMS: "{sms}"

otp_intent options:
NOT_OTP, BANK_OR_CARD_TXN_OTP, DELIVERY_OR_SERVICE_OTP, GENERIC_APP_ACTION_OTP,
APP_LOGIN_OTP, FINANCIAL_LOGIN_OTP, UPI_TXN_OR_PIN_OTP, KYC_OR_ESIGN_OTP, APP_ACCOUNT_CHANGE_OTP

If is_otp=false, force otp_intent="NOT_OTP".
Return ONLY JSON."""
    raw = call_ollama(prompt)
    parsed = parse_json_block(raw)
    if parsed:
        if not parsed.get("is_otp"):
            parsed["otp_intent"] = "NOT_OTP"
        return parsed
    return None


def labels_match(gen: Dict[str, Any], ver: Dict[str, Any]) -> bool:
    gen_otp = bool(gen.get("is_otp"))
    ver_otp = bool(ver.get("is_otp"))
    gen_phish = bool(gen.get("is_phishing"))
    ver_phish = bool(ver.get("is_phishing"))
    gen_intent = gen.get("otp_intent", "NOT_OTP")
    if not gen_otp:
        gen_intent = "NOT_OTP"
    ver_intent = ver.get("otp_intent", "NOT_OTP")
    if not ver_otp:
        ver_intent = "NOT_OTP"
    return gen_otp == ver_otp and gen_phish == ver_phish and gen_intent == ver_intent


def generate_verified_test_set(target_total: int, output_file: Path):
    targets = build_targets(target_total)
    counts = {
        "is_otp": {"True": 0, "False": 0},
        "is_phishing": {"True": 0, "False": 0},
        "otp_intent": {intent: 0 for intent in targets["otp_intent"]},
    }

    rows: List[Dict[str, Any]] = []
    attempts = 0
    max_attempts = target_total * 5

    print(f"Target: {target_total} verified messages")

    while len(rows) < target_total and attempts < max_attempts:
        attempts += 1

        need_otp_true = targets["is_otp"]["True"] - counts["is_otp"]["True"]
        need_otp_false = targets["is_otp"]["False"] - counts["is_otp"]["False"]
        if need_otp_true > 0 and need_otp_false > 0:
            is_otp = (attempts % 2 == 0)
        elif need_otp_true > 0:
            is_otp = True
        else:
            is_otp = False

        if is_otp:
            deficit_intents = [
                intent
                for intent, target in targets["otp_intent"].items()
                if intent != "NOT_OTP" and counts["otp_intent"][intent] < target
            ]
            otp_intent = deficit_intents[attempts % len(deficit_intents)] if deficit_intents else "BANK_OR_CARD_TXN_OTP"
        else:
            otp_intent = "NOT_OTP"

        need_phish_true = targets["is_phishing"]["True"] - counts["is_phishing"]["True"]
        need_phish_false = targets["is_phishing"]["False"] - counts["is_phishing"]["False"]
        if need_phish_true > 0 and need_phish_false > 0:
            is_phishing = (attempts % 3 == 0)
        elif need_phish_true > 0:
            is_phishing = True
        else:
            is_phishing = False

        print(f"[{attempts}] is_otp={is_otp}, intent={otp_intent}, phishing={is_phishing} ...", end=" ")
        generated = generate_candidate(is_otp, otp_intent, is_phishing)
        if not generated:
            print("generation failed")
            continue
        verified = verify_labels(generated["sms"])
        if not verified or not labels_match(generated, verified):
            print("verification mismatch")
            continue

        print("✓")
        row = {
            "original_index": f"test_synthetic_{uuid.uuid4().hex[:8]}",
            "sms_text": generated["sms"],
            "predicted_is_otp": is_otp,
            "predicted_otp_intent": otp_intent,
            "is_phishing_original": is_phishing,
            "classification_status": "synthetic_test",
            "batch_number": "test_set",
            "sender": "",
        }
        rows.append(row)
        counts["is_otp"][str(is_otp)] += 1
        counts["is_phishing"][str(is_phishing)] += 1
        counts["otp_intent"][otp_intent] += 1
        print(f"  Progress: {len(rows)}/{target_total}\n")
        time.sleep(0.5)

    df = pd.DataFrame(rows)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\nSaved {len(df)} verified samples to {output_file}")
    print("\nDistribution:")
    print(df["predicted_is_otp"].value_counts())
    print(df["predicted_otp_intent"].value_counts())
    print(df["is_phishing_original"].value_counts())


def parse_args():
    parser = argparse.ArgumentParser(description="Generate verified synthetic SMS test set.")
    parser.add_argument("--target_total", type=int, default=500, help="Number of verified samples to generate.")
    parser.add_argument(
        "--output_file",
        type=Path,
        default=Path("synthetic_test_set_verified.csv"),
        help="Destination CSV file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_verified_test_set(args.target_total, args.output_file)
"""
Generate a verified synthetic test set with 200 messages across all classes.

This script:
1. Generates synthetic SMS messages using Deepseek API
2. Verifies labels with local Ollama LLM
3. Only keeps messages where both agree on labels
4. Creates balanced coverage across all classes
5. Saves to synthetic_test_set_200_verified.csv

Target distribution:
- is_otp: ~100 True, ~100 False
- otp_intent: ~20-25 per class (9 classes)
- is_phishing: ~100 True, ~100 False
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = "llama3.1:latest"  # or gemma3:12b

OUTPUT_FILE = "synthetic_test_set_200_verified.csv"

# Target counts per class
TARGET_COUNTS = {
    "is_otp": {"True": 100, "False": 100},
    "otp_intent": {
        "NOT_OTP": 25,
        "BANK_OR_CARD_TXN_OTP": 20,
        "DELIVERY_OR_SERVICE_OTP": 20,
        "GENERIC_APP_ACTION_OTP": 20,
        "APP_LOGIN_OTP": 20,
        "FINANCIAL_LOGIN_OTP": 20,
        "UPI_TXN_OR_PIN_OTP": 20,
        "KYC_OR_ESIGN_OTP": 20,
        "APP_ACCOUNT_CHANGE_OTP": 15,
    },
    "is_phishing": {"True": 100, "False": 100},
}

INTENT_EXAMPLES = {
    "NOT_OTP": [
        "INR 1,091.00 spent using ICICI Bank Card XX7007 on 11-May-25 on Swiggy. Avl Limit: INR 2,82,727.46.",
        "Your payment of INR 5000 for Netflix is due by 15/07/2025.",
    ],
    "BANK_OR_CARD_TXN_OTP": [
        "Your OTP for ICICI Bank Card transaction is 456789. Valid for 10 minutes. Do not share.",
        "123456 is OTP for txn of INR 914.77 at SWIGGY LIMI on ICICI Bank Credit Card XX1326.",
    ],
    "DELIVERY_OR_SERVICE_OTP": [
        "PLEASE SHARE THIS CODE ONLY WHEN YOUR ORDER IS DELIVERED : 3505. Swiggy Order 217945204638873",
        "Your delivery OTP is 789012. Share with delivery agent. Valid 5 minutes.",
    ],
    "GENERIC_APP_ACTION_OTP": [
        "Your verification code is 345678. Use it to verify your device. Valid 10 minutes.",
        "OTP 901234 for app verification. Do not share this code.",
    ],
    "APP_LOGIN_OTP": [
        "Netflix: Your login OTP is 567890. Use it to sign in. Valid for 10 minutes.",
        "Instagram: 234567 is your verification code for account login.",
    ],
    "FINANCIAL_LOGIN_OTP": [
        "Zerodha: Your login OTP is 456789. Valid for 10 minutes. Bank never asks for OTP.",
        "Groww: 789012 is your OTP for trading account login. Keep it confidential.",
    ],
    "UPI_TXN_OR_PIN_OTP": [
        "Your UPI PIN setup OTP is 123456. Valid for 5 minutes. Do not share.",
        "GPay: OTP 654321 for UPI transaction. Keep it secret.",
    ],
    "KYC_OR_ESIGN_OTP": [
        "Your KYC verification OTP is 789012. Valid for 10 minutes. Do not disclose.",
        "eSign OTP: 345678. Use for document signing. Valid 5 minutes.",
    ],
    "APP_ACCOUNT_CHANGE_OTP": [
        "Your password reset OTP is 567890. Valid for 10 minutes. Do not share.",
        "Account update verification code: 123456. Valid 5 minutes.",
    ],
}

PHISHING_EXAMPLES = {
    "True": [
        "URGENT: Your account will be suspended. Click here to verify: bit.ly/suspicious123",
        "Congratulations! You won Rs. 50,000. Call 9876543210 to claim your prize.",
        "Your ICICI card is blocked. Verify immediately: icici-fake.com/verify",
    ],
    "False": [
        "INR 1,091.00 spent using ICICI Bank Card XX7007 on 11-May-25 on Swiggy.",
        "Your OTP for ICICI Bank Card transaction is 456789. Valid for 10 minutes.",
    ],
}


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if pd.isna(text):
        return ""
    return " ".join(str(text).strip().split()).lower()


def call_deepseek(prompt: str) -> str:
    """Call Deepseek API."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not found in .env")
    
    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that generates realistic SMS messages and classifies them. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_ollama(prompt: str) -> str:
    """Call local Ollama API."""
    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response."""
    text = text.strip()
    
    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass
    
    # Try to extract JSON block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    
    return None


def generate_synthetic_message(
    is_otp: bool,
    otp_intent: str,
    is_phishing: bool,
) -> Optional[Dict[str, Any]]:
    """Generate a synthetic SMS message with specified labels."""
    
    # Build prompt
    intent_examples = INTENT_EXAMPLES.get(otp_intent, [])
    phishing_examples = PHISHING_EXAMPLES.get("True" if is_phishing else "False", [])
    
    prompt = f"""Generate ONE realistic SMS message with these exact characteristics:

- is_otp: {is_otp}
- otp_intent: {otp_intent}
- is_phishing: {is_phishing}

Guidelines:
- Make it realistic and natural
- If is_otp=True, include an OTP code (4-8 digits)
- Match the otp_intent style
- If is_phishing=True, include suspicious elements (urgent language, links, rewards)
- If is_phishing=False, make it look legitimate
- Keep within 160 characters when possible

Examples for this intent:
{chr(10).join(f"- {ex}" for ex in intent_examples[:3])}

Examples for phishing={is_phishing}:
{chr(10).join(f"- {ex}" for ex in phishing_examples[:2])}

Return ONLY a JSON object with this exact structure:
{{
  "sms": "<the SMS text>",
  "is_otp": {str(is_otp).lower()},
  "otp_intent": "{otp_intent}",
  "is_phishing": {str(is_phishing).lower()}
}}
"""
    
    try:
        response = call_deepseek(prompt)
        parsed = parse_json_response(response)
        if parsed and "sms" in parsed:
            return parsed
    except Exception as e:
        print(f"    [ERROR] Deepseek generation failed: {e}")
    
    return None


def verify_with_ollama(sms: str) -> Optional[Dict[str, Any]]:
    """Verify SMS labels using local Ollama."""
    
    prompt = f"""Classify this SMS message and return ONLY a JSON object:

SMS: "{sms}"

Return JSON with these exact keys:
{{
  "is_otp": true/false,
  "otp_intent": "one of: NOT_OTP, BANK_OR_CARD_TXN_OTP, DELIVERY_OR_SERVICE_OTP, GENERIC_APP_ACTION_OTP, APP_LOGIN_OTP, FINANCIAL_LOGIN_OTP, UPI_TXN_OR_PIN_OTP, KYC_OR_ESIGN_OTP, APP_ACCOUNT_CHANGE_OTP",
  "is_phishing": true/false
}}

Rules:
- If is_otp=false, otp_intent must be "NOT_OTP"
- If is_otp=true, otp_intent must be one of the OTP intent classes
- is_phishing=true if message tries to steal info/money, has suspicious links, or promises fake rewards

Return ONLY the JSON, no other text.
"""
    
    try:
        response = call_ollama(prompt)
        parsed = parse_json_response(response)
        if parsed:
            # Normalize otp_intent
            if parsed.get("is_otp") == False:
                parsed["otp_intent"] = "NOT_OTP"
            return parsed
    except Exception as e:
        print(f"    [ERROR] Ollama verification failed: {e}")
    
    return None


def labels_match(
    generated: Dict[str, Any],
    verified: Dict[str, Any],
) -> bool:
    """Check if generated and verified labels match."""
    # Normalize boolean values
    gen_otp = bool(generated.get("is_otp", False))
    ver_otp = bool(verified.get("is_otp", False))
    
    gen_phishing = bool(generated.get("is_phishing", False))
    ver_phishing = bool(verified.get("is_phishing", False))
    
    gen_intent = str(generated.get("otp_intent", "")).strip()
    ver_intent = str(verified.get("otp_intent", "")).strip()
    
    # Normalize: if is_otp=False, intent should be NOT_OTP
    if not gen_otp:
        gen_intent = "NOT_OTP"
    if not ver_otp:
        ver_intent = "NOT_OTP"
    
    return (
        gen_otp == ver_otp and
        gen_phishing == ver_phishing and
        gen_intent == ver_intent
    )


def generate_verified_test_set() -> pd.DataFrame:
    """Generate verified test set."""
    print("=" * 80)
    print("GENERATING VERIFIED SYNTHETIC TEST SET")
    print("=" * 80)
    
    verified_rows = []
    class_counts = {
        "is_otp": {"True": 0, "False": 0},
        "otp_intent": {intent: 0 for intent in TARGET_COUNTS["otp_intent"].keys()},
        "is_phishing": {"True": 0, "False": 0},
    }
    
    total_needed = 200
    attempts = 0
    max_attempts = 1000  # Safety limit
    
    print(f"\nTarget: {total_needed} verified messages")
    print("Generating and verifying...\n")
    
    while len(verified_rows) < total_needed and attempts < max_attempts:
        attempts += 1
        
        # Determine what we need
        needed_otp_true = TARGET_COUNTS["is_otp"]["True"] - class_counts["is_otp"]["True"]
        needed_otp_false = TARGET_COUNTS["is_otp"]["False"] - class_counts["is_otp"]["False"]
        
        # Decide is_otp
        if needed_otp_true > 0 and needed_otp_false > 0:
            is_otp = (attempts % 2 == 0)  # Alternate
        elif needed_otp_true > 0:
            is_otp = True
        elif needed_otp_false > 0:
            is_otp = False
        else:
            is_otp = (attempts % 2 == 0)
        
        # Decide otp_intent
        if is_otp:
            # Find intent we need most
            intent_counts = class_counts["otp_intent"]
            needed_intents = [
                intent for intent, target in TARGET_COUNTS["otp_intent"].items()
                if intent != "NOT_OTP" and intent_counts[intent] < target
            ]
            if needed_intents:
                otp_intent = needed_intents[attempts % len(needed_intents)]
            else:
                otp_intent = "BANK_OR_CARD_TXN_OTP"  # Default
        else:
            otp_intent = "NOT_OTP"
        
        # Decide is_phishing
        needed_phishing_true = TARGET_COUNTS["is_phishing"]["True"] - class_counts["is_phishing"]["True"]
        needed_phishing_false = TARGET_COUNTS["is_phishing"]["False"] - class_counts["is_phishing"]["False"]
        
        if needed_phishing_true > 0 and needed_phishing_false > 0:
            is_phishing = (attempts % 3 == 0)  # 1/3 phishing
        elif needed_phishing_true > 0:
            is_phishing = True
        elif needed_phishing_false > 0:
            is_phishing = False
        else:
            is_phishing = (attempts % 3 == 0)
        
        # Generate
        print(f"[{attempts}] Generating: is_otp={is_otp}, intent={otp_intent}, phishing={is_phishing}...", end=" ")
        generated = generate_synthetic_message(is_otp, otp_intent, is_phishing)
        
        if not generated:
            print("FAILED (generation)")
            time.sleep(0.5)
            continue
        
        # Verify
        verified = verify_with_ollama(generated["sms"])
        
        if not verified:
            print("FAILED (verification)")
            time.sleep(0.5)
            continue
        
        # Check if labels match
        if not labels_match(generated, verified):
            print("MISMATCH (labels don't agree)")
            time.sleep(0.5)
            continue
        
        # Success - add to verified set
        print("✓ VERIFIED")
        
        row = {
            "original_index": f"test_synthetic_{uuid.uuid4().hex[:8]}",
            "sms_text": generated["sms"],
            "predicted_is_otp": is_otp,
            "predicted_otp_intent": otp_intent,
            "is_phishing_original": is_phishing,
            "classification_status": "synthetic_test",
            "batch_number": "test_set",
            "sender": "",  # Empty for synthetic
        }
        verified_rows.append(row)
        
        # Update counts
        class_counts["is_otp"][str(is_otp)] += 1
        class_counts["otp_intent"][otp_intent] += 1
        class_counts["is_phishing"][str(is_phishing)] += 1
        
        print(f"  Progress: {len(verified_rows)}/{total_needed} verified")
        print(f"  is_otp: {class_counts['is_otp']}")
        print(f"  is_phishing: {class_counts['is_phishing']}")
        print(f"  otp_intent: {sum(class_counts['otp_intent'].values())} total")
        
        time.sleep(1.0)  # Rate limiting
    
    if len(verified_rows) < total_needed:
        print(f"\n⚠ Warning: Only generated {len(verified_rows)}/{total_needed} verified messages")
    
    df = pd.DataFrame(verified_rows)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✓ Saved {len(df)} verified test messages to {OUTPUT_FILE}")
    
    # Print final distribution
    print("\n" + "=" * 80)
    print("FINAL DISTRIBUTION")
    print("=" * 80)
    print("\nis_otp:")
    print(df["predicted_is_otp"].value_counts())
    print("\notp_intent:")
    print(df["predicted_otp_intent"].value_counts())
    print("\nis_phishing:")
    print(df["is_phishing_original"].value_counts())
    
    return df


if __name__ == "__main__":
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not found in .env")
    
    generate_verified_test_set()

