"""Compare synthetic cases on production and a zero-traffic candidate revision."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import threading
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
PURPOSES = {
    "APP_LOGIN_OTP": "sign in to your Acme social app account",
    "FINANCIAL_LOGIN_OTP": "log in to your Acme online banking account",
    "APP_ACCOUNT_CHANGE_OTP": "change your Acme account email address",
    "BANK_OR_CARD_TXN_OTP": "approve your Acme card payment of INR 299",
    "UPI_TXN_OR_PIN_OTP": "reset your Acme UPI PIN",
    "DELIVERY_OR_SERVICE_OTP": "verify receipt of your Acme parcel with the delivery agent",
    "KYC_OR_ESIGN_OTP": "electronically sign your Acme document",
    "GENERIC_APP_ACTION_OTP": "publish your Acme marketplace listing",
}


def routed_cases():
    # Formatted numeric OTPs bypass the contiguous 4-8 digit heuristic and
    # exercise the unchanged ML-to-Groq path without a special routing flag.
    return [
        dict(id=f"routed_{intent}_{index}", text=f"Your OTP is {code} to {purpose}. Valid for five minutes. Never share it.",
             sender="ACME", expected_is_otp=True, expected_intent=intent, slice="formatted_numeric_otp")
        for intent, purpose in PURPOSES.items()
        for index, code in enumerate(("482 917", "482-917", "482917357"))
    ]


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def run(base_url, cases, workers):
    local = threading.local()

    def one(case):
        if not hasattr(local, "session"):
            local.session = requests.Session()
        start = time.perf_counter()
        response = local.session.post(base_url.rstrip("/") + "/api/classify", json={"text": case["text"], "sender": case["sender"]}, timeout=(3, 15))
        elapsed = (time.perf_counter() - start) * 1000
        with response:
            response.raise_for_status()
            body = response.json()
        reasons = body.get("reasons", [])
        return dict(case_id=case["id"], status=response.status_code, elapsed_ms=elapsed,
                    semantic={key: body[key] for key in ("isOtp", "otpIntent", "isPhishing")},
                    response_keys=sorted(body),
                    groq_succeeded=any(str(r).startswith("Groq intent=") for r in reasons),
                    groq_failed=any(str(r).startswith("Groq intent failed:") for r in reasons))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, cases))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-url", required=True)
    parser.add_argument("--baseline-url", default="https://sms-ensemble-hhpimusmbq-el.a.run.app")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    corpus = ROOT / "backend/evaluation/groq-20260907/cases.jsonl"
    stable = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines()]
    routed = routed_cases()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "routed_cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in routed), encoding="utf-8")
    health = {}
    for label, url in (("baseline", args.baseline_url), ("candidate", args.candidate_url)):
        start = time.perf_counter()
        response = requests.get(url.rstrip("/") + "/api/health", timeout=(3, 30))
        response.raise_for_status()
        health[label] = dict(status=response.status_code, elapsed_ms=(time.perf_counter() - start) * 1000, body=response.json())
    if health["candidate"]["body"].get("groqModel") != "qwen/qwen3.6-27b":
        raise RuntimeError("Candidate health does not report the exact Qwen model ID")
    results = {}
    for label, url in (("baseline", args.baseline_url), ("candidate", args.candidate_url)):
        print(f"Checking {label}: {len(stable) + len(routed)} cases", flush=True)
        results[label] = run(url, stable + routed, workers=4)
        (args.output_dir / f"{label}.json").write_text(json.dumps(results[label], indent=2) + "\n", encoding="utf-8")
    baseline = {r["case_id"]: r for r in results["baseline"]}
    candidate = {r["case_id"]: r for r in results["candidate"]}
    stable_mismatches = [c["id"] for c in stable if candidate[c["id"]]["semantic"] != baseline[c["id"]]["semantic"]]
    routed_mismatches = [c["id"] for c in routed if candidate[c["id"]]["semantic"]["otpIntent"] != c["expected_intent"] or not candidate[c["id"]]["semantic"]["isOtp"]]
    flag_mismatches = [c["id"] for c in routed if any(candidate[c["id"]]["semantic"][key] != baseline[c["id"]]["semantic"][key] for key in ("isOtp", "isPhishing"))]
    key_mismatches = [cid for cid in candidate if candidate[cid]["response_keys"] != baseline[cid]["response_keys"]]
    summary = dict(health=health, baseline_url=args.baseline_url, candidate_url=args.candidate_url,
                   stable_cases=len(stable), stable_mismatches=stable_mismatches,
                   routed_cases=len(routed), routed_intent_mismatches=routed_mismatches,
                   routed_flag_mismatches=flag_mismatches, response_key_mismatches=key_mismatches,
                   baseline_routed_failures=sum(baseline[c["id"]]["groq_failed"] for c in routed),
                   candidate_routed_successes=sum(candidate[c["id"]]["groq_succeeded"] for c in routed))
    for label, records in results.items():
        routed_latencies = [r["elapsed_ms"] for r in records if r["case_id"].startswith("routed_")]
        summary[label + "_routed_latency_ms"] = dict(p50=percentile(routed_latencies, .5), p95=percentile(routed_latencies, .95), max=max(routed_latencies))
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    passed = not (stable_mismatches or routed_mismatches or flag_mismatches or key_mismatches) and summary["candidate_routed_successes"] == len(routed)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
