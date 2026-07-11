from __future__ import annotations

import json
import pickle
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_intent_label_contract import (
    REQUIRED_CANONICAL_LABELS,
    ContractError,
    check_contract,
)


class FixtureLabelEncoder:
    pass


def write_fixture_tree(
    base: Path,
    *,
    metadata_labels,
    pickle_labels,
    kotlin_labels,
    kotlin_text: str | None = None,
) -> dict[str, Path]:
    metadata_path = base / "app/src/main/assets/model_metadata.json"
    pickle_path = base / "trained_models/label_encoder_intent.pkl"
    kotlin_path = base / "app/src/main/java/com/smsclassifier/app/classification/OnDeviceClassifier.kt"

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    pickle_path.parent.mkdir(parents=True, exist_ok=True)
    kotlin_path.parent.mkdir(parents=True, exist_ok=True)

    metadata_path.write_text(
        json.dumps(
            {
                "models": {
                    "otp_intent": {
                        "class_names": list(metadata_labels),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    encoder = FixtureLabelEncoder()
    encoder.classes_ = list(pickle_labels)
    with pickle_path.open("wb") as fh:
        pickle.dump(encoder, fh, protocol=4)

    if kotlin_text is None:
        label_lines = "".join(f'            "{label}",\n' for label in kotlin_labels)
        kotlin_text = (
            "package com.smsclassifier.app.classification\n\n"
            "class OnDeviceClassifier {\n"
            "    private fun mapIntentIndex(index: Int): String {\n"
            "        val intents = listOf(\n"
            f"{label_lines}"
            "        )\n"
            "        return intents.getOrNull(index) ?: \"UNKNOWN\"\n"
            "    }\n"
            "}\n"
        )

    kotlin_path.write_text(kotlin_text, encoding="utf-8")

    return {
        "metadata": metadata_path,
        "pickle": pickle_path,
        "kotlin": kotlin_path,
    }


class IntentLabelContractTests(unittest.TestCase):
    def test_matching_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                metadata_labels=REQUIRED_CANONICAL_LABELS,
                pickle_labels=REQUIRED_CANONICAL_LABELS,
                kotlin_labels=REQUIRED_CANONICAL_LABELS,
            )

            result = check_contract(
                root,
                metadata_path=files["metadata"],
                pickle_path=files["pickle"],
                kotlin_path=files["kotlin"],
            )

            self.assertEqual(result["kotlin_labels"], list(REQUIRED_CANONICAL_LABELS))

    def test_order_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            drifted = list(REQUIRED_CANONICAL_LABELS)
            drifted[0], drifted[1] = drifted[1], drifted[0]
            files = write_fixture_tree(
                root,
                metadata_labels=REQUIRED_CANONICAL_LABELS,
                pickle_labels=REQUIRED_CANONICAL_LABELS,
                kotlin_labels=drifted,
            )

            with self.assertRaises(ContractError) as ctx:
                check_contract(
                    root,
                    metadata_path=files["metadata"],
                    pickle_path=files["pickle"],
                    kotlin_path=files["kotlin"],
                )

            self.assertIn("OnDeviceClassifier.kt mapIntentIndex()", str(ctx.exception))
            self.assertIn("drifted", str(ctx.exception))

    def test_missing_labels_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = REQUIRED_CANONICAL_LABELS[:-1]
            files = write_fixture_tree(
                root,
                metadata_labels=missing,
                pickle_labels=missing,
                kotlin_labels=missing,
            )

            with self.assertRaises(ContractError) as ctx:
                check_contract(
                    root,
                    metadata_path=files["metadata"],
                    pickle_path=files["pickle"],
                    kotlin_path=files["kotlin"],
                )

            self.assertIn("Missing", str(ctx.exception))
            self.assertIn("UPI_TXN_OR_PIN_OTP", str(ctx.exception))

    def test_kotlin_parse_failure_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                metadata_labels=REQUIRED_CANONICAL_LABELS,
                pickle_labels=REQUIRED_CANONICAL_LABELS,
                kotlin_labels=REQUIRED_CANONICAL_LABELS,
                kotlin_text=(
                    "package com.smsclassifier.app.classification\n\n"
                    "class OnDeviceClassifier {\n"
                    "    private fun mapIntentIndex(index: Int): String {\n"
                    "        val intents = listOf(\n"
                    '            "APP_ACCOUNT_CHANGE_OTP",\n'
                    '            "APP_LOGIN_OTP"\n'
                    "    }\n"
                    "}\n"
                ),
            )

            with self.assertRaises(ContractError) as ctx:
                check_contract(
                    root,
                    metadata_path=files["metadata"],
                    pickle_path=files["pickle"],
                    kotlin_path=files["kotlin"],
                )

            self.assertIn("Failed to parse Kotlin", str(ctx.exception))

    def test_skip_pickle_supports_release_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                metadata_labels=REQUIRED_CANONICAL_LABELS,
                pickle_labels=REQUIRED_CANONICAL_LABELS,
                kotlin_labels=REQUIRED_CANONICAL_LABELS,
            )
            files["pickle"].unlink()

            result = check_contract(
                root,
                metadata_path=files["metadata"],
                pickle_path=files["pickle"],
                kotlin_path=files["kotlin"],
                skip_pickle=True,
            )

            self.assertEqual(result["pickle_labels"], [])


if __name__ == "__main__":
    unittest.main()
