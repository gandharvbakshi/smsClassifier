"""
Verify existing SMS classifications using Groq's llama-3.3-70b-versatile.

- Reads `classification_results_with_phishing.csv`.
- Sends messages in mini-batches (10 per prompt) to confirm whether the existing
  labels (is_otp, otp_intent, is_phishing) are correct.
- Processes rows in outer batches of 500 to provide regular progress updates.
- Writes cumulative results to `classification_results_with_phishing_verified.csv`
  and a disagreements-only extract to `verification_disagreements.csv`.
- Supports resumable execution: previously verified rows (identified by
  verification_badge) are skipped automatically.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
SOURCE_FILE = os.path.join(BASE_DIR, "classification_results_with_phishing.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "classification_results_with_phishing_verified.csv")
DISAGREEMENT_FILE = os.path.join(BASE_DIR, "verification_disagreements.csv")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "verification_progress_checkpoint.csv")

MODEL_NAME = "llama-3.3-70b-versatile"
BATCH_SIZE = 500               # rows per outer batch (progress logging + checkpoint)
PROMPT_CHUNK_SIZE = 10         # messages per LLM call
MAX_RETRIES_PER_CHUNK = 3
SLEEP_BETWEEN_CHUNKS = 0.2

VERIFICATION_BADGE = f"VERIFIED_{MODEL_NAME}"
VERIFICATION_MODEL = MODEL_NAME

# -----------------------------------------------------------------------------
# Few-shot reference material
# -----------------------------------------------------------------------------

OTP_REFERENCE_EXAMPLES: List[Dict[str, str]] = [
    {
        "sms": "402747 is the OTP for INR 2832.90 transaction on your card. Do not share this OTP.",
        "is_otp": "true",
        "otp_intent": "BANK_OR_CARD_TXN_OTP",
    },
    {
        "sms": "Your Swiggy order OTP is 2356. Share only after delivery.",
        "is_otp": "true",
        "otp_intent": "DELIVERY_OR_SERVICE_OTP",
    },
    {
        "sms": "123456 is your login OTP for MyFinance app. Keep it confidential.",
        "is_otp": "true",
        "otp_intent": "FINANCIAL_LOGIN_OTP",
    },
    {
        "sms": "Reminder: Your electricity bill of Rs. 850 is due on 15 Feb. Pay via BESCOM app.",
        "is_otp": "false",
        "otp_intent": "NOT_OTP",
    },
    {
        "sms": "URGENT! Update your PAN immediately. Visit http://fake-pan-update.in",
        "is_otp": "false",
        "otp_intent": "NOT_OTP",
    },
]

PHISHING_REFERENCE_EXAMPLES: List[Dict[str, Any]] = [
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

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def to_bool(value: Any) -> Any:
    """Convert various truthy representations to Python bool, keep NaN as pd.NA."""
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value
    value_str = str(value).strip().lower()
    if value_str in {"true", "yes", "1"}:
        return True
    if value_str in {"false", "no", "0"}:
        return False
    return pd.NA


def format_json_value(value: Any) -> str:
    """Convert Python/NaN values into JSON-safe string snippets."""
    if pd.isna(value):
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    value_str = str(value).strip()
    if value_str.lower() in {"true", "false"}:
        return value_str.lower()
    return json.dumps(value)


def sanitize_sms(text: str) -> str:
    return text.replace("\\", " ").replace('"', '\\"')


def build_chunk_prompt(chunk_rows: List[Dict[str, Any]]) -> str:
    otp_examples_text = "\n\n".join(
        [
            f"Reference OTP Example {idx + 1}:\nSMS: \"{ex['sms']}\"\nClassification: "
            f"{{\"is_otp\": {ex['is_otp']}, \"otp_intent\": \"{ex['otp_intent']}\"}}"
            for idx, ex in enumerate(OTP_REFERENCE_EXAMPLES)
        ]
    )
    phishing_examples_text = "\n\n".join(
        [
            f"Reference Phishing Example {idx + 1}:\nSMS: \"{ex['sms']}\"\nClassification: "
            f"{{\"is_phishing\": {str(ex['is_phishing']).lower()} }}"
            for idx, ex in enumerate(PHISHING_REFERENCE_EXAMPLES)
        ]
    )
    verification_examples_text = "\n\n".join(
        [
            f"Verification Example {idx + 1}:\nSMS: \"{ex['sms']}\"\nProvided labels: "
            f"{{\"is_otp\": {format_json_value(ex['provided_is_otp'])}, "
            f"\"otp_intent\": \"{ex['provided_otp_intent']}\", "
            f"\"is_phishing\": {format_json_value(ex['provided_is_phishing'])}}}\n"
            f"Output: {json.dumps(ex['expected'])}"
            for idx, ex in enumerate(VERIFICATION_FEW_SHOTS)
        ]
    )

    instructions = f"""You are verifying existing SMS classifications. For each message you receive:
