from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_existing_sms_corpus import evaluate_existing_sms_corpus, main, render_human_report


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "section",
        "id",
        "message_id",
        "sender",
        "body",
        "timestamp",
        "thread_id",
        "type",
        "is_otp",
        "otp_intent",
        "is_phishing",
        "phish_score",
        "reasons",
        "reviewed",
        "user_note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jury_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


class EvaluateExistingSmsCorpusTests(unittest.TestCase):
    def test_majority_metrics_and_privacy_safe_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus_path = root / "sms classifier log 2 may .csv"
            jury_path = root / "analysis" / "jury_results.jsonl"

            write_csv(
                corpus_path,
                [
                    {
                        "section": "message",
                        "id": "1",
                        "message_id": "",
                        "sender": "SENSITIVE-SENDER-1",
                        "body": "SECRET TOKEN X",
                        "timestamp": "1",
                        "thread_id": "10",
                        "type": "1",
                        "is_otp": "true",
                        "otp_intent": "BANK_OR_CARD_TXN_OTP",
                        "is_phishing": "false",
                        "phish_score": "0.01",
                        "reasons": "",
                        "reviewed": "false",
                        "user_note": "",
                    },
                    {
                        "section": "message",
                        "id": "2",
                        "message_id": "",
                        "sender": "SENSITIVE-SENDER-2",
                        "body": "SECRET TOKEN Y",
                        "timestamp": "2",
                        "thread_id": "20",
                        "type": "1",
                        "is_otp": "false",
                        "otp_intent": "NOT_OTP",
                        "is_phishing": "true",
                        "phish_score": "0.99",
                        "reasons": "",
                        "reviewed": "false",
                        "user_note": "",
                    },
                    {
                        "section": "message",
                        "id": "3",
                        "message_id": "",
                        "sender": "SENSITIVE-SENDER-3",
                        "body": "SECRET TOKEN Z",
                        "timestamp": "3",
                        "thread_id": "30",
                        "type": "1",
                        "is_otp": "false",
                        "otp_intent": "NOT_OTP",
                        "is_phishing": "false",
                        "phish_score": "0.02",
                        "reasons": "",
                        "reviewed": "false",
                        "user_note": "",
                    },
                    {
                        "section": "message",
                        "id": "4",
                        "message_id": "",
                        "sender": "SENSITIVE-SENDER-4",
                        "body": "SECRET TOKEN W",
                        "timestamp": "4",
                        "thread_id": "40",
                        "type": "1",
                        "is_otp": "true",
                        "otp_intent": "GENERIC_APP_ACTION_OTP",
                        "is_phishing": "false",
                        "phish_score": "0.03",
                        "reasons": "",
                        "reviewed": "false",
                        "user_note": "",
                    },
                    {
                        "section": "message",
                        "id": "4",
                        "message_id": "",
                        "sender": "SENSITIVE-SENDER-4B",
                        "body": "SECRET TOKEN W2",
                        "timestamp": "5",
                        "thread_id": "41",
                        "type": "1",
                        "is_otp": "true",
                        "otp_intent": "GENERIC_APP_ACTION_OTP",
                        "is_phishing": "false",
                        "phish_score": "0.04",
                        "reasons": "",
                        "reviewed": "false",
                        "user_note": "",
                    },
                ],
            )
            write_jury_jsonl(
                jury_path,
                [
                    {
                        "row_id": 1,
                        "provider": "a",
                        "model": "m1",
                        "verdict": {
                            "is_otp": True,
                            "otp_intent": "BANK_OR_CARD_TXN_OTP",
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 1,
                        "provider": "b",
                        "model": "m2",
                        "verdict": {
                            "is_otp": True,
                            "otp_intent": "BANK_OR_CARD_TXN_OTP",
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 1,
                        "provider": "c",
                        "model": "m3",
                        "verdict": {
                            "is_otp": False,
                            "otp_intent": None,
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 2,
                        "provider": "a",
                        "model": "m1",
                        "verdict": {
                            "is_otp": False,
                            "otp_intent": None,
                            "is_phishing": True,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 2,
                        "provider": "b",
                        "model": "m2",
                        "verdict": {
                            "is_otp": False,
                            "otp_intent": None,
                            "is_phishing": True,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 2,
                        "provider": "c",
                        "model": "m3",
                        "verdict": {
                            "is_otp": False,
                            "otp_intent": None,
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 3,
                        "provider": "a",
                        "model": "m1",
                        "verdict": {
                            "is_otp": False,
                            "otp_intent": None,
                            "is_phishing": True,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 3,
                        "provider": "b",
                        "model": "m2",
                        "verdict": {
                            "is_otp": False,
                            "otp_intent": None,
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 4,
                        "provider": "a",
                        "model": "m1",
                        "verdict": {
                            "is_otp": True,
                            "otp_intent": "APP_LOGIN_OTP",
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 4,
                        "provider": "b",
                        "model": "m2",
                        "verdict": {
                            "is_otp": True,
                            "otp_intent": "APP_LOGIN_OTP",
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 4,
                        "provider": "c",
                        "model": "m3",
                        "verdict": {
                            "is_otp": True,
                            "otp_intent": "BANK_OR_CARD_TXN_OTP",
                            "is_phishing": False,
                        },
                        "ok": True,
                    },
                    {
                        "row_id": 999,
                        "provider": "x",
                        "model": "y",
                        "verdict": None,
                        "error": "quota",
                        "ok": False,
                    },
                ],
            )

            report = evaluate_existing_sms_corpus(corpus_path, jury_path)
            self.assertEqual(report["corpus"]["rows"], 4)
            self.assertEqual(report["corpus"]["parsed_rows"], 5)
            self.assertEqual(report["corpus"]["duplicate_id_groups"], 1)
            self.assertEqual(report["corpus"]["duplicate_rows"], 1)
            self.assertEqual(report["jury"]["rows"], 4)
            self.assertEqual(report["jury"]["records"], 12)
            self.assertEqual(report["otp"]["confusion"], {"tp": 2, "fp": 0, "tn": 2, "fn": 0})
            self.assertEqual(report["phishing"]["confusion"], {"tp": 1, "fp": 0, "tn": 2, "fn": 0})
            self.assertEqual(report["intent"]["confusion"], {"correct": 1, "incorrect": 1})
            self.assertAlmostEqual(report["intent"]["metrics"]["accuracy"], 0.5)

            human = render_human_report(report)
            self.assertNotIn("SECRET TOKEN X", human)
            self.assertNotIn("SENSITIVE-SENDER-1", human)
            self.assertNotIn("row_id", human)
            self.assertIn("duplicate groups: 1", human)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--corpus-csv",
                        str(corpus_path),
                        "--jury-jsonl",
                        str(jury_path),
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed["otp"]["confusion"]["tp"], 2)
            self.assertEqual(parsed["intent"]["support"], 2)
            self.assertNotIn("SECRET TOKEN Y", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
