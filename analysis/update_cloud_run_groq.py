"""Safely update the Groq key on Cloud Run.

Reads GROQ_API_KEY from `android_sms_classifier/app/.env` (preferred)
or falls back to the parent project `.env`, then invokes gcloud with
the value passed via subprocess args (never echoed to console / shell history).

Usage:
    python analysis/update_cloud_run_groq.py             # dry run, prints plan
    python analysis/update_cloud_run_groq.py --apply     # actually deploy
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent           # android_sms_classifier
APP_ENV = ROOT / "app" / ".env"
PARENT_ENV = ROOT.parent / ".env"

PROJECT = "smsclassifier-478611"
REGION = "asia-south1"
SERVICE = "sms-ensemble"


def load_groq_key() -> tuple[str, Path]:
    for candidate in (APP_ENV, PARENT_ENV):
        if not candidate.exists():
            continue
        vals = dotenv_values(candidate)
        key = vals.get("GROQ_API_KEY")
        if key and key.strip() and not key.startswith("gsk_REPLACE"):
            return key.strip(), candidate
    raise SystemExit(
        "ERROR: no usable GROQ_API_KEY found in either:\n"
        f"  - {APP_ENV}\n  - {PARENT_ENV}\n"
        "Make sure one of them contains a real key starting with 'gsk_'."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="actually run the gcloud command (otherwise dry-run)")
    args = ap.parse_args()

    key, source = load_groq_key()
    redacted = f"{key[:8]}...{key[-4:]}"
    print(f"[update] loaded GROQ_API_KEY from: {source}")
    print(f"[update] key (redacted):           {redacted}  (length {len(key)})")
    print(f"[update] target project:           {PROJECT}")
    print(f"[update] target region:            {REGION}")
    print(f"[update] target service:           {SERVICE}")

    # On Windows, gcloud is actually gcloud.cmd. shutil.which finds the right one.
    import shutil
    gcloud_exe = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
    cmd = [
        gcloud_exe, "run", "services", "update", SERVICE,
        "--region", REGION,
        "--project", PROJECT,
        "--update-env-vars", f"GROQ_API_KEY={key}",
    ]
    # The displayed command redacts the key
    display_cmd = cmd[:-1] + [f"GROQ_API_KEY={redacted}"]
    print(f"\n[update] command (key redacted in display):")
    print("  " + " ".join(display_cmd))

    if not args.apply:
        print("\n[update] DRY RUN — pass --apply to actually deploy.")
        return

    print("\n[update] running gcloud ... (this takes ~30-90 seconds)")
    try:
        result = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[update] gcloud FAILED with exit code {e.returncode}")
        sys.exit(e.returncode)
    print("\n[update] gcloud succeeded.")

    # Health check the new revision
    print("\n[update] hitting /api/health to confirm new revision serves traffic ...")
    import time, urllib.request, json
    url = "https://sms-ensemble-hhpimusmbq-el.a.run.app/api/health"
    for attempt in range(5):
        time.sleep(2 if attempt else 0)
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                print(f"  attempt {attempt+1}: HTTP {resp.status}  body={body}")
                if resp.status == 200 and body.get("status") == "ok":
                    print("[update] HEALTHY.")
                    return
        except Exception as e:
            print(f"  attempt {attempt+1}: error {type(e).__name__}: {e}")
    print("[update] WARNING: health check did not return ok within 5 attempts. "
          "Check Cloud Run logs.")


if __name__ == "__main__":
    main()