- The SMS text itself.
- Provided labels: is_otp (true/false), otp_intent (one of the allowed categories), and is_phishing (true/false).

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
    for row in chunk_rows:
        messages.append(
            f'{{"id": "{row["row_id"]}", '
            f'"sms": "{sanitize_sms(row["sms_text"])}", '
            f'"provided_is_otp": {format_json_value(row["provided_is_otp"])}, '
            f'"provided_otp_intent": {format_json_value(row["provided_otp_intent"])}, '
            f'"provided_is_phishing": {format_json_value(row["provided_is_phishing"])}'
            f"}}"
        )

    prompt = (
        instructions
        + "\nMessages to verify:\n["
        + ",\n".join(messages)
        + "]\n\nReturn ONLY the JSON array with objects formatted as "
        + '{"id": "...", "is_otp_verified": true/false/null, '
        + '"otp_intent_verified": true/false/null, "is_phishing_verified": true/false/null}'
    )
    return prompt


def call_groq(prompt: str, api_key: str) -> str:
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
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
    payload = response.json()
    return payload.get("choices", [{}])[0].get("message", {}).get("content", "")


def parse_json_array(content: str) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for value in parsed.values():
                if isinstance(value, list):
                    return value
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
    raise ValueError("Failed to parse JSON array from model response.")


