"""Privacy-safe evaluation harness for the existing SMS corpus and jury votes."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 0:
            return False
        if value == 1:
            return True
        return None

    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y"}:
        return True
    if text in {"false", "f", "0", "no", "n"}:
        return False
    return None


def _coerce_int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("empty integer value")
    return int(text)


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"none", "null"}:
            return None
        return text
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _to_records(source: Any, *, csv_encoding: str = "utf-8-sig") -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        with path.open("r", encoding=csv_encoding, newline="") as fh:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]

    if hasattr(source, "to_dict") and hasattr(source, "columns"):
        # Duck-typed pandas DataFrame support without importing pandas.
        return [dict(row) for row in source.to_dict(orient="records")]

    return [dict(row) for row in source]


def _read_jury_records(source: Any) -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    if hasattr(source, "to_dict") and hasattr(source, "columns"):
        return [dict(row) for row in source.to_dict(orient="records")]

    return [dict(row) for row in source]


def _majority_vote(values: Sequence[Any]) -> Any | None:
    counts = Counter(v for v in values if v is not None)
    if not counts:
        return None
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


@dataclass(frozen=True)
class FieldEvaluation:
    support: int
    unresolved: int
    tp: int | None = None
    fp: int | None = None
    tn: int | None = None
    fn: int | None = None
    correct: int | None = None
    incorrect: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    accuracy: float | None = None


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _binary_metrics(tp: int, fp: int, tn: int, fn: int) -> dict[str, float]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    accuracy = _safe_div(tp + tn, tp + tn + fp + fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def _classification_from_truth(
    app_values: Mapping[int, Any],
    jury_truth: Mapping[int, Any],
    *,
    positive_value: Any,
) -> tuple[FieldEvaluation, dict[str, int]]:
    tp = fp = tn = fn = 0
    unresolved = 0
    support = 0
    for row_id, truth in jury_truth.items():
        if truth is None:
            unresolved += 1
            continue
        if row_id not in app_values:
            continue
        support += 1
        predicted = app_values[row_id]
        if predicted == positive_value and truth == positive_value:
            tp += 1
        elif predicted == positive_value and truth != positive_value:
            fp += 1
        elif predicted != positive_value and truth != positive_value:
            tn += 1
        else:
            fn += 1

    metrics = _binary_metrics(tp, fp, tn, fn)
    return (
        FieldEvaluation(
            support=support,
            unresolved=unresolved,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1=metrics["f1"],
            accuracy=metrics["accuracy"],
        ),
        {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    )


def _exact_match_metrics(
    app_values: Mapping[int, Any],
    jury_truth: Mapping[int, Any],
    *,
    eligible_ids: set[int] | None = None,
) -> tuple[FieldEvaluation, dict[str, int]]:
    support = 0
    unresolved = 0
    correct = 0
    incorrect = 0
    for row_id, truth in jury_truth.items():
        if eligible_ids is not None and row_id not in eligible_ids:
            continue
        if truth is None:
            unresolved += 1
            continue
        if row_id not in app_values:
            continue
        support += 1
        if app_values[row_id] == truth:
            correct += 1
        else:
            incorrect += 1

    total = correct + incorrect
    accuracy = _safe_div(correct, total)
    return (
        FieldEvaluation(
            support=support,
            unresolved=unresolved,
            correct=correct,
            incorrect=incorrect,
            precision=accuracy,
            recall=accuracy,
            f1=accuracy,
            accuracy=accuracy,
        ),
        {"correct": correct, "incorrect": incorrect},
    )


def _aggregate_jury_truth(jury_records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    by_row: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for record in jury_records:
        try:
            row_id = _coerce_int(record["row_id"])
        except Exception:
            continue
        if not record.get("ok"):
            continue
        verdict = record.get("verdict")
        if not isinstance(verdict, Mapping):
            continue
        by_row[row_id].append(verdict)

    otp_truth: dict[int, bool | None] = {}
    phish_truth: dict[int, bool | None] = {}
    intent_truth: dict[int, str | None] = {}
    intent_eligible: set[int] = set()
    vote_counts: dict[int, int] = {}
    unresolved = {"is_otp": 0, "is_phishing": 0, "otp_intent": 0}

    for row_id, votes in by_row.items():
        vote_counts[row_id] = len(votes)
        otp_values = [_coerce_bool(v.get("is_otp")) for v in votes]
        phish_values = [_coerce_bool(v.get("is_phishing")) for v in votes]
        otp = _majority_vote(otp_values)
        phish = _majority_vote(phish_values)
        if otp is None:
            unresolved["is_otp"] += 1
        if phish is None:
            unresolved["is_phishing"] += 1

        otp_truth[row_id] = otp
        phish_truth[row_id] = phish

        if otp is True:
            intent_eligible.add(row_id)
            intent_votes = [
                _coerce_text(v.get("otp_intent"))
                for v in votes
                if _coerce_bool(v.get("is_otp")) is True and _coerce_text(v.get("otp_intent")) is not None
            ]
            intent = _majority_vote(intent_votes)
            if intent is None:
                unresolved["otp_intent"] += 1
            intent_truth[row_id] = intent
        else:
            intent_truth[row_id] = None

    return {
        "by_row": by_row,
        "vote_counts": vote_counts,
        "otp_truth": otp_truth,
        "phish_truth": phish_truth,
        "intent_truth": intent_truth,
        "intent_eligible": intent_eligible,
        "unresolved": unresolved,
    }


def evaluate_existing_sms_corpus(
    corpus_source: Any,
    jury_source: Any,
) -> dict[str, Any]:
    corpus_rows = _to_records(corpus_source)
    jury_records = _read_jury_records(jury_source)
    jury = _aggregate_jury_truth(jury_records)

    corpus_by_id: dict[int, dict[str, Any]] = {}
    corpus_id_counts: Counter[int] = Counter()
    for row in corpus_rows:
        try:
            row_id = _coerce_int(row["id"])
        except Exception:
            continue
        corpus_id_counts[row_id] += 1
        corpus_by_id[row_id] = dict(row)

    app_otp: dict[int, bool] = {}
    app_phish: dict[int, bool] = {}
    app_intent: dict[int, str | None] = {}
    for row_id, row in corpus_by_id.items():
        app_otp[row_id] = bool(_coerce_bool(row.get("is_otp")))
        app_phish[row_id] = bool(_coerce_bool(row.get("is_phishing")))
        app_intent[row_id] = _coerce_text(row.get("otp_intent"))

    overlap_ids = sorted(set(corpus_by_id) & set(jury["otp_truth"]))

    otp_eval, otp_confusion = _classification_from_truth(app_otp, jury["otp_truth"], positive_value=True)
    phish_eval, phish_confusion = _classification_from_truth(
        app_phish, jury["phish_truth"], positive_value=True
    )
    intent_eval, intent_confusion = _exact_match_metrics(
        app_intent,
        jury["intent_truth"],
        eligible_ids=jury["intent_eligible"],
    )

    jury_vote_counts = Counter(jury["vote_counts"].values())

    return {
        "corpus": {
            "rows": len(corpus_by_id),
            "parsed_rows": len(corpus_rows),
            "duplicate_id_groups": sum(1 for count in corpus_id_counts.values() if count > 1),
            "duplicate_rows": sum(count - 1 for count in corpus_id_counts.values() if count > 1),
            "dedupe_strategy": "latest_by_file_order",
        },
        "jury": {
            "records": len(jury_records),
            "rows": len(jury["by_row"]),
            "vote_count_distribution": {str(k): v for k, v in sorted(jury_vote_counts.items())},
            "unresolved": jury["unresolved"],
        },
        "overlap": {
            "rows": len(overlap_ids),
        },
        "otp": {
            "support": otp_eval.support,
            "unresolved": otp_eval.unresolved,
            "confusion": otp_confusion,
            "metrics": {
                "precision": otp_eval.precision,
                "recall": otp_eval.recall,
                "f1": otp_eval.f1,
                "accuracy": otp_eval.accuracy,
            },
        },
        "phishing": {
            "support": phish_eval.support,
            "unresolved": phish_eval.unresolved,
            "confusion": phish_confusion,
            "metrics": {
                "precision": phish_eval.precision,
                "recall": phish_eval.recall,
                "f1": phish_eval.f1,
                "accuracy": phish_eval.accuracy,
            },
        },
        "intent": {
            "support": intent_eval.support,
            "unresolved": intent_eval.unresolved,
            "confusion": intent_confusion,
            "metrics": {
                "precision": intent_eval.precision,
                "recall": intent_eval.recall,
                "f1": intent_eval.f1,
                "accuracy": intent_eval.accuracy,
            },
            "jury_only_when_otp": True,
        },
    }


def _format_pct(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value:.4f}"


def render_human_report(report: Mapping[str, Any]) -> str:
    lines = []
    lines.append("SMS corpus release audit")
    lines.append(
        "Corpus rows: "
        f"{report['corpus']['rows']} (parsed: {report['corpus']['parsed_rows']}, "
        f"duplicate groups: {report['corpus']['duplicate_id_groups']}, "
        f"duplicate rows: {report['corpus']['duplicate_rows']}, "
        f"dedupe: {report['corpus']['dedupe_strategy']})"
    )
    lines.append(
        "Jury rows: "
        f"{report['jury']['rows']} across {report['jury']['records']} records "
        f"(vote distribution: {report['jury']['vote_count_distribution']})"
    )
    lines.append(f"Overlap rows: {report['overlap']['rows']}")

    for label in ("otp", "phishing"):
        section = report[label]
        metrics = section["metrics"]
        conf = section["confusion"]
        lines.append(
            f"{label.upper()}: support={section['support']} unresolved={section['unresolved']} "
            f"TP={conf['tp']} FP={conf['fp']} TN={conf['tn']} FN={conf['fn']} "
            f"precision={_format_pct(metrics['precision'])} recall={_format_pct(metrics['recall'])} "
            f"f1={_format_pct(metrics['f1'])} accuracy={_format_pct(metrics['accuracy'])}"
        )

    intent = report["intent"]
    intent_metrics = intent["metrics"]
    intent_conf = intent["confusion"]
    lines.append(
        "INTENT (jury OTP rows only): "
        f"support={intent['support']} unresolved={intent['unresolved']} "
        f"correct={intent_conf['correct']} incorrect={intent_conf['incorrect']} "
        f"precision={_format_pct(intent_metrics['precision'])} recall={_format_pct(intent_metrics['recall'])} "
        f"f1={_format_pct(intent_metrics['f1'])} accuracy={_format_pct(intent_metrics['accuracy'])}"
    )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate sms classifier log 2 may .csv against analysis/jury_results.jsonl."
    )
    root = default_repo_root()
    parser.add_argument(
        "--corpus-csv",
        type=Path,
        default=root / "sms classifier log 2 may .csv",
        help="Path to the SMS corpus CSV.",
    )
    parser.add_argument(
        "--jury-jsonl",
        type=Path,
        default=root / "analysis" / "jury_results.jsonl",
        help="Path to jury_results.jsonl.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of the human-readable summary.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    report = evaluate_existing_sms_corpus(args.corpus_csv, args.jury_jsonl)
    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_human_report(report) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
