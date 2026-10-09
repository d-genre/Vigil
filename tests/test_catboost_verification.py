"""
Automated Independent Verification Tests for CatBoost Model (Step 6A)
tests/test_catboost_verification.py
"""

import os
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "catboost_fraud.cbm"
TEST_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "test_features.csv"
META_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "feature_metadata.csv"
PRED_ARTIFACT_PATH = PROJECT_ROOT / "reports" / "catboost_test_predictions.csv"
FI_ARTIFACT_PATH = PROJECT_ROOT / "reports" / "catboost_feature_importance.csv"

EXCLUDED_COLUMNS = ['transaction_id', 'timestamp', 'isFraud', 'fraud_type', 'campaign_id', 'Unnamed: 0', 'index', 'row_number']


@pytest.fixture(scope="module")
def catboost_model():
    assert MODEL_PATH.exists(), f"Model file missing at {MODEL_PATH}"
    model = CatBoostClassifier()
    model.load_model(str(MODEL_PATH))
    return model


@pytest.fixture(scope="module")
def test_data():
    if TEST_DATA_PATH.exists():
        return pd.read_csv(TEST_DATA_PATH)
    from ml.data_loader import load_test
    return load_test()


@pytest.fixture(scope="module")
def feature_names():
    if META_DATA_PATH.exists():
        meta_df = pd.read_csv(META_DATA_PATH)
        return meta_df['feature_name'].tolist()
    from ml.train_catboost import get_feature_columns
    return get_feature_columns()


def test_01_model_file_exists():
    """1. Test that model file exists."""
    assert MODEL_PATH.exists()


def test_02_model_loads(catboost_model):
    """2. Test that model can be loaded successfully."""
    assert catboost_model is not None


def test_03_model_has_62_features(catboost_model):
    """3. Test that model expects 62 features."""
    assert len(catboost_model.feature_names_) == 62


def test_04_test_dataset_has_22500_rows(test_data):
    """4. Test that test dataset has 22,500 rows."""
    assert len(test_data) == 22500


def test_05_test_feature_count_is_62(feature_names):
    """5. Test that test feature count is 62."""
    assert len(feature_names) == 62


def test_06_excluded_columns_absent_from_x(feature_names):
    """6. Test that excluded columns are absent from X."""
    for col in EXCLUDED_COLUMNS:
        assert col not in feature_names


def test_07_probabilities_within_0_1(catboost_model, test_data, feature_names):
    """7. Test that probabilities are within [0, 1]."""
    X_test = test_data[feature_names]
    probs = catboost_model.predict_proba(X_test)[:, 1]
    assert (probs >= 0.0).all()
    assert (probs <= 1.0).all()


def test_08_no_nan_probabilities(catboost_model, test_data, feature_names):
    """8. Test that there are no NaN probabilities."""
    X_test = test_data[feature_names]
    probs = catboost_model.predict_proba(X_test)[:, 1]
    assert not np.isnan(probs).any()


def test_09_no_infinite_probabilities(catboost_model, test_data, feature_names):
    """9. Test that there are no infinite probabilities."""
    X_test = test_data[feature_names]
    probs = catboost_model.predict_proba(X_test)[:, 1]
    assert not np.isinf(probs).any()


def test_10_predicted_labels_binary(catboost_model, test_data, feature_names):
    """10. Test that predicted labels are binary (0 or 1)."""
    X_test = test_data[feature_names]
    probs = catboost_model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.90).astype(int)
    assert set(np.unique(preds)).issubset({0, 1})


def test_11_prediction_artifact_rows():
    """11. Test that prediction artifact has 22,500 rows."""
    assert PRED_ARTIFACT_PATH.exists()
    df = pd.read_csv(PRED_ARTIFACT_PATH)
    assert len(df) == 22500


def test_12_prediction_artifact_no_duplicate_tx_ids():
    """12. Test that prediction artifact has no duplicate transaction IDs."""
    df = pd.read_csv(PRED_ARTIFACT_PATH)
    assert df['transaction_id'].nunique() == 22500


def test_13_feature_importance_62_rows():
    """13. Test that feature importance artifact has 62 rows."""
    assert FI_ARTIFACT_PATH.exists()
    df = pd.read_csv(FI_ARTIFACT_PATH)
    assert len(df) == 62


def test_14_feature_importance_no_duplicate_names():
    """14. Test that feature importance has no duplicate feature names."""
    df = pd.read_csv(FI_ARTIFACT_PATH)
    assert df['feature_name'].nunique() == 62


def test_15_saved_predictions_match_regenerated(catboost_model, test_data, feature_names):
    """15. Test that saved predictions match regenerated predictions."""
    df_saved = pd.read_csv(PRED_ARTIFACT_PATH)
    X_test = test_data[feature_names]
    fresh_probs = catboost_model.predict_proba(X_test)[:, 1]
    fresh_preds = (fresh_probs >= 0.90).astype(int)
    
    assert np.allclose(df_saved['fraud_probability'].values, fresh_probs, atol=1e-5)
    assert np.array_equal(df_saved['predicted_label'].values, fresh_preds)


def test_16_deterministic_prediction_check(catboost_model, test_data, feature_names):
    """16. Test that predictions are completely deterministic."""
    X_test = test_data[feature_names]
    probs_run1 = catboost_model.predict_proba(X_test)[:, 1]
    probs_run2 = catboost_model.predict_proba(X_test)[:, 1]
    assert np.array_equal(probs_run1, probs_run2)
