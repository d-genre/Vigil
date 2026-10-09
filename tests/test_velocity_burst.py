import pytest
import pandas as pd
import numpy as np
from backend.fraud_patterns.velocity_burst import detect_velocity_burst


def make_tx(tx_id, ts, acc, amount=100.0, is_fraud=0):
    return {
        "transaction_id": tx_id,
        "timestamp": ts,
        "nameOrig": acc,
        "amount": amount,
        "isFraud": is_fraud,
        "fraud_type": "none",
        "campaign_id": "none"
    }


# Test 1: Single transaction account
def test_01_single_transaction():
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0)]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert res["severity"] == "NONE"


# Test 2: Spaced out transactions over days
def test_02_spaced_transactions():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX2", "2026-01-02 10:00:00", "ACC_1", 100.0),
        make_tx("TX3", "2026-01-03 10:00:00", "ACC_1", 100.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 3: Short-window high frequency burst (5 tx in 5 minutes)
def test_03_short_window_burst():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 100.0)
        for i in range(5)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is True
    assert res["score"] >= 75.0
    assert res["metrics"]["max_tx_count_5m"] == 5


# Test 4: Extended high frequency burst (10 tx in 1 hour)
def test_04_extended_1h_burst():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:{i:02d}:00", "ACC_1", 100.0)
        for i in range(10)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is True
    assert res["score"] == 85.0
    assert res["metrics"]["max_tx_count_1h"] == 10


# Test 5: High cumulative volume burst ($50,000 in 1 hour)
def test_05_high_volume_burst():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 30000.0),
        make_tx("TX2", "2026-01-01 10:20:00", "ACC_1", 25000.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is True
    assert res["score"] >= 85.0
    assert res["metrics"]["max_amount_sum_1h"] == 55000.0


# Test 6: Moderate velocity (3 tx in 5 minutes, low risk)
def test_06_moderate_velocity():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 50.0),
        make_tx("TX2", "2026-01-01 10:02:00", "ACC_1", 50.0),
        make_tx("TX3", "2026-01-01 10:04:00", "ACC_1", 50.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is False  # 45.0 score < 50.0 threshold
    assert res["score"] == 45.0
    assert res["severity"] == "MEDIUM"


# Test 7: Combined high frequency + high volume burst acceleration
def test_7_combined_burst_acceleration():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 7000.0)
        for i in range(4)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is True
    assert res["score"] >= 80.0


# Test 8: Missing timestamps handled safely
def test_08_missing_timestamps():
    txs = [
        make_tx("TX1", None, "ACC_1", 100.0),
        make_tx("TX2", "2026-01-01 10:00:00", "ACC_1", 100.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["score"] >= 0.0


# Test 9: Duplicate transaction IDs handled safely
def test_09_duplicate_transaction_ids():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["score"] >= 0.0


# Test 10: Point-in-time filtering via as_of_timestamp
def test_10_as_of_timestamp_cutoff():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX2", "2026-01-01 10:01:00", "ACC_1", 100.0),
        make_tx("TX3", "2026-01-01 10:02:00", "ACC_1", 100.0),
        make_tx("TX4", "2026-01-01 10:03:00", "ACC_1", 100.0),
        make_tx("TX5", "2026-01-01 10:04:00", "ACC_1", 100.0)
    ]
    # Cutoff at 10:02 excludes TX4 and TX5
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs), as_of_timestamp="2026-01-01 10:02:00")
    assert res["metrics"]["max_tx_count_5m"] == 3
    assert res["detected"] is False


# Test 11: Point-in-time filtering via target transaction_id anchor
def test_11_transaction_id_anchor():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX2", "2026-01-01 10:01:00", "ACC_1", 100.0),
        make_tx("TX3", "2026-01-01 10:02:00", "ACC_1", 100.0),
        make_tx("TX4", "2026-01-01 10:03:00", "ACC_1", 100.0),
        make_tx("TX5", "2026-01-01 10:04:00", "ACC_1", 100.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs), transaction_id="TX3")
    assert res["metrics"]["max_tx_count_5m"] == 3
    assert res["detected"] is False


# Test 12: Future transactions appended do not change historical scores
def test_12_future_appended_records():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX2", "2026-01-01 10:01:00", "ACC_1", 100.0)
    ]
    res1 = detect_velocity_burst("ACC_1", pd.DataFrame(txs), as_of_timestamp="2026-01-01 10:01:00")
    
    # Append 10 future burst transactions
    for i in range(10):
        txs.append(make_tx(f"TX_FUT_{i}", "2026-01-02 10:00:00", "ACC_1", 1000.0))
        
    res2 = detect_velocity_burst("ACC_1", pd.DataFrame(txs), as_of_timestamp="2026-01-01 10:01:00")
    assert res1["score"] == res2["score"]
    assert res1["metrics"] == res2["metrics"]


# Test 13: Label independence (works without isFraud, fraud_type, campaign_id)
def test_13_label_independence():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 100.0, is_fraud=1)
        for i in range(5)
    ]
    df1 = pd.DataFrame(txs)
    df2 = df1.drop(columns=["isFraud", "fraud_type", "campaign_id"])
    
    res1 = detect_velocity_burst("ACC_1", df1)
    res2 = detect_velocity_burst("ACC_1", df2)
    assert res1["score"] == res2["score"]
    assert res1["detected"] == res2["detected"]
    assert res1["evidence"] == res2["evidence"]


