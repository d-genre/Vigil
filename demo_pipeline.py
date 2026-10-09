import json
import pandas as pd
from datetime import datetime

from fraud.aggregator import run_all_detectors
from backend.adapters.detector_adapter import evaluate_all_seven_vigil_patterns
from backend.dossier_service import DossierEngine
from schemas.transaction import Transaction

def main():
    print("=== STARTING FULL END-TO-END PIPELINE (NO GRAPH ENGINE) ===")

    # 1. Simulate a suspicious transaction (Velocity Anomaly / Mule Chain)
    print("\n[1] Simulating Transactions for MULE_CHAIN & VELOCITY_BURST...")
    
    # We create a dataframe that shows ACC_SUSPECT receiving funds from C_UPSTREAM1 and C_UPSTREAM2
    # and then rapidly draining them to C_DOWNSTREAM1 and C_DOWNSTREAM2
    
    tx_df = pd.DataFrame([
        {
            "transaction_id": "TX_REAL_001",
            "nameOrig": "C_UPSTREAM1",
            "nameDest": "ACC_SUSPECT",
            "timestamp": "2026-10-09 10:00:00",
            "amount": 25000.0,
            "device_id": "DEV_NEW_123",
            "ip_address": "203.0.113.50",
            "isFraud": 0
        },
        {
            "transaction_id": "TX_REAL_002",
            "nameOrig": "C_UPSTREAM2",
            "nameDest": "ACC_SUSPECT",
            "timestamp": "2026-10-09 10:05:00",
            "amount": 24000.0,
            "device_id": "DEV_NEW_123",
            "ip_address": "203.0.113.50",
            "isFraud": 0
        },
        {
            "transaction_id": "TX_REAL_003",
            "nameOrig": "ACC_SUSPECT",
            "nameDest": "C_DOWNSTREAM1",
            "timestamp": "2026-10-09 10:10:00",
            "amount": 20000.0,
            "device_id": "DEV_NEW_123",
            "ip_address": "203.0.113.50",
            "isFraud": 0
        },
        {
            "transaction_id": "TX_REAL_004",
            "nameOrig": "ACC_SUSPECT",
            "nameDest": "C_DOWNSTREAM2",
            "timestamp": "2026-10-09 10:15:00",
            "amount": 29000.0,
            "device_id": "DEV_NEW_123",
            "ip_address": "203.0.113.50",
            "isFraud": 0
        }
    ])
    
    # Mocking missing dataframes to prevent errors
    events_df = pd.DataFrame(columns=["account_id", "timestamp", "event_type", "device_id", "ip_address"])
    devices_df = pd.DataFrame(columns=["account_id", "device_id", "timestamp"])
    cities_df = pd.DataFrame(columns=["account_id", "timestamp", "city", "lat", "lon"])
    accounts_df = pd.DataFrame(columns=["account_id", "created_at"])
    beneficiaries_df = pd.DataFrame(columns=["account_id", "beneficiary_id", "added_at"])
    
    # 2. Run Fraud Aggregator (Stage 8B Detectors)
    print("\n[2] Running Stage 8B Pattern Detectors...")
    stage_8c_res = run_all_detectors(
        account_id="ACC_SUSPECT",
        transactions_df=tx_df,
        events_df=events_df,
        devices_df=devices_df,
        cities_df=cities_df,
        accounts_df=accounts_df,
        beneficiaries_df=beneficiaries_df,
        as_of_timestamp="2026-10-09 10:20:00"
    )
    
    print(f"Overall Aggregator Score: {stage_8c_res['overall_score']}")

    # 3. Adapt into VIGIL Investigation State (Stage 8C)
    print("\n[3] Adapting into VIGIL Investigation State (No Graph)...")
    target_tx = Transaction(
        transaction_id="TX_REAL_004",
        timestamp="2026-10-09T10:15:00Z",
        account_id="ACC_SUSPECT",
        amount=29000.0,
        device_id="DEV_NEW_123",
        ip="203.0.113.50"
    )
    
    investigation_state = evaluate_all_seven_vigil_patterns(
        account_id="ACC_SUSPECT",
        stage_8c_output=stage_8c_res,
        transaction=target_tx
    )
    
    print(f"Investigation Status: {investigation_state.status}")
    print(f"Recommended Action: {investigation_state.recommended_action}")
    
    # 4. Generate the Dossier
    print("\n[4] Generating Final Dossier via LLM / Mock Engine...")
    engine = DossierEngine()
    
    tx_data = target_tx.model_dump()
    
    shap_data = {
        "ml_score": investigation_state.risk_score / 100.0,
        "positive_drivers": ["Velocity Anomaly", "Mule Chain Behavior"],
        "negative_drivers": []
    }
    
    graph_data = {
        "cluster_size": 1,
        "note": "Graph Engine Offline / Not Integrated"
    }
    
    dossier = engine.generate_dossier(tx_data, shap_data, graph_data)
    
    # 5. Export Evidences and PDF
    print("\n[5] Exporting Evidence DataFrame...")
    df = engine.export_evidence_to_dataframe(dossier)
    print(df.to_string())
    
    print("\n[6] Building PDF Dossier...")
    pdf_filename = f"dossier_{dossier.transaction_id}.pdf"
    engine.generate_graph_visual(dossier.transaction_id, graph_data["cluster_size"], f"graph_{dossier.transaction_id}.png")
    engine.export_to_pdf(dossier, pdf_filename)
    
    print(f"\n=== PIPELINE COMPLETE! PDF saved to {pdf_filename} ===")

if __name__ == "__main__":
    main()
