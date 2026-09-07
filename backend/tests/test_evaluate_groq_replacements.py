from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.scripts import evaluate_groq_replacements as eval_script


class FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200, headers: dict[str, str] | None = None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def json(self):
        return self._payload

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        })
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


class EvaluateGroqReplacementsTests(unittest.TestCase):
    def test_load_server_prompt_assets_reads_exact_constants(self):
        assets = eval_script.load_server_prompt_assets()
        self.assertIn("You are an SMS security classifier.", assets.system_prompt)
        self.assertIn("Sender: {sender}", assets.user_template)
        self.assertEqual(
            assets.intent_labels,
            (
                "NOT_OTP",
                "APP_ACCOUNT_CHANGE_OTP",
                "APP_LOGIN_OTP",
                "BANK_OR_CARD_TXN_OTP",
                "DELIVERY_OR_SERVICE_OTP",
                "FINANCIAL_LOGIN_OTP",
                "GENERIC_APP_ACTION_OTP",
                "KYC_OR_ESIGN_OTP",
                "UPI_TXN_OR_PIN_OTP",
            ),
        )

    def test_evaluator_runs_with_mock_session_and_writes_summary(self):
        assets = eval_script.load_server_prompt_assets()
        cases = [
            {
                "id": "case-1",
                "text": "Your OTP is 123456",
                "sender": "Example Bank",
                "expected_is_otp": True,
                "expected_intent": "BANK_OR_CARD_TXN_OTP",
                "expected_is_phishing": False,
                "slice": "gold",
            },
            {
                "id": "case-2",
                "text": "Thanks for your order",
                "sender": "Delivery Co",
                "expected_is_otp": None,
                "expected_intent": None,
                "expected_is_phishing": None,
                "slice": "unscored",
            },
        ]
        responses = [
            FakeResponse(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "is_otp": True,
                                        "otp_intent": "BANK_OR_CARD_TXN_OTP",
                                        "is_phishing": False,
                                    }
                                )
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 11,
                        "total_tokens": 21,
                        "reasoning_tokens": 3,
                    },
                },
                status_code=200,
            ),
            FakeResponse(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "is_otp": False,
                                        "otp_intent": "NOT_OTP",
                                        "is_phishing": False,
                                    }
                                )
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 13,
                        "total_tokens": 25,
                        "reasoning_tokens": 4,
                    },
                },
                status_code=200,
            ),
        ]
        fake_session = FakeSession(responses)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            evaluator = eval_script.GroqReplacementEvaluator(
                api_key="test-key",
                models=["openai/gpt-oss-20b"],
                output_dir=output_dir,
                workers=1,
                max_tokens=1024,
                session_factory=lambda: fake_session,
                now_fn=lambda: 1000.0,
            )

            summary = evaluator.run(cases, assets, resume=True)

            self.assertEqual(len(fake_session.calls), 2)
            first_call = fake_session.calls[0]
            self.assertEqual(first_call["url"], eval_script.GROQ_URL)
            self.assertEqual(first_call["timeout"], eval_script.DEFAULT_TIMEOUT)
            self.assertEqual(first_call["headers"]["Authorization"], "Bearer test-key")
            self.assertEqual(first_call["json"]["response_format"], {"type": "json_object"})
            self.assertEqual(first_call["json"]["reasoning_effort"], "low")
            self.assertIn("Sender: Example Bank", first_call["json"]["messages"][1]["content"])
            self.assertIn("Your OTP is 123456", first_call["json"]["messages"][1]["content"])

            model_summary = summary["models_summary"][0]
            self.assertEqual(model_summary["model"], "openai/gpt-oss-20b")
            self.assertEqual(model_summary["records"], 2)
            self.assertEqual(model_summary["intent"]["scored"], 1)
            self.assertEqual(model_summary["intent"]["correct"], 1)
            self.assertEqual(model_summary["is_otp"]["scored"], 1)
            self.assertEqual(model_summary["is_otp"]["correct"], 1)
            self.assertEqual(model_summary["is_phishing"]["scored"], 1)
            self.assertEqual(model_summary["is_phishing"]["correct"], 1)
            self.assertEqual(model_summary["token_totals"]["prompt_tokens"], 22)
            self.assertEqual(model_summary["token_totals"]["completion_tokens"], 24)
            self.assertEqual(model_summary["token_totals"]["total_tokens"], 46)

            model_dir = output_dir / "openai__gpt-oss-20b"
            result_files = list(model_dir.glob("results-*.jsonl"))
            summary_files = list(model_dir.glob("summary-*.json"))
            self.assertEqual(len(result_files), 1)
            self.assertEqual(len(summary_files), 1)

            lines = result_files[0].read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            parsed_line = json.loads(lines[0])
            self.assertEqual(parsed_line["prediction"]["otp_intent"], "BANK_OR_CARD_TXN_OTP")
            self.assertEqual(parsed_line["config"]["response_format"], {"type": "json_object"})
            self.assertIn("prompt_sha", parsed_line)

    def test_summary_counts_errors_and_skips_null_gold(self):
        summary = eval_script.summarize_records(
            [
                {
                    "elapsed_ms": 10.0,
                    "status": "ok",
                    "gold": {"expected_is_otp": True, "expected_intent": "APP_LOGIN_OTP", "expected_is_phishing": False},
                    "prediction": {"is_otp": True, "otp_intent": "APP_LOGIN_OTP", "is_phishing": False},
                    "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3, "reasoning_tokens": 4},
                },
                {
                    "elapsed_ms": 20.0,
                    "status": "invalid_json_response",
                    "gold": {"expected_is_otp": False, "expected_intent": None, "expected_is_phishing": None},
                    "prediction": {"is_otp": None, "otp_intent": None, "is_phishing": None},
                    "usage": {},
                },
            ],
            model="openai/gpt-oss-20b",
            run_key="run-key",
            output_path=Path("out.jsonl"),
            prompt_sha="abc123",
            intent_labels=assets.intent_labels if (assets := eval_script.load_server_prompt_assets()) else (),
            run_started_at="2026-09-07T00:00:00+00:00",
        )

        self.assertEqual(summary["intent"]["scored"], 1)
        self.assertEqual(summary["intent"]["correct"], 1)
        self.assertEqual(summary["intent"]["errors"], 0)
        self.assertEqual(summary["is_otp"]["scored"], 2)
        self.assertEqual(summary["is_otp"]["correct"], 1)
        self.assertEqual(summary["is_otp"]["wrong"], 1)
        self.assertEqual(summary["failures"]["output_failures"], 1)
        self.assertEqual(summary["failures"]["timeouts"], 0)
        self.assertIsNotNone(summary["latency_ms"]["p50"])
        self.assertIsNotNone(summary["latency_ms"]["p95"])

    def test_main_smoke_creates_manifest_and_invokes_evaluator(self):
        cases_path = Path(tempfile.gettempdir()) / "evaluate_groq_cases.jsonl"
        cases_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "id": "one",
                            "text": "OTP 123456",
                            "sender": "Bank",
                            "expected_is_otp": True,
                            "expected_intent": "BANK_OR_CARD_TXN_OTP",
                            "expected_is_phishing": False,
                            "slice": "gold",
                        }
                    )
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        calls: dict[str, object] = {}

        class FakeEvaluator:
            def __init__(self, **kwargs):
                calls["init"] = kwargs

            def run(self, cases, assets, resume=False):
                calls["run"] = {
                    "case_count": len(cases),
                    "resume": resume,
                    "intent_labels": assets.intent_labels,
                }
                return {"models_summary": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "out"
            with patch.object(eval_script, "_load_api_key", return_value="test-key"), patch.object(
                eval_script, "GroqReplacementEvaluator", FakeEvaluator
            ):
                exit_code = eval_script.main(
                    [
                        "--cases",
                        str(cases_path),
                        "--output-dir",
                        str(output_dir),
                        "--models",
                        "openai/gpt-oss-20b",
                        "--workers",
                        "1",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "manifest.json").exists())
            self.assertEqual(calls["init"]["max_tokens"], eval_script.DEFAULT_MAX_TOKENS)
            self.assertEqual(calls["run"]["case_count"], 1)
            self.assertFalse(calls["run"]["resume"])


if __name__ == "__main__":
    unittest.main()
