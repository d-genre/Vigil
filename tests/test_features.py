"""
FRAUD-RING RADAR
Feature Engineering Quality Test Suite (tests/test_features.py)
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ml import features, data_loader


@pytest.fixture(scope="module")
def loaded_features():
    """Module-level fixture to load feature datasets."""
    feat_dir = PROJECT_ROOT / "data" / "processed" / "features"
    df_final = pd.read_csv(feat_dir / "features_final.csv")
    df_train = pd.read_csv(feat_dir / "train_features.csv")
    df_val = pd.read_csv(feat_dir / "val_features.csv")
    df_test = pd.read_csv(feat_dir / "test_features.csv")
    df_meta = pd.read_csv(feat_dir / "feature_metadata.csv")
    return df_final, df_train, df_val, df_test, df_meta


def test_final_dataset_row_count(loaded_features):
    """1. Verify final dataset has 150,000 rows."""
    df_final, _, _, _, _ = loaded_features
    assert len(df_final) == 150000, f"Expected 150,000 rows in final features, got {len(df_final)}"


def test_train_row_count(loaded_features):
    """2. Verify train features has 105,000 rows."""
    _, df_train, _, _, _ = loaded_features
    assert len(df_train) == 105000, f"Expected 105,000 train features, got {len(df_train)}"


def test_val_row_count(loaded_features):
    """3. Verify val features has 22,500 rows."""
    _, _, df_val, _, _ = loaded_features
    assert len(df_val) == 22500, f"Expected 22,500 val features, got {len(df_val)}"


def test_test_row_count(loaded_features):
    """4. Verify test features has 22,500 rows."""
    _, _, _, df_test, _ = loaded_features
    assert len(df_test) == 22500, f"Expected 22,500 test features, got {len(df_test)}"


def test_transaction_id_unique(loaded_features):
    """5. Verify transaction_id is unique across final feature dataset."""
    df_final, _, _, _, _ = loaded_features
    assert df_final['transaction_id'].nunique() == 150000, "transaction_id contains duplicates"


def test_is_fraud_labels(loaded_features):
    """6. Verify isFraud contains correct binary labels."""
    df_final, _, _, _, _ = loaded_features
    labels = set(df_final['isFraud'].unique())
    assert labels == {0, 1}, f"Unexpected isFraud labels: {labels}"


def test_fraud_count_preserved(loaded_features):
    """7. Verify fraud count remains 3,793."""
    df_final, _, _, _, _ = loaded_features
    assert (df_final['isFraud'] == 1).sum() == 3793, "Fraud count altered in feature dataset"


def test_no_infinite_values(loaded_features):
    """8. Verify no infinite feature values exist."""
    df_final, _, _, _, _ = loaded_features
    num_cols = df_final.select_dtypes(include=[np.number]).columns
    inf_mask = np.isinf(df_final[num_cols].values)
    assert not inf_mask.any(), "Infinite values detected in numeric features"


def test_no_nan_explosion(loaded_features):
    """9. Verify no unexpected NaN explosion in generated features."""
    df_final, _, _, _, _ = loaded_features
    meta_cols = set(features.TARGET_COLUMNS + features.GROUND_TRUTH_COLUMNS + features.IDENTIFIER_COLUMNS)
    ml_cols = [c for c in df_final.columns if c not in meta_cols]
    null_counts = df_final[ml_cols].isnull().sum()
    assert (null_counts == 0).all(), f"Unexpected NaN values found in ML features: {null_counts[null_counts > 0]}"


def test_no_ml_feature_uses_is_fraud(loaded_features):
    """10. Verify no ML feature uses isFraud."""
    _, _, _, _, df_meta = loaded_features
    assert not df_meta[df_meta['feature_name'] == 'isFraud']['uses_target'].values[0] if 'isFraud' in df_meta['feature_name'].values else True
    ml_features = df_meta['feature_name'].tolist()
    assert 'isFraud' not in ml_features, "isFraud listed as an ML feature"


def test_no_ml_feature_uses_fraud_type(loaded_features):
    """11. Verify no ML feature uses fraud_type."""
    _, _, _, _, df_meta = loaded_features
    ml_features = df_meta['feature_name'].tolist()
    assert 'fraud_type' not in ml_features, "fraud_type listed as an ML feature"


def test_no_ml_feature_uses_campaign_id(loaded_features):
    """12. Verify no ML feature uses campaign_id."""
    _, _, _, _, df_meta = loaded_features
    ml_features = df_meta['feature_name'].tolist()
    assert 'campaign_id' not in ml_features, "campaign_id listed as an ML feature"


def test_no_ml_feature_uses_transaction_id(loaded_features):
    """13. Verify no ML feature uses transaction_id."""
    _, _, _, _, df_meta = loaded_features
    ml_features = df_meta['feature_name'].tolist()
    assert 'transaction_id' not in ml_features, "transaction_id listed as an ML feature"


def test_no_raw_timestamp_as_ml_input(loaded_features):
    """14. Verify no raw timestamp string is used directly as an ML feature."""
    _, _, _, _, df_meta = loaded_features
    ml_features = df_meta['feature_name'].tolist()
    assert 'timestamp' not in ml_features, "raw timestamp listed as an ML feature"


def test_no_future_beneficiary_timestamps(loaded_features):
    """15. Verify future beneficiary timestamps are not used (age >= 0 or -1 fallback)."""
    df_final, _, _, _, _ = loaded_features
    ages = df_final['beneficiary_age_hours'].values
    valid_ages = ages[ages != -1.0]
    assert (valid_ages >= 0.0).all(), "Negative beneficiary age detected (future beneficiary leak)"


def test_no_future_events_used(loaded_features):
    """16. Verify future events are not used (hours since event >= 0 or -1 fallback)."""
    df_final, _, _, _, _ = loaded_features
    pwd_hrs = df_final['hours_since_password_change'].values
    valid_pwd = pwd_hrs[pwd_hrs != -1.0]
    assert (valid_pwd >= 0.0).all(), "Negative hours since password change detected"
    
    ben_hrs = df_final['hours_since_benef_added'].values
    valid_ben = ben_hrs[ben_hrs != -1.0]
    assert (valid_ben >= 0.0).all(), "Negative hours since beneficiary added detected"


def test_historical_velocity_excludes_current_tx(loaded_features):
    """17. Verify historical velocity prior_tx_count_1m starts at 0 for first transaction of account."""
    df_final, _, _, _, _ = loaded_features
    first_tx_mask = (df_final['time_since_prev_tx_min'] == -1.0)
    assert (df_final.loc[first_tx_mask, 'prior_tx_count_1m'] == 0).all(), "First transaction of account has prior_tx_count_1m > 0"


def test_train_val_test_membership_unchanged(loaded_features):
    """18. Verify train/validation/test transaction membership remains unchanged."""
    _, df_train, df_val, df_test, _ = loaded_features
    tr_clean = data_loader.load_train(processed=True)
    val_clean = data_loader.load_val(processed=True)
    te_clean = data_loader.load_test(processed=True)
    
    assert set(df_train['transaction_id']) == set(tr_clean['transaction_id'])
    assert set(df_val['transaction_id']) == set(val_clean['transaction_id'])
    assert set(df_test['transaction_id']) == set(te_clean['transaction_id'])
