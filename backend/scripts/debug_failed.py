import pandas as pd
import requests
import json

df = pd.read_csv('classification_progress_checkpoint.csv')
fails = df[df['classification_status'] == 'failed']
row = fails.iloc[0]
sms_text = row['sms_text']

print('Original index:', row['original_index'])
print('SMS snippet:', sms_text[:200])

examples = """
Example 1:
SMS: "025061 is the OTP for INR 0975.54 transaction on SWIGGY using ICICI Bank Credit Card XX2583. OTPs are SECRET. DO NOT disclose."
Output: {"is_otp": true, "otp_intent": "BANK_OR_CARD_TXN_OTP"}

Example 2:
SMS: "INR 086.37 spent using ICICI Bank Card XX2427 on 28-Jun-25 on COOKIEMAN. Avl Limit: INR 9,49,437.53. If not you, call 1800 2662/SMS BLOCK 7007 to 0409041691."
Output: {"is_otp": false, "otp_intent": "NOT_OTP"}
""".strip()

prompt = f"""You are a classifier for OTP SMS messages. Your task is to identify if an SMS contains an OTP (One-Time Password) and classify its intent.

IMPORTANT RULES:
1. An OTP is ONLY a message that contains a numeric code used for verification/authentication (e.g., "123456 is your OTP", "Your OTP is 789012")
2. Transaction notifications, balance updates, payment confirmations, and account alerts are NOT OTPs - they are NOT_OTP
3. Only classify as OTP if the message explicitly contains an OTP code and asks you to use it for verification

{examples}

Now classify this SMS:
SMS: "{sms_text}"

Respond ONLY with valid JSON object (no explanation, no markdown):
{{"is_otp": true, "otp_intent": "BANK_OR_CARD_TXN_OTP"}}"""

resp = requests.post(
    'http://localhost:11434/api/generate',
    json={'model': 'deepseek-r1:8b', 'prompt': prompt, 'stream': False},
    timeout=60
)

print('HTTP status:', resp.status_code)
data = resp.json()
print('Keys:', list(data.keys()))
print('\nRaw response:\n')
print(data.get('response'))

