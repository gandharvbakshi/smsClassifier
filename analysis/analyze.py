"""
Phase 5 — analyze jury verdicts vs app verdicts.

Joins:
- The SMS classifier log CSV (app verdicts)
- jury_results.jsonl (one record per row × provider)

Produces:
- Per-axis confusion summary (is_otp, is_phishing, otp_intent)
- Jury agreement breakdown (3/3, 2/3, contested)
- Per-class precision/recall/F1 with Wilson 95% CIs
- Top systematic error patterns (sender prefix, body keyword)
- Sample of contested rows (need human audit)

Usage:
    python analyze.py
    python analyze.py --jury analysis/jury_results.jsonl --csv "sms classifier log 2 may .csv"
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "sms classifier log 2 may .csv"
DEFAULT_JURY = ROOT / "analysis" / "jury_results.jsonl"
DEFAULT_REPORT = ROOT / "analysis" / "analysis_report.md"
DEFAULT_CONTESTED = ROOT / "analysis" / "contested_rows.csv"


# ---------- Wilson 95% CI for a proportion ----------
def wilson(p_hat: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


# ---------- jury aggregation ----------
def consensus(verdicts: list[dict | None], field_: str):
    """Return (consensus_value, agreement_count, num_voters_who_voted)."""
    votes = [v[field_] for v in verdicts if v is not None]
    if not votes:
        return None, 0, 0
    counter = Counter(map(_hashable, votes))
    val, count = counter.most_common(1)[0]
    return _unhash(val), count, len(votes)


def _hashable(v):
    return ("__none__",) if v is None else ("v", v)


def _unhash(v):
    return None if v == ("__none__",) else v[1]


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--jury", type=Path, default=DEFAULT_JURY)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--contested", type=Path, default=DEFAULT_CONTESTED)
    ap.add_argument("--min-agreement", type=int, default=2,
                    help="Min voters that must agree to call a verdict 'jury truth'")
    args = ap.parse_args()

    # ---- load ----
    df = pd.read_csv(args.csv)
    df = df[df["section"] == "message"].copy()
    df["id"] = df["id"].astype(int)
    # Normalize app verdicts
    df["app_is_otp"] = df["is_otp"].map({True: True, "true": True, False: False, "false": False})
    df["app_is_phishing"] = df["is_phishing"].map({True: True, "true": True, False: False, "false": False})
    df["app_otp_intent"] = df["otp_intent"].where(df["otp_intent"].notna(), None)

    jury_records: dict[int, dict[str, dict]] = defaultdict(dict)
    bad_records = 0
    with args.jury.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if not rec.get("ok"):
                    bad_records += 1
                    continue
                jury_records[int(rec["row_id"])][rec["provider"]] = rec["verdict"]
            except Exception:
                bad_records += 1

    print(f"[analyze] CSV rows (message section): {len(df)}")
    print(f"[analyze] Jury rows with at least one OK verdict: {len(jury_records)}")
    print(f"[analyze] Skipped failed jury records: {bad_records}")

    # ---- compute consensus per row ----
    rows = []
    for _, r in df.iterrows():
        rid = int(r["id"])
        verdicts_by_provider = jury_records.get(rid, {})
        verdicts = list(verdicts_by_provider.values())
        n = len(verdicts)

        otp_val, otp_agree, _ = consensus(verdicts, "is_otp")
        phish_val, phish_agree, _ = consensus(verdicts, "is_phishing")
        intent_val, intent_agree, _ = consensus(verdicts, "otp_intent")

        rows.append({
            "row_id": rid,
            "sender": r["sender"],
            "body": r["body"],
            "phish_score": r["phish_score"],
            "app_is_otp": r["app_is_otp"],
            "app_is_phishing": r["app_is_phishing"],
            "app_otp_intent": r["app_otp_intent"],
            "n_voters": n,
            "jury_is_otp": otp_val,
            "jury_is_otp_agree": otp_agree,
            "jury_is_phishing": phish_val,
            "jury_is_phishing_agree": phish_agree,
            "jury_otp_intent": intent_val,
            "jury_otp_intent_agree": intent_agree,
        })

    a = pd.DataFrame(rows)

    # ---- jury agreement breakdown ----
    print()
    print("=== Jury voter coverage ===")
    print(a["n_voters"].value_counts().sort_index().to_string())

    print()
    print("=== Jury agreement on is_otp (rows with all 3 voters) ===")
    full = a[a["n_voters"] == 3]
    print(full["jury_is_otp_agree"].value_counts().sort_index().to_string())

    # ---- accuracy where jury is confident (>= min_agreement voters agree) ----
    def report_axis(axis: str, app_col: str, jury_col: str, agree_col: str,
                    min_n: int = 2, label: str = ""):
        # Use only rows where: enough voters AND enough agreement
        confident = a[(a["n_voters"] >= min_n) & (a[agree_col] >= args.min_agreement)].copy()
        if len(confident) == 0:
            return f"\n=== {label} ===\nNo confident jury verdicts.\n"

        tp = ((confident[app_col] == True) & (confident[jury_col] == True)).sum()
        fp = ((confident[app_col] == True) & (confident[jury_col] == False)).sum()
        fn = ((confident[app_col] == False) & (confident[jury_col] == True)).sum()
        tn = ((confident[app_col] == False) & (confident[jury_col] == False)).sum()

        prec_n = tp + fp
        rec_n = tp + fn
        precision = tp / prec_n if prec_n else 0.0
        recall = tp / rec_n if rec_n else 0.0
        accuracy = (tp + tn) / (tp + fp + fn + tn)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        prec_lo, prec_hi = wilson(precision, prec_n)
        rec_lo, rec_hi = wilson(recall, rec_n)
        acc_lo, acc_hi = wilson(accuracy, len(confident))

        out = []
        out.append(f"\n=== {label}  (n={len(confident)} confident jury verdicts) ===")
        out.append(f"  Confusion: TP={tp}  FP={fp}  FN={fn}  TN={tn}")
        out.append(f"  Accuracy:  {accuracy:.3f}   95% CI [{acc_lo:.3f}, {acc_hi:.3f}]")
        out.append(f"  Precision: {precision:.3f}   95% CI [{prec_lo:.3f}, {prec_hi:.3f}]   "
                   f"(of app's {prec_n} positives, {tp} are real)")
        out.append(f"  Recall:    {recall:.3f}   95% CI [{rec_lo:.3f}, {rec_hi:.3f}]   "
                   f"(of {rec_n} real positives, app caught {tp})")
        out.append(f"  F1:        {f1:.3f}")
        return "\n".join(out) + "\n"

    summary = []
    summary.append("# SMS Classifier Accuracy Audit\n")
    summary.append(f"Dataset: `{args.csv.name}` ({len(df)} message rows)\n")
    summary.append(f"Jury: 3 LLM judges (OpenAI gpt-4o-mini, Google gemini-2.5-flash-lite, "
                   f"DeepSeek deepseek-chat)\n")
    summary.append(f"Confidence floor: at least {args.min_agreement} judges must agree to "
                   f"count a row as 'jury truth'.\n")

    summary.append("## Coverage\n")
    cov = a["n_voters"].value_counts().sort_index()
    for k, v in cov.items():
        summary.append(f"- Rows with {k} voters: {v}\n")

    summary.append("\n## Headline metrics (app vs jury truth)\n")
    summary.append(report_axis("is_otp", "app_is_otp", "jury_is_otp",
                               "jury_is_otp_agree", label="OTP detection (is_otp)"))
    summary.append(report_axis("is_phishing", "app_is_phishing", "jury_is_phishing",
                               "jury_is_phishing_agree", label="Phishing detection (is_phishing)"))

    # ---- per-intent accuracy (for rows the jury agrees ARE OTPs) ----
    summary.append("\n## OTP intent accuracy\n")
    confident_otp = a[(a["jury_is_otp"] == True) & (a["jury_is_otp_agree"] >= args.min_agreement)
                      & (a["jury_otp_intent_agree"] >= args.min_agreement)].copy()
    if len(confident_otp) == 0:
        summary.append("No rows with confident OTP+intent jury verdicts.\n")
    else:
        intent_correct = (confident_otp["app_otp_intent"] == confident_otp["jury_otp_intent"]).sum()
        n = len(confident_otp)
        acc = intent_correct / n
        lo, hi = wilson(acc, n)
        summary.append(f"Of {n} messages where jury confidently says is_otp=True AND "
                       f"agrees on intent:\n")
        summary.append(f"- App's intent matches jury's intent: **{intent_correct}/{n} = "
                       f"{acc:.1%}** (95% CI [{lo:.1%}, {hi:.1%}])\n\n")

        # Cross-tab
        summary.append("### Confusion matrix (rows=jury intent, cols=app intent)\n\n")
        ct = pd.crosstab(confident_otp["jury_otp_intent"].fillna("(none)"),
                         confident_otp["app_otp_intent"].fillna("(none)"),
                         margins=True, margins_name="TOTAL")
        summary.append("```\n" + ct.to_string() + "\n```\n")

    # ---- top systematic errors ----
    summary.append("\n## Top systematic error patterns\n")
    # Errors = rows where jury confidently disagrees with app on is_otp
    errs = a[(a["jury_is_otp_agree"] >= args.min_agreement) &
             (a["app_is_otp"] != a["jury_is_otp"]) &
             a["app_is_otp"].notna() & a["jury_is_otp"].notna()].copy()

    summary.append(f"\nTotal confident is_otp errors: **{len(errs)}**\n")
    if len(errs):
        fp = errs[errs["app_is_otp"] == True]
        fn = errs[errs["app_is_otp"] == False]
        summary.append(f"- False positives (app said OTP, isn't): {len(fp)}\n")
        summary.append(f"- False negatives (app missed OTP): {len(fn)}\n")

        def sender_prefix(s):
            if not isinstance(s, str):
                return "(none)"
            parts = s.split("-")
            if len(parts) >= 2:
                return f"{parts[0]}-XXXXX-{parts[-1] if len(parts) > 2 else parts[1][:1]}"
            return s[:6]

        summary.append("\n### False positives by sender prefix\n")
        if len(fp):
            top_fp = fp["sender"].apply(sender_prefix).value_counts().head(10)
            summary.append("```\n" + top_fp.to_string() + "\n```\n")

        summary.append("\n### False negatives by sender prefix\n")
        if len(fn):
            top_fn = fn["sender"].apply(sender_prefix).value_counts().head(10)
            summary.append("```\n" + top_fn.to_string() + "\n```\n")

        # Sample 5 of each
        def fmt_row(r):
            body = (r["body"] or "")[:120].replace("\n", " ")
            return (f"  - row {r['row_id']:>5} sender={r['sender']:<15} app=otp:{r['app_is_otp']} "
                    f"jury=otp:{r['jury_is_otp']} | {body}")

        summary.append("\n### Sample false positives (app says OTP, jury says no)\n")
        for _, r in fp.head(8).iterrows():
            summary.append(fmt_row(r) + "\n")
        summary.append("\n### Sample false negatives (app says not-OTP, jury says is OTP)\n")
        for _, r in fn.head(8).iterrows():
            summary.append(fmt_row(r) + "\n")

    # ---- contested rows for human audit ----
    contested = a[
        # jury split (no majority)
        ((a["n_voters"] == 3) & (a["jury_is_otp_agree"] < 2))
        | ((a["n_voters"] == 3) & (a["jury_is_phishing_agree"] < 2))
        # OR jury fully agrees but disagrees with app (need to confirm jury is right)
        | ((a["jury_is_otp_agree"] == 3) & (a["app_is_otp"] != a["jury_is_otp"]))
        | ((a["jury_is_phishing_agree"] == 3) & (a["app_is_phishing"] != a["jury_is_phishing"]))
    ].copy()
    contested.to_csv(args.contested, index=False)

    summary.append(f"\n## Contested rows for human audit\n")
    summary.append(f"Saved to `{args.contested.name}` ({len(contested)} rows).\n")
    summary.append("These are rows where the jury split, OR the jury unanimously "
                   "disagreed with the app (i.e. high-confidence app errors that should be "
                   "spot-checked against the LLMs).\n")

    args.report.write_text("".join(summary), encoding="utf-8")
    print(f"\n[analyze] wrote report: {args.report}")
    print(f"[analyze] wrote contested rows: {args.contested}")


if __name__ == "__main__":
    main()
