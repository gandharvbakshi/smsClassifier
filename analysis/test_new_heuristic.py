"""
Offline unit test for the NEW heuristic OTP classifier.

Loads the SMS classifier log CSV + the LLM jury verdicts, derives per-row
consensus jury truth, runs the NEW heuristic against every row, and reports:

  - Baseline:   App's recorded is_otp predictions vs jury truth.
                (This is the prod stack: OLD heuristic + ML, as it ran on the
                phone in early May.)

  - NEW heuristic alone:
                Predictions of the rewritten heuristic (is_otp AND
                confidence > 0.5, i.e. anything that would override ML
                in the server) vs jury truth.

  - Diff:       FPs the new heuristic suppresses, TPs it loses.

Run from the repo root:
    python android_sms_classifier/analysis/test_new_heuristic.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

# ---- paths ----
SCRIPT_DIR = Path(__file__).resolve().parent
ANDROID_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = ANDROID_ROOT.parent
CSV = ANDROID_ROOT / "sms classifier log 2 may .csv"
JURY = SCRIPT_DIR / "jury_results.jsonl"

# ---- import the NEW heuristic ----
sys.path.insert(0, str(PROJECT_ROOT))
from backend.classification.heuristic_classifier import HeuristicOtpClassifier  # noqa: E402

OVERRIDE_THRESHOLD = 0.5  # mirrors backend/scripts/android_backend_server.py


# -------------------- helpers --------------------

def consensus(verdicts: list[dict], field: str):
    """(value, agree_count, voter_count) — value=None means no voters."""
    votes = [v[field] for v in verdicts if v is not None]
    if not votes:
        return None, 0, 0
    counter = Counter(_h(v) for v in votes)
    val, count = counter.most_common(1)[0]
    return _u(val), count, len(votes)


def _h(v): return ("__none__",) if v is None else ("v", v)
def _u(v): return None if v == ("__none__",) else v[1]


def metrics(name: str, tp: int, fp: int, tn: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "name": name, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": p, "recall": r, "f1": f1, "specificity": spec,
        "support_pos": tp + fn, "support_neg": tn + fp,
    }


def fmt(m: dict) -> str:
    return (f"{m['name']:<32}  "
            f"P={m['precision']*100:5.1f}%  "
            f"R={m['recall']*100:5.1f}%  "
            f"F1={m['f1']*100:5.1f}%  "
            f"Spec={m['specificity']*100:5.1f}%  "
            f"(TP={m['tp']:4d}  FP={m['fp']:4d}  "
            f"TN={m['tn']:4d}  FN={m['fn']:3d})")


# -------------------- main --------------------

def main():
    print(f"[test] CSV       = {CSV}")
    print(f"[test] Jury      = {JURY}")
    if not CSV.exists():
        sys.exit(f"FATAL: CSV not found: {CSV}")
    if not JURY.exists():
        sys.exit(f"FATAL: jury results not found: {JURY}")

    # ---- load CSV ----
    df = pd.read_csv(CSV)
    df = df[df["section"] == "message"].copy()
    df["id"] = df["id"].astype(int)
    df["app_is_otp"] = df["is_otp"].map({True: True, "true": True, False: False, "false": False})
    df["body"] = df["body"].fillna("")
    df["sender"] = df["sender"].fillna("")
    print(f"[test] CSV message rows: {len(df)}")

    # ---- load jury ----
    jury: dict[int, dict[str, dict]] = defaultdict(dict)
    with JURY.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not rec.get("ok"):
                continue
            jury[int(rec["row_id"])][rec["provider"]] = rec["verdict"]
    print(f"[test] Jury rows with at least one OK verdict: {len(jury)}")

    # ---- iterate ----
    rows_with_truth = 0
    app_tp = app_fp = app_tn = app_fn = 0
    new_tp = new_fp = new_tn = new_fn = 0

    new_suppressed_fps: list[dict] = []   # OLD said yes (FP), NEW says no
    new_lost_tps: list[dict] = []         # JURY says yes, NEW says no
    new_kept_tps: list[dict] = []         # JURY says yes, NEW says yes
    new_new_fps: list[dict] = []          # JURY says no, NEW says yes (regression)

    for _, row in df.iterrows():
        rid = int(row["id"])
        verdicts = list(jury.get(rid, {}).values())
        if len(verdicts) < 2:
            continue
        otp_val, agree, _ = consensus(verdicts, "is_otp")
        if otp_val is None or agree < 2:
            continue
        rows_with_truth += 1

        truth = bool(otp_val)
        body = str(row["body"])
        sender = str(row["sender"])

        # baseline (app as deployed)
        app_pred = bool(row["app_is_otp"])
        if app_pred and truth:        app_tp += 1
        elif app_pred and not truth:  app_fp += 1
        elif not app_pred and not truth: app_tn += 1
        else: app_fn += 1

        # new heuristic alone
        h = HeuristicOtpClassifier.classify(body, sender)
        new_pred = bool(h["isOtp"]) and h["confidence"] > OVERRIDE_THRESHOLD
        if new_pred and truth:           new_tp += 1
        elif new_pred and not truth:     new_fp += 1
        elif not new_pred and not truth: new_tn += 1
        else: new_fn += 1

        # diff bookkeeping
        if app_pred and not truth and not new_pred:
            new_suppressed_fps.append({
                "row_id": rid, "sender": sender, "body": body[:160],
                "new_reasons": h["reasons"],
            })
        if truth and not new_pred:
            new_lost_tps.append({
                "row_id": rid, "sender": sender, "body": body[:160],
                "new_reasons": h["reasons"],
            })
        if truth and new_pred:
            new_kept_tps.append({"row_id": rid})
        if not truth and new_pred and not app_pred:
            new_new_fps.append({
                "row_id": rid, "sender": sender, "body": body[:160],
                "new_reasons": h["reasons"], "new_conf": h["confidence"],
            })

    print(f"[test] Rows with valid jury truth (>=2 voters, >=2 agree): {rows_with_truth}")
    print()

    app_m = metrics("APP (deployed: OLD+ML)", app_tp, app_fp, app_tn, app_fn)
    new_m = metrics("NEW heuristic ALONE",     new_tp, new_fp, new_tn, new_fn)
    print("=" * 100)
    print(fmt(app_m))
    print(fmt(new_m))
    print("=" * 100)
    print()

    # ---- diff narrative ----
    print(f"NEW heuristic SUPPRESSES {len(new_suppressed_fps)} of the APP's {app_fp} false positives.")
    print(f"  (These would no longer override ML in the server, so ML's correct 'no' would stand.)")
    print()
    print(f"NEW heuristic CATCHES   {len(new_kept_tps)} of the {app_tp + app_fn} jury-yes rows on its own.")
    print(f"NEW heuristic MISSES    {len(new_lost_tps)} jury-yes rows (would defer to ML).")
    print(f"NEW heuristic FIRES NEW {len(new_new_fps)} false positives (jury-no, OLD app said no, NEW says yes).")
    print()

    # ---- examples ----
    print("─" * 100)
    print(f"SUPPRESSED FALSE POSITIVES (sample of {min(8, len(new_suppressed_fps))} of {len(new_suppressed_fps)}):")
    print("─" * 100)
    for ex in new_suppressed_fps[:8]:
        print(f"  row {ex['row_id']:>4}  sender={ex['sender']!r}")
        print(f"    body: {ex['body']!r}")
        print(f"    NEW says: NOT OTP — {ex['new_reasons']}")
        print()

    if new_lost_tps:
        print("─" * 100)
        print(f"LOST TRUE POSITIVES (sample of {min(8, len(new_lost_tps))} of {len(new_lost_tps)}):")
        print("─" * 100)
        for ex in new_lost_tps[:8]:
            print(f"  row {ex['row_id']:>4}  sender={ex['sender']!r}")
            print(f"    body: {ex['body']!r}")
            print(f"    NEW says: NOT OTP — {ex['new_reasons']}")
            print()

    if new_new_fps:
        print("─" * 100)
        print(f"NEW REGRESSIONS — heuristic now FPs that OLD didn't (sample of "
              f"{min(8, len(new_new_fps))} of {len(new_new_fps)}):")
        print("─" * 100)
        for ex in new_new_fps[:8]:
            print(f"  row {ex['row_id']:>4}  sender={ex['sender']!r}  conf={ex['new_conf']:.2f}")
            print(f"    body: {ex['body']!r}")
            print(f"    NEW reasons: {ex['new_reasons']}")
            print()


if __name__ == "__main__":
    main()
