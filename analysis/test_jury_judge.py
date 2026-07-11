"""Focused unit tests for jury_judge provider parsing and env loading."""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import jury_judge  # noqa: E402


class FakeAnthropicClient:
    def __init__(self, response):
        self._response = response
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        self.kwargs = kwargs
        return self._response


class JuryJudgeTests(unittest.IsolatedAsyncioTestCase):
    def test_default_fallback_env_is_projects_level(self):
        self.assertEqual(jury_judge.DEFAULT_FALLBACK_ENV, Path(r"D:\Projects\.env"))

    def test_parse_json_object_accepts_markdown_fence(self):
        parsed = jury_judge._parse_json_object(
            "```json\n{\"is_otp\": false, \"is_phishing\": false}\n```"
        )
        self.assertFalse(parsed["is_otp"])

    async def test_call_anthropic_parses_json_and_tracks_tokens(self):
        response = SimpleNamespace(
            content=[SimpleNamespace(text='{"is_otp": true, "otp_intent": null, '
                                          '"is_phishing": false, "confidence": 0.91, '
                                          '"reasoning": "looks like an OTP"}')],
            usage=SimpleNamespace(input_tokens=123, output_tokens=45),
        )
        client = FakeAnthropicClient(response)

        raw, in_tokens, out_tokens = await jury_judge.call_anthropic(
            client,
            sender="TX-TEST",
            body="Your OTP is 123456.",
        )
        verdict = jury_judge.validate_verdict(raw)

        self.assertEqual(in_tokens, 123)
        self.assertEqual(out_tokens, 45)
        self.assertTrue(client.kwargs["messages"][0]["content"].startswith("You are an expert"))
        self.assertEqual(verdict["is_otp"], True)
        self.assertIsNone(verdict["otp_intent"])
        self.assertEqual(verdict["is_phishing"], False)
        self.assertAlmostEqual(verdict["confidence"], 0.91)
        self.assertEqual(verdict["reasoning"], "looks like an OTP")

    def test_load_jury_env_uses_app_env_before_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app_env = tmp_path / "app.env"
            fallback_env = tmp_path / "fallback.env"
            app_env.write_text(
                "OPENAI_API_KEY=from_app\n"
                "APP_ONLY=app_value\n",
                encoding="utf-8",
            )
            fallback_env.write_text(
                "OPENAI_API_KEY=from_fallback\n"
                "FALLBACK_ONLY=fallback_value\n",
                encoding="utf-8",
            )

            with patch.object(jury_judge, "DEFAULT_ENV", app_env), \
                 patch.object(jury_judge, "DEFAULT_FALLBACK_ENV", fallback_env), \
                 patch.dict(os.environ, {}, clear=True):
                jury_judge.load_jury_env()

                self.assertEqual(os.environ["OPENAI_API_KEY"], "from_app")
                self.assertEqual(os.environ["APP_ONLY"], "app_value")
                self.assertEqual(os.environ["FALLBACK_ONLY"], "fallback_value")


if __name__ == "__main__":
    unittest.main()
