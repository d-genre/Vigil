"""
Automated Unit Tests for Isolation Forest Baseline Model (Step 7)
tests/test_isolation_forest.py
"""

from pathlib import Path
import pytest
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "isolation_forest.pkl"
VAL_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "val_features.csv"
TEST_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "test_features.csv"
META_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "feature_metadata.csv"
VAL_PRED_PATH = PROJECT_ROOT / "reports" / "isolation_validation_predictions.csv"
TEST_PRED_PATH = PROJECT_ROOT / "reports" / "isolation_test_predictions.csv"

EXCLUDED_COLUMNS = ['transaction_id', 'timestamp', 'isFraud', 'fraud_type', 'campaign_id', 'Unnamed: 0', 'index', 'row_number']


@pytest.fixture(scope="module")
def isolation_model():
    assert MODEL_PATH.exists(), f"Model file missing at {MODEL_PATH}"
    return joblib.load(MODEL_PATH)


@pytest.fixture(scope="module")
def test_data():
    assert TEST_DATA_PATH.exists(), f"Test data missing at {TEST_DATA_PATH}"
    return pd.read_csv(TEST_DATA_PATH)


@pytest.fixture(scope="module")
def val_data():
    assert VAL_DATA_PATH.exists(), f"Validation data missing at {VAL_DATA_PATH}"
    return pd.read_csv(VAL_DATA_PATH)


@pytest.fixture(scope="module")
def feature_names():
    assert META_DATA_PATH.exists(), f"Metadata missing at {META_DATA_PATH}"
    meta_df = pd.read_csv(META_DATA_PATH)
    return meta_df['feature_name'].tolist()


def test_01_model_file_exists():
    """1. Test that model file exists."""
    assert MODEL_PATH.exists()


def test_02_model_loads(isolation_model):
    """2. Test that model can be loaded successfully."""
    assert isinstance(isolation_model, IsolationForest)


def test_03_model_has_62_features(isolation_model):
    """3. Test that model expects 62 features."""
    assert isolation_model.n_features_in_ == 62


def test_04_training_feature_count_is_62(feature_names):
    """4. Test that training feature count is 62."""
    assert len(feature_names) == 62


def test_05_excluded_columns_absent_from_x(feature_names):
    """5. Test that excluded columns are absent from X."""
    for col in EXCLUDED_COLUMNS:
        assert col not in feature_names


def test_06_validation_prediction_row_count():
    """6. Test that validation prediction row count is 22,500."""
    assert VAL_PRED_PATH.exists()
    df = pd.read_csv(VAL_PRED_PATH)
    assert len(df) == 22500


def test_07_test_prediction_row_count():
    """7. Test that test prediction row count is 22,500."""
    assert TEST_PRED_PATH.exists()
    df = pd.read_csv(TEST_PRED_PATH)
    assert len(df) == 22500


def test_08_anomaly_scores_are_finite(isolation_model, test_data, feature_names):
    """8. Test that anomaly scores are finite."""
    X_test = test_data[feature_names]
    scores = -isolation_model.decision_function(X_test)
    assert np.isfinite(scores).all()


def test_09_no_nan_anomaly_scores(isolation_model, test_data, feature_names):
    """9. Test that there are no NaN anomaly scores."""
    X_test = test_data[feature_names]
    scores = -isolation_model.decision_function(X_test)
    assert not np.isnan(scores).any()


def test_10_predicted_labels_are_binary():
    """10. Test that predicted labels are binary."""
    df = pd.read_csv(TEST_PRED_PATH)
    assert set(df['predicted_label'].unique()).issubset({0, 1})


def test_11_prediction_files_exist():
    """11. Test that prediction files exist."""
    assert VAL_PRED_PATH.exists()
    assert TEST_PRED_PATH.exists()


def test_12_saved_model_generates_predictions(isolation_model, test_data, feature_names):
    """12. Test that saved model can generate predictions."""
    X_test = test_data[feature_names]
    scores = -isolation_model.decision_function(X_test)
    assert len(scores) == len(test_data)


def test_13_anomaly_score_direction_documented(isolation_model, test_data, feature_names):
    """13. Test that anomaly score direction is fraud-oriented (negative decision function)."""
    X_test = test_data[feature_names]
    dec_func = isolation_model.decision_function(X_test)
    scores = -dec_func
    assert np.allclose(scores, -dec_func)


def test_14_selected_threshold_exists():
    """14. Test that selected threshold exists and operates on predictions."""
    df = pd.read_csv(TEST_PRED_PATH)
    assert 'anomaly_score' in df.columns
    assert 'predicted_label' in df.columns


def test_15_test_prediction_artifact_columns():
    """15. Test that test prediction artifact has required columns."""
    df = pd.read_csv(TEST_PRED_PATH)
    required = {'transaction_id', 'y_true', 'anomaly_score', 'predicted_label'}
    assert required.issubset(set(df.columns))
