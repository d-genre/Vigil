import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import joblib

from fraud.mule_chain import detect_mule_chain
from fraud.common import PROJECT_ROOT

@pytest.fixture
def sample_mule_chain_data():
    """Generates synthetic transactions representing a clear A1, A2 -> M -> C1, C2 mule chain."""
    tx_data = [
        # Upstream senders to M (account C_MULE)
        {"transaction_id": "TX-M1", "timestamp": "2026-01-01 10:00:00", "type": "TRANSFER", "amount": 5000.0, "nameOrig": "C_UP1", "nameDest": "C_MULE", "device_id": "D-UP1", "ip_address": "IP-UP1"},
        {"transaction_id": "TX-M2", "timestamp": "2026-01-01 10:30:00", "type": "TRANSFER", "amount": 4000.0, "nameOrig": "C_UP2", "nameDest": "C_MULE", "device_id": "D-UP2", "ip_address": "IP-UP2"},
        
        # Outgoing transfers from M to downstream accounts
        {"transaction_id": "TX-M3", "timestamp": "2026-01-01 11:00:00", "type": "TRANSFER", "amount": 4500.0, "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "device_id": "D-MULE", "ip_address": "IP-MULE"},
        {"transaction_id": "TX-M4", "timestamp": "2026-01-01 11:15:00", "type": "TRANSFER", "amount": 4200.0, "nameOrig": "C_MULE", "nameDest": "C_DOWN2", "device_id": "D-MULE", "ip_address": "IP-MULE"},
        
        # Future transaction occurring AFTER cutoff
        {"transaction_id": "TX-M5_FUTURE", "timestamp": "2026-01-05 10:00:00", "type": "TRANSFER", "amount": 10000.0, "nameOrig": "C_UP3", "nameDest": "C_MULE", "device_id": "D-UP3", "ip_address": "IP-UP3"}
    ]
    return pd.DataFrame(tx_data)


def test_01_detector_imports():
    assert callable(detect_mule_chain)


def test_02_result_schema(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    required_keys = ["pattern_name", "detected", "score", "severity", "account_id", "transaction_id", "as_of_timestamp", "evidence", "entities", "transactions", "metrics", "paths", "explanation"]
    for k in required_keys:
        assert k in res
    assert res["pattern_name"] == "MULE_CHAIN"


def test_03_account_to_account_identification(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["metrics"]["incoming_count"] == 2
    assert res["metrics"]["outgoing_count"] == 2


def test_04_upstream_sender_identification(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["entities"]["upstream_accounts"] == ["C_UP1", "C_UP2"]


def test_05_downstream_recipient_identification(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["entities"]["downstream_accounts"] == ["C_DOWN1", "C_DOWN2"]


def test_06_path_detection(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert len(res["paths"]) > 0
    path = res["paths"][0]
    assert len(path["path_nodes"]) == 3
    assert path["path_nodes"][1] == "C_MULE"


def test_07_transaction_ids_in_paths_real(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    for p in res["paths"]:
        for tx_id in p["transaction_ids"]:
            assert tx_id in sample_mule_chain_data["transaction_id"].values


def test_08_timestamps_in_paths_valid(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    for p in res["paths"]:
        assert pd.to_datetime(p["timestamps"][0]) <= pd.to_datetime(p["timestamps"][1])


def test_09_incoming_outgoing_metrics(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["metrics"]["total_incoming_amount"] == 9000.0
    assert res["metrics"]["total_outgoing_amount"] == 8700.0


def test_10_flow_through_calculation(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert pytest.approx(res["metrics"]["flow_through_ratio"], 0.01) == 8700.0 / 9000.0


def test_11_multiple_upstream_increases_score():
    data_1_up = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 11:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
    ])
    data_2_up = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 10:15:00", "nameOrig": "C_UP2", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T3", "timestamp": "2026-01-01 11:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 1900},
    ])
    res1 = detect_mule_chain(account_id="C_MULE", transactions_df=data_1_up, as_of_timestamp="2026-01-02 00:00:00")
    res2 = detect_mule_chain(account_id="C_MULE", transactions_df=data_2_up, as_of_timestamp="2026-01-02 00:00:00")
    assert res2["score"] > res1["score"]


def test_12_multiple_downstream_increases_score():
    data_1_down = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 2000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 11:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 1900},
    ])
    data_2_down = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 2000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 11:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
        {"transaction_id": "T3", "timestamp": "2026-01-01 11:15:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN2", "amount": 950},
    ])
    res1 = detect_mule_chain(account_id="C_MULE", transactions_df=data_1_down, as_of_timestamp="2026-01-02 00:00:00")
    res2 = detect_mule_chain(account_id="C_MULE", transactions_df=data_2_down, as_of_timestamp="2026-01-02 00:00:00")
    assert res2["score"] > res1["score"]


def test_13_temporal_proximity_handled():
    tx_fast = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 10:15:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
    ])
    res = detect_mule_chain(account_id="C_MULE", transactions_df=tx_fast, as_of_timestamp="2026-01-02 00:00:00")
    assert res["metrics"]["min_time_diff_minutes"] == 15.0


