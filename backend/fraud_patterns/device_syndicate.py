"""
FRAUD-RING RADAR
Device Syndicate Fraud Pattern Detector (backend/fraud_patterns/device_syndicate.py)

Identifies Device Syndicate patterns where multiple accounts share the same physical
device or suspicious device identifiers, evaluating fan-out, temporal concentration,
and device characteristics under strict point-in-time and label-independent safeguards.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List, Set
from pathlib import Path

from .common import (
    load_transactions_clean,
    format_pattern_result,
    build_evidence_item,
    PROJECT_ROOT
)

DEVICES_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "devices_clean.csv"

INVALID_DEVICE_SENTINELS: Set[str] = {
    "", "none", "null", "nan", "0", "unknown", "undefined", "n/a"
}


def load_devices_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    """Loads cleaned devices dataset."""
    path = data_path or DEVICES_CLEAN_PATH
    if not path.exists():
        return pd.DataFrame(columns=['device_id', 'account_count', 'transaction_count', 'device_age_days', 'is_emulator'])
    return pd.read_csv(path)


def is_valid_device_id(dev_id: Any) -> bool:
    """Validates if a device_id is non-null and not a placeholder sentinel."""
    if pd.isnull(dev_id):
        return False
    dev_str = str(dev_id).strip().lower()
    return dev_str not in INVALID_DEVICE_SENTINELS


def detect_device_syndicate(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    devices_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects DEVICE_SYNDICATE pattern for a specific account.

    Parameters:
        account_id: Identifier of the account to investigate.
        transactions_df: Optional transactions dataframe (defaults to loading transactions_clean.csv).
        devices_df: Optional devices metadata dataframe (defaults to loading devices_clean.csv).
        transaction_id: Optional transaction anchor to investigate.
        as_of_timestamp: Optional point-in-time cutoff.
        config: Optional parameter dictionary (score_threshold, window_hours, min_syndicate_accounts).

    Returns:
        Dict adhering to project standard pattern detection schema.
    """
    cfg = config or {}
    score_threshold = float(cfg.get("score_threshold", 50.0))
    window_hours = float(cfg.get("window_hours", 24.0))
    min_syndicate_accounts = int(cfg.get("min_syndicate_accounts", 3))

    raw_account_id = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)

    empty_entities = {
        "account_id": raw_account_id,
        "devices": [],
        "co_accounts": []
    }
    empty_metrics = {
        "max_accounts_per_device": 0,
        "shared_devices_count": 0,
        "emulator_device_detected": False,
        "recent_sharing_24h": 0
    }

    # 1. Load Data
    if transactions_df is None:
        tx_df = load_transactions_clean()
    else:
        tx_df = transactions_df.copy()
        if 'ts' not in tx_df.columns and 'timestamp' in tx_df.columns:
            tx_df['ts'] = pd.to_datetime(tx_df['timestamp'], errors='coerce')

    if devices_df is None:
        d_df = load_devices_clean()
    else:
        d_df = devices_df.copy()

    if tx_df.empty or 'nameOrig' not in tx_df.columns:
        return format_pattern_result(
            "DEVICE_SYNDICATE", False, 0.0, [], empty_entities, [], empty_metrics, "Empty transaction dataframe."
        )

    acc_tx_df = tx_df[tx_df['nameOrig'] == raw_account_id].copy()
    if acc_tx_df.empty:
        return format_pattern_result(
            "DEVICE_SYNDICATE", False, 0.0, [], empty_entities, [], empty_metrics, f"No transactions found for account {raw_account_id}."
        )

    # 2. Point-in-Time Cutoff Determination
    cutoff_ts = None
    if as_of_timestamp is not None:
        cutoff_ts = pd.to_datetime(as_of_timestamp, errors='coerce')

    if transaction_id is not None:
        anchor_tx = acc_tx_df[acc_tx_df['transaction_id'] == transaction_id]
        if not anchor_tx.empty:
            anchor_ts = anchor_tx['ts'].iloc[0]
            if cutoff_ts is None or (pd.notnull(anchor_ts) and anchor_ts < cutoff_ts):
                cutoff_ts = anchor_ts
        else:
            return format_pattern_result(
                "DEVICE_SYNDICATE", False, 0.0, [], empty_entities, [], empty_metrics, f"Transaction {transaction_id} not found."
            )

    # Filter all transactions strictly to eligible history prior to cutoff
    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        eligible_tx_df = tx_df[tx_df['ts'] <= cutoff_ts].copy()
        acc_tx_df = acc_tx_df[acc_tx_df['ts'] <= cutoff_ts].copy()
    else:
        eligible_tx_df = tx_df.copy()

    if acc_tx_df.empty:
        return format_pattern_result(
            "DEVICE_SYNDICATE", False, 0.0, [], empty_entities, [], empty_metrics, "No eligible transactions prior to cutoff."
        )

    # 3. Target Account Devices Selection
    # If transaction_id is provided, focus on the device associated with that transaction
    if transaction_id:
        target_tx_row = acc_tx_df[acc_tx_df['transaction_id'] == transaction_id]
        if not target_tx_row.empty and 'device_id' in target_tx_row.columns:
            target_devices = set(target_tx_row['device_id'].dropna().unique())
        else:
            target_devices = set()
    else:
        if 'device_id' in acc_tx_df.columns:
            target_devices = set(acc_tx_df['device_id'].dropna().unique())
        else:
            target_devices = set()

    # Filter out invalid / sentinel / placeholder device IDs
    valid_target_devices = {d for d in target_devices if is_valid_device_id(d)}

    if not valid_target_devices:
        return format_pattern_result(
            "DEVICE_SYNDICATE", False, 0.0, [], empty_entities, [tx_id for tx_id in acc_tx_df['transaction_id']], empty_metrics, "No valid device identifiers associated with account."
        )

    # 4. Evaluate Sharing for Valid Target Devices Prior to Cutoff
    evidence = []
    max_score = 0.0
    all_co_accounts = set()
    all_relevant_tx_ids = set(acc_tx_df['transaction_id'].unique())
    
    max_accs_observed = 0
    shared_dev_count = 0
    emulator_detected = False
    max_recent_accs_24h = 0

    # Map device emulator status from devices_df if present
    emulator_devices = set()
    if not d_df.empty and 'device_id' in d_df.columns and 'is_emulator' in d_df.columns:
        emulator_devices = set(d_df[d_df['is_emulator'] == 1]['device_id'].astype(str).unique())

    # Build device-to-account mapping from eligible transactions
    valid_eligible_tx = eligible_tx_df[
        eligible_tx_df['device_id'].isin(valid_target_devices)
    ].copy()

    for dev_id in sorted(list(valid_target_devices)):
        dev_txs = valid_eligible_tx[valid_eligible_tx['device_id'] == dev_id].copy()
        
        # Distinct accounts using this device prior to cutoff
        dev_accounts = set(dev_txs['nameOrig'].unique())
        num_accounts = len(dev_accounts)
        
        if num_accounts > 1:
            shared_dev_count += 1
            co_accs = dev_accounts - {raw_account_id}
            all_co_accounts.update(co_accs)
            
        max_accs_observed = max(max_accs_observed, num_accounts)

        # Check temporal concentration (accounts using device within window_hours prior to cutoff or max window)
        dev_recent_accs = 0
        if num_accounts > 1 and not dev_txs.empty and 'ts' in dev_txs.columns:
            dev_txs_sorted = dev_txs.sort_values('ts')
            latest_ts = dev_txs_sorted['ts'].max()
            window_start = latest_ts - pd.Timedelta(hours=window_hours)
            recent_dev_txs = dev_txs_sorted[dev_txs_sorted['ts'] >= window_start]
            dev_recent_accs = recent_dev_txs['nameOrig'].nunique()
            max_recent_accs_24h = max(max_recent_accs_24h, dev_recent_accs)

        # Emulator check
        is_emu = str(dev_id) in emulator_devices
        if is_emu:
            emulator_detected = True

        # Calculate device-level suspicion score
        dev_score = 0.0
        reasons = []

        if num_accounts >= 5:
            dev_score = 85.0
            reasons.append(f"High-density device syndicate: shared across {num_accounts} distinct accounts")
        elif num_accounts >= 3:
            dev_score = 65.0
            reasons.append(f"Moderate device syndicate: shared across {num_accounts} distinct accounts")
        elif num_accounts == 2:
            dev_score = 25.0
            reasons.append(f"Low device sharing: shared across 2 accounts")

        # Temporal concentration booster
        if dev_recent_accs >= 3 and num_accounts >= 3:
            dev_score = max(dev_score, 75.0)
            reasons.append(f"High temporal concentration: {dev_recent_accs} accounts active within {window_hours:.0f}h window")

        # Emulator booster
        if is_emu and num_accounts >= 2:
            dev_score = min(100.0, dev_score + 15.0)
            reasons.append("Device identified as an emulator")

        # Collect evidence if score indicates notable sharing
        if dev_score >= 25.0:
            relevant_txs = list(dev_txs['transaction_id'].unique())
            evidence_type = "HIGH_DEVICE_FANOUT" if num_accounts >= min_syndicate_accounts else "SHARED_DEVICE_WARNING"
            
            evidence.append(build_evidence_item(
                evidence_type=evidence_type,
                description=f"Device {dev_id}: {'; '.join(reasons)}",
                value=num_accounts,
                threshold=min_syndicate_accounts,
                transaction_ids=relevant_txs[:10]  # Traceable transaction IDs
            ))

        if dev_score > max_score:
            max_score = dev_score

    # Multi-device coordination booster: account operates across multiple shared devices
    if shared_dev_count >= 2 and max_score >= 50.0:
        max_score = min(100.0, max_score + 10.0)
        evidence.append(build_evidence_item(
            evidence_type="MULTI_SHARED_DEVICE_COORDINATION",
            description=f"Account operates across {shared_dev_count} distinct shared devices",
            value=shared_dev_count,
            threshold=2,
            transaction_ids=list(all_relevant_tx_ids)[:10]
        ))

    detected = max_score >= score_threshold

    if detected:
        explanation = f"Detected device syndicate activity on device(s) shared across up to {max_accs_observed} accounts."
    elif shared_dev_count > 0:
        explanation = f"Low-risk shared device detected ({max_accs_observed} account(s)), below syndicate threshold."
    else:
        explanation = "No suspicious device sharing detected."

    metrics = {
        "max_accounts_per_device": max_accs_observed,
        "shared_devices_count": shared_dev_count,
        "emulator_device_detected": emulator_detected,
        "recent_sharing_24h": max_recent_accs_24h
    }

    entities = {
        "account_id": raw_account_id,
        "devices": list(valid_target_devices),
        "co_accounts": list(all_co_accounts)
    }

    return format_pattern_result(
        pattern_name="DEVICE_SYNDICATE",
        detected=detected,
        score=max_score,
        evidence=evidence,
        entities=entities,
        transactions=list(all_relevant_tx_ids),
        metrics=metrics,
        explanation=explanation
    )
