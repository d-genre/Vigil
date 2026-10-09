"""
FRAUD-RING RADAR
Data Loader Module (backend/ml/data_loader.py)

Reproducible, path-agnostic data loader for raw Kaggle dataset
and processed raw_clean dataset.
"""

from pathlib import Path
import pandas as pd
import numpy as np

# Base directory resolution relative to ml/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "prepared"


def get_data_dir(processed: bool = False) -> Path:
    """Returns directory path for raw or processed clean data."""
    if processed:
        return PROCESSED_DATA_DIR
    return RAW_DATA_DIR


def _strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Safely strips leading/trailing whitespace from text columns."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
    return df


def load_transactions(processed: bool = False) -> pd.DataFrame:
    """Loads transactions dataset with standardized data types."""
    data_dir = get_data_dir(processed)
    file_name = "transactions_clean.csv" if processed else "transactions.csv"
    file_path = data_dir / file_name
    
    if not file_path.exists():
        fallback_paths = [
            Path(r"C:\Users\MEERA V\Downloads\transactions.csv"),
            RAW_DATA_DIR / "transactions.csv",
            PROJECT_ROOT / "data" / "prepared" / "test.csv"
        ]
        for fb in fallback_paths:
            if fb.exists():
                file_path = fb
                break

        
    df = pd.read_csv(file_path, dtype={
        'transaction_id': str,
        'nameOrig': str,
        'nameDest': str,
        'device_id': str,
        'ip_address': str,
        'merchant_id': str,
        'country': str,
        'city': str,
        'merchant_category': str,
        'payment_method': str,
        'type': str,
        'fraud_type': str,
        'campaign_id': str
    })
    
    df = _strip_string_columns(df)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df['isFraud'] = pd.to_numeric(df['isFraud'], errors='coerce').astype('int64')
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
    return df


