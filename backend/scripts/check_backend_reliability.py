from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import requests


SAFE_EXAMPLES: list[dict[str, str]] = [
    {
        "name": "loginOTP",
        "text": "Your login code is 482917. Do not share this code with anyone.",
        "sender": "ACME",
    },
    {
        "name": "deliveryOTP",
        "text": "Please share 615204 with the delivery agent to complete handoff.",
        "sender": "DELIVERY",
    },
    {
        "name": "bankOTP",
        "text": "Use 904311 to approve your bank card transaction. Never share this code.",
        "sender": "BANK",
    },
    {
        "name": "phishingURL",
        "text": "Update your account at http://secure-check.example/login and share code 771244.",
        "sender": "SAFE-ALERT",
    },
    {
        "name": "normal",
        "text": "Lunch is at 1 pm. See you after work.",
        "sender": "FRIEND",
    },
]


@dataclass(frozen=True)
class RequestResult:
    endpoint: str
    status_code: int
    latency_ms: float
    semantic: Dict[str, Any]


class ThreadLocalSessionFactory:
    def __init__(self) -> None:
        self._local = threading.local()

    def session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session


def _safe_json_value(response: requests.Response) -> Dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _semantic_fields(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "isOtp": body.get("isOtp"),
        "otpIntent": body.get("otpIntent"),
        "isPhishing": body.get("isPhishing"),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    try:
        return float(statistics.quantiles(values, n=100, method="inclusive")[int(pct) - 1])
    except Exception:  # noqa: BLE001
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
        return float(ordered[index])


def _health_check(session: requests.Session, base_url: str) -> Dict[str, Any]:
    started = time.perf_counter()
    response = session.get(f"{base_url}/health", timeout=10)
    try:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
        }
    finally:
        response.close()


def _classify_payload(example: dict[str, str], install_id: str, run_id: str) -> Dict[str, Any]:
    return {
        "text": example["text"],
        "sender": example["sender"],
        "installId": install_id,
        "appVersionCode": 999999,
        "appVersionName": f"reliability-{run_id}",
    }


def _purchase_probe_payload(install_id: str, run_id: str) -> Dict[str, Any]:
    return {
        "installId": install_id,
        "packageName": "com.smsclassifier.app",
        "productId": "pro_yearly",
        "purchaseToken": f"invalid-test-{run_id}",
        "productType": "subs",
    }


def _post_json(session: requests.Session, endpoint: str, payload: Dict[str, Any]) -> RequestResult:
    started = time.perf_counter()
    response = session.post(endpoint, json=payload, timeout=10)
    try:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return RequestResult(
            endpoint=endpoint,
            status_code=response.status_code,
            latency_ms=latency_ms,
            semantic=_semantic_fields(_safe_json_value(response)),
        )
    finally:
        response.close()


def _run_one(
    base_url: str,
    endpoint_path: str,
    payload: Dict[str, Any],
    session_factory: ThreadLocalSessionFactory,
) -> RequestResult:
    session = session_factory.session()
    return _post_json(session, f"{base_url}{endpoint_path}", payload)


def _run_classify_batch(
    *,
    base_url: str,
    examples: list[dict[str, str]],
    install_id: str,
    run_id: str,
    load_level: int,
    session_factory: ThreadLocalSessionFactory,
) -> list[RequestResult]:
    payloads = [_classify_payload(examples[index % len(examples)], install_id, run_id) for index in range(32)]
    results: list[Optional[RequestResult]] = [None] * len(payloads)
    with concurrent.futures.ThreadPoolExecutor(max_workers=load_level) as executor:
        futures = {
            executor.submit(_run_one, base_url, "/classify", payload, session_factory): index
            for index, payload in enumerate(payloads)
        }
        for future in concurrent.futures.as_completed(futures):
            index = futures[future]
            try:
                result = future.result()
            except BaseException:  # noqa: BLE001
                for pending in futures:
                    pending.cancel()
                raise
            results[index] = result
            if result.status_code >= 400:
                for pending in futures:
                    if pending is not future:
                        pending.cancel()
                raise RuntimeError(f"classify request failed with status {result.status_code} at {result.endpoint}")
    ordered_results = [item for item in results if item is not None]
    if len(ordered_results) != len(payloads):
        raise RuntimeError("did not collect all classify results")
    return ordered_results


def _compare_against_baseline(
    candidate_results: Iterable[RequestResult],
    baseline_results: Iterable[RequestResult],
) -> Dict[str, Any]:
    candidate_list = list(candidate_results)
    baseline_list = list(baseline_results)
    semantic_fields = ("isOtp", "otpIntent", "isPhishing")
    mismatch_count = 0
    total = min(len(candidate_list), len(baseline_list))
    for candidate, baseline in zip(candidate_list, baseline_list):
        candidate_body = candidate.semantic
        baseline_body = baseline.semantic
        if any(candidate_body.get(field) != baseline_body.get(field) for field in semantic_fields):
            mismatch_count += 1
    return {
        "total": total,
        "semantic_mismatches": mismatch_count,
        "semantic_match_rate": 0.0 if total == 0 else (total - mismatch_count) / total,
    }


