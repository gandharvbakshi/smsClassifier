from __future__ import annotations

import argparse
import ast
import concurrent.futures
import dataclasses
import hashlib
import json
import os
import subprocess
import shutil
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import quantiles
from typing import Any, Callable, Iterable

import requests


SERVER_PATH = Path(__file__).with_name("android_backend_server.py")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODELS = (
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "qwen/qwen3.8-27b",
)
DEFAULT_TIMEOUT = (1.5, 6.0)
DEFAULT_MAX_TOKENS = 1024
DEFAULT_WORKERS = 4
MODEL_TIMESTAMP = datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ServerPromptAssets:
    system_prompt: str
    user_template: str
    intent_labels: tuple[str, ...]


def _read_server_ast() -> ast.Module:
    return ast.parse(SERVER_PATH.read_text(encoding="utf-8"))


def load_server_prompt_assets() -> ServerPromptAssets:
    module = _read_server_ast()
    wanted: dict[str, Any] = {}
    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in {
            "SYSTEM_PROMPT",
            "USER_TEMPLATE",
            "INTENT_LABELS",
        }:
            continue
        wanted[target.id] = ast.literal_eval(node.value)

    missing = {"SYSTEM_PROMPT", "USER_TEMPLATE", "INTENT_LABELS"} - wanted.keys()
    if missing:
        raise RuntimeError(f"Failed to load server prompt constants: {sorted(missing)!r}")

    return ServerPromptAssets(
        system_prompt=str(wanted["SYSTEM_PROMPT"]),
        user_template=str(wanted["USER_TEMPLATE"]),
        intent_labels=tuple(str(label) for label in wanted["INTENT_LABELS"]),
    )


def _json_canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def case_content_hash(case: dict[str, Any]) -> str:
    payload = {
        "id": case.get("id"),
        "text": case.get("text"),
        "sender": case.get("sender"),
        "expected_is_otp": case.get("expected_is_otp"),
        "expected_intent": case.get("expected_intent"),
        "expected_is_phishing": case.get("expected_is_phishing"),
        "slice": case.get("slice"),
        "groq_needed": case.get("groq_needed", False),
    }
    return _sha256_text(_json_canonical(payload))


def build_prompt(case: dict[str, Any], assets: ServerPromptAssets) -> str:
    sender = str(case.get("sender") or "UNKNOWN").strip()
    sms = str(case.get("text") or "").replace("\r\n", "\n").strip()
    return assets.user_template.format(sender=sender, sms=sms)


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if not isinstance(obj, dict):
                raise ValueError(f"Case line {line_no} must be a JSON object")
            cases.append(obj)
    return cases


def _model_reasoning_effort(model: str) -> str:
    return "low" if model.startswith("openai/gpt") else "none"


def build_run_key(
    *,
    model: str,
    assets: ServerPromptAssets,
    max_tokens: int,
    temperature: float = 0.0,
    response_format: dict[str, str] | None = None,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
) -> str:
    payload = {
        "model": model,
        "system_prompt_sha": _sha256_text(assets.system_prompt),
        "user_template_sha": _sha256_text(assets.user_template),
        "intent_labels": list(assets.intent_labels),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "response_format": response_format or {"type": "json_object"},
        "reasoning_effort": _model_reasoning_effort(model),
        "timeout": {"connect": timeout[0], "read": timeout[1]},
    }
    return _sha256_text(_json_canonical(payload))


def build_request_payload(
    *,
    model: str,
    assets: ServerPromptAssets,
    case: dict[str, Any],
    max_tokens: int,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": assets.system_prompt},
            {"role": "user", "content": build_prompt(case, assets)},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "reasoning_effort": _model_reasoning_effort(model),
    }


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            if value != value:  # NaN
                return None
            if value in (float("inf"), float("-inf")):
                return None
        except Exception:
            return None
        return float(value)
    return None


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _parse_json_response(response: requests.Response) -> tuple[dict[str, Any] | None, str | None]:
    try:
        body = response.json()
    except ValueError:
        return None, "invalid_json_response"

    if isinstance(body, dict):
        choices = body.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, dict):
                        return content, None
                    if isinstance(content, str):
                        try:
                            parsed = json.loads(content)
                        except json.JSONDecodeError:
                            return None, "invalid_json_response"
                        if isinstance(parsed, dict):
                            return parsed, None
                        return None, "invalid_schema"
        if isinstance(body.get("response"), dict):
            return body["response"], None
        if isinstance(body.get("response"), str):
            try:
                parsed = json.loads(body["response"])
            except json.JSONDecodeError:
                return None, "invalid_json_response"
            if isinstance(parsed, dict):
                return parsed, None
            return None, "invalid_schema"
    return None, "invalid_schema"


