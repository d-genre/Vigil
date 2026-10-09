"""
FRAUD-RING RADAR
Unit Test Suite for CatBoost Model (tests/test_catboost.py)
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml import train_catboost


@pytest.fixture(scope="module")
def loaded_model():
    """Module-level fixture to load trained CatBoost model artifact."""
    model_path = PROJECT_ROOT / "models" / "catboost_fraud.cbm"
    assert model_path.exists(), f"CatBoost model file missing at {model_path}"
    model = CatBoostClassifier()
    model.load_model(str(model_path))
    return model


@pytest.fixture(scope="module")
def feature_data():
    """Module-level fixture to load val and test feature datasets."""
    feat_dir = PROJECT_ROOT / "data" / "processed" / "features"
    val_df = pd.read_csv(feat_dir / "val_features.csv")
    te_df = pd.read_csv(feat_dir / "test_features.csv")
    feature_cols = train_catboost.get_feature_columns()
    return val_df, te_df, feature_cols


def test_model_file_exists():
    """1. Verify model file exists."""
    model_path = PROJECT_ROOT / "models" / "catboost_fraud.cbm"
    assert model_path.exists(), f"Model file missing at {model_path}"


def test_model_can_be_loaded(loaded_model):
    """2. Verify model can be loaded successfully."""
    assert loaded_model is not None


def test_model_expects_62_features(loaded_model):
    """3. Verify model expects 62 features."""
    assert len(loaded_model.feature_names_) == 62, f"Expected 62 features, got {len(loaded_model.feature_names_)}"


def test_required_feature_columns_exist(feature_data):
    """4. Verify required feature columns exist and match 62 features."""
    _, _, feature_cols = feature_data
    assert len(feature_cols) == 62, f"Expected 62 feature columns, got {len(feature_cols)}"


def test_excluded_columns_absent_from_x(feature_data):
    """5. Verify excluded columns are absent from X."""
    _, _, feature_cols = feature_data
    for col in train_catboost.EXCLUDED_COLUMNS:
        assert col not in feature_cols, f"Excluded column {col} found in model inputs"


def test_val_prediction_row_count(loaded_model, feature_data):
    """6. Verify validation prediction row count = 22,500."""
    val_df, _, feature_cols = feature_data
    probs = loaded_model.predict_proba(val_df[feature_cols])[:, 1]
    assert len(probs) == 22500, f"Expected 22,500 val predictions, got {len(probs)}"


def test_test_prediction_row_count(loaded_model, feature_data):
    """7. Verify test prediction row count = 22,500."""
    _, te_df, feature_cols = feature_data
    probs = loaded_model.predict_proba(te_df[feature_cols])[:, 1]
    assert len(probs) == 22500, f"Expected 22,500 test predictions, got {len(probs)}"


def test_probabilities_between_0_and_1(loaded_model, feature_data):
    """8. Verify probabilities are between 0 and 1."""
    _, te_df, feature_cols = feature_data
    probs = loaded_model.predict_proba(te_df[feature_cols])[:, 1]
    assert (probs >= 0.0).all() and (probs <= 1.0).all(), "Probabilities outside [0, 1] range"


def test_predictions_are_binary(loaded_model, feature_data):
    """9. Verify predictions are binary."""
    _, te_df, feature_cols = feature_data
    preds = loaded_model.predict(te_df[feature_cols])
    labels = set(np.unique(preds))
    assert labels.issubset({0, 1}), f"Non-binary prediction labels found: {labels}"


def test_no_nan_predictions(loaded_model, feature_data):
    """10. Verify no NaN predictions."""
    _, te_df, feature_cols = feature_data
    probs = loaded_model.predict_proba(te_df[feature_cols])[:, 1]
    assert not np.isnan(probs).any(), "NaN predictions detected"


def test_feature_importance_contains_62_features(loaded_model):
    """11. Verify feature importance contains 62 features."""
    importances = loaded_model.get_feature_importance()
    assert len(importances) == 62, f"Expected 62 feature importances, got {len(importances)}"


def test_saved_prediction_files_exist():
    """12. Verify saved prediction files exist."""
    reports_dir = PROJECT_ROOT / "reports"
    val_pred = reports_dir / "catboost_validation_predictions.csv"
    te_pred = reports_dir / "catboost_test_predictions.csv"
    feat_imp = reports_dir / "catboost_feature_importance.csv"
    assert val_pred.exists(), f"Missing {val_pred}"
    assert te_pred.exists(), f"Missing {te_pred}"
    assert feat_imp.exists(), f"Missing {feat_imp}"