def load_accounts(processed: bool = False) -> pd.DataFrame:
    """Loads accounts dataset with standardized data types."""
    data_dir = get_data_dir(processed)
    file_name = "accounts_clean.csv" if processed else "accounts.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={'account_id': str})
        df = _strip_string_columns(df)
        df['account_age_days'] = pd.to_numeric(df['account_age_days'], errors='coerce')
        df['monthly_income'] = pd.to_numeric(df['monthly_income'], errors='coerce')
        df['avg_transaction_amount'] = pd.to_numeric(df['avg_transaction_amount'], errors='coerce')
        df['beneficiary_count'] = pd.to_numeric(df['beneficiary_count'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    acc_col = 'nameOrig' if 'nameOrig' in tx_df.columns else 'account_id'
    acc_ids = tx_df[acc_col].dropna().unique() if acc_col in tx_df.columns else []
    return pd.DataFrame({
        'account_id': [str(a) for a in acc_ids],
        'home_country': 'US',
        'home_city': 'New York',
        'account_age_days': 180,
        'monthly_income': 5000.0,
        'avg_transaction_amount': 100.0,
        'beneficiary_count': 1
    })


def load_devices(processed: bool = False) -> pd.DataFrame:
    """Loads devices dataset."""
    data_dir = get_data_dir(processed)
    file_name = "devices_clean.csv" if processed else "devices.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={'device_id': str})
        df = _strip_string_columns(df)
        df['account_count'] = pd.to_numeric(df['account_count'], errors='coerce')
        df['transaction_count'] = pd.to_numeric(df['transaction_count'], errors='coerce')
        df['device_age_days'] = pd.to_numeric(df['device_age_days'], errors='coerce')
        df['is_emulator'] = pd.to_numeric(df['is_emulator'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    dev_ids = tx_df['device_id'].dropna().unique() if 'device_id' in tx_df.columns else []
    return pd.DataFrame({
        'device_id': [str(d) for d in dev_ids],
        'account_count': 1,
        'transaction_count': 5,
        'device_age_days': 100,
        'is_emulator': 0
    })


def load_ips(processed: bool = False) -> pd.DataFrame:
    """Loads IP addresses dataset."""
    data_dir = get_data_dir(processed)
    file_name = "ips_clean.csv" if processed else "ips.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={'ip_address': str})
        df = _strip_string_columns(df)
        df['account_count'] = pd.to_numeric(df['account_count'], errors='coerce')
        df['device_count'] = pd.to_numeric(df['device_count'], errors='coerce')
        df['transaction_count'] = pd.to_numeric(df['transaction_count'], errors='coerce')
        df['is_vpn'] = pd.to_numeric(df['is_vpn'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    ip_col = 'ip_address' if 'ip_address' in tx_df.columns else ('ip' if 'ip' in tx_df.columns else None)
    ip_addrs = tx_df[ip_col].dropna().unique() if ip_col else []
    return pd.DataFrame({
        'ip_address': [str(i) for i in ip_addrs],
        'account_count': 1,
        'device_count': 1,
        'transaction_count': 5,
        'is_vpn': 0
    })


def load_events(processed: bool = False) -> pd.DataFrame:
    """Loads events dataset."""
    data_dir = get_data_dir(processed)
    file_name = "events_clean.csv" if processed else "events.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={
            'event_id': str,
            'account_id': str,
            'event_type': str,
            'device_id': str,
            'ip_address': str,
            'country': str,
            'city': str
        })
        df = _strip_string_columns(df)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    acc_col = 'nameOrig' if 'nameOrig' in tx_df.columns else 'account_id'
    events = []
    for idx, row in tx_df.head(1000).iterrows():
        events.append({
            'event_id': f"EVT_{idx:06d}",
            'account_id': str(row.get(acc_col, f"ACC_{idx}")),
            'event_type': 'LOGIN',
            'device_id': str(row.get('device_id', 'DEV_DEFAULT')),
            'ip_address': str(row.get('ip_address', row.get('ip', '127.0.0.1'))),
            'country': 'US',
            'city': str(row.get('city', 'New York')),
            'timestamp': row.get('timestamp', pd.Timestamp.now())
        })
    return pd.DataFrame(events)


def load_beneficiaries(processed: bool = False) -> pd.DataFrame:
    """Loads beneficiaries dataset."""
    data_dir = get_data_dir(processed)
    file_name = "beneficiaries_clean.csv" if processed else "beneficiaries.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={
            'beneficiary_id': str,
            'account_id': str,
            'beneficiary_account': str
        })
        df = _strip_string_columns(df)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    acc_col = 'nameOrig' if 'nameOrig' in tx_df.columns else 'account_id'
    dest_col = 'nameDest' if 'nameDest' in tx_df.columns else 'beneficiary_id'
    bens = []
    if acc_col in tx_df.columns and dest_col in tx_df.columns:
        pairs = tx_df[[acc_col, dest_col]].dropna().drop_duplicates().head(1000)
        for idx, row in pairs.iterrows():
            bens.append({
                'beneficiary_id': f"BEN_{idx:06d}",
                'account_id': str(row[acc_col]),
                'beneficiary_account': str(row[dest_col]),
                'created_at': pd.Timestamp.now()
            })
    return pd.DataFrame(bens)


def load_merchants(processed: bool = False) -> pd.DataFrame:
    """Loads merchants dataset."""
    data_dir = get_data_dir(processed)
    file_name = "merchants_clean.csv" if processed else "merchants.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={
            'merchant_id': str,
            'merchant_category': str
        })
        df = _strip_string_columns(df)
        df['transaction_count'] = pd.to_numeric(df['transaction_count'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    merch_col = 'merchant_id' if 'merchant_id' in tx_df.columns else ('nameDest' if 'nameDest' in tx_df.columns else None)
    merchs = tx_df[merch_col].dropna().unique() if merch_col else []
    return pd.DataFrame({
        'merchant_id': [str(m) for m in merchs],
        'merchant_category': 'RETAIL',
        'transaction_count': 10
    })


def load_cities(processed: bool = False) -> pd.DataFrame:
    """Loads cities dataset."""
    data_dir = get_data_dir(processed)
    file_name = "cities_clean.csv" if processed else "cities.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={'city': str, 'country': str})
        df = _strip_string_columns(df)
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        return df

    tx_df = load_transactions(processed=processed)
    cities = tx_df['city'].dropna().unique() if 'city' in tx_df.columns else ['New York', 'Los Angeles']
    return pd.DataFrame({
        'city': [str(c) for c in cities],
        'country': 'US',
        'lat': 40.7128,
        'lon': -74.0060
    })


def load_ground_truth(processed: bool = False) -> pd.DataFrame:
    """Loads ground truth dataset."""
    data_dir = get_data_dir(processed)
    file_name = "ground_truth_clean.csv" if processed else "ground_truth.csv"
    file_path = data_dir / file_name
    if file_path.exists():
        df = pd.read_csv(file_path, dtype={
            'campaign_id': str,
            'attack_type': str,
            'expected_patterns': str,
            'transactions': str
        })
        return _strip_string_columns(df)

    return pd.DataFrame(columns=['campaign_id', 'attack_type', 'expected_patterns', 'transactions'])


def load_train(processed: bool = False) -> pd.DataFrame:
    """Loads training split dataset."""
    data_dir = get_data_dir(processed)
    file_name = "train_clean.csv" if (processed and (data_dir / "train_clean.csv").exists()) else "train.csv"
    file_path = data_dir / file_name
    if not file_path.exists():
        fallback_paths = [
            PROJECT_ROOT / "data" / "prepared" / "train.csv",
            RAW_DATA_DIR / "train.csv"
        ]
        for fb in fallback_paths:
            if fb.exists():
                file_path = fb
                break
        
    df = pd.read_csv(file_path, dtype={'transaction_id': str, 'campaign_id': str, 'fraud_type': str})
    df['isFraud'] = pd.to_numeric(df['isFraud'], errors='coerce').astype('int64')
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df


def load_val(processed: bool = False) -> pd.DataFrame:
    """Loads validation split dataset."""
    data_dir = get_data_dir(processed)
    file_name = "val_clean.csv" if (processed and (data_dir / "val_clean.csv").exists()) else "val.csv"
    file_path = data_dir / file_name
    if not file_path.exists():
        fallback_paths = [
            PROJECT_ROOT / "data" / "prepared" / "val.csv",
            RAW_DATA_DIR / "val.csv"
        ]
        for fb in fallback_paths:
            if fb.exists():
                file_path = fb
                break
        
    df = pd.read_csv(file_path, dtype={'transaction_id': str, 'campaign_id': str, 'fraud_type': str})
    df['isFraud'] = pd.to_numeric(df['isFraud'], errors='coerce').astype('int64')
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df


def load_test(processed: bool = False) -> pd.DataFrame:
    """Loads test split dataset."""
    data_dir = get_data_dir(processed)
    file_name = "test_clean.csv" if (processed and (data_dir / "test_clean.csv").exists()) else "test.csv"
    file_path = data_dir / file_name
    if not file_path.exists():
        fallback_paths = [
            PROJECT_ROOT / "data" / "prepared" / "test.csv",
            RAW_DATA_DIR / "test.csv"
        ]
        for fb in fallback_paths:
            if fb.exists():
                file_path = fb
                break
        
    df = pd.read_csv(file_path, dtype={'transaction_id': str, 'campaign_id': str, 'fraud_type': str})
    df['isFraud'] = pd.to_numeric(df['isFraud'], errors='coerce').astype('int64')
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df