def _validate_prediction(
    raw: dict[str, Any] | None,
    intent_labels: tuple[str, ...],
) -> tuple[dict[str, Any] | None, bool, str | None]:
    if not isinstance(raw, dict):
        return None, False, "invalid_schema"

    allowed_keys = {"is_otp", "otp_intent", "is_phishing"}
    if set(raw.keys()) != allowed_keys:
        return None, False, "invalid_schema"

    is_otp = raw.get("is_otp")
    otp_intent = raw.get("otp_intent")
    is_phishing = raw.get("is_phishing")

    if not isinstance(is_otp, bool):
        return None, False, "invalid_schema"
    if not isinstance(otp_intent, str) or otp_intent not in intent_labels:
        return None, False, "invalid_schema"
    if not isinstance(is_phishing, bool):
        return None, False, "invalid_schema"
    if is_otp is False and otp_intent != "NOT_OTP":
        return None, False, "invalid_schema"
    if is_otp is True and otp_intent == "NOT_OTP":
        return None, False, "invalid_schema"
    return {
        "is_otp": is_otp,
        "otp_intent": otp_intent,
        "is_phishing": is_phishing,
    }, True, None


def _rate_limit_headers(headers: Any) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    if not headers:
        return safe
    header_names = {
        "retry-after",
        "x-ratelimit-limit-requests",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-reset-requests",
        "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-tokens",
    }
    for key in header_names:
        value = headers.get(key)
        if value is None:
            continue
        try:
            parsed = float(value)
            if parsed == parsed and parsed not in (float("inf"), float("-inf")):
                safe[key.replace("-", "_")] = parsed
                continue
        except Exception:
            pass
    return safe


def _response_usage(body: dict[str, Any]) -> dict[str, int | None]:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None, "reasoning_tokens": None}
    return {
        "prompt_tokens": _safe_int(usage.get("prompt_tokens")),
        "completion_tokens": _safe_int(usage.get("completion_tokens")),
        "total_tokens": _safe_int(usage.get("total_tokens")),
        "reasoning_tokens": _safe_int(
            usage.get("reasoning_tokens")
            if usage.get("reasoning_tokens") is not None
            else usage.get("completion_tokens_details", {}).get("reasoning_tokens")
            if isinstance(usage.get("completion_tokens_details"), dict)
            else None
        ),
    }


def _safe_error_details(response: requests.Response | None) -> dict[str, Any]:
    if response is None:
        return {}
    details: dict[str, Any] = {"status_code": response.status_code}
    details.update(_rate_limit_headers(response.headers))
    try:
        payload = response.json()
    except Exception:
        return details
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            error_type = error.get("type")
            if isinstance(error_type, str):
                details["error_type"] = error_type
            error_code = error.get("code")
            if isinstance(error_code, str):
                details["error_code"] = error_code
    return details


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _macro_f1(gold_labels: list[str | None], pred_labels: list[str | None], label_space: Iterable[str]) -> tuple[float | None, dict[str, dict[str, int]]]:
    counts: dict[str, dict[str, int]] = {}
    f1_values: list[float] = []
    for label in label_space:
        tp = fp = fn = 0
        for gold, pred in zip(gold_labels, pred_labels):
            if gold == label and pred == label:
                tp += 1
            elif gold != label and pred == label:
                fp += 1
            elif gold == label and pred != label:
                fn += 1
        counts[label] = {"tp": tp, "fp": fp, "fn": fn}
        denom = (2 * tp) + fp + fn
        if denom > 0:
            f1_values.append((2 * tp) / denom)
    if not f1_values:
        return None, counts
    return sum(f1_values) / len(f1_values), counts


