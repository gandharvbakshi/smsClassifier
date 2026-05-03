"""Show side-by-side: app verdict vs each LLM verdict, for the dry-run rows."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "sms classifier log 2 may .csv")
df = df[df["section"] == "message"].copy()
df["id"] = df["id"].astype(int)

results = []
with open(ROOT / "analysis" / "jury_dryrun.jsonl", encoding="utf-8") as f:
    for line in f:
        results.append(json.loads(line))

by_row: dict[int, dict] = {}
for r in results:
    by_row.setdefault(r["row_id"], {})[r["provider"]] = r

print(f"{'row':>5} | {'app_otp':<7} {'app_intent':<24} {'app_ph':<6} | "
      f"{'oai_otp':<7} {'oai_intent':<24} {'oai_ph':<6} | "
      f"{'ds_otp':<7} {'ds_intent':<24} {'ds_ph':<6} | body")
print("-" * 200)

for row_id, vmap in sorted(by_row.items()):
    rec = df[df["id"] == row_id].iloc[0]
    body = str(rec["body"])[:90].replace("\n", " ")
    app_otp = rec["is_otp"]
    app_intent = (rec["otp_intent"] or "")[:24] if pd.notna(rec["otp_intent"]) else ""
    app_ph = rec["is_phishing"]

    def fmt(provider):
        v = vmap.get(provider)
        if not v or not v.get("ok"):
            return ("ERR", "ERR", "ERR")
        verdict = v["verdict"]
        return (
            str(verdict["is_otp"])[:5],
            (verdict["otp_intent"] or "")[:24],
            str(verdict["is_phishing"])[:5],
        )

    o = fmt("openai")
    d = fmt("deepseek")
    print(f"{row_id:>5} | {str(app_otp)[:5]:<7} {app_intent:<24} {str(app_ph)[:5]:<6} | "
          f"{o[0]:<7} {o[1]:<24} {o[2]:<6} | "
          f"{d[0]:<7} {d[1]:<24} {d[2]:<6} | {body}")
