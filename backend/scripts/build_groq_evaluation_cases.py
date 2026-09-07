"""Freeze deduplicated evaluation cases and measure routing without network calls."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    from backend.scripts.feedback_regression_cases import FEEDBACK_REGRESSION_CASES

    rows = list(csv.DictReader(args.synthetic_csv.open(encoding="utf-8-sig")))
    cases, seen = [], {}
    for index, row in enumerate(rows):
        case = dict(
            id=f"synthetic_{index:03d}", text=row["sms_text"].strip(),
            sender=row["sender"].strip() or "UNKNOWN",
            expected_is_otp=row["predicted_is_otp"].lower() == "true",
            expected_intent=row["predicted_otp_intent"],
            expected_is_phishing=row["is_phishing_original"].lower() == "true",
            slice="existing_synthetic",
        )
        key = (case["text"], case["sender"])
        gold = tuple(case[k] for k in ("expected_is_otp", "expected_intent", "expected_is_phishing"))
        if key in seen:
            assert seen[key] == gold, "Conflicting duplicate reference labels"
            continue
        seen[key] = gold
        cases.append(case)
    synthetic_unique = len(cases)
    for row in FEEDBACK_REGRESSION_CASES:
        cases.append(dict(
            id="regression_" + row.case_id, text=row.text, sender=row.sender,
            expected_is_otp=row.expected_is_otp,
            expected_intent=row.expected_otp_intent or ("NOT_OTP" if not row.expected_is_otp else None),
            expected_is_phishing=row.expected_is_phishing, slice="sanitized_regression",
        ))
    challenge = ROOT / "backend/evaluation/groq_replacement_challenge.jsonl"
    cases.extend(json.loads(line) for line in challenge.read_text(encoding="utf-8").splitlines() if line)
    assert len({case["id"] for case in cases}) == len(cases)
    assert len({(case["text"].strip(), case["sender"].strip()) for case in cases}) == len(cases)

    # These overrides affect this local evaluation process only. Never call
    # Web Risk, Groq, storage, or a hosted backend to discover routing.
    os.environ["GROQ_API_KEY"] = "offline-routing-placeholder"
    os.environ["WEB_RISK_MODE"] = "off"
    os.environ["GROQ_PHISHING_MODE"] = "off"
    os.environ["CLASSIFICATION_DIAGNOSTICS_ENABLED"] = "false"
    logging.disable(logging.CRITICAL)
    from backend.scripts import android_backend_server as server

    server._emit_structured_log = lambda *args, **kwargs: None
    server._enforce_classify_rate_limit = lambda *args, **kwargs: None
    routed = False

    def unavailable(*args, **kwargs):
        nonlocal routed
        routed = True
        raise RuntimeError("Offline retired-provider baseline")

    server.call_groq_full_classification = unavailable
    for case in cases:
        assert case["expected_intent"] is None or case["expected_intent"] in server.INTENT_LABELS
        routed = False
        result = server._classify_impl(server.ClassifyRequest(text=case["text"], sender=case["sender"]), None)
        case["groq_needed"] = routed
        case["baseline_output"] = dict(is_otp=result.isOtp, otp_intent=result.otpIntent, is_phishing=result.isPhishing)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "cases.jsonl"
    path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8")
    manifest = dict(
        original_synthetic_rows=len(rows), unique_synthetic_rows=synthetic_unique,
        duplicates_removed=len(rows) - synthetic_unique, total_cases=len(cases),
        slices=dict(Counter(c["slice"] for c in cases)),
        intent_counts=dict(Counter(c["expected_intent"] or "UNSCORED" for c in cases)),
        groq_needed=sum(c["groq_needed"] for c in cases),
        groq_needed_intent_scored=sum(c["groq_needed"] and c["expected_intent"] is not None for c in cases),
        source_sha256=hashlib.sha256(args.synthetic_csv.read_bytes()).hexdigest(),
        cases_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        caveat="Synthetic/project reference labels, not a random production sample. Routing uses exact deployed models with Web Risk off and provider unavailable. Unknown intent labels remain unscored.",
    )
    (args.output_dir / "corpus_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
