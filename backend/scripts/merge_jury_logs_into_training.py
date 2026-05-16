"""
Merge device SMS logs + LLM jury JSONL into the canonical LightGBM training CSV.

Produces a NEW CSV (never overwrites master unless you rename it manually).
Use that file as --train-csv for test_models_on_synthetic.py (with --force-retrain).

Consensus rule (deterministic):
    The winning label must appear >= min-agreement votes.
    Rows with unresolved ties / insufficient agreement are skipped (reported).

Usage (from SMS Classifier mono-repo root):

    cd backend
    python scripts/merge_jury_logs_into_training.py \\
      --master data/classification_results_with_phishing_llm_balanced_with_sender.csv \\
      --device-log "../../android_sms_classifier/sms classifier log 2 may .csv" \\
      --jury "../../android_sms_classifier/analysis/jury_results.jsonl" \\
      --output data/classification_training_merged_jury_may2026.csv

Dry run (statistics only):

    python scripts/merge_jury_logs_into_training.py --dry-run ...

"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# -----------------------------------------------------------------------------
# Jury consensus (same semantics as analyze.py, but rejects weak majorities)


def _hashable(v):
    return ("__none__",) if v is None else ("v", v)


def _unhash(v):
    return None if v == ("__none__",) else v[1]


def consensus_vote(verdicts: list[dict], field_: str):
    votes = [v[field_] for v in verdicts if v is not None]
    if not votes:
        return None, 0, 0
    counter = Counter(map(_hashable, votes))
    val, count = counter.most_common(1)[0]
    return _unhash(val), count, len(votes)


def consensus_with_floor(
    verdicts: list[dict], field_: str, min_agreement: int
) -> tuple[Optional[Any], int, int]:
    """Return (value or None if top label has <min_agreement votes), top_count, n_voters."""
    val, count, nv = consensus_vote(verdicts, field_)
    if val is None or count < min_agreement:
        return None, count, nv
    return val, count, nv


def load_jury_records(path: Path) -> dict[int, dict[str, dict]]:
    by_row: dict[int, dict[str, dict]] = defaultdict(dict)
    with path.open(encoding="utf-8") as f:
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
            by_row[int(rec["row_id"])][rec["provider"]] = rec["verdict"]
    return by_row


def normalize_dedupe_key(sender: str, body: str) -> str:
    s = " ".join(str(sender or "").strip().lower().split())
    b = " ".join(str(body or "").strip().lower().split())
    return f"{s}|||{b}"


def build_jury_training_rows(
    device_log: pd.DataFrame,
    jury_map: dict[int, dict[str, dict]],
    min_agreement: int,
    batch_tag: str,
):
    msgs = device_log[device_log["section"] == "message"].copy()
    msgs["id"] = msgs["id"].astype(int)

    rows = []
    stats = defaultdict(int)

    for _, r in msgs.iterrows():
        rid = int(r["id"])
        body = "" if pd.isna(r.get("body")) else str(r["body"])
        sender_raw = "" if pd.isna(r.get("sender")) else str(r["sender"])

        verdicts_by = jury_map.get(rid)
        if not verdicts_by:
            stats["no_jury"] += 1
            continue

        verdicts = list(verdicts_by.values())
        otp_val, otp_cnt, nv = consensus_with_floor(
            verdicts, "is_otp", min_agreement
        )
        ph_val, ph_cnt, _ = consensus_with_floor(
            verdicts, "is_phishing", min_agreement
        )
        if otp_val is None:
            stats["reject_is_otp_tie_or_low"] += 1
            continue
        if ph_val is None:
            stats["reject_is_phishing_tie_or_low"] += 1
            continue

        intent_val, int_cnt, _ = consensus_vote(verdicts, "otp_intent")
        is_otp = bool(otp_val)
        # Intent: OTP rows need coherent intent votes; ambiguous → generic bucket
        if not is_otp:
            predicted_intent = "NOT_OTP"
        else:
            if int_cnt >= min_agreement and intent_val is not None:
                predicted_intent = str(intent_val)
            else:
                predicted_intent = "GENERIC_APP_ACTION_OTP"
                stats["intent_fallback_generic"] += 1

        stats["accepted"] += 1
        rows.append(
            {
                "sms_text": body,
                "sender": sender_raw,
                "predicted_is_otp": bool(is_otp),
                "predicted_otp_intent": predicted_intent,
                "classification_status": "jury_gold",
                "batch_number": batch_tag,
                "is_phishing_original": bool(ph_val),
                "log_row_id": rid,
                "_dedupe_key": normalize_dedupe_key(sender_raw, body),
                "jury_n_voters": nv,
                "jury_otp_vote_strength": otp_cnt,
                "jury_phish_vote_strength": ph_cnt,
            }
        )

    df = pd.DataFrame(rows)
    return df, dict(stats)


def merge_with_master(
    master: pd.DataFrame,
    jury_df: pd.DataFrame,
    mode: str,
) -> tuple[pd.DataFrame, dict]:
    """
    mode:
        append_skip_dup — strip jury rows whose _dedupe_key already exists on master.
        append_all — append every accepted jury row (may duplicate corpus).
        supersede — drop master rows with matching dedupe keys, then concat jury rows.
    """
    meta = defaultdict(int)

    master = master.copy()
    master["_dedupe_key"] = [
        normalize_dedupe_key(s, t)
        for s, t in zip(
            master["sender"].fillna("").astype(str),
            master["sms_text"].fillna("").astype(str),
        )
    ]

    jd = jury_df.copy()
    master_keys = set(master["_dedupe_key"])

    meta["master_rows_before_merge"] = len(master)

    if mode == "supersede":
        keys_to_replace = set(jd["_dedupe_key"])
        before = len(master)
        master_core = master[~master["_dedupe_key"].isin(keys_to_replace)].drop(
            columns=["_dedupe_key"]
        )
        meta["master_rows_removed_for_supersede"] = before - len(master_core)
        jd_kept = jd
        meta["jury_rows_kept"] = len(jd_kept)
    elif mode == "append_skip_dup":
        jd_kept = jd[~jd["_dedupe_key"].isin(master_keys)].copy()
        meta["jury_skipped_already_in_master"] = len(jd) - len(jd_kept)
        meta["jury_rows_kept"] = len(jd_kept)
        master_core = master.drop(columns=["_dedupe_key"])
    elif mode == "append_all":
        jd_kept = jd
        meta["jury_skipped_already_in_master"] = 0
        meta["jury_rows_kept"] = len(jd_kept)
        master_core = master.drop(columns=["_dedupe_key"])
    else:
        raise ValueError(f"Unknown mode: {mode}")

    jd_kept = jd_kept.drop(
        columns=[
            "_dedupe_key",
            "log_row_id",
            "jury_n_voters",
            "jury_otp_vote_strength",
            "jury_phish_vote_strength",
        ],
        errors="ignore",
    )

    m_oi = pd.to_numeric(master_core["original_index"], errors="coerce")
    next_ix = int(m_oi.max()) + 1 if m_oi.notna().any() else 1
    jd_kept.insert(
        0,
        "original_index",
        range(next_ix, next_ix + len(jd_kept)),
    )

    cols_master = master_core.columns.tolist()
    for miss in cols_master:
        if miss not in jd_kept.columns:
            jd_kept[miss] = pd.NA
    jd_kept = jd_kept[cols_master]

    merged = pd.concat([master_core, jd_kept], ignore_index=True, sort=False)
    meta["final_rows"] = len(merged)
    return merged, dict(meta)


def main():
    parser = argparse.ArgumentParser(description="Merge jury-labeled SMS log into LightGBM training CSV.")
    default_master = Path(__file__).resolve().parents[1] / "data" / "classification_results_with_phishing_llm_balanced_with_sender.csv"

    repo_root_candidate = Path(__file__).resolve().parents[2]
    android = repo_root_candidate / "android_sms_classifier"
    default_log = android / "sms classifier log 2 may .csv"
    default_jury = android / "analysis" / "jury_results.jsonl"

    parser.add_argument("--master", type=Path, default=default_master, help="Existing training CSV (73k canonical file).")
    parser.add_argument("--device-log", type=Path, default=default_log, help='Device export CSV (section/message rows).')
    parser.add_argument("--jury", type=Path, default=default_jury, help="jury_results.jsonl from jury_judge.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "data"
        / "classification_training_merged_jury_may2026.csv",
        help="Output merged CSV path.",
    )
    parser.add_argument("--backup-master", action="store_true", help=f"Timestamp-copy --master beside output before merge.")
    parser.add_argument("--min-agreement", type=int, default=2)
    parser.add_argument(
        "--mode",
        choices=("append_skip_dup", "append_all", "supersede"),
        default="append_skip_dup",
        help="How to fuse jury rows onto master corpus.",
    )
    parser.add_argument("--batch-tag", type=str, default="jury_may2026", help='batch_number stored for appended rows.')
    parser.add_argument("--dry-run", action="store_true", help="Statistics only — do not write output.")
    args = parser.parse_args()

    if not args.master.exists():
        raise SystemExit(f"Master CSV not found: {args.master}")
    if not args.device_log.exists():
        raise SystemExit(f"Device log not found: {args.device_log}")
    if not args.jury.exists():
        raise SystemExit(f"Jury JSONL not found: {args.jury}")

    print(f"[merge] Master:        {args.master}")
    print(f"[merge] Device log:    {args.device_log}")
    print(f"[merge] Jury:          {args.jury}")
    print(f"[merge] Mode:          {args.mode}")
    print(f"[merge] Min agreement: {args.min_agreement}")

    jury_map = load_jury_records(args.jury)
    print(f"[merge] Jury OK row_ids indexed: {len(jury_map)}")

    raw_log = pd.read_csv(args.device_log)
    jury_df, j_stats = build_jury_training_rows(
        raw_log, jury_map, args.min_agreement, args.batch_tag
    )

    print("\n[Jury cohort stats]")
    for k, v in sorted(j_stats.items()):
        print(f"  {k}: {v}")
    print(f"[merge] Accepted jury rows: {len(jury_df)}")

    master = pd.read_csv(args.master, low_memory=False)
    print(f"[merge] Master rows: {len(master)}")

    merged, m_stats = merge_with_master(master, jury_df, args.mode)
    print("\n[Fusion stats]")
    for k, v in sorted(m_stats.items()):
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n[merge] Dry run — skipping write.")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.backup_master:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup = args.output.parent / f"{args.master.stem}_backup_{stamp}.csv"
        shutil.copy2(args.master, backup)
        print(f"[merge] Backup master -> {backup}")

    merged.to_csv(args.output, index=False)
    print(f"\n[merge] Wrote {len(merged)} rows -> {args.output}")

    outp = args.output.as_posix()
    print(f"""
=== Next steps (run from `{Path(__file__).resolve().parents[1].as_posix()}` with deps installed) ===

1. Compare supervised metrics (writes model_comparison_results/):
       python scripts/train_lightgbm_comparison.py --source {outp}

2. Retrain pickles under trained_models/ + benchmark synthetic hold-out:
       python scripts/test_models_on_synthetic.py --train-csv "{outp}" --force-retrain

3. If metrics improve vs synthetic_test_results.json baseline, redeploy Docker
   with refreshed backend/trained_models/*.pkl.
""")


if __name__ == "__main__":
    main()
