"""
Unit & Integration Tests for VIGIL FastAPI Application (tests/test_api_endpoints.py)
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verifies GET /health returns 200 OK and expected subsystems."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "subsystems" in data
    assert "ml_screening" in data["subsystems"]
    assert "database" in data["subsystems"]


import uuid

def test_submit_transaction_endpoint():
    """Verifies POST /transactions ingests transaction and returns risk score."""
    tx_id = f"TX_API_TEST_{uuid.uuid4().hex[:8]}"
    tx_payload = {
        "transaction_id": tx_id,
        "timestamp": "2026-10-09T10:40:00Z",
        "account_id": "ACC_API_01",
        "amount": 5000.0,
        "device_id": "D99",
        "ip": "10.0.0.1",
        "transaction_type": "TRANSFER"
    }

    res_post = client.post("/transactions", json=tx_payload)
    assert res_post.status_code == 201
    post_data = res_post.json()
    assert post_data["transaction_id"] == tx_id
    assert "risk_score" in post_data
    assert "risk_level" in post_data
    assert "requires_investigation" in post_data


def test_get_transactions_list():
    """Verifies GET /transactions retrieves ingested transactions."""
    tx_id = f"TX_API_TEST_{uuid.uuid4().hex[:8]}"
    tx_payload = {
        "transaction_id": tx_id,
        "timestamp": "2026-10-09T10:41:00Z",
        "account_id": "ACC_API_02",
        "amount": 15000.0,
        "transaction_type": "PAYMENT"
    }
    client.post("/transactions", json=tx_payload)

    res_txs = client.get("/transactions")
    assert res_txs.status_code == 200
    txs_data = res_txs.json()
    assert "transactions" in txs_data
    assert txs_data["total"] >= 1