def _select_scored_value(value: Any) -> Any | None:
    return value if value is not None else None


class GroqReplacementEvaluator:
    def __init__(
        self,
        *,
        api_key: str,
        models: Iterable[str],
        output_dir: Path,
        workers: int = DEFAULT_WORKERS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
        session_factory: Callable[[], requests.Session] = requests.Session,
        now_fn: Callable[[], float] = time.perf_counter,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.api_key = api_key
        self.models = list(models)
        self.output_dir = output_dir
        self.workers = workers
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.session_factory = session_factory
        self.now_fn = now_fn
        self.event_callback = event_callback or (lambda payload: None)
        self._thread_local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = self.session_factory()
            self._thread_local.session = session
        return session

    def _log_event(self, payload: dict[str, Any]) -> None:
        safe_payload = {k: v for k, v in payload.items() if k not in {"api_key", "prompt", "sms", "text", "sender"}}
        self.event_callback(safe_payload)

    def _load_existing_case_hashes(self, path: Path, run_key: str, resume: bool) -> dict[str, dict[str, Any]]:
        if not resume or not path.exists():
            return {}
        existing: dict[str, dict[str, Any]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if record.get("run_key") != run_key:
                    continue
                case_hash = record.get("case_hash")
                if isinstance(case_hash, str):
                    existing[case_hash] = record
        return existing

    def _call_api(self, model: str, case: dict[str, Any], assets: ServerPromptAssets) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        session = self._session()
        payload = build_request_payload(model=model, assets=assets, case=case, max_tokens=self.max_tokens)
        started = self.now_fn()
        response: requests.Response | None = None
        try:
            response = session.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            elapsed_ms = max(0.0, (self.now_fn() - started) * 1000.0)
            self._log_event(
                {
                    "model": model,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    **_rate_limit_headers(response.headers),
                }
            )
            if response.status_code >= 400:
                details = _safe_error_details(response)
                return None, {
                    "status": "api_error",
                    "error_type": details.get("error_type"),
                    "error_code": details.get("error_code"),
                    "status_code": details.get("status_code"),
                    "elapsed_ms": elapsed_ms,
                    "rate_limit": {k: v for k, v in details.items() if k.startswith("x_ratelimit") or k == "retry_after"},
                }

            body = response.json()
            parsed, parse_error = _parse_json_response(response)
            if parse_error:
                return None, {
                    "status": parse_error,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }
            prediction, schema_valid, schema_error = _validate_prediction(parsed, assets.intent_labels)
            finish_reason = None
            if isinstance(body, dict):
                choices = body.get("choices")
                if isinstance(choices, list) and choices:
                    first = choices[0]
                    if isinstance(first, dict):
                        finish_reason = first.get("finish_reason")
            return {
                "prediction": prediction,
                "schema_valid": schema_valid,
                "schema_error": schema_error,
                "finish_reason": finish_reason,
                "usage": _response_usage(body if isinstance(body, dict) else {}),
            }, {
                "status": "ok" if schema_valid else "invalid_schema",
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            }
        except requests.Timeout as exc:
            elapsed_ms = max(0.0, (self.now_fn() - started) * 1000.0)
            self._log_event({"model": model, "status": "timeout", "elapsed_ms": elapsed_ms})
            return None, {
                "status": "timeout",
                "error_type": exc.__class__.__name__,
                "elapsed_ms": elapsed_ms,
            }
        except requests.RequestException as exc:
            elapsed_ms = max(0.0, (self.now_fn() - started) * 1000.0)
            self._log_event({"model": model, "status": "request_error", "elapsed_ms": elapsed_ms})
            details = {"status": "request_error", "error_type": exc.__class__.__name__, "elapsed_ms": elapsed_ms}
            response_obj = getattr(exc, "response", None)
            if isinstance(response_obj, requests.Response):
                details.update(_safe_error_details(response_obj))
            return None, details
        finally:
            if response is not None:
                response.close()

    def _evaluate_case(
        self,
        *,
        model: str,
        case: dict[str, Any],
        assets: ServerPromptAssets,
        run_key: str,
        run_started: str,
    ) -> dict[str, Any]:
        case_hash = case_content_hash(case)
        request_started = self.now_fn()
        api_result, telemetry = self._call_api(model, case, assets)
        elapsed_ms = telemetry.get("elapsed_ms")
        if not isinstance(elapsed_ms, (int, float)):
            elapsed_ms = max(0.0, (self.now_fn() - request_started) * 1000.0)
        prediction = api_result["prediction"] if api_result else None
        schema_valid = bool(api_result and api_result.get("schema_valid"))
        schema_error = api_result["schema_error"] if api_result else telemetry.get("status")
        finish_reason = api_result["finish_reason"] if api_result else None
        usage = api_result["usage"] if api_result else {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "reasoning_tokens": None,
        }

        gold_is_otp = case.get("expected_is_otp")
        gold_intent = case.get("expected_intent")
        gold_is_phishing = case.get("expected_is_phishing")

        predicted_is_otp = prediction.get("is_otp") if prediction else None
        predicted_intent = prediction.get("otp_intent") if prediction else None
        predicted_is_phishing = prediction.get("is_phishing") if prediction else None

        is_otp_scored = isinstance(gold_is_otp, bool)
        intent_scored = isinstance(gold_intent, str) and gold_intent != ""
        is_phishing_scored = isinstance(gold_is_phishing, bool)

        status = telemetry.get("status", "unknown")
        valid_json = status == "ok"
        gold_to_pred = {
            "expected_is_otp": gold_is_otp,
            "expected_intent": gold_intent,
            "expected_is_phishing": gold_is_phishing,
        }
        pred_to_store = {
            "is_otp": predicted_is_otp,
            "otp_intent": predicted_intent,
            "is_phishing": predicted_is_phishing,
        }
        correct = (
            (not is_otp_scored or predicted_is_otp is gold_is_otp)
            and (not intent_scored or predicted_intent == gold_intent)
            and (not is_phishing_scored or predicted_is_phishing is gold_is_phishing)
        )
        return {
            "run_key": run_key,
            "run_started_at": run_started,
            "model": model,
            "model_timestamp": MODEL_TIMESTAMP,
            "case_id": case.get("id"),
            "case_hash": case_hash,
            "slice": case.get("slice"),
            "groq_needed": case.get("groq_needed", False),
            "gold": gold_to_pred,
            "prediction": pred_to_store,
            "schema_valid": schema_valid,
            "valid_json": valid_json,
            "status": status,
            "finish_reason": finish_reason,
            "elapsed_ms": elapsed_ms,
            "usage": usage,
            "error_type": telemetry.get("error_type"),
            "error_code": telemetry.get("error_code"),
            "status_code": telemetry.get("status_code"),
            "config": {
                "model": model,
                "max_tokens": self.max_tokens,
                "timeout": {"connect": self.timeout[0], "read": self.timeout[1]},
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "reasoning_effort": _model_reasoning_effort(model),
                "prompt_sha": _sha256_text(_json_canonical({
                    "system_prompt": assets.system_prompt,
                    "user_template": assets.user_template,
                    "intent_labels": list(assets.intent_labels),
                })),
            },
            "prompt_sha": _sha256_text(_json_canonical({
                "system_prompt": assets.system_prompt,
                "user_template": assets.user_template,
                "intent_labels": list(assets.intent_labels),
            })),
            "correct": correct,
        }

    def _model_paths(self, model: str, run_key: str) -> tuple[Path, Path]:
        slug = model.replace("/", "__")
        model_dir = self.output_dir / slug
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir / f"results-{run_key}.jsonl", model_dir / f"summary-{run_key}.json"

    def run(self, cases: list[dict[str, Any]], assets: ServerPromptAssets, resume: bool = False) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        run_started_at = datetime.now(timezone.utc).isoformat()
        overall: dict[str, Any] = {
            "generated_at": run_started_at,
            "model_timestamp": MODEL_TIMESTAMP,
            "models": list(self.models),
            "cases_file_count": len(cases),
            "models_summary": [],
        }

        for model in self.models:
            run_key = build_run_key(
                model=model,
                assets=assets,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            results_path, summary_path = self._model_paths(model, run_key)
            existing = self._load_existing_case_hashes(results_path, run_key, resume=resume)
            seen_hashes = set(existing)

            records: list[dict[str, Any]] = []
            write_mode = "a" if resume and results_path.exists() else "w"
            with results_path.open(write_mode, encoding="utf-8") as results_file:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
                    future_map: dict[concurrent.futures.Future[dict[str, Any]], dict[str, Any]] = {}
                    for case in cases:
                        c_hash = case_content_hash(case)
                        if c_hash in seen_hashes:
                            continue
                        future = pool.submit(
                            self._evaluate_case,
                            model=model,
                            case=case,
                            assets=assets,
                            run_key=run_key,
                            run_started=run_started_at,
                        )
                        future_map[future] = case

                    for future in concurrent.futures.as_completed(future_map):
                        record = future.result()
                        records.append(record)
                        results_file.write(_json_canonical(record) + "\n")
                        results_file.flush()

            case_hashes = {case_content_hash(case) for case in cases}
            all_records = [r for h, r in existing.items() if h in case_hashes] + records
            summary = summarize_records(
                all_records,
                model=model,
                run_key=run_key,
                output_path=results_path,
                prompt_sha=_sha256_text(_json_canonical({
                    "system_prompt": assets.system_prompt,
                    "user_template": assets.user_template,
                    "intent_labels": list(assets.intent_labels),
                })),
                intent_labels=assets.intent_labels,
                run_started_at=run_started_at,
            )
            summary_path.write_text(_json_canonical(summary) + "\n", encoding="utf-8")
            overall["models_summary"].append(summary)
            print(json.dumps({"model": model, "cases": len(all_records), "intent_accuracy": summary["intent"]["accuracy"], "p95_ms": summary["latency_ms"]["p95"], "failures": summary["failures"]}), flush=True)

        return overall


def summarize_records(
    records: list[dict[str, Any]],
    *,
    model: str,
    run_key: str,
    output_path: Path,
    prompt_sha: str,
    intent_labels: tuple[str, ...],
    run_started_at: str,
) -> dict[str, Any]:
    gold_intents: list[str | None] = []
    pred_intents: list[str | None] = []
    eligible_intent_records: list[dict[str, Any]] = []
    intent_scores: Counter[str] = Counter()
    otp_scores: Counter[str] = Counter()
    phish_scores: Counter[str] = Counter()
    latencies = [float(r["elapsed_ms"]) for r in records if isinstance(r.get("elapsed_ms"), (int, float))]
    token_totals = Counter()
    output_failures = 0
    timeouts = 0

    for record in records:
        gold = record.get("gold", {})
        pred = record.get("prediction", {})
        gold_intent = gold.get("expected_intent")
        pred_intent = pred.get("otp_intent")
        gold_is_otp = gold.get("expected_is_otp")
        pred_is_otp = pred.get("is_otp")
        gold_is_phish = gold.get("expected_is_phishing")
        pred_is_phish = pred.get("is_phishing")

        if isinstance(gold_intent, str) and gold_intent:
            gold_intents.append(gold_intent)
            pred_intents.append(pred_intent if isinstance(pred_intent, str) else None)
            eligible_intent_records.append(record)
            if record.get("status") in {"timeout", "request_error", "api_error", "invalid_json_response", "invalid_schema"}:
                intent_scores["errors"] += 1
            elif pred_intent == gold_intent:
                intent_scores["correct"] += 1
            else:
                intent_scores["wrong"] += 1

        if isinstance(gold_is_otp, bool):
            if isinstance(pred_is_otp, bool) and pred_is_otp == gold_is_otp:
                otp_scores["correct"] += 1
            else:
                otp_scores["wrong"] += 1

        if isinstance(gold_is_phish, bool):
            if isinstance(pred_is_phish, bool) and pred_is_phish == gold_is_phish:
                phish_scores["correct"] += 1
            else:
                phish_scores["wrong"] += 1

        usage = record.get("usage") or {}
        for key in ["prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens"]:
            value = usage.get(key)
            if isinstance(value, int):
                token_totals[key] += value

        if record.get("status") not in {"ok"}:
            output_failures += 1
        if record.get("status") == "timeout":
            timeouts += 1

    macro_f1, per_label_counts = _macro_f1(gold_intents, pred_intents, intent_labels)
    intent_total = len(gold_intents)
    otp_total = sum(1 for record in records if isinstance(record.get("gold", {}).get("expected_is_otp"), bool))
    phish_total = sum(1 for record in records if isinstance(record.get("gold", {}).get("expected_is_phishing"), bool))

    intent_correct = intent_scores["correct"]
    intent_wrong = intent_scores["wrong"]
    intent_errors = intent_scores["errors"]
    otp_correct = otp_scores["correct"]
    otp_wrong = otp_scores["wrong"]
    phish_correct = phish_scores["correct"]
    phish_wrong = phish_scores["wrong"]

    def ratio(correct: int, total: int) -> float | None:
        return (correct / total) if total else None

    summary = {
        "model": model,
        "run_key": run_key,
        "run_started_at": run_started_at,
        "prompt_sha": prompt_sha,
        "output_path": str(output_path),
        "records": len(records),
        "intent": {
            "scored": intent_total,
            "correct": intent_correct,
            "wrong": intent_wrong,
            "errors": intent_errors,
            "accuracy": ratio(intent_correct, intent_total),
            "macro_f1": macro_f1,
            "per_label_counts": per_label_counts,
        },
        "is_otp": {
            "scored": otp_total,
            "correct": otp_correct,
            "wrong": otp_wrong,
            "accuracy": ratio(otp_correct, otp_total),
        },
        "is_phishing": {
            "scored": phish_total,
            "correct": phish_correct,
            "wrong": phish_wrong,
            "accuracy": ratio(phish_correct, phish_total),
        },
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
        },
        "failures": {
            "output_failures": output_failures,
            "timeouts": timeouts,
        },
        "token_totals": dict(token_totals),
        "labels": list(intent_labels),
    }
    return summary


def _load_api_key() -> str:
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        return env_key
    proc = subprocess.run(
        [
            shutil.which("gcloud.cmd") or shutil.which("gcloud") or "gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret=sms-classifier-groq-api-key",
            "--project=smsclassifier-478611",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    secret = proc.stdout.strip()
    if not secret:
        raise RuntimeError("GROQ API key secret was empty")
    return secret


def _write_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(_json_canonical(manifest) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Groq replacement models against SMS classifier cases.")
    parser.add_argument("--cases", type=Path, required=True, help="JSONL file containing evaluation cases.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for JSONL outputs and summaries.")
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS), help="Model IDs to evaluate.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent requests per model.")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Max completion tokens per request.")
    parser.add_argument("--resume", action="store_true", help="Continue from matching cached results when present.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    assets = load_server_prompt_assets()
    cases = load_cases(args.cases)
    api_key = _load_api_key()
    evaluator = GroqReplacementEvaluator(
        api_key=api_key,
        models=args.models,
        output_dir=args.output_dir,
        workers=args.workers,
        max_tokens=args.max_tokens,
    )
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_timestamp": MODEL_TIMESTAMP,
        "models": list(args.models),
        "cases_path": str(args.cases),
        "cases_count": len(cases),
        "output_dir": str(args.output_dir),
        "max_tokens": args.max_tokens,
        "workers": args.workers,
        "prompt_sha": _sha256_text(_json_canonical({
            "system_prompt": assets.system_prompt,
            "user_template": assets.user_template,
            "intent_labels": list(assets.intent_labels),
        })),
        "run_key_prefix": "per-model",
        "server_path": str(SERVER_PATH),
    }
    _write_manifest(args.output_dir, manifest)
    evaluator.run(cases, assets, resume=args.resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