def merge_results(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    if existing_df.empty:
        return new_df
    overlap = set(existing_df["original_index"]).intersection(new_df["original_index"])
    if overlap:
        existing_df = existing_df[~existing_df["original_index"].isin(overlap)]
    return pd.concat([existing_df, new_df], ignore_index=True)


def write_outputs(all_results: pd.DataFrame) -> None:
    all_results.sort_values("original_index", inplace=True)
    all_results.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    disagreements = all_results[all_results["needs_manual_review"]]
    disagreements.to_csv(DISAGREEMENT_FILE, index=False, encoding="utf-8-sig")

    checkpoint_payload = {
        "last_saved": datetime.utcnow().isoformat() + "Z",
        "total_verified": int(len(all_results)),
    }
    pd.Series(checkpoint_payload).to_json(CHECKPOINT_FILE, indent=2)


# -----------------------------------------------------------------------------
# Main processing
# -----------------------------------------------------------------------------


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set.")

    if not os.path.exists(SOURCE_FILE):
        raise FileNotFoundError(f"{SOURCE_FILE} not found.")

    source_df = pd.read_csv(SOURCE_FILE)
    required_columns = {
        "original_index",
        "sms_text",
        "predicted_is_otp",
        "predicted_otp_intent",
        "is_phishing",
    }
    missing = required_columns - set(source_df.columns)
    if missing:
        raise ValueError(f"Source file is missing required columns: {missing}")

    # Normalise provided labels
    source_df["provided_is_otp"] = source_df["predicted_is_otp"].apply(to_bool)
    source_df["provided_otp_intent"] = source_df["predicted_otp_intent"].fillna(pd.NA)
    source_df["provided_is_phishing"] = source_df["is_phishing"].apply(to_bool)
    source_df["row_id"] = source_df["original_index"].astype(str)

    # Load prior verification results (if any) to support resumable runs
    if os.path.exists(OUTPUT_FILE):
        verified_df = pd.read_csv(OUTPUT_FILE)
        already_verified = set(verified_df["original_index"])
        print(f"Resuming verification: {len(already_verified)} rows already verified.")
    else:
        verified_df = pd.DataFrame()
        already_verified = set()

    remaining_df = source_df[~source_df["original_index"].isin(already_verified)].copy()
    total_rows = len(source_df)
    remaining_rows = len(remaining_df)

    if remaining_rows == 0:
        print("All rows are already verified. Nothing to do.")
        return

    print(f"Total rows: {total_rows:,}")
    print(f"Pending verification: {remaining_rows:,}")
    print(f"Processing in outer batches of {BATCH_SIZE} rows and {PROMPT_CHUNK_SIZE} messages per prompt.\n")

    all_results = verified_df.copy()
    start_time = time.time()

    for batch_start in range(0, remaining_rows, BATCH_SIZE):
        batch = remaining_df.iloc[batch_start : batch_start + BATCH_SIZE].copy()
        batch_index = batch_start // BATCH_SIZE + 1
        total_batches = (remaining_rows + BATCH_SIZE - 1) // BATCH_SIZE

        print("=" * 80)
        print(f"BATCH {batch_index}/{total_batches} | rows {batch_start + 1:,}–{batch_start + len(batch):,}")
        print("=" * 80)

        chunk: List[Dict[str, Any]] = []
        chunk_lookup: Dict[str, Dict[str, Any]] = {}
        batch_results: List[Dict[str, Any]] = []

        def flush_chunk():
            nonlocal chunk, chunk_lookup, batch_results
            if not chunk:
                return
            for attempt in range(1, MAX_RETRIES_PER_CHUNK + 1):
                prompt = build_chunk_prompt(chunk)
                try:
                    response_text = call_groq(prompt, api_key)
                    parsed = parse_json_array(response_text)
                    if len(parsed) != len(chunk):
                        raise ValueError("Mismatch between prompt size and response size.")

                    for item in parsed:
                        row_id = item.get("id")
                        linked = chunk_lookup.get(row_id)
                        if not linked:
                            continue

                        verification_is_otp = to_bool(item.get("is_otp_verified"))
                        verification_otp_intent = to_bool(item.get("otp_intent_verified"))
                        verification_is_phishing = to_bool(item.get("is_phishing_verified"))

                        needs_manual = (
                            (verification_is_otp is not pd.NA and verification_is_otp is False)
                            or (verification_otp_intent is not pd.NA and verification_otp_intent is False)
                            or (verification_is_phishing is not pd.NA and verification_is_phishing is False)
                            or (verification_is_otp is pd.NA)
                            or (verification_otp_intent is pd.NA)
                            or (verification_is_phishing is pd.NA)
                        )

                        batch_results.append(
                            {
                                "original_index": linked["original_index"],
                                "sms_text": linked["sms_text"],
                                "predicted_is_otp": linked["provided_is_otp"],
                                "predicted_otp_intent": linked["provided_otp_intent"],
                                "is_phishing": linked["provided_is_phishing"],
                                "verification_is_otp": verification_is_otp,
                                "verification_otp_intent": verification_otp_intent,
                                "verification_is_phishing": verification_is_phishing,
                                "verification_model": VERIFICATION_MODEL,
                                "verification_badge": VERIFICATION_BADGE if not needs_manual else None,
                                "verification_timestamp": datetime.utcnow().isoformat() + "Z",
                                "needs_manual_review": needs_manual,
                            }
                        )

                    chunk = []
                    chunk_lookup = {}
                    return
                except Exception as exc:
                    if attempt < MAX_RETRIES_PER_CHUNK:
                        print(f"  Chunk retry {attempt}/{MAX_RETRIES_PER_CHUNK} failed: {exc}. Retrying...")
                        time.sleep(1.0)
                        continue
                    else:
                        print(f"  Chunk failed after {attempt} attempts: {exc}. Marking rows for manual review.")
                        for linked in chunk_lookup.values():
                            batch_results.append(
                                {
                                    "original_index": linked["original_index"],
                                    "sms_text": linked["sms_text"],
                                    "predicted_is_otp": linked["provided_is_otp"],
                                    "predicted_otp_intent": linked["provided_otp_intent"],
                                    "is_phishing": linked["provided_is_phishing"],
                                    "verification_is_otp": pd.NA,
                                    "verification_otp_intent": pd.NA,
                                    "verification_is_phishing": pd.NA,
                                    "verification_model": VERIFICATION_MODEL,
                                    "verification_badge": None,
                                    "verification_timestamp": datetime.utcnow().isoformat() + "Z",
                                    "needs_manual_review": True,
                                }
                            )
                        chunk = []
                        chunk_lookup = {}
                        return

        for idx, row in enumerate(batch.itertuples(index=False), start=1):
            row_dict = {
                "row_id": str(row.original_index),
                "original_index": row.original_index,
                "sms_text": row.sms_text if isinstance(row.sms_text, str) else "",
                "provided_is_otp": row.provided_is_otp,
                "provided_otp_intent": row.provided_otp_intent,
                "provided_is_phishing": row.provided_is_phishing,
            }
            chunk.append(row_dict)
            chunk_lookup[row_dict["row_id"]] = row_dict

            if len(chunk) >= PROMPT_CHUNK_SIZE:
                flush_chunk()
                time.sleep(SLEEP_BETWEEN_CHUNKS)

            if idx % 50 == 0 or idx == len(batch):
                processed_in_batch = len(batch_results)
                print(
                    f"  Processed {idx}/{len(batch)} rows in this batch | "
                    f"Verified rows collected: {processed_in_batch}"
                )

        flush_chunk()

        batch_df = pd.DataFrame(batch_results)
        all_results = merge_results(all_results, batch_df)
        write_outputs(all_results)

        total_verified = len(all_results)
        pending_rows = total_rows - total_verified
        elapsed = time.time() - start_time
        avg_per_row = elapsed / total_verified if total_verified else 0
        print(
            f"\nBatch {batch_index} complete. "
            f"Total verified: {total_verified:,} | Pending: {pending_rows:,} | "
            f"Elapsed: {elapsed/60:.1f} min | Avg per row: {avg_per_row:.2f}s"
        )

    print("\nVerification run finished. Results saved to:")
    print(f"  - {OUTPUT_FILE}")
    print(f"  - {DISAGREEMENT_FILE} (rows flagged for manual review)")
    print(f"  - {CHECKPOINT_FILE} (checkpoint metadata)")


if __name__ == "__main__":
    main()