def _summarize_results(results: Iterable[RequestResult]) -> Dict[str, Any]:
    result_list = list(results)
    latencies = [item.latency_ms for item in result_list]
    status_counts: Dict[str, int] = {}
    for item in result_list:
        status_key = str(item.status_code)
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
    return {
        "count": len(result_list),
        "status_counts": status_counts,
        "latency_ms": {
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "max": max(latencies) if latencies else 0.0,
        },
    }


def _invalid_purchase_probe(base_url: str, install_id: str, run_id: str, session_factory: ThreadLocalSessionFactory) -> Dict[str, Any]:
    session = session_factory.session()
    started = time.perf_counter()
    response = session.post(
        f"{base_url}/purchases/verify",
        json=_purchase_probe_payload(install_id, run_id),
        timeout=10,
    )
    try:
        payload = _safe_json_value(response)
        return {
            "endpoint": f"{base_url}/purchases/verify",
            "status_code": response.status_code,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            "validationStatus": payload.get("validationStatus"),
        }
    finally:
        response.close()


def _normalize_base_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/api"):
        return cleaned
    return f"{cleaned}/api"


def _ensure_health_ok(base_url: str, session_factory: ThreadLocalSessionFactory) -> Dict[str, Any]:
    health = _health_check(session_factory.session(), base_url)
    if health["status_code"] != 200:
        raise RuntimeError(f"health check failed with status {health['status_code']}")
    return health


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic SMS backend reliability checks.")
    parser.add_argument("--url", required=True, help="Candidate backend base URL, for example https://host/api")
    parser.add_argument("--baseline-url", help="Optional baseline backend base URL for sequential comparison")
    parser.add_argument("--output", required=True, help="Path to write JSON results")
    args = parser.parse_args()

    candidate_base = _normalize_base_url(args.url)
    baseline_base = _normalize_base_url(args.baseline_url) if args.baseline_url else None
    run_id = uuid.uuid4().hex[:12]
    install_id = f"synthetic-reliability-{run_id}"
    session_factory = ThreadLocalSessionFactory()

    report: Dict[str, Any] = {
        "health": _ensure_health_ok(candidate_base, session_factory),
    }

    if baseline_base:
        baseline_health = _health_check(session_factory.session(), baseline_base)
        if baseline_health["status_code"] != 200:
            raise RuntimeError(f"baseline health check failed with status {baseline_health['status_code']}")
        report["baseline"] = {
            "base_url": baseline_base,
            "health": baseline_health,
        }

    candidate_sequential = [
        _run_one(
            candidate_base,
            "/classify",
            _classify_payload(SAFE_EXAMPLES[index], install_id, run_id),
            session_factory,
        )
        for index in range(len(SAFE_EXAMPLES))
    ]
    if any(item.status_code >= 400 for item in candidate_sequential):
        raise RuntimeError("candidate sequential classify request failed")

    report["candidate_sequential"] = _summarize_results(candidate_sequential)

    if baseline_base:
        baseline_sequential = [
            _run_one(
                baseline_base,
                "/classify",
                _classify_payload(SAFE_EXAMPLES[index], install_id, run_id),
                session_factory,
            )
            for index in range(len(SAFE_EXAMPLES))
        ]
        if any(item.status_code >= 400 for item in baseline_sequential):
            raise RuntimeError("baseline sequential classify request failed")
        report["baseline"]["sequential"] = _summarize_results(baseline_sequential)
        report["baseline"]["sequential_compare"] = _compare_against_baseline(
            candidate_sequential,
            baseline_sequential,
        )
        if report["baseline"]["sequential_compare"]["semantic_mismatches"]:
            raise RuntimeError("candidate classification differs from baseline")

    candidate_classify: Dict[str, Dict[str, Any]] = {}
    for load_level in (8, 16, 32):
        candidate_results = _run_classify_batch(
            base_url=candidate_base,
            examples=SAFE_EXAMPLES,
            install_id=install_id,
            run_id=run_id,
            load_level=load_level,
            session_factory=session_factory,
        )
        if len(candidate_results) != 32:
            raise RuntimeError(f"candidate load {load_level} returned {len(candidate_results)} results instead of 32")

        candidate_classify[str(load_level)] = _summarize_results(candidate_results)

        if any(item.status_code >= 500 for item in candidate_results):
            raise RuntimeError(f"candidate load {load_level} produced a server error")

    report["classify"] = candidate_classify

    purchase_result = _invalid_purchase_probe(candidate_base, install_id, run_id, session_factory)
    if purchase_result["status_code"] != 200:
        raise RuntimeError(f"purchase probe returned status {purchase_result['status_code']}")
    if purchase_result.get("validationStatus") not in {"invalid", "unavailable"}:
        raise RuntimeError(
            f"purchase probe returned unexpected validation status {purchase_result.get('validationStatus')}"
        )
    report["purchase_probe"] = purchase_result

    report["endpoints"] = {
        "candidate": {
            "health": f"{candidate_base}/health",
            "classify": f"{candidate_base}/classify",
            "purchase_verify": f"{candidate_base}/purchases/verify",
        }
    }
    if baseline_base:
        report["endpoints"]["baseline"] = {
            "health": f"{baseline_base}/health",
            "classify": f"{baseline_base}/classify",
        }

    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
