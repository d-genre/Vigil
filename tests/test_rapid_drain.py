import pytest
import pandas as pd
import numpy as np
from backend.fraud_patterns.rapid_drain import detect_rapid_drain


@pytest.fixture
def sample_accounts_df():
    return pd.DataFrame([
        {"account_id": "ACC_1", "monthly_income": 5000.0, "avg_transaction_amount": 200.0},
        {"account_id": "ACC_HIGH_INC", "monthly_income": 20000.0, "avg_transaction_amount": 1000.0}
    ])


@pytest.fixture
def sample_events_df():
    return pd.DataFrame([
        {"event_id": "EV1", "timestamp": "2026-01-01 09:00:00", "account_id": "ACC_1", "event_type": "BENEFICIARY_ADDED"},
        {"event_id": "EV2", "timestamp": "2026-01-01 08:00:00", "account_id": "ACC_1", "event_type": "LOGIN"}
    ])


@pytest.fixture
def sample_beneficiaries_df():
    return pd.DataFrame([
        {"beneficiary_id": "B1", "account_id": "ACC_1", "beneficiary_account": "DEST_BENEF_1", "created_at": "2026-01-01 09:00:00"}
    ])


def make_tx(tx_id, ts, acc, dest="DEST_1", tx_type="TRANSFER", amount=100.0, is_fraud=0):
    return {
        "transaction_id": tx_id,
        "timestamp": ts,
        "nameOrig": acc,
        "nameDest": dest,
        "type": tx_type,
        "amount": amount,
        "isFraud": is_fraud,
        "fraud_type": "none",
        "campaign_id": "none"
    }


