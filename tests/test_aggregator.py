"""
FRAUD-RING RADAR
Tests for Aggregation Engine (tests/test_aggregator.py)
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from fraud.aggregator import (
    run_all_detectors,
    STATUS_SUCCESS_FLAGGED,
    STATUS_SUCCESS_CLEAN,
    STATUS_SKIPPED_MISSING_DATA,
    STATUS_ERROR,
    _aggregate_score
)

def create_mock_result(pattern_name, detected=False, score=0.0, txs=None, metrics=None, entities=None):
    if txs is None:
        txs = []
    if metrics is None:
        metrics = {}
    if entities is None:
        entities = {}
    return {
        "pattern_name": pattern_name,
        "detected": detected,
        "score": score,
        "severity": "NONE",
        "evidence": [],
        "entities": entities,
        "transactions": txs,
        "metrics": metrics,
        "explanation": "mock"
    }

@pytest.fixture
def clean_mocks():
    return {
        "CARD_TESTING": MagicMock(return_value=create_mock_result("CARD_TESTING", False, 0.0, entities={"devices": ["d1"]})),
        "ACCOUNT_TAKEOVER": MagicMock(return_value=create_mock_result("ACCOUNT_TAKEOVER", False, 0.0, metrics={"baseline_devices": 1})),
        "MULE_CHAIN": MagicMock(return_value=create_mock_result("MULE_CHAIN", False, 0.0, metrics={"incoming_count": 1})),
        "IMPOSSIBLE_TRAVEL": MagicMock(return_value=create_mock_result("IMPOSSIBLE_TRAVEL", False, 0.0, metrics={"valid_location_pairs": 1})),
        "DEVICE_SYNDICATE": MagicMock(return_value=create_mock_result("DEVICE_SYNDICATE", False, 0.0, metrics={"max_accounts_per_device": 1})),
        "VELOCITY_BURST": MagicMock(return_value=create_mock_result("VELOCITY_BURST", False, 0.0, metrics={"max_tx_count_5m": 1})),
        "RAPID_DRAIN": MagicMock(return_value=create_mock_result("RAPID_DRAIN", False, 0.0, metrics={"outgoing_sum_1h": 10.0}))
    }

def test_all_detectors_clean(clean_mocks):
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        assert res["overall_score"] == 0.0
        assert res["overall_severity"] == "NONE"
        assert res["total_unique_flagged_transactions"] == 0
        for name in clean_mocks:
            assert res["execution_status"][name] == STATUS_SUCCESS_CLEAN
            assert res["detector_results"][name]["detected"] is False

def test_one_detector_flags(clean_mocks):
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 70.0, txs=["tx1", "tx2"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        assert res["overall_score"] == 70.0
        assert res["overall_severity"] == "HIGH"
        assert res["total_unique_flagged_transactions"] == 2
        assert res["execution_status"]["VELOCITY_BURST"] == STATUS_SUCCESS_FLAGGED

def test_overlapping_transactions_deduplication(clean_mocks):
    # Velocity burst and Rapid Drain flag the exact same transactions
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 80.0, txs=["tx1", "tx2"])
    clean_mocks["RAPID_DRAIN"].return_value = create_mock_result("RAPID_DRAIN", True, 70.0, txs=["tx1", "tx2"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        # Base 80.0 + 5.0 (for complete overlap) = 85.0
        assert res["overall_score"] == 85.0
        assert res["total_unique_flagged_transactions"] == 2

def test_unique_transactions_add_higher_risk(clean_mocks):
    # One unique transaction each
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 80.0, txs=["tx1", "tx2"])
    clean_mocks["RAPID_DRAIN"].return_value = create_mock_result("RAPID_DRAIN", True, 70.0, txs=["tx1", "tx3"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        # Base 80.0 + 15.0 (for having unique tx3) = 95.0
        assert res["overall_score"] == 95.0
        assert res["total_unique_flagged_transactions"] == 3

def test_score_bounded_to_100(clean_mocks):
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 90.0, txs=["tx1"])
    clean_mocks["RAPID_DRAIN"].return_value = create_mock_result("RAPID_DRAIN", True, 80.0, txs=["tx2"])
    clean_mocks["CARD_TESTING"].return_value = create_mock_result("CARD_TESTING", True, 60.0, txs=["tx3"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        # Base 90 + 15 + 15 = 120, capped at 100
        assert res["overall_score"] == 100.0

def test_missing_data_status(clean_mocks):
    # Return empty metrics -> should be flagged as SKIPPED_MISSING_DATA
    clean_mocks["MULE_CHAIN"].return_value = create_mock_result("MULE_CHAIN", False, 0.0, metrics={})
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        assert res["execution_status"]["MULE_CHAIN"] == STATUS_SKIPPED_MISSING_DATA

def test_detector_exception_is_isolated(clean_mocks):
    clean_mocks["CARD_TESTING"].side_effect = ValueError("Some internal error")
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        assert res["execution_status"]["CARD_TESTING"] == STATUS_ERROR
        # Other detectors should still succeed
        assert res["execution_status"]["VELOCITY_BURST"] == STATUS_SUCCESS_CLEAN
        assert res["overall_score"] == 0.0

def test_point_in_time_passed_down(clean_mocks):
    as_of = "2023-10-01 12:00:00"
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        run_all_detectors("C123", as_of_timestamp=as_of)
        for mock_func in clean_mocks.values():
            # Check that as_of_timestamp was passed to each detector
            assert mock_func.call_args.kwargs["as_of_timestamp"] == as_of

def test_input_dataframes_unchanged(clean_mocks):
    df = pd.DataFrame({"A": [1, 2]})
    original_df = df.copy()
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        run_all_detectors("C123", transactions_df=df)
        
    pd.testing.assert_frame_equal(df, original_df)

def test_malformed_detector_result_schema(clean_mocks):
    # Missing 'detected' key
    clean_mocks["CARD_TESTING"].return_value = {"score": 50.0}
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        assert res["execution_status"]["CARD_TESTING"] == STATUS_ERROR
        assert "execution failed" in res["detector_results"]["CARD_TESTING"]["explanation"].lower()

@pytest.mark.parametrize("bad_score", [
    "80",       # string score
    True,       # boolean score
    float('nan'), # NaN
    float('inf'), # Positive infinity
    float('-inf'), # Negative infinity
    -10.0,      # Negative score
    101.0,      # > 100 score
    None        # Missing score
])
def test_malformed_score_is_isolated(clean_mocks, bad_score):
    clean_mocks["CARD_TESTING"].return_value = create_mock_result("CARD_TESTING", True, bad_score, txs=["tx1"])
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 70.0, txs=["tx2"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        
        # CARD_TESTING should fail
        assert res["execution_status"]["CARD_TESTING"] == STATUS_ERROR
        
        # VELOCITY_BURST should succeed
        assert res["execution_status"]["VELOCITY_BURST"] == STATUS_SUCCESS_FLAGGED
        
        # Overall score should only include VELOCITY_BURST (70.0)
        assert res["overall_score"] == 70.0
        assert res["total_unique_flagged_transactions"] == 1

@pytest.mark.parametrize("bad_txs", [
    "TX123",    # string instead of list
    None,       # None
    {"tx1": 1}, # dict
    {"tx1"}     # set
])
def test_malformed_transactions_collection_is_isolated(clean_mocks, bad_txs):
    mock_res = create_mock_result("CARD_TESTING", True, 80.0)
    mock_res["transactions"] = bad_txs
    clean_mocks["CARD_TESTING"].return_value = mock_res
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 70.0, txs=["tx2"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        
        assert res["execution_status"]["CARD_TESTING"] == STATUS_ERROR
        assert res["overall_score"] == 70.0
        assert res["total_unique_flagged_transactions"] == 1

@pytest.mark.parametrize("bad_tx_list", [
    ["tx1", ""],       # contains empty string
    ["tx1", None],     # contains None
    ["tx1", 123]       # contains int
])
def test_malformed_transaction_id_is_isolated(clean_mocks, bad_tx_list):
    mock_res = create_mock_result("CARD_TESTING", True, 80.0)
    mock_res["transactions"] = bad_tx_list
    clean_mocks["CARD_TESTING"].return_value = mock_res
    clean_mocks["VELOCITY_BURST"].return_value = create_mock_result("VELOCITY_BURST", True, 70.0, txs=["tx2"])
    
    with patch.dict('fraud.aggregator.DETECTORS', clean_mocks):
        res = run_all_detectors("C123")
        
        assert res["execution_status"]["CARD_TESTING"] == STATUS_ERROR
        assert res["overall_score"] == 70.0
        assert res["total_unique_flagged_transactions"] == 1
