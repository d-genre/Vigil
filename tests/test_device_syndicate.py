import pytest
import pandas as pd
import numpy as np
from backend.fraud_patterns.device_syndicate import detect_device_syndicate, is_valid_device_id


@pytest.fixture
def sample_devices_df():
    return pd.DataFrame([
        {"device_id": "D_NORMAL", "account_count": 1, "transaction_count": 10, "device_age_days": 100, "is_emulator": 0},
        {"device_id": "D_SHARED", "account_count": 5, "transaction_count": 50, "device_age_days": 10, "is_emulator": 0},
        {"device_id": "D_EMULATOR", "account_count": 4, "transaction_count": 20, "device_age_days": 2, "is_emulator": 1},
        {"device_id": "D_BENIGN", "account_count": 2, "transaction_count": 15, "device_age_days": 200, "is_emulator": 0},
    ])


def make_tx(tx_id, ts, acc, device_id, is_fraud=0):
    return {
        "transaction_id": tx_id,
        "timestamp": ts,
        "nameOrig": acc,
        "device_id": device_id,
        "isFraud": is_fraud,
        "fraud_type": "none",
        "campaign_id": "none"
    }


# Test 1: Several accounts sharing one device in a suspicious pattern (>=5 accounts)
def test_01_suspicious_device_syndicate(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED")
        for i in range(5)
    ]
    res = detect_device_syndicate("ACC_0", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is True
    assert res["score"] == 85.0
    assert res["severity"] == "CRITICAL"
    assert res["metrics"]["max_accounts_per_device"] == 5


# Test 2: A device used by only one account
def test_02_single_account_device(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_SOLO", "D_NORMAL"),
        make_tx("TX2", "2026-01-01 11:00:00", "ACC_SOLO", "D_NORMAL")
    ]
    res = detect_device_syndicate("ACC_SOLO", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert res["severity"] == "NONE"


# Test 3: Two accounts sharing a device without enough evidence for high risk
def test_03_two_accounts_low_risk(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_BENIGN"),
        make_tx("TX2", "2026-01-01 12:00:00", "ACC_B", "D_BENIGN")
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] == 25.0
    assert res["severity"] == "LOW"


# Test 4: Legitimate-looking shared device scenario
def test_04_legitimate_family_sharing(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "PARENT", "D_BENIGN"),
        make_tx("TX2", "2026-01-05 10:00:00", "CHILD", "D_BENIGN")
    ]
    res = detect_device_syndicate("PARENT", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] < 50.0


# Test 5: Missing device identifiers (None / NaN)
def test_05_missing_device_identifier(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", None),
        make_tx("TX2", "2026-01-01 11:00:00", "ACC_A", None)
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "No valid device identifiers" in res["explanation"]


# Test 6: Placeholder or invalid device identifiers ('none', '0', 'unknown')
def test_06_placeholder_device_identifiers(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "none"),
        make_tx("TX2", "2026-01-01 11:00:00", "ACC_B", "unknown"),
        make_tx("TX3", "2026-01-01 12:00:00", "ACC_C", "0")
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 7: Missing timestamps handled safely
def test_07_missing_timestamps(sample_devices_df):
    txs = [
        make_tx("TX1", None, "ACC_A", "D_SHARED"),
        make_tx("TX2", "2026-01-01 10:00:00", "ACC_B", "D_SHARED")
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    assert res["score"] >= 0.0


# Test 8: Duplicate transaction observations
def test_08_duplicate_observations(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_SHARED"),
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_SHARED"),
        make_tx("TX2", "2026-01-01 10:00:00", "ACC_B", "D_SHARED")
    ]
    res1 = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    res2 = detect_impossible_travel = detect_device_syndicate("ACC_A", pd.DataFrame(txs[:2]), sample_devices_df)
    assert res1["detected"] is False or res1["score"] == 25.0


# Test 9: Transactions outside the investigation cutoff
def test_09_transactions_outside_cutoff(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_NORMAL"),
        make_tx("TX2", "2026-01-01 10:30:00", "ACC_B", "D_NORMAL"),
        make_tx("TX3", "2026-01-01 11:00:00", "ACC_C", "D_NORMAL"),
        make_tx("TX4", "2026-01-01 11:30:00", "ACC_D", "D_NORMAL")
    ]
    # Cutoff at 10:15 excludes TX2, TX3, TX4
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, as_of_timestamp="2026-01-01 10:15:00")
    assert res["metrics"]["max_accounts_per_device"] == 1
    assert res["detected"] is False


# Test 10: Future transactions do not change historical scores
def test_10_future_appended_records(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_BENIGN"),
        make_tx("TX2", "2026-01-01 12:00:00", "ACC_B", "D_BENIGN")
    ]
    res1 = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, as_of_timestamp="2026-01-01 12:00:00")
    
    # Append 10 future syndicate transactions
    for i in range(10):
        txs.append(make_tx(f"TX_FUTURE_{i}", "2026-01-02 10:00:00", f"ACC_FUT_{i}", "D_BENIGN"))
        
    res2 = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, as_of_timestamp="2026-01-01 12:00:00")
    assert res1["score"] == res2["score"]
    assert res1["metrics"] == res2["metrics"]


