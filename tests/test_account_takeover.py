import pytest
import pandas as pd
from backend.fraud_patterns.account_takeover import detect_account_takeover

@pytest.fixture
def sample_ato_data():
    tx_data = [
        # Baseline transactions
        {"transaction_id": "TX-1", "timestamp": "2026-01-01 10:00:00", "nameOrig": "C123", "device_id": "D-1", "ip_address": "IP-1", "city": "CityA", "country": "CountryA", "type": "PAYMENT"},
        {"transaction_id": "TX-2", "timestamp": "2026-01-02 12:00:00", "nameOrig": "C123", "device_id": "D-1", "ip_address": "IP-1", "city": "CityA", "country": "CountryA", "type": "PAYMENT"},
        
        # Window transaction (New device, new IP, with transfer)
        {"transaction_id": "TX-3", "timestamp": "2026-01-10 14:00:00", "nameOrig": "C123", "device_id": "D-2", "ip_address": "IP-2", "city": "CityB", "country": "CountryA", "type": "TRANSFER"},
    ]
    
    ev_data = [
        # Baseline event
        {"event_id": "E-1", "timestamp": "2026-01-01 09:00:00", "account_id": "C123", "event_type": "LOGIN", "device_id": "D-1", "ip_address": "IP-1", "city": "CityA", "country": "CountryA"},
        
        # Window events (Password change + beneficiary added)
        {"event_id": "E-2", "timestamp": "2026-01-10 13:30:00", "account_id": "C123", "event_type": "PASSWORD_CHANGE", "device_id": "D-2", "ip_address": "IP-2", "city": "CityB", "country": "CountryA"},
        {"event_id": "E-3", "timestamp": "2026-01-10 13:40:00", "account_id": "C123", "event_type": "BENEFICIARY_ADDED", "device_id": "D-2", "ip_address": "IP-2", "city": "CityB", "country": "CountryA"},
    ]
    
    tx_df = pd.DataFrame(tx_data)
    ev_df = pd.DataFrame(ev_data)
    
    return tx_df, ev_df

def test_detect_ato_positive(sample_ato_data):
    tx_df, ev_df = sample_ato_data
    
    result = detect_account_takeover(
        account_id="C123",
        transactions_df=tx_df,
        events_df=ev_df,
        as_of_timestamp="2026-01-10 14:05:00"
    )
    
    assert result["detected"] is True
    assert result["score"] >= 80.0 # 35 + 35 + 20 + 20 + 15 + 10 = 135 -> capped to 100 in common.py
    assert result["metrics"]["new_device"] is True
    assert result["metrics"]["password_changed"] is True
    assert result["metrics"]["beneficiary_added"] is True
    assert result["metrics"]["financial_movement"] is True
    
    # Verify event_ids traceability
    pw_evidence = next((e for e in result["evidence"] if e["evidence_type"] == "PASSWORD_CHANGE"), None)
    assert pw_evidence is not None
    assert "E-2" in pw_evidence.get("event_ids", [])
    
    ba_evidence = next((e for e in result["evidence"] if e["evidence_type"] == "BENEFICIARY_ADDED"), None)
    assert ba_evidence is not None
    assert "E-3" in ba_evidence.get("event_ids", [])

def test_detect_ato_point_in_time_safety(sample_ato_data):
    tx_df, ev_df = sample_ato_data
    
    # Query BEFORE the ATO events
    result = detect_account_takeover(
        account_id="C123",
        transactions_df=tx_df,
        events_df=ev_df,
        as_of_timestamp="2026-01-05 00:00:00"
    )
    
    assert result["detected"] is False
    assert result["metrics"]["password_changed"] is False
    assert result["metrics"]["new_device"] is False

def test_detect_ato_weak_signal(sample_ato_data):
    tx_df, ev_df = sample_ato_data
    
    # Remove the password change and beneficiary added to leave only new device/IP
    ev_df = ev_df[~ev_df['event_type'].isin(['PASSWORD_CHANGE', 'BENEFICIARY_ADDED'])]
    
    result = detect_account_takeover(
        account_id="C123",
        transactions_df=tx_df,
        events_df=ev_df,
        as_of_timestamp="2026-01-10 14:05:00"
    )
    
    # Score should be 20 (device) + 20 (IP) + 15 (loc) + 10 (movement) = 65 -> detected if threshold is 50
    assert result["detected"] is True
    assert result["score"] == 65.0

def test_detect_ato_new_device_only(sample_ato_data):
    tx_df, ev_df = sample_ato_data
    # Remove password change and beneficiary added
    ev_df = ev_df[~ev_df['event_type'].isin(['PASSWORD_CHANGE', 'BENEFICIARY_ADDED'])]
    # Remove new IP and location from tx_df and ev_df window events
    tx_df.loc[tx_df['transaction_id'] == 'TX-3', 'ip_address'] = 'IP-1'
    tx_df.loc[tx_df['transaction_id'] == 'TX-3', 'city'] = 'CityA'
    
    result = detect_account_takeover(
        account_id="C123",
        transactions_df=tx_df,
        events_df=ev_df,
        as_of_timestamp="2026-01-10 14:05:00"
    )
    # Score: 20 (new device) + 10 (movement) = 30 < 50
    assert result["detected"] is False
    assert result["score"] == 30.0

def test_detect_ato_password_change_only(sample_ato_data):
    tx_df, ev_df = sample_ato_data
    # Remove beneficiary added
    ev_df = ev_df[ev_df['event_type'] != 'BENEFICIARY_ADDED']
    # Remove new device, IP, location from tx_df and ev_df
    tx_df.loc[tx_df['transaction_id'] == 'TX-3', ['device_id', 'ip_address', 'city']] = ['D-1', 'IP-1', 'CityA']
    ev_df.loc[ev_df['event_id'] == 'E-2', ['device_id', 'ip_address', 'city']] = ['D-1', 'IP-1', 'CityA']
    
    result = detect_account_takeover(
        account_id="C123",
        transactions_df=tx_df,
        events_df=ev_df,
        as_of_timestamp="2026-01-10 14:05:00"
    )
    # Score: 35 (password) + 10 (movement) = 45 < 50
    assert result["detected"] is False
    assert result["score"] == 45.0

def test_detect_ato_beneficiary_added_only(sample_ato_data):
    tx_df, ev_df = sample_ato_data
    # Remove password change
    ev_df = ev_df[ev_df['event_type'] != 'PASSWORD_CHANGE']
    # Remove new device, IP, location from tx_df and ev_df
    tx_df.loc[tx_df['transaction_id'] == 'TX-3', ['device_id', 'ip_address', 'city']] = ['D-1', 'IP-1', 'CityA']
    ev_df.loc[ev_df['event_id'] == 'E-3', ['device_id', 'ip_address', 'city']] = ['D-1', 'IP-1', 'CityA']
    
    result = detect_account_takeover(
        account_id="C123",
        transactions_df=tx_df,
        events_df=ev_df,
        as_of_timestamp="2026-01-10 14:05:00"
    )
    # Score: 35 (beneficiary) + 10 (movement) = 45 < 50
    assert result["detected"] is False
    assert result["score"] == 45.0
