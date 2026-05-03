"""
LLM-as-jury classifier for SMS messages.

Sends each row of the SMS classification log to N independent LLM judges
(OpenAI, Google Gemini, DeepSeek), records each verdict to a JSONL file
that is RESUMABLE: re-running picks up exactly where it stopped without
double-spending API credits.

Designed for the SMS Classifier accuracy audit:
- Strict JSON schema (Pydantic-style validation, lightweight)
- Per-provider concurrency caps to respect rate limits
- Token + cost tracking per provider
- --limit N for stratified dry-runs before the full pass

Usage:
    python jury_judge.py --limit 20            # dry run
    python jury_judge.py                        # full run
    python jury_judge.py --models openai,google # subset of jury
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

# ---------- paths ----------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DATASET = PROJECT_ROOT / "sms classifier log 2 may .csv"
DEFAULT_ENV = PROJECT_ROOT / "app" / ".env"
DEFAULT_OUTPUT = SCRIPT_DIR / "jury_results.jsonl"

# ---------- canonical intent enum (mirrors OnDeviceClassifier.mapIntentIndex) ----------
INTENT_ENUM = [
    "APP_ACCOUNT_CHANGE_OTP",
    "APP_LOGIN_OTP",
    "BANK_OR_CARD_TXN_OTP",
    "DELIVERY_OR_SERVICE_OTP",
    "FINANCIAL_LOGIN_OTP",
    "GENERIC_APP_ACTION_OTP",
    "KYC_OR_ESIGN_OTP",
    "UPI_TXN_OR_PIN_OTP",
]
# Note: NOT_OTP is not a positive intent; we use null when is_otp=false.

JUDGE_PROMPT = """You are an expert classifier for SMS messages received by phone users in India.

Classify the SMS along three axes. Be strict and literal — do NOT guess.

1. is_otp (boolean): Does this SMS deliver a one-time code FOR the recipient to enter elsewhere
   to authenticate themselves or authorize an action?
   - TRUE: an OTP / verification code / login code / transaction approval code is present and the
     recipient is meant to USE it.
   - FALSE: transaction notifications ("Rs 500 spent on..."), bills, delivery status, marketing,
     bank balance alerts, recharge confirmations — even if numeric codes appear.

2. otp_intent (one of the enum values, or null if is_otp=false):
   - APP_ACCOUNT_CHANGE_OTP   - changing email/phone/password/profile on an app/account
   - APP_LOGIN_OTP             - logging into a generic (non-banking) app
   - BANK_OR_CARD_TXN_OTP      - authorizing a bank/card transaction (purchase, transfer)
   - DELIVERY_OR_SERVICE_OTP   - code to share with delivery agent / service technician
   - FINANCIAL_LOGIN_OTP       - logging into a bank / wallet / financial portal
   - GENERIC_APP_ACTION_OTP    - any other OTP not fitting the above
   - KYC_OR_ESIGN_OTP          - KYC verification, e-sign, Aadhaar verification
   - UPI_TXN_OR_PIN_OTP        - UPI transaction / setting UPI PIN / VPA actions

3. is_phishing (boolean): Is this message trying to deceive the recipient (suspicious link,
   fake-urgency credential-harvest, fake KYC expiry, fake delivery-failure-with-payment-link,
   fake refund, lottery scam, etc.)?
   - TRUE: includes deceptive links / requests for credentials / impersonation / scam patterns.
   - FALSE: legitimate bank/merchant/delivery notifications (even if from unrecognized sender),
     real OTPs, transactional alerts.

Respond with EXACTLY this JSON object and nothing else:
{"is_otp": true|false, "otp_intent": "ENUM_OR_NULL", "is_phishing": true|false, "confidence": 0.0-1.0, "reasoning": "max 30 words"}

