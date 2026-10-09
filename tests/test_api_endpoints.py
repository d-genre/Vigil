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
    assert data["subsystems"]["detector_adapter"] == "ready"


def test_submit_transaction_and_get_investigation():
    """Verifies POST /transactions and subsequent GET /investigations/{case_id}."""
    tx_payload = {
        "transaction_id": "TX_API_001",
        "timestamp": "2026-10-09T10:40:00Z",
        "account_id": "ACC_API_01",
        "amount": 5000.0,
        "device_id": "D99",
        "ip": "10.0.0.1"
    }

    res_post = client.post("/transactions", json=tx_payload)
    assert res_post.status_code == 201
    post_data = res_post.json()
    assert post_data["transaction_id"] == "TX_API_001"
    assert "case_id" in post_data

    case_id = post_data["case_id"]

    # Retrieve investigation
    res_get = client.get(f"/investigations/{case_id}")
    assert res_get.status_code == 200
    inv_data = res_get.json()
    assert inv_data["case_id"] == case_id
    assert inv_data["transaction"]["account_id"] == "ACC_API_01"
    assert len(inv_data["patterns_detected"]) == 7


def test_human_decision_flow():
    """Verifies GET /cases and POST /cases/{case_id}/decision."""
    tx_payload = {
        "transaction_id": "TX_API_002",
        "timestamp": "2026-10-09T10:41:00Z",
        "account_id": "ACC_API_02",
        "amount": 15000.0
    }
    client.post("/transactions", json=tx_payload)

    # List cases
    res_cases = client.get("/cases")
    assert res_cases.status_code == 200
    cases_list = res_cases.json()
    assert len(cases_list) >= 1

    case_id = cases_list[0]["case_id"]

    # Submit decision
    decision_payload = {
        "action": "BLOCK",
        "reason": "Confirmed fraud pattern",
        "analyst_id": "ANALYST_99"
    }
    res_dec = client.post(f"/cases/{case_id}/decision", json=decision_payload)
    assert res_dec.status_code == 200
    dec_data = res_dec.json()
    assert dec_data["status"] == "RESOLVED"
    assert dec_data["decision"] == "BLOCK"
