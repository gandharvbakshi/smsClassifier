"""Privacy-safe semantic OTP-intent shadow evaluator.

This module builds class prototypes from OTP-positive labeled examples, then
evaluates a prototype-based intent classifier with explicit UNKNOWN abstention.

Design goals:
- privacy-safe: never writes sender text, body text, or identifiers to artifacts
- optional dependencies: transformers/torch are only imported when the default
  encoder is actually requested
- testable: all embedding work can be injected for unit tests

The default encoder is ``intfloat/e5-small`` with normalized mean pooling.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


UNKNOWN_LABEL = "UNKNOWN"
DEFAULT_MODEL_NAME = "intfloat/e5-small"
DEFAULT_TRAIN_RATIO = 0.6
DEFAULT_CALIB_RATIO = 0.2
DEFAULT_TEST_RATIO = 0.2
DEFAULT_TARGET_ACCEPTED_ACCURACY = 0.90
DEFAULT_SYNTHETIC_BLEND_WEIGHT = 0.10

CANONICAL_INTENTS = [
    "APP_ACCOUNT_CHANGE_OTP",
    "APP_LOGIN_OTP",
    "BANK_OR_CARD_TXN_OTP",
    "DELIVERY_OR_SERVICE_OTP",
    "FINANCIAL_LOGIN_OTP",
    "GENERIC_APP_ACTION_OTP",
    "KYC_OR_ESIGN_OTP",
    "UPI_TXN_OR_PIN_OTP",
]

CSV_INTENT_ALIASES = {
    "app_account_change_otp": "APP_ACCOUNT_CHANGE_OTP",
    "app_login_otp": "APP_LOGIN_OTP",
    "bank_or_card_txn_otp": "BANK_OR_CARD_TXN_OTP",
    "delivery_or_service_otp": "DELIVERY_OR_SERVICE_OTP",
    "financial_login_otp": "FINANCIAL_LOGIN_OTP",
    "generic_app_action_otp": "GENERIC_APP_ACTION_OTP",
    "kyc_or_esign_otp": "KYC_OR_ESIGN_OTP",
    "upi_txn_or_pin_otp": "UPI_TXN_OR_PIN_OTP",
    "not_otp": None,
    "": None,
}


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{6,}\d)\b")
_LONG_NUM_RE = re.compile(r"\b\d{3,}\b")
_SHORT_NUM_RE = re.compile(r"\b\d+\b")
_HEX_RE = re.compile(r"\b[a-f0-9]{6,}\b", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


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


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        text = str(value).strip()
        if not text:
            return None
        return int(text)
    except Exception:
        return None


def _stable_hash_int(text: str) -> int:
    return int.from_bytes(sha256(text.encode("utf-8")).digest()[:8], "big")


def normalize_sender(sender: Any) -> str:
    text = _coerce_text(sender) or ""
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def normalize_template(body: Any) -> str:
    text = _coerce_text(body) or ""
    text = text.lower()
    text = _URL_RE.sub(" <URL> ", text)
    text = _EMAIL_RE.sub(" <EMAIL> ", text)
    text = _PHONE_RE.sub(" <PHONE> ", text)
    text = _HEX_RE.sub(" <HEX> ", text)
    text = re.sub(r"\b(?:otp|code|passcode|pin|password)\s*[:=-]?\s*\d{3,8}\b", " <CODE> ", text)
    text = _LONG_NUM_RE.sub(" <NUM> ", text)
    text = _SHORT_NUM_RE.sub(" <NUM> ", text)
    text = re.sub(r"\b\d{2}:\d{2}(?::\d{2})?\b", " <TIME> ", text)
    text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", " <DATE> ", text)
    text = re.sub(r"[^a-z<>\s_/-]", " ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def group_key(sender: Any, body: Any) -> str:
    return f"{normalize_sender(sender)}\u0000{normalize_template(body)}"


def canonical_intent(raw_intent: Any) -> str | None:
    text = _coerce_text(raw_intent)
    if text is None:
        return None
    return CSV_INTENT_ALIASES.get(text.strip().lower(), text.strip().upper())


def _label_from_record(record: Mapping[str, Any]) -> str | None:
    is_otp = _coerce_bool(record.get("is_otp"))
    if is_otp is not True:
        return None
    intent = canonical_intent(record.get("otp_intent"))
    if intent is None or intent not in CANONICAL_INTENTS:
        return None
    return intent


def _approved_synthetic(record: Mapping[str, Any]) -> bool:
    for key in ("approved", "jury_approved", "is_jury_approved", "ok"):
        value = record.get(key)
        if value is not None:
            return _coerce_bool(value) is True
    return False


@dataclass(frozen=True)
class SemanticExample:
    row_id: int | None
    sender: str
    body: str
    label: str
    source: str
    group_id: str

    @property
    def encoder_text(self) -> str:
        # E5 works best with passage-style inputs for document-like texts.
        return f"passage: {self.sender}\n{self.body}"


@dataclass(frozen=True)
class Prediction:
    label: str
    similarity: float
    margin: float
    top2: tuple[tuple[str, float], tuple[str, float]] | None = None


def load_majority_jury_labels(jury_path: Path | str) -> dict[int, dict[str, Any]]:
    latest_by_provider: dict[tuple[int, str], Mapping[str, Any]] = {}
    path = Path(jury_path)
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not _coerce_bool(record.get("ok")):
                continue
            row_id = _safe_int(record.get("row_id"))
            if row_id is None:
                continue
            verdict = record.get("verdict")
            if not isinstance(verdict, Mapping):
                continue
            provider = _coerce_text(record.get("provider")) or f"record-{line_number}"
            latest_by_provider[(row_id, provider)] = verdict

    by_row: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for (row_id, _provider), verdict in latest_by_provider.items():
        by_row[row_id].append(verdict)

    majority: dict[int, dict[str, Any]] = {}
    for row_id, verdicts in by_row.items():
        otp_votes = [_coerce_bool(verdict.get("is_otp")) for verdict in verdicts]
        true_count = sum(vote is True for vote in otp_votes)
        false_count = sum(vote is False for vote in otp_votes)
        if true_count == false_count:
            is_otp: bool | None = None
        else:
            is_otp = true_count > false_count

        intent_votes = [
            canonical_intent(verdict.get("otp_intent"))
            for verdict in verdicts
            if _coerce_bool(verdict.get("is_otp")) is True
        ]
        intent_counts = Counter(
            intent for intent in intent_votes if intent in CANONICAL_INTENTS
        )
        intent: str | None = None
        if intent_counts:
            ranked = intent_counts.most_common()
            if len(ranked) == 1 or ranked[0][1] > ranked[1][1]:
                intent = ranked[0][0]
        majority[row_id] = {
            "is_otp": is_otp,
            "otp_intent": intent if is_otp is True else None,
            "provider_votes": len(verdicts),
        }
    return majority


def load_majority_jury_otp_votes(jury_path: Path | str) -> dict[int, bool | None]:
    return {
        row_id: labels.get("is_otp")
        for row_id, labels in load_majority_jury_labels(jury_path).items()
    }


def load_examples_from_csv(
    csv_path: Path | str,
    jury_votes: Mapping[int, bool | None] | None = None,
    jury_labels: Mapping[int, Mapping[str, Any]] | None = None,
) -> tuple[list[SemanticExample], dict[str, int]]:
    path = Path(csv_path)
    examples: list[SemanticExample] = []
    counts = {
        "csv_positive": 0,
        "jury_supported_positive": 0,
        "jury_intent_override": 0,
        "jury_recovered_positive": 0,
        "skipped_unresolved_jury_intent": 0,
        "skipped_conflict": 0,
        "duplicate_ids": 0,
    }
    rows_by_id: dict[int, Mapping[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row_index, row in enumerate(reader, start=1):
            if row.get("section") and row.get("section") != "message":
                continue
            row_id = _safe_int(row.get("id")) or row_index
            if row_id in rows_by_id:
                counts["duplicate_ids"] += 1
            rows_by_id[row_id] = row

    for row_id, row in rows_by_id.items():
        app_label = _label_from_record(row)
        if app_label is not None:
            counts["csv_positive"] += 1
        jury_record = jury_labels.get(row_id) if jury_labels is not None else None
        jury_vote = (
            _coerce_bool(jury_record.get("is_otp"))
            if jury_record is not None
            else jury_votes.get(row_id) if jury_votes is not None else None
        )
        label = app_label
        if jury_labels is not None or jury_votes is not None:
            if jury_vote is False:
                if app_label is not None:
                    counts["skipped_conflict"] += 1
                continue
            if jury_vote is True:
                counts["jury_supported_positive"] += 1
                jury_intent = canonical_intent(
                    jury_record.get("otp_intent") if jury_record is not None else None
                )
                if jury_intent in CANONICAL_INTENTS:
                    if app_label is None:
                        counts["jury_recovered_positive"] += 1
                    elif jury_intent != app_label:
                        counts["jury_intent_override"] += 1
                    label = jury_intent
                elif jury_labels is not None:
                    counts["skipped_unresolved_jury_intent"] += 1
                    continue
        if label is None:
            continue
        sender = _coerce_text(row.get("sender")) or ""
        body = _coerce_text(row.get("body")) or ""
        examples.append(
            SemanticExample(
                row_id=row_id,
                sender=sender,
                body=body,
                label=label,
                source="csv",
                group_id=group_key(sender, body),
            )
        )
    return examples, counts


def load_examples_from_synthetic_jsonl(jsonl_path: Path | str) -> tuple[list[SemanticExample], dict[str, int]]:
    path = Path(jsonl_path)
    examples: list[SemanticExample] = []
    counts = {"synthetic_total": 0, "synthetic_approved": 0}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            counts["synthetic_total"] += 1
            if not _approved_synthetic(record):
                continue
            label = _label_from_record(record)
            if label is None:
                continue
            counts["synthetic_approved"] += 1
            sender = _coerce_text(record.get("sender")) or ""
            body = _coerce_text(record.get("body")) or ""
            row_id = _safe_int(record.get("row_id"))
            examples.append(
                SemanticExample(
                    row_id=row_id,
                    sender=sender,
                    body=body,
                    label=label,
                    source="synthetic",
                    group_id=group_key(sender, body),
                )
            )
    return examples, counts


def load_training_examples(
    csv_path: Path | str,
    jury_path: Path | str | None = None,
    synthetic_path: Path | str | None = None,
) -> tuple[list[SemanticExample], dict[str, int]]:
    jury_labels = load_majority_jury_labels(jury_path) if jury_path is not None else None
    examples, counts = load_examples_from_csv(csv_path, jury_labels=jury_labels)
    if synthetic_path is not None:
        synthetic_examples, synthetic_counts = load_examples_from_synthetic_jsonl(synthetic_path)
        examples.extend(synthetic_examples)
        counts.update(synthetic_counts)
    return examples, counts


def _group_examples(examples: Sequence[SemanticExample]) -> dict[str, list[SemanticExample]]:
    grouped: dict[str, list[SemanticExample]] = defaultdict(list)
    for example in examples:
        grouped[example.group_id].append(example)
    return grouped


def _group_label(examples: Sequence[SemanticExample]) -> str:
    counts = Counter(example.label for example in examples)
    best = max(counts.items(), key=lambda item: (item[1], item[0]))
    return best[0]


def split_examples_by_group(
    examples: Sequence[SemanticExample],
    *,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    calib_ratio: float = DEFAULT_CALIB_RATIO,
    test_ratio: float = DEFAULT_TEST_RATIO,
) -> dict[str, list[SemanticExample]]:
    if not math.isclose(train_ratio + calib_ratio + test_ratio, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        raise ValueError("split ratios must sum to 1.0")

    grouped = _group_examples(examples)
    by_label: dict[str, list[tuple[str, list[SemanticExample]]]] = defaultdict(list)
    for group_id, group_examples in grouped.items():
        by_label[_group_label(group_examples)].append((group_id, group_examples))

    splits = {"train": [], "calibration": [], "heldout": []}
    for label in sorted(by_label):
        ordered = sorted(by_label[label], key=lambda item: _stable_hash_int(item[0]))
        group_count = len(ordered)
        if group_count == 1:
            allocations = {"train": 1, "calibration": 0, "heldout": 0}
        elif group_count == 2:
            allocations = {"train": 1, "calibration": 1, "heldout": 0}
        else:
            train_n = max(1, int(round(group_count * train_ratio)))
            calib_n = max(1, int(round(group_count * calib_ratio)))
            if train_n + calib_n >= group_count:
                overflow = train_n + calib_n - (group_count - 1)
                if overflow > 0:
                    train_n = max(1, train_n - overflow)
            heldout_n = group_count - train_n - calib_n
            if heldout_n < 1:
                if train_n > calib_n and train_n > 1:
                    train_n -= 1
                elif calib_n > 1:
                    calib_n -= 1
                heldout_n = group_count - train_n - calib_n
            allocations = {"train": train_n, "calibration": calib_n, "heldout": heldout_n}

        idx = 0
        for split_name in ("train", "calibration", "heldout"):
            take = allocations[split_name]
            for _, group_examples in ordered[idx : idx + take]:
                splits[split_name].extend(group_examples)
            idx += take

    return splits


def split_real_examples_with_training_only_synthetic(
    examples: Sequence[SemanticExample],
    *,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    calib_ratio: float = DEFAULT_CALIB_RATIO,
    test_ratio: float = DEFAULT_TEST_RATIO,
) -> dict[str, list[SemanticExample]]:
    real_examples = [example for example in examples if example.source != "synthetic"]
    synthetic_examples = [example for example in examples if example.source == "synthetic"]
    splits = split_examples_by_group(
        real_examples,
        train_ratio=train_ratio,
        calib_ratio=calib_ratio,
        test_ratio=test_ratio,
    )
    splits["train"].extend(synthetic_examples)
    return splits


def _vector_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _vector_norm(a: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def _vector_normalize(a: Sequence[float]) -> list[float]:
    norm = _vector_norm(a)
    if norm == 0.0:
        return [0.0 for _ in a]
    return [x / norm for x in a]


def _vector_mean(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    sums = [0.0] * dim
    for vec in vectors:
        for i, value in enumerate(vec):
            sums[i] += float(value)
    return [value / len(vectors) for value in sums]


def _as_float_vectors(encoded: Any) -> list[list[float]]:
    if hasattr(encoded, "detach"):
        encoded = encoded.detach()
    if hasattr(encoded, "cpu"):
        encoded = encoded.cpu()
    if hasattr(encoded, "tolist"):
        encoded = encoded.tolist()
    if isinstance(encoded, list):
        if not encoded:
            return []
        if encoded and isinstance(encoded[0], (int, float)):
            return [[float(v) for v in encoded]]
        return [[float(v) for v in row] for row in encoded]
    raise TypeError("encoder must return a tensor-like object or nested sequence")


def _encode_texts(embedder: Any, texts: Sequence[str]) -> list[list[float]]:
    if hasattr(embedder, "encode"):
        encoded = embedder.encode(list(texts))
    elif callable(embedder):
        encoded = embedder(list(texts))
    else:
        raise TypeError("embedder must be callable or expose an encode() method")
    vectors = _as_float_vectors(encoded)
    if len(vectors) != len(texts):
        raise ValueError("encoder returned the wrong number of vectors")
    return vectors


def load_default_sentence_encoder(model_name: str = DEFAULT_MODEL_NAME, device: str | None = None) -> Any:
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except Exception as exc:  # pragma: no cover - exercised only in optional runtime
        raise RuntimeError(
            "Default semantic encoder requires optional dependencies: "
            "install 'transformers' and 'torch' to use intfloat/e5-small."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    class _Encoder:
        def __init__(self, tokenizer, model, device):
            self.tokenizer = tokenizer
            self.model = model
            self.device = device

        def encode(self, texts: Sequence[str]) -> Any:
            encoded_batches = []
            for start in range(0, len(texts), 32):
                batch = self.tokenizer(
                    list(texts[start : start + 32]),
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                ).to(self.device)
                with torch.no_grad():
                    outputs = self.model(**batch)
                    token_embeddings = outputs.last_hidden_state
                    attention_mask = batch["attention_mask"].unsqueeze(-1).type_as(token_embeddings)
                    summed = (token_embeddings * attention_mask).sum(dim=1)
                    counts = attention_mask.sum(dim=1).clamp(min=1.0)
                    mean_pooled = summed / counts
                    normalized = torch.nn.functional.normalize(mean_pooled, p=2, dim=1)
                encoded_batches.append(normalized.cpu())
            return torch.cat(encoded_batches, dim=0) if encoded_batches else torch.empty((0, 0))

    return _Encoder(tokenizer, model, device)


def fit_class_prototypes(
    examples: Sequence[SemanticExample],
    embedder: Any,
    *,
    synthetic_blend_weight: float = DEFAULT_SYNTHETIC_BLEND_WEIGHT,
) -> tuple[dict[str, list[float]], dict[str, int], int]:
    if not 0.0 <= synthetic_blend_weight <= 1.0:
        raise ValueError("synthetic_blend_weight must be between 0.0 and 1.0")
    labels = sorted({example.label for example in examples})
    vectors = _encode_texts(embedder, [example.encoder_text for example in examples])
    if not vectors:
        raise ValueError("no examples available to fit prototypes")
    by_label: dict[str, list[list[float]]] = defaultdict(list)
    real_by_label: dict[str, list[list[float]]] = defaultdict(list)
    synthetic_by_label: dict[str, list[list[float]]] = defaultdict(list)
    for example, vector in zip(examples, vectors):
        normalized = _vector_normalize(vector)
        by_label[example.label].append(normalized)
        target = synthetic_by_label if example.source == "synthetic" else real_by_label
        target[example.label].append(normalized)

    prototypes: dict[str, list[float]] = {}
    supports: dict[str, int] = {}
    embedding_dim = len(vectors[0])
    for label in labels:
        label_vectors = by_label.get(label, [])
        if not label_vectors:
            continue
        supports[label] = len(label_vectors)
        real_vectors = real_by_label.get(label, [])
        synthetic_vectors = synthetic_by_label.get(label, [])
        if real_vectors:
            real_prototype = _vector_normalize(_vector_mean(real_vectors))
            if synthetic_vectors and synthetic_blend_weight > 0.0:
                synthetic_prototype = _vector_normalize(_vector_mean(synthetic_vectors))
                blended = [
                    (1.0 - synthetic_blend_weight) * real_value
                    + synthetic_blend_weight * synthetic_value
                    for real_value, synthetic_value in zip(real_prototype, synthetic_prototype)
                ]
                prototypes[label] = _vector_normalize(blended)
            else:
                prototypes[label] = real_prototype
        else:
            prototypes[label] = _vector_normalize(_vector_mean(synthetic_vectors))
    return prototypes, supports, embedding_dim


def _predict_from_vectors(
    vector: Sequence[float],
    prototypes: Mapping[str, Sequence[float]],
) -> Prediction:
    scored = sorted(
        ((label, float(_vector_dot(vector, proto))) for label, proto in prototypes.items()),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    if not scored:
        return Prediction(label=UNKNOWN_LABEL, similarity=float("-inf"), margin=float("-inf"))
    top1 = scored[0]
    top2 = scored[1] if len(scored) > 1 else (UNKNOWN_LABEL, float("-inf"))
    return Prediction(
        label=top1[0],
        similarity=top1[1],
        margin=top1[1] - top2[1],
        top2=(top1, top2),
    )


def predict_examples(
    examples: Sequence[SemanticExample],
    prototypes: Mapping[str, Sequence[float]],
    embedder: Any,
    *,
    similarity_threshold: float,
    margin_threshold: float,
) -> list[Prediction]:
    vectors = _encode_texts(embedder, [example.encoder_text for example in examples])
    predictions: list[Prediction] = []
    for vector in vectors:
        vector = _vector_normalize(vector)
        pred = _predict_from_vectors(vector, prototypes)
        if pred.similarity < similarity_threshold or pred.margin < margin_threshold:
            pred = Prediction(label=UNKNOWN_LABEL, similarity=pred.similarity, margin=pred.margin, top2=pred.top2)
        predictions.append(pred)
    return predictions


@dataclass(frozen=True)
class ThresholdSelection:
    similarity_threshold: float
    margin_threshold: float
    calibration_accuracy: float
    calibration_coverage: float
    calibration_accepted_accuracy: float
    calibration_accepted_count: int


def _score_thresholds(
    truths: Sequence[str],
    predictions: Sequence[Prediction],
    *,
    similarity_threshold: float,
    margin_threshold: float,
) -> tuple[float, float, float, int]:
    accepted = 0
    correct = 0
    total = len(truths)
    for truth, prediction in zip(truths, predictions):
        if prediction.similarity < similarity_threshold or prediction.margin < margin_threshold:
            continue
        accepted += 1
        if prediction.label == truth:
            correct += 1
    accepted_accuracy = (correct / accepted) if accepted else 0.0
    coverage = (accepted / total) if total else 0.0
    accuracy = (correct / total) if total else 0.0
    objective = accepted_accuracy * coverage
    return objective, accuracy, accepted_accuracy, accepted


def select_thresholds(
    calibration_examples: Sequence[SemanticExample],
    prototypes: Mapping[str, Sequence[float]],
    embedder: Any,
    target_accepted_accuracy: float = DEFAULT_TARGET_ACCEPTED_ACCURACY,
) -> ThresholdSelection:
    vectors = _encode_texts(embedder, [example.encoder_text for example in calibration_examples])
    truths = [example.label for example in calibration_examples]
    predictions = [_predict_from_vectors(_vector_normalize(vector), prototypes) for vector in vectors]
    if not predictions:
        raise ValueError("no calibration examples available for threshold selection")

    similarity_values = sorted({pred.similarity for pred in predictions})
    margin_values = sorted({pred.margin for pred in predictions})
    similarity_candidates = [similarity_values[0] - 1e-9] + [value + 1e-9 for value in similarity_values]
    margin_candidates = [margin_values[0] - 1e-9] + [value + 1e-9 for value in margin_values]

    minimum_accepted = min(len(truths), max(2, math.ceil(len(truths) * 0.10)))
    best: tuple[float, float, float, float, float, float, float, int] | None = None
    for sim_thr in similarity_candidates:
        for margin_thr in margin_candidates:
            objective, accuracy, accepted_accuracy, accepted = _score_thresholds(
                truths,
                predictions,
                similarity_threshold=sim_thr,
                margin_threshold=margin_thr,
            )
            coverage = (accepted / len(truths)) if truths else 0.0
            qualifies = accepted >= minimum_accepted and accepted_accuracy >= target_accepted_accuracy
            candidate = (
                1.0 if qualifies else 0.0,
                coverage if qualifies else accepted_accuracy,
                accepted_accuracy if qualifies else coverage,
                objective,
                accuracy,
                -sim_thr,
                -margin_thr,
                accepted,
            )
            if best is None or candidate > best:
                best = candidate

    assert best is not None
    _, _, _, _best_objective, best_accuracy, neg_sim, neg_margin, accepted_count = best
    sim_thr = -neg_sim
    margin_thr = -neg_margin
    _, _, best_accepted_accuracy, accepted_count = _score_thresholds(
        truths,
        predictions,
        similarity_threshold=sim_thr,
        margin_threshold=margin_thr,
    )
    best_coverage = accepted_count / len(truths) if truths else 0.0
    return ThresholdSelection(
        similarity_threshold=sim_thr,
        margin_threshold=margin_thr,
        calibration_accuracy=best_accuracy,
        calibration_coverage=best_coverage,
        calibration_accepted_accuracy=best_accepted_accuracy,
        calibration_accepted_count=accepted_count,
    )


def _classification_metrics(truths: Sequence[str], predictions: Sequence[str], labels: Sequence[str]) -> dict[str, Any]:
    total = len(truths)
    correct = sum(1 for truth, pred in zip(truths, predictions) if truth == pred)
    accuracy = correct / total if total else 0.0
    per_class: dict[str, dict[str, float | int]] = {}
    macro_f1_values: list[float] = []
    for label in labels:
        tp = fp = fn = 0
        support = 0
        for truth, pred in zip(truths, predictions):
            if truth == label:
                support += 1
                if pred == label:
                    tp += 1
                else:
                    fn += 1
            elif pred == label:
                fp += 1
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        if support:
            macro_f1_values.append(f1)
        per_class[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    macro_f1 = sum(macro_f1_values) / len(macro_f1_values) if macro_f1_values else 0.0
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "support": {label: per_class[label]["support"] for label in labels},
        "correct": correct,
        "total": total,
    }


def evaluate_shadow_model(
    *,
    csv_path: Path | str,
    jury_path: Path | str,
    embedder: Any,
    model_name: str = DEFAULT_MODEL_NAME,
    synthetic_path: Path | str | None = None,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    calib_ratio: float = DEFAULT_CALIB_RATIO,
    test_ratio: float = DEFAULT_TEST_RATIO,
    synthetic_blend_weight: float = DEFAULT_SYNTHETIC_BLEND_WEIGHT,
) -> dict[str, Any]:
    examples, source_counts = load_training_examples(csv_path, jury_path=jury_path, synthetic_path=synthetic_path)
    if not examples:
        raise ValueError("no OTP-positive intent examples were loaded")

    splits = split_real_examples_with_training_only_synthetic(
        examples,
        train_ratio=train_ratio,
        calib_ratio=calib_ratio,
        test_ratio=test_ratio,
    )
    train_examples = splits["train"]
    calib_examples = splits["calibration"] or splits["train"]
    heldout_examples = splits["heldout"]
    if not train_examples:
        raise ValueError("no training examples available after grouped split")
    if not heldout_examples:
        raise ValueError("no held-out examples available after grouped split")
    if not calib_examples:
        raise ValueError("no calibration examples available after grouped split")

    prototypes, train_support, embedding_dim = fit_class_prototypes(
        train_examples,
        embedder,
        synthetic_blend_weight=synthetic_blend_weight,
    )
    selection = select_thresholds(calib_examples, prototypes, embedder)
    heldout_predictions = predict_examples(
        heldout_examples,
        prototypes,
        embedder,
        similarity_threshold=selection.similarity_threshold,
        margin_threshold=selection.margin_threshold,
    )
    heldout_truths = [example.label for example in heldout_examples]
    heldout_labels = sorted({example.label for example in examples})
    predicted_labels = [pred.label for pred in heldout_predictions]
    accepted_mask = [pred.label != UNKNOWN_LABEL for pred in heldout_predictions]
    accepted_truths = [truth for truth, accepted in zip(heldout_truths, accepted_mask) if accepted]
    accepted_predictions = [pred for pred in predicted_labels if pred != UNKNOWN_LABEL]

    overall = _classification_metrics(heldout_truths, predicted_labels, heldout_labels)
    accepted = _classification_metrics(accepted_truths, accepted_predictions, heldout_labels) if accepted_truths else {
        "accuracy": 0.0,
        "macro_f1": 0.0,
        "per_class": {label: {"support": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0} for label in heldout_labels},
        "support": {label: 0 for label in heldout_labels},
        "correct": 0,
        "total": 0,
    }
    coverage = sum(accepted_mask) / len(heldout_predictions) if heldout_predictions else 0.0

    artifact = {
        "model_name": model_name,
        "embedding_dim": embedding_dim,
        "labels": heldout_labels,
        "thresholds": {
            "similarity": selection.similarity_threshold,
            "margin": selection.margin_threshold,
        },
        "prototype_norms": {label: _vector_norm(proto) for label, proto in prototypes.items()},
        "prototypes": prototypes,
        "split_counts": {name: len(values) for name, values in splits.items()},
        "source_counts": source_counts,
        "normalization": {
            "sender": "lower_trimmed_whitespace",
            "template": "lowercase_regex_masked",
            "pooling": "mean",
            "prototype_normalization": "l2",
            "embedding_normalization": "l2",
        },
        "synthetic_blend_weight": synthetic_blend_weight,
    }

    return {
        "model_name": model_name,
        "thresholds": {
            "similarity": selection.similarity_threshold,
            "margin": selection.margin_threshold,
            "calibration_accuracy": selection.calibration_accuracy,
            "calibration_coverage": selection.calibration_coverage,
            "calibration_accepted_accuracy": selection.calibration_accepted_accuracy,
            "calibration_accepted_count": selection.calibration_accepted_count,
            "target_accepted_accuracy": DEFAULT_TARGET_ACCEPTED_ACCURACY,
        },
        "split_counts": {name: len(values) for name, values in splits.items()},
        "train_support": train_support,
        "heldout": {
            "accuracy": overall["accuracy"],
            "macro_f1": overall["macro_f1"],
            "accepted_accuracy": accepted["accuracy"],
            "accepted_macro_f1": accepted["macro_f1"],
            "coverage": coverage,
            "support": overall["support"],
            "per_class": overall["per_class"],
            "correct": overall["correct"],
            "total": overall["total"],
        },
        "artifact": artifact,
    }


def _write_json(path: Path | str, payload: Mapping[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-path", type=Path, default=Path(__file__).resolve().parents[1] / "sms classifier log 2 may .csv")
    parser.add_argument("--jury-path", type=Path, default=Path(__file__).resolve().parent / "jury_results.jsonl")
    parser.add_argument("--synthetic-path", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=Path(__file__).resolve().parent / "semantic_intent_shadow_results.json")
    parser.add_argument("--artifact-json", type=Path, default=Path(__file__).resolve().parent / "semantic_intent_shadow_artifact.json")
    parser.add_argument("--model-name", type=str, default=DEFAULT_MODEL_NAME)
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO)
    parser.add_argument("--calib-ratio", type=float, default=DEFAULT_CALIB_RATIO)
    parser.add_argument("--test-ratio", type=float, default=DEFAULT_TEST_RATIO)
    parser.add_argument(
        "--synthetic-blend-weight",
        type=float,
        default=DEFAULT_SYNTHETIC_BLEND_WEIGHT,
        help="Bounded contribution of synthetic examples when a real class prototype exists.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    embedder = load_default_sentence_encoder(args.model_name)
    result = evaluate_shadow_model(
        csv_path=args.csv_path,
        jury_path=args.jury_path,
        synthetic_path=args.synthetic_path,
        embedder=embedder,
        model_name=args.model_name,
        train_ratio=args.train_ratio,
        calib_ratio=args.calib_ratio,
        test_ratio=args.test_ratio,
        synthetic_blend_weight=args.synthetic_blend_weight,
    )
    _write_json(args.output_json, result)
    _write_json(args.artifact_json, result["artifact"])
    heldout = result["heldout"]
    print(
        json.dumps(
            {
                "accuracy": heldout["accuracy"],
                "macro_f1": heldout["macro_f1"],
                "accepted_accuracy": heldout["accepted_accuracy"],
                "coverage": heldout["coverage"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
