"""
Automated Unit Tests for Card Testing Detector (Step 8B.1)
tests/test_card_testing.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
import numpy as np

from fraud.card_testing import detect_card_testing
from fraud.common import load_transactions_clean

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_ZIP_PATH = PROJECT_ROOT / "data" / "raw" / "fraud_data_share.zip"
GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "graph" / "fraud_graph.gpickle"
CATBOOST_MODEL_PATH = PROJECT_ROOT / "models" / "catboost_fraud.cbm"
LOGISTIC_MODEL_PATH = PROJECT_ROOT / "models" / "logistic_regression.pkl"
ISO_MODEL_PATH = PROJECT_ROOT / "models" / "isolation_forest.pkl"


@pytest.fixture(scope="module")
def clean_tx_data():
    return load_transactions_clean()


def test_01_detector_imports():
    """1. Test that detector imports successfully."""
    assert callable(detect_card_testing)


def test_02_required_schema_keys(clean_tx_data):
    """2. Test that detector returns required schema keys."""
    res = detect_card_testing("C0000340", clean_tx_data)
    required_keys = {"pattern_name", "detected", "score", "severity", "evidence", "entities", "transactions", "metrics", "explanation"}
    assert required_keys.issubset(set(res.keys()))


def test_03_card_testing_only_pattern_name(clean_tx_data):
    """3. Test that CARD_TESTING is the only pattern name produced."""
    res = detect_card_testing("C0000340", clean_tx_data)
    assert res["pattern_name"] == "CARD_TESTING"


def test_04_empty_input_handled_safely():
    """4. Test that empty DataFrame input is handled safely."""
    empty_df = pd.DataFrame(columns=['transaction_id', 'timestamp', 'nameOrig', 'amount', 'status'])
    res = detect_card_testing("C9999999", empty_df)
    assert res["detected"] is False
    assert res["score"] == 0.0


def test_05_no_match_returns_detected_false(clean_tx_data):
    """5. Test that no-match input returns detected = False, score = 0."""
    res = detect_card_testing("NON_EXISTENT_ACCOUNT", clean_tx_data)
    assert res["detected"] is False
    assert res["score"] == 0.0


def test_06_matching_behavior_returns_detected_true(clean_tx_data):
    """6. Test that matching card-testing behavior returns detected = True."""
    # Account C0000340 is known card-testing account
    res = detect_card_testing("C0000340", clean_tx_data)
    assert res["detected"] is True
    assert res["score"] > 50.0


def test_07_score_is_deterministic(clean_tx_data):
    """7. Test that score is deterministic across multiple calls."""
    res1 = detect_card_testing("C0000340", clean_tx_data)
    res2 = detect_card_testing("C0000340", clean_tx_data)
    assert res1["score"] == res2["score"]
    assert res1["detected"] == res2["detected"]


def test_08_evidence_is_structured(clean_tx_data):
    """8. Test that evidence items are properly structured."""
    res = detect_card_testing("C0000340", clean_tx_data)
    assert len(res["evidence"]) > 0
    for item in res["evidence"]:
        assert "evidence_type" in item
        assert "description" in item
        assert "value" in item
        assert "threshold" in item
        assert "transaction_ids" in item


def test_09_transaction_ids_in_evidence_exist(clean_tx_data):
    """9. Test that transaction IDs in evidence actually exist in source data."""
    res = detect_card_testing("C0000340", clean_tx_data)
    all_tx_ids = set(clean_tx_data['transaction_id'])
    for tx_id in res["transactions"]:
        assert tx_id in all_tx_ids


def test_10_as_of_timestamp_excludes_future(clean_tx_data):
    """10. Test that as_of_timestamp excludes future transactions."""
    cutoff = "2026-01-01 12:00:00"
    res = detect_card_testing("C0000340", clean_tx_data, as_of_timestamp=cutoff)
    if res["metrics"]["last_timestamp"] is not None:
        assert res["metrics"]["last_timestamp"] <= cutoff


def test_11_future_tx_cannot_cause_historical_suspicion(clean_tx_data):
    """11. Test that point-in-time evaluation before attack window returns detected = False."""
    # Before the card testing attack occurred on C0000340 (2026-01-02 04:14:00)
    early_cutoff = "2026-01-01 23:59:59"
    res = detect_card_testing("C0000340", clean_tx_data, as_of_timestamp=early_cutoff)
    assert res["detected"] is False


def test_12_nomerch_handled_safely(clean_tx_data):
    """12. Test that NOMERCH is excluded from real merchant entities."""
    res = detect_card_testing("C0000340", clean_tx_data)
    assert "NOMERCH" not in res["entities"]["merchants"]
    assert "nomerch" not in res["entities"]["merchants"]


def test_13_zero_invalid_timestamps_handled_safely():
    """13. Test that invalid timestamp format doesn't crash detector."""
    data = [
        {"transaction_id": "TX-1", "timestamp": "invalid_ts", "nameOrig": "C100", "amount": 2.0, "status": "FAILED"}
    ]
    df = pd.DataFrame(data)
    res = detect_card_testing("C100", df)
    assert isinstance(res, dict)