# Test 14: Deterministic scoring
def test_14_deterministic_scoring():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 100.0)
        for i in range(5)
    ]
    df = pd.DataFrame(txs)
    res1 = detect_velocity_burst("ACC_1", df)
    res2 = detect_velocity_burst("ACC_1", df)
    assert res1 == res2


# Test 15: Score strictly bounded between 0 and 100
def test_15_score_bounds():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:{i:02d}:00", "ACC_1", 10000.0)
        for i in range(30)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert 0.0 <= res["score"] <= 100.0


# Test 16: Evidence includes valid real source transaction IDs
def test_16_evidence_source_identifiers():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 100.0)
        for i in range(5)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert len(res["evidence"]) > 0
    assert "TX0" in res["evidence"][0]["transaction_ids"]


# Test 17: No fabricated transaction IDs in evidence
def test_17_no_fabricated_transaction_ids():
    txs = [
        make_tx("TX_REAL_1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX_REAL_2", "2026-01-01 10:01:00", "ACC_1", 100.0),
        make_tx("TX_REAL_3", "2026-01-01 10:02:00", "ACC_1", 100.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    for ev in res["evidence"]:
        for tx_id in ev["transaction_ids"]:
            assert tx_id in ["TX_REAL_1", "TX_REAL_2", "TX_REAL_3"]


# Test 18: Empty input dataframe
def test_18_empty_input():
    res = detect_velocity_burst("ACC_1", pd.DataFrame())
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 19: Non-existent account ID
def test_19_nonexistent_account():
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_EXISTS", 100.0)]
    res = detect_velocity_burst("ACC_DOES_NOT_EXIST", pd.DataFrame(txs))
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 20: Schema keys verification
def test_20_schema_keys():
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0)]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    expected_keys = {
        "pattern_name", "detected", "score", "severity", "evidence",
        "entities", "transactions", "metrics", "explanation"
    }
    assert expected_keys.issubset(res.keys())
    assert res["pattern_name"] == "VELOCITY_BURST"


# Test 21: Configurable thresholds
def test_21_configurable_thresholds():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0),
        make_tx("TX2", "2026-01-01 10:01:00", "ACC_1", 100.0)
    ]
    cfg = {"threshold_5m_count": 2, "score_threshold": 40.0}
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs), config=cfg)
    assert res["detected"] is True  # Detected because 5m threshold lowered to 2


# Test 22: Account prefix stripping
def test_22_account_prefix_stripping():
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_100", 100.0)]
    res1 = detect_velocity_burst("ACC_100", pd.DataFrame(txs))
    res2 = detect_velocity_burst("ACCOUNT:ACC_100", pd.DataFrame(txs))
    assert res1["score"] == res2["score"]
    assert res2["entities"]["account_id"] == "ACC_100"


# Test 23: Boundary case - exactly 5 transactions in 5 minutes
def test_23_exactly_5_tx_5m():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 10.0)
        for i in range(5)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["metrics"]["max_tx_count_5m"] == 5
    assert res["score"] >= 75.0


# Test 24: Boundary case - exactly 6 transactions in 1 hour
def test_24_exactly_6_tx_1h():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:{i*5:02d}:00", "ACC_1", 10.0)
        for i in range(6)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["metrics"]["max_tx_count_1h"] == 6
    assert res["score"] >= 65.0


# Test 25: Boundary case - exactly $25,000 in 1 hour
def test_25_exactly_25k_1h():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 25000.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["metrics"]["max_amount_sum_1h"] == 25000.0
    assert res["score"] >= 65.0


# Test 26: Zero eligible transactions prior to cutoff
def test_26_zero_eligible_tx_cutoff():
    txs = [make_tx("TX1", "2026-01-02 10:00:00", "ACC_1", 100.0)]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs), as_of_timestamp="2026-01-01 00:00:00")
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "No eligible transactions" in res["explanation"]


# Test 27: Invalid transaction_id anchor returns explanation
def test_27_invalid_transaction_id_anchor():
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 100.0)]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs), transaction_id="NON_EXISTENT_TX")
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "not found" in res["explanation"]


# Test 28: Metrics accuracy
def test_28_metrics_accuracy():
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", 1500.0),
        make_tx("TX2", "2026-01-01 10:02:00", "ACC_1", 2500.0)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["metrics"]["max_tx_count_5m"] == 2
    assert res["metrics"]["max_tx_count_1h"] == 2
    assert res["metrics"]["max_amount_sum_1h"] == 4000.0


# Test 29: Evidence type formatting
def test_29_evidence_type_formatting():
    txs = [
        make_tx(f"TX{i}", f"2026-01-01 10:0{i}:00", "ACC_1", 100.0)
        for i in range(5)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert any(ev["evidence_type"] == "HIGH_VELOCITY_BURST" for ev in res["evidence"])



# Test 30: Multi-burst peak detection across timeline
def test_30_multi_burst_peak_detection():
    # Morning small burst (2 tx), Evening large burst (6 tx)
    txs = [
        make_tx("TX1", "2026-01-01 09:00:00", "ACC_1", 100.0),
        make_tx("TX2", "2026-01-01 09:02:00", "ACC_1", 100.0),
    ] + [
        make_tx(f"TX_EV_{i}", f"2026-01-01 18:0{i}:00", "ACC_1", 500.0)
        for i in range(6)
    ]
    res = detect_velocity_burst("ACC_1", pd.DataFrame(txs))
    assert res["detected"] is True
    assert res["metrics"]["max_tx_count_5m"] == 6
    assert res["score"] >= 75.0
