"""
FRAUD-RING RADAR
Unit Test Suite for Logistic Regression Model (tests/test_logistic.py)
"""

import sys
from pathlib import Path
import pytest
import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml import train_logistic


@pytest.fixture(scope="module")
def loaded_pipeline():
    """Module-level fixture to load trained Logistic Regression pipeline."""
    model_path = PROJECT_ROOT / "models" / "logistic_regression.pkl"
    assert model_path.exists(), f"Model file does not exist at {model_path}"
    pipeline = joblib.load(model_path)
    return pipeline


@pytest.fixture(scope="module")
def feature_data():
    """Module-level fixture to load val and test feature datasets."""
    feat_dir = PROJECT_ROOT / "data" / "processed" / "features"
    val_df = pd.read_csv(feat_dir / "val_features.csv")
    te_df = pd.read_csv(feat_dir / "test_features.csv")
    feature_cols = train_logistic.get_feature_columns()
    return val_df, te_df, feature_cols


def test_model_file_exists():
    """1. Verify model file exists."""
    model_path = PROJECT_ROOT / "models" / "logistic_regression.pkl"
    assert model_path.exists(), f"Model file missing at {model_path}"


def test_pipeline_can_be_loaded(loaded_pipeline):
    """2. Verify pipeline can be loaded and has expected sklearn steps."""
    assert loaded_pipeline is not None
    assert 'scaler' in loaded_pipeline.named_steps
    assert 'model' in loaded_pipeline.named_steps


def test_expected_feature_count_matches(feature_data):
    """3. Verify expected feature count matches generated ML features."""
    _, _, feature_cols = feature_data
    assert len(feature_cols) == 62, f"Expected 62 features, got {len(feature_cols)}"


def test_target_not_in_features(feature_data):
    """4. Verify target (isFraud) is not among model features."""
    _, _, feature_cols = feature_data
    assert 'isFraud' not in feature_cols, "isFraud found in model features"


def test_fraud_type_not_in_features(feature_data):
    """5. Verify fraud_type is not among model features."""
    _, _, feature_cols = feature_data
    assert 'fraud_type' not in feature_cols, "fraud_type found in model features"


def test_campaign_id_not_in_features(feature_data):
    """6. Verify campaign_id is not among model features."""
    _, _, feature_cols = feature_data
    assert 'campaign_id' not in feature_cols, "campaign_id found in model features"


def test_transaction_id_not_in_features(feature_data):
    """7. Verify transaction_id is not among model features."""
    _, _, feature_cols = feature_data
    assert 'transaction_id' not in feature_cols, "transaction_id found in model features"


def test_timestamp_not_in_features(feature_data):
    """8. Verify timestamp is not among model features."""
    _, _, feature_cols = feature_data
    assert 'timestamp' not in feature_cols, "timestamp found in model features"


def test_prediction_works_on_val_data(loaded_pipeline, feature_data):
    """9. Verify prediction works on validation data."""
    val_df, _, feature_cols = feature_data
    probs = loaded_pipeline.predict_proba(val_df[feature_cols])[:, 1]
    assert len(probs) == len(val_df)


def test_prediction_works_on_test_data(loaded_pipeline, feature_data):
    """10. Verify prediction works on test data."""
    _, te_df, feature_cols = feature_data
    probs = loaded_pipeline.predict_proba(te_df[feature_cols])[:, 1]
    assert len(probs) == len(te_df)


def test_predicted_probabilities_range(loaded_pipeline, feature_data):
    """11. Verify predicted probabilities are between 0 and 1."""
    _, te_df, feature_cols = feature_data
    probs = loaded_pipeline.predict_proba(te_df[feature_cols])[:, 1]
    assert (probs >= 0.0).all() and (probs <= 1.0).all(), "Probabilities outside [0, 1] range"


def test_prediction_row_count_matches_input(loaded_pipeline, feature_data):
    """12. Verify prediction row count matches input row count."""
    val_df, te_df, feature_cols = feature_data
    val_probs = loaded_pipeline.predict_proba(val_df[feature_cols])[:, 1]
    te_probs = loaded_pipeline.predict_proba(te_df[feature_cols])[:, 1]
    assert len(val_probs) == 22500, f"Validation probability count {len(val_probs)} != 22,500"
    assert len(te_probs) == 22500, f"Test probability count {len(te_probs)} != 22,500"
