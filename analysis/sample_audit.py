"""Print rows for me (the assistant) to audit personally."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "sms classifier log 2 may .csv")
df = df[df["section"] == "message"].copy()
df["id"] = df["id"].astype(int)

# Load jury
jury: dict[int, dict[str, dict]] = {}
for line in open(ROOT / "analysis" / "jury_results.jsonl", encoding="utf-8"):
    rec = json.loads(line)
    if rec.get("ok"):
        jury.setdefault(int(rec["row_id"]), {})[rec["provider"]] = rec["verdict"]

# 1) Truly split rows: 3 voters, no majority on is_otp (1-1-1 effectively or split 2-1 still has majority)
# Actually with 3 voters, jury_is_otp_agree<2 means a 1-1-1 tie, but is_otp is binary so max is 2-1.
# Our analyzer logged 3 rows with agreement=2 — those are 2-1 splits. Let's get them.
split_rows = []
for rid, vmap in jury.items():
    if len(vmap) != 3:
        continue
    otp_votes = [v["is_otp"] for v in vmap.values()]
    if otp_votes.count(True) == 2 or otp_votes.count(False) == 2:
        # Could be 2-1 split. Skip the 3-0 cases.
        if 2 in (otp_votes.count(True), otp_votes.count(False)) and 1 in (otp_votes.count(True), otp_votes.count(False)):
            split_rows.append((rid, vmap))

print(f"=== Truly split is_otp rows (2-1 disagreement among 3 voters): {len(split_rows)} ===")
for rid, vmap in split_rows[:10]:
    rec = df[df["id"] == rid].iloc[0]
    body = str(rec["body"])[:200].replace("\n", " ")
    print(f"\nrow {rid}  sender={rec['sender']}  app_otp={rec['is_otp']}  app_intent={rec.get('otp_intent')}")
    print(f"  body: {body}")
    for prov, v in vmap.items():
        print(f"  {prov:<10}: is_otp={v['is_otp']} intent={v['otp_intent']} phish={v['is_phishing']} reason={v.get('reasoning','')[:120]}")

# 2) Sample 8 unanimous-disagreement rows (jury 3/3 says X, app says NOT X)
print("\n\n=== Sample unanimous-jury-disagrees-with-app rows (8 false positives, 8 false negatives) ===")
import random
random.seed(7)
unanimous_disagree_fp = []  # app says OTP, jury 3/3 says no
unanimous_disagree_fn = []  # app says not-OTP, jury 3/3 says yes
for rid, vmap in jury.items():
    if len(vmap) != 3:
        continue
    otp_votes = [v["is_otp"] for v in vmap.values()]
    if otp_votes.count(True) == 3:
        jury_otp = True
    elif otp_votes.count(False) == 3:
        jury_otp = False
    else:
        continue
    rec = df[df["id"] == rid]
    if rec.empty:
        continue
    rec = rec.iloc[0]
    app_otp = rec["is_otp"]
    if app_otp == True and jury_otp == False:
        unanimous_disagree_fp.append((rid, vmap))
    elif app_otp == False and jury_otp == True:
        unanimous_disagree_fn.append((rid, vmap))

random.shuffle(unanimous_disagree_fp)
random.shuffle(unanimous_disagree_fn)

print(f"\n--- 8 random false positives (n={len(unanimous_disagree_fp)} total) ---")
for rid, vmap in unanimous_disagree_fp[:8]:
    rec = df[df["id"] == rid].iloc[0]
    body = str(rec["body"])[:220].replace("\n", " ")
    print(f"row {rid}  sender={rec['sender']}  app_intent={rec.get('otp_intent')}")
    print(f"  body: {body}")

print(f"\n--- 8 random false negatives (n={len(unanimous_disagree_fn)} total) ---")
for rid, vmap in unanimous_disagree_fn[:8]:
    rec = df[df["id"] == rid].iloc[0]
    body = str(rec["body"])[:220].replace("\n", " ")
    print(f"row {rid}  sender={rec['sender']}")
    print(f"  body: {body}")
