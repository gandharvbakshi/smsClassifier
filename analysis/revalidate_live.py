"""Re-validate the LIVE Cloud Run backend against the LLM jury truth.

Procedure:
1. Load CSV (old app verdicts) + jury_results.jsonl (LLM verdicts).
2. Compute "jury truth": majority vote on (is_otp, otp_intent, is_phishing).
3. Pick a stratified sample biased toward rows where OLD APP disagreed with
   jury (the "risk zone" — these are where errors live, so the most informative
   re-test).
4. Send each sample row to /api/classify on the live backend.
5. Compare:
   - LIVE vs jury truth      → current backend accuracy
   - LIVE vs OLD app verdict → backend drift (did production change?)
6. Report per-axis metrics with Wilson 95% CIs.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "sms classifier log 2 may .csv"
JURY = ROOT / "analysis" / "jury_results.jsonl"
BACKEND = "https://sms-ensemble-hhpimusmbq-el.a.run.app/api/classify"


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def majority(votes: list, min_agree: int = 2):
    """Return (value, count) where value is the most-common, count is its votes,
    or (None, 0) if no value reaches min_agree."""
    if not votes:
        return None, 0
    c = Counter(votes)
    val, count = c.most_common(1)[0]
    if count >= min_agree:
        return val, count
    return None, 0


def load_truth() -> dict[int, dict]:
    """Build {row_id: {is_otp, otp_intent, is_phishing, app_*}} dict."""
    df = pd.read_csv(CSV)
    df = df[df["section"] == "message"].copy()
    df["id"] = df["id"].astype(int)

    jury_by_row: dict[int, list[dict]] = defaultdict(list)
    with JURY.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("ok"):
                    jury_by_row[int(rec["row_id"])].append(rec["verdict"])
            except Exception:
                continue

    truth: dict[int, dict] = {}
    for _, row in df.iterrows():
        rid = int(row["id"])
        verdicts = jury_by_row.get(rid, [])
        if not verdicts:
            continue
        otp_val, otp_n = majority([v["is_otp"] for v in verdicts])
        phish_val, phish_n = majority([v["is_phishing"] for v in verdicts])
        intent_val, intent_n = majority(
            [v["otp_intent"] for v in verdicts if v["is_otp"]],
        )
        truth[rid] = {
            "sender": row["sender"],
            "body": row["body"],
            "phish_score": row.get("phish_score", 0),
            # JURY TRUTH (what we believe is correct)
            "jury_is_otp": otp_val,
            "jury_is_otp_n": otp_n,
            "jury_otp_intent": intent_val,
            "jury_otp_intent_n": intent_n,
            "jury_is_phishing": phish_val,
            "jury_is_phishing_n": phish_n,
            # OLD APP VERDICT (what the CSV log captured)
            "old_app_is_otp": _coerce_bool(row["is_otp"]),
            "old_app_otp_intent": row["otp_intent"] if pd.notna(row["otp_intent"]) else None,
            "old_app_is_phishing": _coerce_bool(row["is_phishing"]),
        }
    return truth


def _coerce_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return None


def stratified_sample(truth: dict[int, dict], n: int, seed: int = 7) -> list[int]:
    """Pick rows: 70% from rows where OLD APP disagreed with JURY (where errors hid),
    30% from rows where they agreed (sanity-check we don't break good cases)."""
    random.seed(seed)
    disagreed_otp = [
        rid for rid, t in truth.items()
        if t["jury_is_otp"] is not None
        and t["old_app_is_otp"] is not None
        and t["jury_is_otp"] != t["old_app_is_otp"]
    ]
    agreed = [
        rid for rid, t in truth.items()
        if t["jury_is_otp"] is not None
        and t["old_app_is_otp"] is not None
        and t["jury_is_otp"] == t["old_app_is_otp"]
    ]
    n_disagree = min(int(n * 0.7), len(disagreed_otp))
    n_agree = min(n - n_disagree, len(agreed))
    sample = random.sample(disagreed_otp, n_disagree) + random.sample(agreed, n_agree)
    random.shuffle(sample)
    return sample


def call_live(sender: str, body: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        BACKEND,
        data=json.dumps({"sender": sender or "", "text": body or ""}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def call_live_async(sender: str, body: str, sem: asyncio.Semaphore, timeout: int = 30):
    async with sem:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, call_live, sender, body, timeout)


async def run_sample(truth: dict[int, dict], sample_ids: list[int], concurrency: int):
    sem = asyncio.Semaphore(concurrency)
    results: dict[int, dict] = {}

    async def one(rid: int):
        t = truth[rid]
        t0 = time.time()
        try:
            live = await call_live_async(str(t["sender"] or ""), str(t["body"] or ""), sem)
            results[rid] = {
                "ok": True,
                "live_is_otp": live["isOtp"],
                "live_otp_intent": live["otpIntent"] if live["isOtp"] else None,
                "live_is_phishing": live["isPhishing"],
                "live_phish_score": live["phishScore"],
                "live_reasons": live["reasons"],
                "elapsed_ms": int((time.time() - t0) * 1000),
            }
        except Exception as e:
            results[rid] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    tasks = [one(rid) for rid in sample_ids]
    # Show progress every 10
    print(f"[live] dispatching {len(tasks)} live-backend calls "
          f"(concurrency={concurrency})...")
    for i in range(0, len(tasks), 10):
        batch = tasks[i:i+10]
        await asyncio.gather(*batch)
        print(f"[live] {min(i+10, len(tasks))}/{len(tasks)} done")
    return results


def axis_metrics(label: str, app_vals: list, truth_vals: list, ci_n: int = None):
    """Print precision/recall/accuracy for a binary axis."""
    pairs = [(a, t) for a, t in zip(app_vals, truth_vals) if a is not None and t is not None]
    n = len(pairs)
    if n == 0:
        print(f"  {label}: no comparable rows")
        return
    tp = sum(1 for a, t in pairs if a is True and t is True)
    fp = sum(1 for a, t in pairs if a is True and t is False)
    fn = sum(1 for a, t in pairs if a is False and t is True)
    tn = sum(1 for a, t in pairs if a is False and t is False)
    acc = (tp + tn) / n
    prec_n = tp + fp
    rec_n = tp + fn
    prec = tp / prec_n if prec_n else 0.0
    rec = tp / rec_n if rec_n else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc_lo, acc_hi = wilson(acc, n)
    prec_lo, prec_hi = wilson(prec, prec_n) if prec_n else (0, 0)
    rec_lo, rec_hi = wilson(rec, rec_n) if rec_n else (0, 0)
    print(f"  {label}  (n={n})")
    print(f"    confusion:  TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    print(f"    accuracy:   {acc:.3f}  CI [{acc_lo:.3f}, {acc_hi:.3f}]")
    print(f"    precision:  {prec:.3f}  CI [{prec_lo:.3f}, {prec_hi:.3f}]")
    print(f"    recall:     {rec:.3f}  CI [{rec_lo:.3f}, {rec_hi:.3f}]")
    print(f"    F1:         {f1:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="sample size")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=ROOT / "analysis" / "revalidation_results.jsonl")
    args = ap.parse_args()

    print("[load] reading CSV + jury_results.jsonl ...")
    truth = load_truth()
    print(f"[load] rows with jury truth available: {len(truth)}")

    sample_ids = stratified_sample(truth, args.n, seed=args.seed)
    print(f"[sample] selected {len(sample_ids)} rows for re-validation")

    n_disagree = sum(
        1 for rid in sample_ids
        if truth[rid]["jury_is_otp"] != truth[rid]["old_app_is_otp"]
    )
    print(f"[sample]   - {n_disagree} are 'old-app vs jury disagreements' (high-risk zone)")
    print(f"[sample]   - {len(sample_ids) - n_disagree} are agreements (sanity check)")

    results = asyncio.run(run_sample(truth, sample_ids, args.concurrency))

    # write results
    with args.out.open("w", encoding="utf-8") as f:
        for rid, r in results.items():
            t = truth[rid]
            rec = {"row_id": rid, **{k: t[k] for k in t if k not in ("body",)}, **r}
            rec["body_preview"] = (t["body"] or "")[:80]
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    print(f"\n[write] saved per-row results to {args.out}")

    # collect for metrics
    live_otp, live_phish = [], []
    truth_otp, truth_phish = [], []
    old_otp, old_phish = [], []
    intent_match_live = 0
    intent_match_old = 0
    intent_n = 0
    failures = 0
    drift_live_vs_old_otp = 0
    for rid, r in results.items():
        if not r.get("ok"):
            failures += 1
            continue
        t = truth[rid]
        live_otp.append(r["live_is_otp"])
        live_phish.append(r["live_is_phishing"])
        truth_otp.append(t["jury_is_otp"])
        truth_phish.append(t["jury_is_phishing"])
        old_otp.append(t["old_app_is_otp"])
        old_phish.append(t["old_app_is_phishing"])
        if r["live_is_otp"] != t["old_app_is_otp"]:
            drift_live_vs_old_otp += 1
        # intent only when both live AND truth agree it's an OTP
        if (r["live_is_otp"] and t["jury_is_otp"] and t["jury_otp_intent"]):
            intent_n += 1
            if r["live_otp_intent"] == t["jury_otp_intent"]:
                intent_match_live += 1
            if t["old_app_otp_intent"] == t["jury_otp_intent"]:
                intent_match_old += 1

    print(f"\n[errors] {failures} backend call failures")
    print(f"\n=== LIVE backend vs JURY TRUTH (current accuracy) ===")
    axis_metrics("is_otp     ", live_otp, truth_otp)
    axis_metrics("is_phishing", live_phish, truth_phish)
    if intent_n:
        rate = intent_match_live / intent_n
        lo, hi = wilson(rate, intent_n)
        print(f"  intent agreement (n={intent_n}): "
              f"{rate:.1%}  CI [{lo:.1%}, {hi:.1%}]")
    print(f"\n=== OLD APP (CSV log) vs JURY TRUTH (for reference) ===")
    axis_metrics("is_otp     ", old_otp, truth_otp)
    axis_metrics("is_phishing", old_phish, truth_phish)
    if intent_n:
        rate = intent_match_old / intent_n
        lo, hi = wilson(rate, intent_n)
        print(f"  intent agreement (n={intent_n}): "
              f"{rate:.1%}  CI [{lo:.1%}, {hi:.1%}]")
    print(f"\n=== DRIFT: LIVE vs OLD APP ===")
    n_compare = len(live_otp)
    drift_pct = drift_live_vs_old_otp / n_compare if n_compare else 0
    print(f"  is_otp: {drift_live_vs_old_otp}/{n_compare} rows ({drift_pct:.1%}) "
          f"now classified differently than the CSV log")


if __name__ == "__main__":
    main()
