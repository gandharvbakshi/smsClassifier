"""Purchase contract regression tests; model inference is intentionally isolated."""
import builtins
import importlib.util
import io
import json
import pickle
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from google.api_core.exceptions import NotFound


@pytest.fixture
def server(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setenv("FEEDBACK_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("FEEDBACK_GCS_BUCKET", raising=False)
    path = Path(__file__).resolve().parents[1] / "scripts/android_backend_server.py"
    spec = importlib.util.spec_from_file_location("purchase_test_server", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    original_open, original_exists = builtins.open, Path.exists
    names = {"tfidf_vectorizer.pkl", "model_isotp_lgb.pkl", "model_phishing_lgb.pkl"}

    def fake_open(path, *args, **kwargs):
        if Path(path).name in names:
            return io.BytesIO(pickle.dumps(None))
        return original_open(path, *args, **kwargs)

    with patch("builtins.open", fake_open), patch.object(
        Path, "exists", lambda path: path.name in names or original_exists(path)
    ):
        spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_gcs_client", lambda: None)
    return module


def purchase(server):
    return server.PurchaseVerifyRequest(
        installId="synthetic-install", firebaseUid="synthetic-uid",
        productId="pro_lifetime", productType="inapp", purchaseToken="private-test-token",
    )


@pytest.mark.parametrize("status,valid", [("unavailable", None), ("invalid", False)])
def test_failed_validation_preserves_existing_paid_and_trial(server, monkeypatch, status, valid):
    req = purchase(server)
    record = server._load_entitlement(req.installId, req.firebaseUid)
    record.update(proActive=True, trialStartedAt=1, trialExpiresAt=9999999999999)
    server._write_entitlement(record)
    monkeypatch.setattr(server, "_validate_play_purchase", lambda _: server.PlayValidationResult(status, valid))
    result = server.verify_purchase(req)
    assert result["proActive"] is True
    assert result["trialStartedAt"] == 1
    assert result["validationStatus"] == status


def test_duplicate_verified_purchase_is_idempotent_and_never_stores_token(server, monkeypatch):
    req = purchase(server)
    monkeypatch.setattr(server, "_validate_play_purchase", lambda _: server.PlayValidationResult("verified", True, "inapp"))
    first = server.verify_purchase(req)
    second = server.verify_purchase(req)
    assert first == second
    assert second["proActive"] is True
    stored = [p.read_text() for p in server.FEEDBACK_LOG_DIR.glob("entitlements_*.json")]
    assert len(stored) == 2
    assert all(req.purchaseToken not in row for row in stored)


def fake_gcs(server, monkeypatch):
    blob = Mock()
    client = Mock()
    client.bucket.return_value.blob.return_value = blob
    monkeypatch.setattr(server, "FEEDBACK_GCS_BUCKET", "synthetic-bucket")
    monkeypatch.setattr(server, "_gcs_client", lambda: client)
    return blob


def test_storage_read_is_one_bounded_request(server, monkeypatch):
    blob = fake_gcs(server, monkeypatch)
    blob.download_as_text.return_value = '{"proActive":true}'
    assert server._read_entitlement_blob("test.json")["proActive"]
    blob.exists.assert_not_called()
    blob.download_as_text.assert_called_once_with(encoding="utf-8", timeout=3.0, retry=None)


@pytest.mark.parametrize("error", [NotFound("absent"), TimeoutError("slow")])
def test_storage_read_failure_retains_local_fallback(server, monkeypatch, error):
    blob = fake_gcs(server, monkeypatch)
    blob.download_as_text.side_effect = error
    server._local_entitlement_path("test.json").write_text('{"proActive":true}')
    assert server._read_entitlement_blob("test.json")["proActive"]


def test_storage_write_does_not_hold_global_lock_and_retains_fallback(server, monkeypatch):
    blob = fake_gcs(server, monkeypatch)

    def upload(*args, **kwargs):
        assert not server.ENTITLEMENT_LOCK.locked()
        assert kwargs["timeout"] == 3.0
        assert kwargs["retry"] is None
        raise TimeoutError("slow")

    blob.upload_from_string.side_effect = upload
    server._write_entitlement({"installId": "synthetic-install", "proActive": True})
    files = list(server.FEEDBACK_LOG_DIR.glob("entitlements_*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["proActive"]


def test_timeout_is_unavailable_and_log_does_not_include_token(server, caplog):
    result = server._play_validation_error(TimeoutError("private-test-token"))
    assert result.status == "unavailable" and result.valid is None
    assert "private-test-token" not in caplog.text


def test_purchase_storage_budget_shrinks_and_resets(server, monkeypatch):
    token = server._PURCHASE_DEADLINE.set(101.5)
    try:
        monkeypatch.setattr(server.time, "monotonic", lambda: 100.0)
        assert server._entitlement_io_timeout() == 1.5
        monkeypatch.setattr(server.time, "monotonic", lambda: 102.0)
        with pytest.raises(TimeoutError):
            server._entitlement_io_timeout()
    finally:
        server._PURCHASE_DEADLINE.reset(token)
    assert server._entitlement_io_timeout() == 3.0


@pytest.mark.parametrize("state,valid", [(0, True), (1, False), (2, False)])
def test_product_validation_retains_purchase_state_contract(server, monkeypatch, state, valid):
    service = Mock()
    execute = service.purchases.return_value.products.return_value.get.return_value.execute
    execute.return_value = {"purchaseState": state}
    monkeypatch.setattr(server, "_android_publisher_service", lambda: service)
    result = server._validate_one_time_purchase(purchase(server))
    assert result.valid is valid
    execute.assert_called_once_with(num_retries=0)


def test_http_purchase_response_remains_compatible(server, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(server, "_validate_play_purchase", lambda _: server.PlayValidationResult("unavailable", None))
    response = TestClient(server.app).post("/api/purchases/verify", json=purchase(server).model_dump())
    assert response.status_code == 200
    assert response.json()["validationStatus"] == "unavailable"
    assert response.json()["proActive"] is False
    assert server._PURCHASE_DEADLINE.get() is None