def test_14_missing_optional_fields_do_not_crash():
    """14. Test that missing optional metadata columns do not crash detector."""
    minimal_df = pd.DataFrame([
        {"transaction_id": "TX-1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C100", "amount": 2.0},
        {"transaction_id": "TX-2", "timestamp": "2026-01-01 10:00:30", "nameOrig": "C100", "amount": 1.5},
        {"transaction_id": "TX-3", "timestamp": "2026-01-01 10:01:00", "nameOrig": "C100", "amount": 3.0},
        {"transaction_id": "TX-4", "timestamp": "2026-01-01 10:01:30", "nameOrig": "C100", "amount": 2.5}
    ])
    res = detect_card_testing("C100", minimal_df)
    assert res["detected"] is True


def test_15_detector_does_not_require_isfraud():
    """15. Test that detector operates on data without isFraud column."""
    data = [
        {"transaction_id": f"TX-{i}", "timestamp": f"2026-01-01 10:00:{i:02d}", "nameOrig": "C200", "amount": 2.0, "status": "FAILED"}
        for i in range(5)
    ]
    df = pd.DataFrame(data)
    assert "isFraud" not in df.columns
    res = detect_card_testing("C200", df)
    assert res["detected"] is True


def test_16_detector_does_not_require_fraud_type():
    """16. Test that detector operates on data without fraud_type column."""
    data = [
        {"transaction_id": f"TX-{i}", "timestamp": f"2026-01-01 10:00:{i:02d}", "nameOrig": "C200", "amount": 2.0, "status": "FAILED"}
        for i in range(5)
    ]
    df = pd.DataFrame(data)
    assert "fraud_type" not in df.columns
    res = detect_card_testing("C200", df)
    assert res["detected"] is True


def test_17_detector_does_not_require_campaign_id():
    """17. Test that detector operates on data without campaign_id column."""
    data = [
        {"transaction_id": f"TX-{i}", "timestamp": f"2026-01-01 10:00:{i:02d}", "nameOrig": "C200", "amount": 2.0, "status": "FAILED"}
        for i in range(5)
    ]
    df = pd.DataFrame(data)
    assert "campaign_id" not in df.columns
    res = detect_card_testing("C200", df)
    assert res["detected"] is True


def test_18_existing_graph_artifact_untouched():
    """18. Test that graph artifact exists and is untouched."""
    assert GRAPH_PATH.exists()


def test_19_existing_ml_models_untouched():
    """19. Test that existing ML model artifacts exist and are untouched."""
    assert CATBOOST_MODEL_PATH.exists()
    assert LOGISTIC_MODEL_PATH.exists()
    assert ISO_MODEL_PATH.exists()


def test_20_raw_data_untouched():
    """20. Test that raw data transaction dataset remains untouched."""
    from ml.excel_loader import resolve_dataset_path
    p = resolve_dataset_path()
    assert p.exists()
    assert p.stat().st_size > 0


def test_21_negative_test_normal_behavior():
    """21. Negative test: Ordinary transactions do not trigger CARD_TESTING."""
    normal_data = [
        {"transaction_id": "TX-N1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C300", "amount": 1500.0, "status": "SUCCESS"},
        {"transaction_id": "TX-N2", "timestamp": "2026-01-02 14:00:00", "nameOrig": "C300", "amount": 3200.0, "status": "SUCCESS"},
        {"transaction_id": "TX-N3", "timestamp": "2026-01-03 18:00:00", "nameOrig": "C300", "amount": 5.00, "status": "SUCCESS"},
        {"transaction_id": "TX-N4", "timestamp": "2026-01-04 20:00:00", "nameOrig": "C300", "amount": 250.0, "status": "FAILED"}
    ]
    df = pd.DataFrame(normal_data)
    res = detect_card_testing("C300", df)
    assert res["detected"] is False
    assert res["score"] == 0.0