# Test 11: transaction_id-anchored cutoff behavior
def test_11_transaction_id_anchor(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_BENIGN"),
        make_tx("TX2", "2026-01-01 12:00:00", "ACC_B", "D_BENIGN"),
        make_tx("TX3", "2026-01-01 14:00:00", "ACC_C", "D_BENIGN")
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, transaction_id="TX1")
    assert res["metrics"]["max_accounts_per_device"] == 1
    assert res["detected"] is False


# Test 12: Label independence (works without isFraud, fraud_type, campaign_id)
def test_12_label_independence(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED", is_fraud=1)
        for i in range(5)
    ]
    df1 = pd.DataFrame(txs)
    df2 = df1.drop(columns=["isFraud", "fraud_type", "campaign_id"])
    
    res1 = detect_device_syndicate("ACC_0", df1, sample_devices_df)
    res2 = detect_device_syndicate("ACC_0", df2, sample_devices_df)
    assert res1["score"] == res2["score"]
    assert res1["detected"] == res2["detected"]
    assert res1["evidence"] == res2["evidence"]


# Test 13: Deterministic scoring
def test_13_deterministic_scoring(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED")
        for i in range(4)
    ]
    df = pd.DataFrame(txs)
    res1 = detect_device_syndicate("ACC_0", df, sample_devices_df)
    res2 = detect_device_syndicate("ACC_0", df, sample_devices_df)
    assert res1 == res2


# Test 14: Score remains strictly bounded between 0 and 100
def test_14_score_bounds(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", f"ACC_{i}", "D_EMULATOR")
        for i in range(20)
    ]
    res = detect_device_syndicate("ACC_0", pd.DataFrame(txs), sample_devices_df)
    assert 0.0 <= res["score"] <= 100.0


# Test 15: Evidence includes valid source identifiers
def test_15_evidence_source_identifiers(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED")
        for i in range(5)
    ]
    res = detect_device_syndicate("ACC_0", pd.DataFrame(txs), sample_devices_df)
    assert len(res["evidence"]) > 0
    assert "TX1" in res["evidence"][0]["transaction_ids"]


