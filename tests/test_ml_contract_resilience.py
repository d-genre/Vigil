import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app

client = TestClient(app)

import uuid

def get_base_payload():
    return {
        "transaction_id": f"TX_ML_TEST_{uuid.uuid4().hex[:8]}",
        "account_id": "ACC_999",
        "amount": 1200.0,
        "currency": "INR",
        "device_id": "DEV_10",
        "ip": "10.0.0.1",
        "beneficiary_id": "BEN_55",
        "timestamp": "2026-10-09T12:00:00",
        "location": "Indore, IN",
        "transaction_type": "TRANSFER"
    }

# 1. Valid responses: LOW, MEDIUM, HIGH
@pytest.mark.parametrize("prob, risk_label, should_investigate", [
    (0.15, "LOW", False),
    (0.55, "MEDIUM", True),
    (0.88, "HIGH", True),
])
def test_valid_responses(prob, risk_label, should_investigate):
    with patch("backend.ml_service.ScreeningService.screen", return_value=(prob, risk_label)):
        response = client.post("/transactions", json=get_base_payload())
        assert response.status_code == 201
        data = response.json()
        assert data["risk_score"] == prob
        assert data["risk_level"] == risk_label
        assert data["requires_investigation"] is should_investigate

# 2. Mathematical limits: prob = 0.0 and prob = 1.0
@pytest.mark.parametrize("prob, risk_label", [
    (0.0, "LOW"),
    (1.0, "HIGH"),
])
def test_boundary_probabilities(prob, risk_label):
    with patch("backend.ml_service.ScreeningService.screen", return_value=(prob, risk_label)):
        response = client.post("/transactions", json=get_base_payload())
        assert response.status_code == 201
        data = response.json()
        assert data["risk_score"] == prob
        assert data["risk_level"] == risk_label

# 3. Boundary conditions: prob = 0.39 vs 0.40
@pytest.mark.parametrize("prob, expected_label, should_investigate", [
    (0.39, "LOW", False),
    (0.40, "MEDIUM", True),
])
def test_threshold_boundaries(prob, expected_label, should_investigate):
    with patch("backend.ml_service.ScreeningService.screen", return_value=(prob, expected_label)):
        response = client.post("/transactions", json=get_base_payload())
        assert response.status_code == 201
        data = response.json()
        assert data["risk_score"] == prob
        assert data["risk_level"] == expected_label
        assert data["requires_investigation"] is should_investigate

# 4. Invalid out-of-bounds probabilities
@pytest.mark.parametrize("invalid_prob, expected_clamped", [
    (-0.25, 0.0),
    (1.45, 1.0),
])
def test_invalid_out_of_bounds_probability(invalid_prob, expected_clamped):
    with patch("backend.ml_service.ScreeningService.screen", return_value=(invalid_prob, "HIGH")):
        response = client.post("/transactions", json=get_base_payload())
        assert response.status_code == 201
        data = response.json()
        assert data["risk_score"] == expected_clamped

# 5. Invalid risk label such as "UNKNOWN"
def test_invalid_risk_label_handling():
    with patch("backend.ml_service.ScreeningService.screen", return_value=(0.60, "UNKNOWN")):
        response = client.post("/transactions", json=get_base_payload())
        assert response.status_code == 500

# 6. ML runtime exceptions handled gracefully
def test_ml_exception_handling():
    with patch("backend.ml_service.ScreeningService.screen", side_effect=Exception("ML inference failure")):
        response = client.post("/transactions", json=get_base_payload())
        assert response.status_code == 500