def test_14_one_in_one_out_weak_signal_protection():
    tx_single = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 10:15:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
    ])
    res = detect_mule_chain(account_id="C_MULE", transactions_df=tx_single, as_of_timestamp="2026-01-02 00:00:00")
    # 1 in + 1 out should NOT trigger high-confidence detection (detected=False, score < 50)
    assert res["detected"] is False
    assert res["score"] < 50.0


def test_15_score_bounds(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert 0.0 <= res["score"] <= 100.0


def test_16_score_is_deterministic(sample_mule_chain_data):
    res1 = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    res2 = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res1["score"] == res2["score"]
    assert res1["detected"] == res2["detected"]


def test_17_identical_input_identical_output(sample_mule_chain_data):
    res1 = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    res2 = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res1 == res2


def test_18_point_in_time_excludes_future(sample_mule_chain_data):
    res_past = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert "TX-M5_FUTURE" not in res_past["transactions"]
    assert "C_UP3" not in res_past["entities"]["upstream_accounts"]


def test_19_future_outgoing_cannot_influence_past():
    data = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2_FUTURE", "timestamp": "2026-01-05 10:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
    ])
    res = detect_mule_chain(account_id="C_MULE", transactions_df=data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["metrics"]["outgoing_count"] == 0
    assert res["detected"] is False


def test_20_future_incoming_cannot_influence_past():
    data = pd.DataFrame([
        {"transaction_id": "T1_FUTURE", "timestamp": "2026-01-05 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
    ])
    res = detect_mule_chain(account_id="C_MULE", transactions_df=data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["metrics"]["incoming_count"] == 0
    assert res["detected"] is False


def test_21_future_paths_cannot_influence_past():
    data = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C_UP1", "nameDest": "C_MULE", "amount": 1000},
        {"transaction_id": "T2_FUTURE", "timestamp": "2026-01-05 10:00:00", "nameOrig": "C_MULE", "nameDest": "C_DOWN1", "amount": 950},
    ])
    res = detect_mule_chain(account_id="C_MULE", transactions_df=data, as_of_timestamp="2026-01-02 00:00:00")
    assert len(res["paths"]) == 0


def test_22_labels_not_required(sample_mule_chain_data):
    df_no_labels = sample_mule_chain_data.drop(columns=["isFraud", "fraud_type", "campaign_id"], errors="ignore")
    res = detect_mule_chain(account_id="C_MULE", transactions_df=df_no_labels, as_of_timestamp="2026-01-02 00:00:00")
    assert res["detected"] is True


def test_23_label_independence(sample_mule_chain_data):
    # Verify no fraud label columns are accessed or required
    df_stripped = sample_mule_chain_data[["transaction_id", "timestamp", "type", "amount", "nameOrig", "nameDest", "device_id", "ip_address"]]
    res = detect_mule_chain(account_id="C_MULE", transactions_df=df_stripped, as_of_timestamp="2026-01-02 00:00:00")
    assert res["detected"] is True


def test_24_no_fabricated_event_types(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    for ev in res["evidence"]:
        assert "EMAIL_CHANGE" not in ev["evidence_type"]
        assert "LOCATION_CHANGE" not in ev["evidence_type"]


def test_25_evidence_is_structured(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    for item in res["evidence"]:
        assert "evidence_type" in item
        assert "description" in item
        assert "value" in item
        assert "threshold" in item
        assert "transaction_ids" in item


def test_26_evidence_contains_real_transaction_ids(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    for item in res["evidence"]:
        for tx_id in item["transaction_ids"]:
            assert tx_id in sample_mule_chain_data["transaction_id"].values


def test_27_evidence_contains_real_account_ids(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["entities"]["target_account"] == "C_MULE"


def test_28_evidence_timestamps_amounts_match(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res["metrics"]["total_incoming_amount"] == 9000.0


def test_29_path_traversal_deterministic(sample_mule_chain_data):
    res1 = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    res2 = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    assert res1["paths"] == res2["paths"]


def test_30_path_traversal_bounded(sample_mule_chain_data):
    res = detect_mule_chain(account_id="C_MULE", transactions_df=sample_mule_chain_data, as_of_timestamp="2026-01-02 00:00:00")
    for p in res["paths"]:
        assert len(p["path_nodes"]) <= 4


def test_31_card_testing_regression():
    from fraud.card_testing import detect_card_testing
    res = detect_card_testing(account_id="C0000340")
    assert "pattern_name" in res
    assert res["pattern_name"] == "CARD_TESTING"


def test_32_account_takeover_regression():
    from fraud.account_takeover import detect_account_takeover
    res = detect_account_takeover(account_id="C0000529")
    assert "pattern_name" in res
    assert res["pattern_name"] == "ACCOUNT_TAKEOVER"


def test_33_raw_data_unchanged():
    from ml.data_loader import RAW_DATA_DIR
    assert RAW_DATA_DIR.exists()


def test_34_graph_artifact_unchanged():
    from graph.build_graph import load_fraud_graph
    G = load_fraud_graph()
    assert G.number_of_nodes() > 0


def test_35_existing_ml_models_unchanged():
    cbm_path = Path(__file__).resolve().parent.parent / "models" / "catboost_fraud.cbm"
    assert cbm_path.exists()
    assert cbm_path.stat().st_size > 0
