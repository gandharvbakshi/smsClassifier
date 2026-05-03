"""Single-call Google key smoke test with the real SMS prompt."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "app" / ".env")
key = os.getenv("GOOGLE_API_KEY")
print(f"key length: {len(key) if key else 'MISSING'}")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jury_judge import JUDGE_PROMPT  # reuse the actual prompt

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

genai.configure(api_key=key)
import sys
TARGETS = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
target = sys.argv[1] if len(sys.argv) > 1 else TARGETS[0]
print(f"trying model: {target}")
m = genai.GenerativeModel(target)

prompt = (JUDGE_PROMPT
          .replace("{sender}", "JX-ICICIT-S")
          .replace("{body}", "095440 is One-Time Password for INR 388.00 transaction towards Swiggy Limi using ICICI Bank Credit Card XX7007. OTPs are SECRET. DO NOT disclose"))

# Disable all safety filters; SMS classification should not need safety blocks.
safety = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

try:
    resp = m.generate_content(
        prompt,
        generation_config={
            "temperature": 0.0,
            "max_output_tokens": 2000,
            "response_mime_type": "application/json",
        },
        safety_settings=safety,
    )
    print("---")
    print(f"finish_reason: {resp.candidates[0].finish_reason}")
    print(f"safety_ratings: {resp.candidates[0].safety_ratings}")
    if hasattr(resp, "usage_metadata"):
        print(f"in_tokens={resp.usage_metadata.prompt_token_count} "
              f"out_tokens={resp.usage_metadata.candidates_token_count}")
    print(f"text: {resp.text!r}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    if 'resp' in dir():
        print("candidates:", resp.candidates)
