"""Regression tests for Groq runtime generation config wiring."""

from __future__ import annotations

import builtins
import importlib.util
import io
import pickle
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT_DIR / "scripts/android_backend_server.py"
MODEL_FILENAMES = {"tfidf_vectorizer.pkl", "model_isotp_lgb.pkl", "model_phishing_lgb.pkl"}


def load_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **env: str):
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setenv("FEEDBACK_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("FEEDBACK_GCS_BUCKET", raising=False)
    monkeypatch.delenv("GROQ_MAX_TOKENS", raising=False)
    monkeypatch.delenv("GROQ_REASONING_EFFORT", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    module_name = f"groq_generation_config_test_server_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    original_open, original_exists = builtins.open, Path.exists

    def fake_open(path, *args, **kwargs):
        if Path(path).name in MODEL_FILENAMES:
            return io.BytesIO(pickle.dumps(None))
        return original_open(path, *args, **kwargs)

    with patch("builtins.open", fake_open), patch.object(
        Path, "exists", lambda path: path.name in MODEL_FILENAMES or original_exists(path)
    ):
        spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_gcs_client", lambda: None)
    return module


def test_call_groq_forwards_configured_generation_values(monkeypatch, tmp_path):
    server = load_server(
        monkeypatch,
        tmp_path,
        GROQ_MAX_TOKENS="512",
        GROQ_REASONING_EFFORT="low",
    )
    calls = []

    class FakeTransport:
        def post_chat_completions(self, messages, **kwargs):
            calls.append({"messages": messages, "kwargs": kwargs})
            return {"choices": []}

    monkeypatch.setattr(server, "GROQ_TRANSPORT", FakeTransport())

    server.call_groq([{"role": "user", "content": "hello"}])

    assert calls[0]["kwargs"] == {"temperature": 0.0, "max_tokens": 512, "reasoning_effort": "low"}


def test_call_groq_omits_reasoning_effort_when_env_unset(monkeypatch, tmp_path):
    server = load_server(
        monkeypatch,
        tmp_path,
    )
    calls = []

    class FakeTransport:
        def post_chat_completions(self, messages, **kwargs):
            calls.append({"messages": messages, "kwargs": kwargs})
            return {"choices": []}

    monkeypatch.setattr(server, "GROQ_TRANSPORT", FakeTransport())

    server.call_groq([{"role": "user", "content": "hello"}])

    assert calls[0]["kwargs"] == {"temperature": 0.0, "max_tokens": 256}
    assert "reasoning_effort" not in calls[0]["kwargs"]


def test_call_groq_serializes_configured_none_reasoning_effort(monkeypatch, tmp_path):
    server = load_server(
        monkeypatch,
        tmp_path,
        GROQ_MAX_TOKENS="1024",
        GROQ_REASONING_EFFORT="none",
    )
    calls = []

    class FakeTransport:
        def post_chat_completions(self, messages, **kwargs):
            calls.append({"messages": messages, "kwargs": kwargs})
            return {"choices": []}

    monkeypatch.setattr(server, "GROQ_TRANSPORT", FakeTransport())

    server.call_groq([{"role": "user", "content": "hello"}])

    assert calls[0]["kwargs"] == {"temperature": 0.0, "max_tokens": 1024, "reasoning_effort": "none"}


@pytest.mark.parametrize("value", ["0", "-1", "invalid", " "])
def test_invalid_output_budget_preserves_default(monkeypatch, tmp_path, value):
    server = load_server(monkeypatch, tmp_path, GROQ_MAX_TOKENS=value)
    assert server.GROQ_MAX_TOKENS == 256


def test_invalid_reasoning_effort_env_fails_fast(monkeypatch, tmp_path):
    with pytest.raises(EnvironmentError, match="GROQ_REASONING_EFFORT"):
        load_server(
            monkeypatch,
            tmp_path,
            GROQ_REASONING_EFFORT="banana",
        )
