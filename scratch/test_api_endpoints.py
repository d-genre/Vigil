import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

def run_tests():
    client = TestClient(app)
    print("=== STARTING FASTAPI ENDPOINT VERIFICATION TESTS ===")

    # 1. Test /health
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health failed: {resp.text}"
    print("[PASS] 1. GET /health ->", resp.json()["status"])

    # 2. Test GET /api/transactions/stream (initial seed)
    resp = client.get("/api/transactions/stream")
    assert resp.status_code == 200, f"Stream failed: {resp.text}"
    data = resp.json()
    assert data["total"] == 8, f"Expected 8 seed transactions, got {data['total']}"
    print(f"[PASS] 2. GET /api/transactions/stream -> {data['total']} transactions returned")

    # 3. Test GET /api/transactions/stream?tick=true
    resp = client.get("/api/transactions/stream?tick=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 9, f"Expected 9 transactions after tick, got {data['total']}"
    print(f"[PASS] 3. GET /api/transactions/stream?tick=true -> ticked new transaction (total: {data['total']})")

    # 4. Test POST /api/transactions/simulate-attack
    resp = client.post("/api/transactions/simulate-attack")
    assert resp.status_code == 201, f"Simulate attack failed: {resp.text}"
    attack_data = resp.json()
    tx_id = attack_data["transaction"]["transaction_id"]
    assert "TX_FLAGGED_" in tx_id, f"Invalid attack ID: {tx_id}"
    print(f"[PASS] 4. POST /api/transactions/simulate-attack -> Injected attack TX: {tx_id}")

    # 5. Test GET /api/graph/{transaction_id} (High Risk)
    resp = client.get(f"/api/graph/{tx_id}")
    assert resp.status_code == 200, f"Graph failed: {resp.text}"
    graph = resp.json()
    assert graph["fraud_pattern"] == "MULTI_ACCOUNT_SMURFING_RING"
    print(f"[PASS] 5. GET /api/graph/{tx_id} -> Fraud Pattern: {graph['fraud_pattern']}, Nodes: {len(graph['nodes'])}")

    # 6. Test GET /api/dossier/{transaction_id} (High Risk)
    resp = client.get(f"/api/dossier/{tx_id}")
    assert resp.status_code == 200, f"Dossier failed: {resp.text}"
    dossier = resp.json()
    assert dossier["verdict"] == "REJECT_AND_FREEZE"
    print(f"[PASS] 6. GET /api/dossier/{tx_id} -> Verdict: {dossier['verdict']}, Score: {dossier['risk_score']}")

    # 7. Test GET /api/dossier/{transaction_id}/pdf
    resp = client.get(f"/api/dossier/{tx_id}/pdf")
    assert resp.status_code == 200, f"PDF export failed: {resp.text}"
    assert resp.headers["content-type"] == "application/pdf"
    pdf_bytes = resp.content
    assert pdf_bytes.startswith(b"%PDF"), "Response is not a valid PDF file binary"
    print(f"[PASS] 7. GET /api/dossier/{tx_id}/pdf -> Valid PDF returned ({len(pdf_bytes)} bytes)")

    # 8. Test Benign Graph & Dossier fallback
    benign_tx_id = "TX_BENIGN_1001"
    resp = client.get(f"/api/graph/{benign_tx_id}")
    assert resp.json()["fraud_pattern"] == "NORMAL_RETAIL_PURCHASE"
    print(f"[PASS] 8. GET /api/graph/{benign_tx_id} -> Benign fallback verified")

    resp = client.get(f"/api/dossier/{benign_tx_id}")
    assert resp.json()["verdict"] == "APPROVE"
    print(f"[PASS] 9. GET /api/dossier/{benign_tx_id} -> Benign verdict verified")

    print("\nALL FASTAPI ENDPOINT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