# Test 16: No fabricated transaction IDs
def test_16_no_fabricated_transaction_ids(sample_devices_df):
    txs = [
        make_tx("TX_REAL_1", "2026-01-01 10:00:00", "ACC_A", "D_SHARED"),
        make_tx("TX_REAL_2", "2026-01-01 10:30:00", "ACC_B", "D_SHARED")
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    for ev in res["evidence"]:
        for tx_id in ev["transaction_ids"]:
            assert tx_id in ["TX_REAL_1", "TX_REAL_2"]


# Test 17: Empty input dataframe
def test_17_empty_input(sample_devices_df):
    res = detect_device_syndicate("ACC_A", pd.DataFrame(), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 18: Insufficient historical data (non-existent account)
def test_18_nonexistent_account(sample_devices_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_EXISTS", "D_SHARED")]
    res = detect_device_syndicate("ACC_DOES_NOT_EXIST", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 19: Shared-device activity in different time windows
def test_19_time_window_concentration(sample_devices_df):
    # 3 accounts in same 1-hour window
    txs_recent = [
        make_tx("TX1", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED")
        for i in range(3)
    ]
    res_recent = detect_device_syndicate("ACC_0", pd.DataFrame(txs_recent), sample_devices_df)
    
    # 3 accounts spaced across 30 days
    txs_spaced = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_0", "D_SHARED"),
        make_tx("TX2", "2026-01-15 10:00:00", "ACC_1", "D_SHARED"),
        make_tx("TX3", "2026-02-01 10:00:00", "ACC_2", "D_SHARED")
    ]
    res_spaced = detect_device_syndicate("ACC_0", pd.DataFrame(txs_spaced), sample_devices_df)
    
    assert res_recent["score"] > res_spaced["score"]


# Test 20: Regression compatibility with standard schema
def test_20_schema_keys(sample_devices_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_NORMAL")]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    expected_keys = {
        "pattern_name", "detected", "score", "severity", "evidence",
        "entities", "transactions", "metrics", "explanation"
    }
    assert expected_keys.issubset(res.keys())
    assert res["pattern_name"] == "DEVICE_SYNDICATE"


# Test 21: Emulator device booster test
def test_21_emulator_device_booster(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_EMULATOR"),
        make_tx("TX2", "2026-01-01 10:30:00", "ACC_B", "D_EMULATOR")
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    assert res["metrics"]["emulator_device_detected"] is True
    assert res["score"] >= 40.0  # Boosted due to emulator


# Test 22: Multi-device coordination booster
def test_22_multi_device_coordination(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_SHARED_1"),
        make_tx("TX2", "2026-01-01 10:10:00", "ACC_B", "D_SHARED_1"),
        make_tx("TX3", "2026-01-01 10:20:00", "ACC_C", "D_SHARED_1"),
        make_tx("TX4", "2026-01-01 11:00:00", "ACC_A", "D_SHARED_2"),
        make_tx("TX5", "2026-01-01 11:10:00", "ACC_D", "D_SHARED_2"),
        make_tx("TX6", "2026-01-01 11:20:00", "ACC_E", "D_SHARED_2"),
    ]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df)
    assert res["metrics"]["shared_devices_count"] == 2
    assert res["score"] > 65.0


# Test 23: Sentinel helper function
def test_23_is_valid_device_id_sentinels():
    assert is_valid_device_id("D001") is True
    assert is_valid_device_id(None) is False
    assert is_valid_device_id("") is False
    assert is_valid_device_id("none") is False
    assert is_valid_device_id("NULL") is False
    assert is_valid_device_id("0") is False
    assert is_valid_device_id("unknown") is False


# Test 24: Configurable threshold test
def test_24_configurable_threshold(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_BENIGN"),
        make_tx("TX2", "2026-01-01 10:30:00", "ACC_B", "D_BENIGN")
    ]
    cfg = {"score_threshold": 20.0}
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, config=cfg)
    assert res["detected"] is True  # Detected because threshold lowered to 20.0


# Test 25: Account prefix strip test
def test_25_account_prefix_stripping(sample_devices_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_100", "D_NORMAL")]
    res1 = detect_device_syndicate("ACC_100", pd.DataFrame(txs), sample_devices_df)
    res2 = detect_device_syndicate("ACCOUNT:ACC_100", pd.DataFrame(txs), sample_devices_df)
    assert res1["score"] == res2["score"]
    assert res2["entities"]["account_id"] == "ACC_100"


# Test 26: Moderate syndicate sharing (3 accounts)
def test_26_moderate_syndicate_three_accounts(sample_devices_df):
    txs = [
        make_tx(f"TX{i}", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED_3")
        for i in range(3)
    ]
    res = detect_device_syndicate("ACC_0", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is True
    assert res["score"] >= 65.0
    assert res["severity"] in ["HIGH", "CRITICAL"]


# Test 27: Four accounts syndicate sharing
def test_27_four_accounts_syndicate(sample_devices_df):
    txs = [
        make_tx(f"TX{i}", "2026-01-01 10:00:00", f"ACC_{i}", "D_SHARED_4")
        for i in range(4)
    ]
    res = detect_device_syndicate("ACC_0", pd.DataFrame(txs), sample_devices_df)
    assert res["detected"] is True
    assert res["score"] >= 65.0


# Test 28: Zero eligible transactions prior to cutoff
def test_28_no_eligible_tx_prior_to_cutoff(sample_devices_df):
    txs = [make_tx("TX1", "2026-01-02 10:00:00", "ACC_A", "D_SHARED")]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, as_of_timestamp="2026-01-01 00:00:00")
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "No eligible transactions" in res["explanation"]


# Test 29: Invalid transaction_id anchor returns explanation
def test_29_invalid_transaction_id_anchor(sample_devices_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_A", "D_NORMAL")]
    res = detect_device_syndicate("ACC_A", pd.DataFrame(txs), sample_devices_df, transaction_id="NON_EXISTENT_TX")
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "not found" in res["explanation"]


# Test 30: Co-accounts entity list accuracy
def test_30_co_accounts_entity_list(sample_devices_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_MAIN", "D_SHARED"),
        make_tx("TX2", "2026-01-01 10:10:00", "ACC_SYND_1", "D_SHARED"),
        make_tx("TX3", "2026-01-01 10:20:00", "ACC_SYND_2", "D_SHARED")
    ]
    res = detect_device_syndicate("ACC_MAIN", pd.DataFrame(txs), sample_devices_df)
    assert "ACC_MAIN" not in res["entities"]["co_accounts"]
    assert "ACC_SYND_1" in res["entities"]["co_accounts"]
    assert "ACC_SYND_2" in res["entities"]["co_accounts"]
