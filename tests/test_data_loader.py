"""
FRAUD-RING RADAR
Unit Test Suite for Data Loader & Validation Pipeline (tests/test_data_loader.py)
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml import data_loader


def test_transactions_clean_row_count():
    """1. Verify transactions_clean.csv has exactly 150,000 rows."""
    df = data_loader.load_transactions(processed=True)
    assert len(df) == 150000, f"Expected 150,000 rows, got {len(df)}"


def test_transaction_id_uniqueness():
    """2. Verify transaction_id is unique."""
    df = data_loader.load_transactions(processed=True)
    assert df['transaction_id'].nunique() == 150000, "transaction_id contains duplicate values"


def test_transaction_id_no_missing():
    """3. Verify transaction_id has no missing values."""
    df = data_loader.load_transactions(processed=True)
    assert df['transaction_id'].isnull().sum() == 0, "transaction_id contains missing values"


def test_fraud_legitimate_sum():
    """4. Verify fraud + legitimate = 150,000."""
    df = data_loader.load_transactions(processed=True)
    legit_cnt = (df['isFraud'] == 0).sum()
    fraud_cnt = (df['isFraud'] == 1).sum()
    assert legit_cnt + fraud_cnt == 150000, f"Sum of fraud ({fraud_cnt}) and legit ({legit_cnt}) does not equal 150,000"


def test_fraud_count():
    """5. Verify fraud count = 3,793."""
    df = data_loader.load_transactions(processed=True)
    fraud_cnt = (df['isFraud'] == 1).sum()
    assert fraud_cnt == 3793, f"Expected 3,793 fraud transactions, got {fraud_cnt}"


def test_splits_sum_to_150k():
    """6. Verify train + val + test = 150,000."""
    tr = data_loader.load_train(processed=True)
    val = data_loader.load_val(processed=True)
    te = data_loader.load_test(processed=True)
    total_splits = len(tr) + len(val) + len(te)
    assert len(tr) == 105000, f"Expected 105,000 train rows, got {len(tr)}"
    assert len(val) == 22500, f"Expected 22,500 val rows, got {len(val)}"
    assert len(te) == 22500, f"Expected 22,500 test rows, got {len(te)}"
    assert total_splits == 150000, f"Expected total 150,000 split rows, got {total_splits}"


def test_no_multisplit_transactions():
    """7. Verify no transaction appears in multiple splits."""
    tr = data_loader.load_train(processed=True)
    val = data_loader.load_val(processed=True)
    te = data_loader.load_test(processed=True)
    
    s_tr = set(tr['transaction_id'])
    s_val = set(val['transaction_id'])
    s_te = set(te['transaction_id'])
    
    assert len(s_tr.intersection(s_val)) == 0, "Train and Val share transaction IDs"
    assert len(s_tr.intersection(s_te)) == 0, "Train and Test share transaction IDs"
    assert len(s_val.intersection(s_te)) == 0, "Val and Test share transaction IDs"


def test_timestamp_parsing():
    """8. Verify timestamp parsing works and returns datetime objects."""
    df = data_loader.load_transactions(processed=True)
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp']), "Timestamp column is not datetime type"
    assert df['timestamp'].isnull().sum() == 0, "Timestamp contains null/unparseable values"


def test_required_columns_exist():
    """9. Verify required columns exist in transactions dataset."""
    df = data_loader.load_transactions(processed=True)
    required = {'transaction_id', 'timestamp', 'type', 'amount', 'nameOrig', 'nameDest', 'device_id', 'ip_address', 'country', 'city', 'merchant_id', 'merchant_category', 'payment_method', 'status', 'isFraud', 'fraud_type', 'campaign_id'}
    actual = set(df.columns)
    assert required.issubset(actual), f"Missing required columns: {required - actual}"


def test_raw_vs_clean_row_count_match():
    """10. Verify cleaned data does not unexpectedly change raw row counts."""
    df_raw = data_loader.load_transactions(processed=False)
    df_clean = data_loader.load_transactions(processed=True)
    assert len(df_raw) == len(df_clean) == 150000, f"Raw ({len(df_raw)}) and Clean ({len(df_clean)}) row counts mismatch"
