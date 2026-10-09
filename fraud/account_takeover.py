import pandas as pd
from typing import Dict, Any, Optional, Union, List
import numpy as np
from pathlib import Path

from .common import (
    load_transactions_clean,
    format_pattern_result,
    build_evidence_item,
    PROJECT_ROOT
)

DEFAULT_WINDOW_HOURS = 1.0  # Empirically profiled: 100% of ATO financial txs occur within 1h of security event
DEFAULT_SCORE_THRESHOLD = 50.0

EVENTS_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "events_clean.csv"

def load_events_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    path = data_path or EVENTS_CLEAN_PATH
    if not path.exists():
        from ml import data_loader
        df = data_loader.load_events(processed=True)
        if 'timestamp' in df.columns and 'ts' not in df.columns:
            df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df
    df = pd.read_csv(path)
    df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df

def detect_account_takeover(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    events_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects Account Takeover (ATO) pattern for a specific account.
    """
    cfg = config or {}
    window_hours = float(cfg.get("window_hours", DEFAULT_WINDOW_HOURS))
    score_threshold = float(cfg.get("score_threshold", DEFAULT_SCORE_THRESHOLD))

    raw_account_id = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)

    # Load data
    if transactions_df is None:
        tx_df = load_transactions_clean()
    else:
        tx_df = transactions_df.copy()
        if 'ts' not in tx_df.columns and 'timestamp' in tx_df.columns:
            tx_df['ts'] = pd.to_datetime(tx_df['timestamp'], errors='coerce')

    if events_df is None:
        ev_df = load_events_clean()
    else:
        ev_df = events_df.copy()
        if 'ts' not in ev_df.columns and 'timestamp' in ev_df.columns:
            ev_df['ts'] = pd.to_datetime(ev_df['timestamp'], errors='coerce')

    empty_entities = {
        "account_id": raw_account_id,
        "devices": [],
        "ips": [],
        "merchants": []
    }
    empty_metrics = {
        "new_device": False,
        "new_ip": False,
        "new_location": False,
        "password_changed": False,
        "beneficiary_added": False,
        "financial_movement": False,
        "baseline_devices": 0,
        "baseline_ips": 0
    }

    acc_tx_df = tx_df[tx_df['nameOrig'] == raw_account_id].copy() if not tx_df.empty and 'nameOrig' in tx_df.columns else pd.DataFrame()
    acc_ev_df = ev_df[ev_df['account_id'] == raw_account_id].copy() if not ev_df.empty and 'account_id' in ev_df.columns else pd.DataFrame()

    if acc_tx_df.empty and acc_ev_df.empty:
        return format_pattern_result(
            pattern_name="ACCOUNT_TAKEOVER",
            detected=False,
            score=0.0,
            evidence=[],
            entities=empty_entities,
            transactions=[],
            metrics=empty_metrics,
            explanation=f"No transactions or events found for account {raw_account_id}."
        )

    # Determine Point-in-Time Cutoff
    cutoff_ts = None
    if as_of_timestamp is not None:
        cutoff_ts = pd.to_datetime(as_of_timestamp, errors='coerce')
    elif transaction_id is not None and not acc_tx_df.empty:
        anchor_tx = acc_tx_df[acc_tx_df['transaction_id'] == transaction_id]
        if not anchor_tx.empty:
            cutoff_ts = anchor_tx['ts'].iloc[0]

    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        if not acc_tx_df.empty:
            acc_tx_df = acc_tx_df[acc_tx_df['ts'] <= cutoff_ts]
        if not acc_ev_df.empty:
            acc_ev_df = acc_ev_df[acc_ev_df['ts'] <= cutoff_ts]

    if acc_tx_df.empty and acc_ev_df.empty:
        return format_pattern_result(
            pattern_name="ACCOUNT_TAKEOVER",
            detected=False,
            score=0.0,
            evidence=[],
            entities=empty_entities,
            transactions=[],
            metrics=empty_metrics,
            explanation=f"No point-in-time data found for account {raw_account_id} as of {cutoff_ts}."
        )

    # We need a cutoff_ts to define the window. If none is provided, use the max timestamp in the data
    if cutoff_ts is None or pd.isnull(cutoff_ts):
        max_tx_ts = acc_tx_df['ts'].max() if not acc_tx_df.empty else pd.NaT
        max_ev_ts = acc_ev_df['ts'].max() if not acc_ev_df.empty else pd.NaT
        if pd.notnull(max_tx_ts) and pd.notnull(max_ev_ts):
            cutoff_ts = max(max_tx_ts, max_ev_ts)
        elif pd.notnull(max_tx_ts):
            cutoff_ts = max_tx_ts
        else:
            cutoff_ts = max_ev_ts

    window_start = cutoff_ts - pd.Timedelta(hours=window_hours)

    # Split into Baseline and Window
    tx_baseline = acc_tx_df[acc_tx_df['ts'] < window_start] if not acc_tx_df.empty else pd.DataFrame()
    ev_baseline = acc_ev_df[acc_ev_df['ts'] < window_start] if not acc_ev_df.empty else pd.DataFrame()

    tx_window = acc_tx_df[(acc_tx_df['ts'] >= window_start) & (acc_tx_df['ts'] <= cutoff_ts)] if not acc_tx_df.empty else pd.DataFrame()
    ev_window = acc_ev_df[(acc_ev_df['ts'] >= window_start) & (acc_ev_df['ts'] <= cutoff_ts)] if not acc_ev_df.empty else pd.DataFrame()

    # Collect Baseline Sets
    baseline_devices = set()
    baseline_ips = set()
    baseline_cities = set()
    baseline_countries = set()

    if not tx_baseline.empty:
        if 'device_id' in tx_baseline.columns:
            baseline_devices.update(tx_baseline['device_id'].dropna().unique())
        if 'ip_address' in tx_baseline.columns:
            baseline_ips.update(tx_baseline['ip_address'].dropna().unique())
        if 'city' in tx_baseline.columns:
            baseline_cities.update(tx_baseline['city'].dropna().unique())
        if 'country' in tx_baseline.columns:
            baseline_countries.update(tx_baseline['country'].dropna().unique())

    if not ev_baseline.empty:
        if 'device_id' in ev_baseline.columns:
            baseline_devices.update(ev_baseline['device_id'].dropna().unique())
        if 'ip_address' in ev_baseline.columns:
            baseline_ips.update(ev_baseline['ip_address'].dropna().unique())
        if 'city' in ev_baseline.columns:
            baseline_cities.update(ev_baseline['city'].dropna().unique())
        if 'country' in ev_baseline.columns:
            baseline_countries.update(ev_baseline['country'].dropna().unique())

    # Evaluate Window Signals
    window_devices = set()
    window_ips = set()
    window_cities = set()
    window_countries = set()
    
    financial_movement_txs = []

    if not tx_window.empty:
        if 'device_id' in tx_window.columns:
            window_devices.update(tx_window['device_id'].dropna().unique())
        if 'ip_address' in tx_window.columns:
            window_ips.update(tx_window['ip_address'].dropna().unique())
        if 'city' in tx_window.columns:
            window_cities.update(tx_window['city'].dropna().unique())
        if 'country' in tx_window.columns:
            window_countries.update(tx_window['country'].dropna().unique())
        
        # Look for financial movement (e.g. transfers, payments)
        if 'type' in tx_window.columns:
            movement = tx_window[tx_window['type'].isin(['TRANSFER', 'PAYMENT', 'CASH_OUT'])]
            if not movement.empty:
                financial_movement_txs = movement['transaction_id'].tolist()

    if not ev_window.empty:
        if 'device_id' in ev_window.columns:
            window_devices.update(ev_window['device_id'].dropna().unique())
        if 'ip_address' in ev_window.columns:
            window_ips.update(ev_window['ip_address'].dropna().unique())
        if 'city' in ev_window.columns:
            window_cities.update(ev_window['city'].dropna().unique())
        if 'country' in ev_window.columns:
            window_countries.update(ev_window['country'].dropna().unique())

    # New elements
    new_devices = window_devices - baseline_devices if baseline_devices else set()
    new_ips = window_ips - baseline_ips if baseline_ips else set()
    new_cities = window_cities - baseline_cities if baseline_cities else set()
    new_countries = window_countries - baseline_countries if baseline_countries else set()

    is_new_device = len(new_devices) > 0
    is_new_ip = len(new_ips) > 0
    is_new_location = len(new_cities) > 0 or len(new_countries) > 0

    password_changed = False
    beneficiary_added = False
    password_changed_events = []
    beneficiary_added_events = []

    if not ev_window.empty and 'event_type' in ev_window.columns:
        pw_events = ev_window[ev_window['event_type'] == 'PASSWORD_CHANGE']
        if not pw_events.empty:
            password_changed = True
            password_changed_events = pw_events['event_id'].tolist()
            
        ba_events = ev_window[ev_window['event_type'] == 'BENEFICIARY_ADDED']
        if not ba_events.empty:
            beneficiary_added = True
            beneficiary_added_events = ba_events['event_id'].tolist()

    # Calculate Score
    score = 0.0
    evidence = []

    if password_changed:
        score += 35.0
        evidence.append(build_evidence_item("PASSWORD_CHANGE", "Password change occurred in the window.", True, True, [], event_ids=password_changed_events))
    if beneficiary_added:
        score += 35.0
        evidence.append(build_evidence_item("BENEFICIARY_ADDED", "Beneficiary added in the window.", True, True, [], event_ids=beneficiary_added_events))
    if is_new_device:
        score += 20.0
        evidence.append(build_evidence_item("NEW_DEVICE", f"Unfamiliar device(s) seen: {', '.join(map(str, new_devices))}", True, True, []))
    if is_new_ip:
        score += 20.0
        evidence.append(build_evidence_item("NEW_IP", f"Unfamiliar IP(s) seen: {', '.join(map(str, new_ips))}", True, True, []))
    if is_new_location:
        score += 15.0
        evidence.append(build_evidence_item("NEW_LOCATION", f"Unfamiliar location seen.", True, True, []))
    
    has_financial_movement = len(financial_movement_txs) > 0
    
    # Financial movement itself doesn't add score unless there's an anomaly, 
    # but it acts as a multiplier or required context for ATO
    # If there is no financial movement, ATO might just be an attempt. We keep the score but mention it.
    if has_financial_movement and score > 0:
        score += 10.0
        evidence.append(build_evidence_item("FINANCIAL_MOVEMENT", f"Financial movement after anomalies.", True, True, financial_movement_txs))

    detected = score >= score_threshold

    metrics = {
        "new_device": is_new_device,
        "new_ip": is_new_ip,
        "new_location": is_new_location,
        "password_changed": bool(password_changed),
        "beneficiary_added": bool(beneficiary_added),
        "financial_movement": has_financial_movement,
        "baseline_devices": len(baseline_devices),
        "baseline_ips": len(baseline_ips)
    }

    all_window_txs = tx_window['transaction_id'].tolist() if not tx_window.empty else []

    entities = {
        "account_id": raw_account_id,
        "devices": list(window_devices),
        "ips": list(window_ips),
        "merchants": list(tx_window['merchant_id'].dropna().unique()) if not tx_window.empty and 'merchant_id' in tx_window.columns else []
    }

    if detected:
        explanation = f"Detected ACCOUNT_TAKEOVER on account {raw_account_id} with score {score}."
    else:
        explanation = f"No ACCOUNT_TAKEOVER pattern detected on account {raw_account_id}."

    return format_pattern_result(
        pattern_name="ACCOUNT_TAKEOVER",
        detected=detected,
        score=score,
        evidence=evidence,
        entities=entities,
        transactions=all_window_txs,
        metrics=metrics,
        explanation=explanation
    )