SMS:
sender: {sender}
body: {body}
"""

# ---------- pricing (USD per 1M tokens, input/output) ----------
# Update these from provider pricing pages; used only for cost estimates.
PRICING = {
    "openai":   {"in": 0.15,  "out": 0.60,  "model": "gpt-4o-mini"},
    "google":   {"in": 0.10,  "out": 0.40,  "model": "gemini-2.5-flash-lite"},
    "deepseek": {"in": 0.27,  "out": 1.10,  "model": "deepseek-chat"},
}


@dataclass
class CostTracker:
    in_tokens: int = 0
    out_tokens: int = 0
    calls: int = 0
    errors: int = 0

    def add(self, in_t: int, out_t: int):
        self.in_tokens += in_t
        self.out_tokens += out_t
        self.calls += 1

    def cost_usd(self, provider: str) -> float:
        p = PRICING[provider]
        return (self.in_tokens * p["in"] + self.out_tokens * p["out"]) / 1_000_000


@dataclass
class JuryConfig:
    dataset_path: Path
    output_path: Path
    models: list[str]
    limit: int | None
    concurrency_per_model: int = 6
    # Per-provider overrides; falls back to concurrency_per_model.
    concurrency_overrides: dict[str, int] = field(default_factory=dict)
    seed: int = 42


# ============================================================
# Provider clients (lazy import so missing keys don't crash other providers)
# ============================================================

async def call_openai(client, sender: str, body: str) -> tuple[dict, int, int]:
    prompt = JUDGE_PROMPT.replace("{sender}", sender).replace("{body}", body)
    resp = await client.chat.completions.create(
        model=PRICING["openai"]["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    in_t = resp.usage.prompt_tokens if resp.usage else 0
    out_t = resp.usage.completion_tokens if resp.usage else 0
    return json.loads(content), in_t, out_t


async def call_deepseek(client, sender: str, body: str) -> tuple[dict, int, int]:
    # DeepSeek is OpenAI-compatible
    prompt = JUDGE_PROMPT.replace("{sender}", sender).replace("{body}", body)
    resp = await client.chat.completions.create(
        model=PRICING["deepseek"]["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    in_t = resp.usage.prompt_tokens if resp.usage else 0
    out_t = resp.usage.completion_tokens if resp.usage else 0
    return json.loads(content), in_t, out_t


async def call_google(model_obj, sender: str, body: str) -> tuple[dict, int, int]:
    prompt = JUDGE_PROMPT.replace("{sender}", sender).replace("{body}", body)
    # google-generativeai is sync; offload to executor to avoid blocking
    loop = asyncio.get_event_loop()

    # Disable safety filters: SMS dataset legitimately contains scam / phishing
    # / explicit content that we are TRYING to classify. Safety blocks would
    # cause silent verdict-loss exactly on the rows that matter most.
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    def _sync_call():
        return model_obj.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0,
                # 2000 is a safety margin for any thinking-token overhead even
                # though gemini-2.5-flash-lite has thinking off by default.
                "max_output_tokens": 2000,
                "response_mime_type": "application/json",
            },
            safety_settings=safety,
        )

    resp = await loop.run_in_executor(None, _sync_call)
    text = resp.text
    in_t = getattr(resp.usage_metadata, "prompt_token_count", 0) if hasattr(resp, "usage_metadata") else 0
    out_t = getattr(resp.usage_metadata, "candidates_token_count", 0) if hasattr(resp, "usage_metadata") else 0
    return json.loads(text), in_t, out_t


# ============================================================
# Schema validation
# ============================================================

def validate_verdict(raw: dict) -> dict:
    """Coerce/validate a model's JSON output to the canonical schema."""
    is_otp = bool(raw.get("is_otp", False))
    intent = raw.get("otp_intent")
    if intent in (None, "", "null", "NOT_OTP"):
        intent = None
    elif intent not in INTENT_ENUM:
        # Some models may return slight variations; keep raw for audit but
        # mark as invalid.
        intent = f"INVALID:{intent}"
    if not is_otp:
        intent = None
    is_phishing = bool(raw.get("is_phishing", False))
    confidence = float(raw.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(raw.get("reasoning", ""))[:300]
    return {
        "is_otp": is_otp,
        "otp_intent": intent,
        "is_phishing": is_phishing,
        "confidence": confidence,
        "reasoning": reasoning,
    }


# ============================================================
# Resumable JSONL log
# ============================================================

def load_existing_pairs(output_path: Path) -> set[tuple[int, str]]:
    """Only count *successful* records as 'done'. Failed records get retried on
    the next run, otherwise rate-limit errors would be permanent."""
    if not output_path.exists():
        return set()
    pairs: set[tuple[int, str]] = set()
    with output_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("ok"):
                    pairs.add((int(rec["row_id"]), rec["provider"]))
            except Exception:
                continue
    return pairs


def append_jsonl(output_path: Path, record: dict, lock: asyncio.Lock):
    # Synchronous append guarded by an asyncio lock (writes are tiny)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ============================================================
# Main loop
# ============================================================

async def judge_row(
    row_id: int,
    sender: str,
    body: str,
    provider: str,
    client_or_model,
    sem: asyncio.Semaphore,
    output_path: Path,
    write_lock: asyncio.Lock,
    tracker: CostTracker,
    max_retries: int = 4,
):
    async with sem:
        t0 = time.time()
        attempt = 0
        last_err: Exception | None = None
        while attempt <= max_retries:
            try:
                if provider == "openai":
                    verdict, in_t, out_t = await call_openai(client_or_model, sender, body)
                elif provider == "deepseek":
                    verdict, in_t, out_t = await call_deepseek(client_or_model, sender, body)
                elif provider == "google":
                    verdict, in_t, out_t = await call_google(client_or_model, sender, body)
                else:
                    raise ValueError(f"unknown provider {provider}")
                verdict = validate_verdict(verdict)
                tracker.add(in_t, out_t)
                elapsed_ms = int((time.time() - t0) * 1000)
                record = {
                    "row_id": row_id,
                    "provider": provider,
                    "model": PRICING[provider]["model"],
                    "verdict": verdict,
                    "in_tokens": in_t,
                    "out_tokens": out_t,
                    "elapsed_ms": elapsed_ms,
                    "attempts": attempt + 1,
                    "ok": True,
                }
                break
            except Exception as e:
                last_err = e
                msg = str(e)
                # Retry on rate limits / transient network errors
                is_retryable = (
                    "ResourceExhausted" in type(e).__name__
                    or "429" in msg
                    or "RateLimitError" in type(e).__name__
                    or "Timeout" in type(e).__name__
                    or "JSONDecodeError" in type(e).__name__
                )
                if is_retryable and attempt < max_retries:
                    # Exponential backoff with jitter; Google free tier is the
                    # primary culprit so 2^attempt seconds is conservative.
                    import random
                    backoff = (2 ** attempt) + random.random()
                    await asyncio.sleep(backoff)
                    attempt += 1
                    continue
                tracker.errors += 1
                record = {
                    "row_id": row_id,
                    "provider": provider,
                    "model": PRICING[provider]["model"],
                    "verdict": None,
                    "error": f"{type(e).__name__}: {msg[:300]}",
                    "attempts": attempt + 1,
                    "ok": False,
                }
                break
        async with write_lock:
            append_jsonl(output_path, record, write_lock)


async def run_jury(cfg: JuryConfig):
    load_dotenv(DEFAULT_ENV)
    df = pd.read_csv(cfg.dataset_path)
    df = df[df["section"] == "message"].copy()
    df = df.reset_index(drop=True)
    if cfg.limit:
        # Stratified-ish: take a spread by predicted label combos
        df = stratified_sample(df, cfg.limit, seed=cfg.seed)

    print(f"[jury] dataset rows to process: {len(df)}")
    print(f"[jury] models: {cfg.models}")
    print(f"[jury] output: {cfg.output_path}")

    existing = load_existing_pairs(cfg.output_path)
    print(f"[jury] resuming: {len(existing)} (row,model) verdicts already on disk")

    # ---- init clients ----
    clients: dict[str, Any] = {}
    trackers: dict[str, CostTracker] = {m: CostTracker() for m in cfg.models}

    if "openai" in cfg.models:
        from openai import AsyncOpenAI
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            print("[jury] WARNING: OPENAI_API_KEY missing — dropping openai")
            cfg.models.remove("openai")
        else:
            clients["openai"] = AsyncOpenAI(api_key=key)

    if "deepseek" in cfg.models:
        from openai import AsyncOpenAI
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            print("[jury] WARNING: DEEPSEEK_API_KEY missing — dropping deepseek")
            cfg.models.remove("deepseek")
        else:
            clients["deepseek"] = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com")

    if "google" in cfg.models:
        import google.generativeai as genai
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            print("[jury] WARNING: GOOGLE_API_KEY missing — dropping google")
            cfg.models.remove("google")
        else:
            genai.configure(api_key=key)
            clients["google"] = genai.GenerativeModel(PRICING["google"]["model"])

    if not cfg.models:
        print("[jury] no usable providers — aborting")
        sys.exit(1)

    # ---- per-provider semaphores ----
    sems = {
        m: asyncio.Semaphore(cfg.concurrency_overrides.get(m, cfg.concurrency_per_model))
        for m in cfg.models
    }
    for m, sem in sems.items():
        print(f"[jury] {m} concurrency = {sem._value}")
    write_lock = asyncio.Lock()

    # ---- build task list, skipping existing ----
    tasks = []
    for _, row in df.iterrows():
        row_id = int(row["id"])
        sender = str(row.get("sender", "") or "")
        body = str(row.get("body", "") or "")
        for m in cfg.models:
            if (row_id, m) in existing:
                continue
            tasks.append(
                judge_row(
                    row_id, sender, body, m, clients[m],
                    sems[m], cfg.output_path, write_lock, trackers[m],
                )
            )

    if not tasks:
        print("[jury] nothing to do (all already judged)")
    else:
        print(f"[jury] dispatching {len(tasks)} new judgments")
        # tqdm.gather gives a progress bar
        await tqdm.gather(*tasks, desc="judging")

    # ---- summary ----
    print("\n=== Jury run complete ===")
    total = 0.0
    for m, t in trackers.items():
        c = t.cost_usd(m)
        total += c
        print(f"  {m:<10}  calls={t.calls:>5}  errors={t.errors:>3}  "
              f"in_tok={t.in_tokens:>8}  out_tok={t.out_tokens:>7}  ${c:.4f}")
    print(f"  TOTAL: ${total:.4f}")


def stratified_sample(df: pd.DataFrame, n: int, seed: int = 42) -> pd.DataFrame:
    """Stratify by (is_otp, is_phishing, otp_intent) and (phish_score band)."""
    df = df.copy()
    df["__band"] = pd.cut(
        df["phish_score"].astype(float),
        bins=[-0.01, 0.1, 0.3, 0.7, 0.9, 1.01],
        labels=["very_low", "low", "mid", "high", "very_high"],
    )
    df["__strata"] = (
        df["is_otp"].astype(str) + "|" +
        df["is_phishing"].astype(str) + "|" +
        df["otp_intent"].astype(str).fillna("none") + "|" +
        df["__band"].astype(str)
    )
    counts = df["__strata"].value_counts()
    per_stratum = max(1, n // len(counts))
    out = (
        df.groupby("__strata", group_keys=False)
          .apply(lambda g: g.sample(min(len(g), per_stratum), random_state=seed))
    )
    if len(out) < n:
        remainder = df.drop(out.index).sample(min(n - len(out), len(df) - len(out)),
                                              random_state=seed)
        out = pd.concat([out, remainder])
    return out.head(n).drop(columns=["__band", "__strata"])


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--output",  type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--models",  type=str, default="openai,google,deepseek",
                   help="comma-separated provider list")
    p.add_argument("--limit",   type=int, default=None,
                   help="if set, stratified sample of this many rows (dry run)")
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--concurrency-google", type=int, default=None,
                   help="override concurrency for google (free tier is rate-limited)")
    p.add_argument("--concurrency-openai", type=int, default=None)
    p.add_argument("--concurrency-deepseek", type=int, default=None)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    args = parse_args()
    overrides: dict[str, int] = {}
    if args.concurrency_google is not None:
        overrides["google"] = args.concurrency_google
    if args.concurrency_openai is not None:
        overrides["openai"] = args.concurrency_openai
    if args.concurrency_deepseek is not None:
        overrides["deepseek"] = args.concurrency_deepseek
    cfg = JuryConfig(
        dataset_path=args.dataset,
        output_path=args.output,
        models=[m.strip() for m in args.models.split(",") if m.strip()],
        limit=args.limit,
        concurrency_per_model=args.concurrency,
        concurrency_overrides=overrides,
        seed=args.seed,
    )
    asyncio.run(run_jury(cfg))


if __name__ == "__main__":
    main()
