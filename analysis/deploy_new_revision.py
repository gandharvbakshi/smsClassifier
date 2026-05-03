"""Deploy a new Cloud Run revision with the latest pushed image.

Reads GROQ_API_KEY from `app/.env` (or parent `.env`) and passes it via
subprocess args (never echoed in shell history). Then waits for the new
revision to serve a healthy /api/health response.

Usage:
    python analysis/deploy_new_revision.py             # dry run
    python analysis/deploy_new_revision.py --apply     # deploy
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
APP_ENV = ROOT / "app" / ".env"
PARENT_ENV = ROOT.parent / ".env"

PROJECT = "smsclassifier-478611"
REGION = "asia-south1"
SERVICE = "sms-ensemble"
IMAGE = f"gcr.io/{PROJECT}/sms-ensemble:latest"
HEALTH_URL = "https://sms-ensemble-hhpimusmbq-el.a.run.app/api/health"


def load_groq_key():
    for candidate in (APP_ENV, PARENT_ENV):
        if not candidate.exists():
            continue
        vals = dotenv_values(candidate)
        key = vals.get("GROQ_API_KEY")
        if key and key.strip() and not key.startswith("gsk_REPLACE"):
            return key.strip(), candidate
    raise SystemExit(
        "ERROR: no usable GROQ_API_KEY found in either:\n"
        f"  - {APP_ENV}\n  - {PARENT_ENV}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    key, source = load_groq_key()
    redacted = f"{key[:8]}...{key[-4:]}"
    print(f"[deploy] image:       {IMAGE}")
    print(f"[deploy] service:     {SERVICE}  (project={PROJECT}, region={REGION})")
    print(f"[deploy] groq key:    {redacted}  (from {source})")

    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
    cmd = [
        gcloud, "run", "deploy", SERVICE,
        "--image", IMAGE,
        "--region", REGION,
        "--project", PROJECT,
        "--port", "8000",
        "--set-env-vars", f"GROQ_API_KEY={key}",
        "--platform", "managed",
        "--allow-unauthenticated",
        "--memory", "512Mi",
        "--cpu", "1",
        "--timeout", "60",
        "--max-instances", "10",
        "--quiet",
    ]
    print("[deploy] command (key redacted):")
    redacted_cmd = [c if not c.startswith("GROQ_API_KEY=") else f"GROQ_API_KEY={redacted}"
                    for c in cmd]
    print("  " + " ".join(redacted_cmd))

    if not args.apply:
        print("\n[deploy] DRY RUN — pass --apply to actually deploy.")
        return

    print("\n[deploy] running gcloud (60-180s) ...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[deploy] gcloud FAILED with exit code {e.returncode}")
        sys.exit(e.returncode)
    print("\n[deploy] gcloud succeeded.")

    print(f"\n[deploy] waiting for {HEALTH_URL} to return ok ...")
    for attempt in range(8):
        time.sleep(3 if attempt else 0)
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                print(f"  attempt {attempt+1}: HTTP {resp.status}  body={body}")
                if resp.status == 200 and body.get("status") == "ok":
                    print("[deploy] HEALTHY.")
                    return
        except Exception as e:
            print(f"  attempt {attempt+1}: error {type(e).__name__}: {e}")
    print("[deploy] WARNING: health check did not return ok within 8 attempts.")
    sys.exit(1)


if __name__ == "__main__":
    main()