# Test 1: High drain ratio positive test (100% of income in 1h)
def test_01_high_drain_ratio(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 5500.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is True
    assert res["score"] >= 70.0
    assert res["metrics"]["drain_ratio_1h"] == 1.1


# Test 2: Extreme drain ratio (200%+ of income)
def test_02_extreme_drain_ratio(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "CASH_OUT", 12000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is True
    assert res["score"] == 85.0
    assert res["severity"] == "CRITICAL"


# Test 3: Low drain ratio (10% of income, no risk)
def test_03_low_drain_ratio(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "PAYMENT", 500.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 4: Beneficiary abuse (beneficiary added followed shortly by large transfer)
def test_04_beneficiary_abuse(sample_accounts_df, sample_events_df, sample_beneficiaries_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_BENEF_1", "TRANSFER", 3000.0)
    ]
    res = detect_rapid_drain(
        "ACC_1", pd.DataFrame(txs),
        events_df=sample_events_df,
        accounts_df=sample_accounts_df,
        beneficiaries_df=sample_beneficiaries_df
    )
    assert res["detected"] is True
    assert res["score"] >= 90.0
    assert res["metrics"]["beneficiary_added_24h"] is True


# Test 5: Beneficiary addition alone without outgoing transfer
def test_05_beneficiary_added_no_outgoing(sample_accounts_df, sample_events_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "CASH_IN", 1000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), events_df=sample_events_df, accounts_df=sample_accounts_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 6: Multi-recipient rapid drain
def test_06_multi_recipient_drain(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 2000.0),
        make_tx("TX2", "2026-01-01 10:10:00", "ACC_1", "DEST_2", "TRANSFER", 2000.0),
        make_tx("TX3", "2026-01-01 10:20:00", "ACC_1", "DEST_3", "TRANSFER", 2000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is True
    assert res["metrics"]["distinct_recipients_1h"] == 3
    assert res["score"] >= 80.0


# Test 7: Account prefix stripping
def test_07_account_prefix_stripping(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    res1 = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    res2 = detect_rapid_drain("ACCOUNT:ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res1["score"] == res2["score"]
    assert res2["entities"]["account_id"] == "ACC_1"


# Test 8: Missing timestamps handled safely
def test_08_missing_timestamps(sample_accounts_df):
    txs = [
        make_tx("TX1", None, "ACC_1", "DEST_1", "TRANSFER", 1000.0),
        make_tx("TX2", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 1000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["score"] >= 0.0


# Test 9: Missing/null events or beneficiary data handled safely
def test_09_missing_events_and_beneficiaries(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), events_df=pd.DataFrame(), beneficiaries_df=pd.DataFrame(), accounts_df=sample_accounts_df)
    assert res["detected"] is True


# Test 10: Point-in-time cutoff via as_of_timestamp
def test_10_as_of_timestamp_cutoff(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 1000.0),
        make_tx("TX2", "2026-01-01 12:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, as_of_timestamp="2026-01-01 11:00:00")
    assert res["detected"] is False
    assert res["metrics"]["outgoing_sum_1h"] == 1000.0


# Test 11: Point-in-time cutoff via target transaction_id anchor
def test_11_transaction_id_anchor(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 1000.0),
        make_tx("TX2", "2026-01-01 12:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, transaction_id="TX1")
    assert res["detected"] is False
    assert res["metrics"]["outgoing_sum_1h"] == 1000.0


# Test 12: Future transactions appended do not change historical scores
def test_12_future_appended_records(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 500.0)
    ]
    res1 = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, as_of_timestamp="2026-01-01 10:30:00")
    
    # Append future massive drain
    txs.append(make_tx("TX_FUTURE", "2026-01-02 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 50000.0))
    res2 = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, as_of_timestamp="2026-01-01 10:30:00")
    
    assert res1["score"] == res2["score"]
    assert res1["metrics"] == res2["metrics"]


# Test 13: Label independence (works without isFraud, fraud_type, campaign_id)
def test_13_label_independence(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0, is_fraud=1)
    ]
    df1 = pd.DataFrame(txs)
    df2 = df1.drop(columns=["isFraud", "fraud_type", "campaign_id"])
    
    res1 = detect_rapid_drain("ACC_1", df1, accounts_df=sample_accounts_df)
    res2 = detect_rapid_drain("ACC_1", df2, accounts_df=sample_accounts_df)
    assert res1["score"] == res2["score"]
    assert res1["detected"] == res2["detected"]
    assert res1["evidence"] == res2["evidence"]


# Test 14: Deterministic scoring
def test_14_deterministic_scoring(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    df = pd.DataFrame(txs)
    res1 = detect_rapid_drain("ACC_1", df, accounts_df=sample_accounts_df)
    res2 = detect_rapid_drain("ACC_1", df, accounts_df=sample_accounts_df)
    assert res1 == res2


# Test 15: Score strictly bounded between 0 and 100
def test_15_score_bounds(sample_accounts_df, sample_events_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 500000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), events_df=sample_events_df, accounts_df=sample_accounts_df)
    assert 0.0 <= res["score"] <= 100.0


# Test 16: Evidence includes valid real source transaction IDs
def test_16_evidence_source_identifiers(sample_accounts_df):
    txs = [make_tx("TX_REAL_1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert len(res["evidence"]) > 0
    assert "TX_REAL_1" in res["evidence"][0]["transaction_ids"]


# Test 17: No fabricated transaction IDs in evidence
def test_17_no_fabricated_transaction_ids(sample_accounts_df):
    txs = [
        make_tx("TX_REAL_1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 3000.0),
        make_tx("TX_REAL_2", "2026-01-01 10:10:00", "ACC_1", "DEST_2", "TRANSFER", 3000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    for ev in res["evidence"]:
        for tx_id in ev["transaction_ids"]:
            assert tx_id in ["TX_REAL_1", "TX_REAL_2"]


# Test 18: Empty input dataframe
def test_18_empty_input(sample_accounts_df):
    res = detect_rapid_drain("ACC_1", pd.DataFrame(), accounts_df=sample_accounts_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 19: Non-existent account ID
def test_19_nonexistent_account(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_EXISTS", "DEST_1", "TRANSFER", 6000.0)]
    res = detect_rapid_drain("ACC_DOES_NOT_EXIST", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


# Test 20: Schema keys verification
def test_20_schema_keys(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 100.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    expected_keys = {
        "pattern_name", "detected", "score", "severity", "evidence",
        "entities", "transactions", "metrics", "explanation"
    }
    assert expected_keys.issubset(res.keys())
    assert res["pattern_name"] == "RAPID_DRAIN"


# Test 21: Configurable thresholds
def test_21_configurable_thresholds(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 2500.0)]
    cfg = {"drain_ratio_threshold": 0.4, "score_threshold": 40.0}
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, config=cfg)
    assert res["detected"] is True  # Detected because ratio threshold lowered to 0.4


# Test 22: Outgoing transaction filtering (CASH_IN ignored)
def test_22_cash_in_ignored(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "CASH_IN", 50000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is False
    assert res["metrics"]["outgoing_sum_1h"] == 0.0


# Test 23: Multiple outgoing types (CASH_OUT and PAYMENT)
def test_23_multiple_outgoing_types(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "CASH_OUT", 3000.0),
        make_tx("TX2", "2026-01-01 10:10:00", "ACC_1", "DEST_2", "PAYMENT", 3000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is True
    assert res["metrics"]["outgoing_sum_1h"] == 6000.0


# Test 24: Zero eligible transactions prior to cutoff
def test_24_zero_eligible_tx_cutoff(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-02 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, as_of_timestamp="2026-01-01 00:00:00")
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "No eligible transactions" in res["explanation"]


# Test 25: Invalid transaction_id anchor returns explanation
def test_25_invalid_transaction_id_anchor(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, transaction_id="NON_EXISTENT_TX")
    assert res["detected"] is False
    assert res["score"] == 0.0
    assert "not found" in res["explanation"]


# Test 26: Metrics accuracy
def test_26_metrics_accuracy(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 2500.0),
        make_tx("TX2", "2026-01-01 10:15:00", "ACC_1", "DEST_2", "TRANSFER", 2500.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["metrics"]["outgoing_sum_1h"] == 5000.0
    assert res["metrics"]["drain_ratio_1h"] == 1.0
    assert res["metrics"]["distinct_recipients_1h"] == 2


# Test 27: Entities accuracy
def test_27_entities_accuracy(sample_accounts_df, sample_beneficiaries_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 6000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df, beneficiaries_df=sample_beneficiaries_df)
    assert res["entities"]["account_id"] == "ACC_1"
    assert "DEST_BENEF_1" in res["entities"]["beneficiaries"]
    assert "DEST_1" in res["entities"]["destinations"]


# Test 28: Evidence type formatting
def test_28_evidence_type_formatting(sample_accounts_df, sample_events_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 3000.0)]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), events_df=sample_events_df, accounts_df=sample_accounts_df)
    assert res["evidence"][0]["evidence_type"] == "BENEFICIARY_DRAIN_ABUSE"


# Test 29: Custom accounts metadata dataframe override
def test_29_custom_accounts_override(sample_accounts_df):
    txs = [make_tx("TX1", "2026-01-01 10:00:00", "ACC_HIGH_INC", "DEST_1", "TRANSFER", 6000.0)]
    # For 20k income, 6k is only 30% drain ratio (low risk)
    res = detect_rapid_drain("ACC_HIGH_INC", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is False
    assert res["metrics"]["drain_ratio_1h"] == 0.3


# Test 30: Multi-burst drain peak detection across timeline
def test_30_multi_burst_timeline(sample_accounts_df):
    txs = [
        make_tx("TX1", "2026-01-01 10:00:00", "ACC_1", "DEST_1", "TRANSFER", 1000.0),
        make_tx("TX2", "2026-01-02 10:00:00", "ACC_1", "DEST_2", "TRANSFER", 12000.0)
    ]
    res = detect_rapid_drain("ACC_1", pd.DataFrame(txs), accounts_df=sample_accounts_df)
    assert res["detected"] is True
    assert res["metrics"]["drain_ratio_1h"] == 2.4
    assert res["score"] == 85.0
