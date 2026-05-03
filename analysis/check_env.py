"""Verify required API keys exist in app/.env without printing them."""
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).resolve().parent.parent / "app" / ".env"
print(f"loading: {env_path}  exists={env_path.exists()}")
load_dotenv(env_path)
for key in ["OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY"]:
    val = os.getenv(key)
    if val:
        print(f"  {key}: set (length={len(val)})")
    else:
        print(f"  {key}: MISSING")
