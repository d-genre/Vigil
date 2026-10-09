"""
FRAUD-RING RADAR
CARD_TESTING Fraud Pattern Detector (backend/fraud_patterns/card_testing.py)

Detects high-velocity, small-amount payment authorization testing clusters on accounts.
Supports point-in-time investigation without label dependency.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from .common import (
    load_transactions_clean,
    format_pattern_result,
    build_evidence_item
)

DEFAULT_WINDOW_MINUTES = 5.0
DEFAULT_SMALL_AMOUNT_MAX = 10.00
DEFAULT_MIN_ATTEMPTS = 4
DEFAULT_MIN_SMALL_ATTEMPTS = 3


def detect_card_testing(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects Card Testing pattern for a specific account.
    
    Parameters:
      account_id: Target account identifier (e.g. 'C0000340' or 'ACCOUNT:C0000340')
      transactions_df: Optional DataFrame of transactions. If None, loads clean transactions.
      transaction_id: Optional anchor transaction ID for investigation.
      as_of_timestamp: Point-in-time upper bound timestamp.
      config: Optional custom threshold overrides (window_minutes, small_amount_max, min_attempts).
    """
    cfg = config or {}
    window_minutes = float(cfg.get("window_minutes", DEFAULT_WINDOW_MINUTES))
    small_amount_max = float(cfg.get("small_amount_max", DEFAULT_SMALL_AMOUNT_MAX))
    min_attempts = int(cfg.get("min_attempts", DEFAULT_MIN_ATTEMPTS))
    min_small_attempts = int(cfg.get("min_small_attempts", DEFAULT_MIN_SMALL_ATTEMPTS))

    # Clean account prefix if present
    raw_account_id = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)
    
    # Load dataset if not provided
    if transactions_df is None:
        df = load_transactions_clean()
    else:
        df = transactions_df.copy()
        if 'ts' not in df.columns and 'timestamp' in df.columns:
            df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # Default empty output schema
    empty_entities = {
        "account_id": raw_account_id,
        "devices": [],
        "ips": [],
        "merchants": []
    }
    empty_metrics = {
        "window_duration_minutes": window_minutes,
        "attempt_count": 0,
        "small_amount_count": 0,
        "failed_or_declined_count": 0,
        "min_amount": 0.0,
        "max_amount": 0.0,
        "total_amount": 0.0,
        "first_timestamp": None,
        "last_timestamp": None
    }

    if df.empty or 'nameOrig' not in df.columns:
        return format_pattern_result(
            pattern_name="CARD_TESTING",
            detected=False,
            score=0.0,
            evidence=[],
            entities=empty_entities,
            transactions=[],
            metrics=empty_metrics,
            explanation=f"No transactions found for account {raw_account_id}."
        )

    # Filter account transactions
    acc_df = df[df['nameOrig'] == raw_account_id].copy()
    if 'ts' in acc_df.columns:
        acc_df = acc_df.dropna(subset=['ts'])

    if acc_df.empty:
        return format_pattern_result(
            pattern_name="CARD_TESTING",
            detected=False,
            score=0.0,
            evidence=[],
            entities=empty_entities,
            transactions=[],
            metrics=empty_metrics,
            explanation=f"No transactions found for account {raw_account_id}."
        )

    # Determine Point-in-Time Cutoff
    cutoff_ts = None
    if as_of_timestamp is not None:
        cutoff_ts = pd.to_datetime(as_of_timestamp, errors='coerce')
    elif transaction_id is not None:
        anchor_tx = acc_df[acc_df['transaction_id'] == transaction_id]
        if not anchor_tx.empty:
            cutoff_ts = anchor_tx['ts'].iloc[0]

    # Apply strict Point-in-Time filtering: timestamp <= cutoff_ts
    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        acc_df = acc_df[acc_df['ts'] <= cutoff_ts]

    if acc_df.empty:
        return format_pattern_result(
            pattern_name="CARD_TESTING",
            detected=False,
            score=0.0,
            evidence=[],
            entities=empty_entities,
            transactions=[],
            metrics=empty_metrics,
            explanation=f"No point-in-time transactions found for account {raw_account_id} as of {cutoff_ts}."
        )

    # Sort chronologically
    acc_df = acc_df.sort_values('ts')
    timestamps = acc_df['ts'].values
    amounts = acc_df['amount'].values
    tx_ids = acc_df['transaction_id'].values
    statuses = acc_df['status'].values if 'status' in acc_df.columns else np.array(['SUCCESS'] * len(acc_df))
    devices = acc_df['device_id'].dropna().unique().tolist() if 'device_id' in acc_df.columns else []
    ips = acc_df['ip_address'].dropna().unique().tolist() if 'ip_address' in acc_df.columns else []
    
    # Exclude NOMERCH from merchant entities
    merchants = []
    if 'merchant_id' in acc_df.columns:
        raw_merchs = acc_df['merchant_id'].dropna().unique()
        merchants = [str(m) for m in raw_merchs if str(m).upper() != 'NOMERCH']

    # Search sliding windows ending at each transaction
    best_window_txs = []
    best_score = 0.0
    best_evidence = []
    best_metrics = empty_metrics.copy()
    detected = False

    n_txs = len(timestamps)
    for i in range(n_txs):
        win_end = timestamps[i]
        win_start = win_end - np.timedelta64(int(window_minutes * 60), 's')
        
        mask = (timestamps >= win_start) & (timestamps <= win_end)
        win_indices = np.where(mask)[0]
        
        win_tx_ids = tx_ids[win_indices].tolist()
        win_amounts = amounts[win_indices]
        win_statuses = statuses[win_indices]
        win_ts = timestamps[win_indices]

        attempt_count = len(win_tx_ids)
        small_count = int((win_amounts <= small_amount_max).sum())
        failed_count = int(np.isin(win_statuses, ['FAILED', 'DECLINED']).sum())
        
        # Check rule thresholds
        if attempt_count >= min_attempts and small_count >= min_small_attempts:
            detected = True
            
            # Deterministic Score Calculation
            # 1. Attempt count base (50 for min_attempts, up to 75)
            attempt_score = min(75.0, 50.0 + (attempt_count - min_attempts) * 5.0)
            
            # 2. Small amount concentration addon (up to 20 points)
            small_ratio = small_count / max(1, attempt_count)
            small_score = small_ratio * 20.0
            
            # 3. Failed/Declined attempt addon (up to 10 points)
            failed_ratio = failed_count / max(1, attempt_count)
            failed_score = failed_ratio * 10.0
            
            calc_score = attempt_score + small_score + failed_score
            
            if calc_score > best_score:
                best_score = calc_score
                best_window_txs = win_tx_ids
                
                # Format evidence items
                best_evidence = [
                    build_evidence_item(
                        evidence_type="CARD_TESTING_VELOCITY",
                        description=f"{attempt_count} payment attempts occurred within a {window_minutes}-minute window.",
                        value=attempt_count,
                        threshold=min_attempts,
                        transaction_ids=win_tx_ids
                    ),
                    build_evidence_item(
                        evidence_type="SMALL_AMOUNT_CLUSTER",
                        description=f"{small_count} of {attempt_count} attempts were <= ₹{small_amount_max:.2f}.",
                        value=small_count,
                        threshold=min_small_attempts,
                        transaction_ids=win_tx_ids
                    )
                ]
                if failed_count > 0:
                    best_evidence.append(
                        build_evidence_item(
                            evidence_type="FAILED_ATTEMPTS_PRESENT",
                            description=f"{failed_count} attempts were FAILED or DECLINED.",
                            value=failed_count,
                            threshold=1,
                            transaction_ids=win_tx_ids
                        )
                    )
                    
                best_metrics = {
                    "window_duration_minutes": round(float((win_ts[-1] - win_ts[0]) / np.timedelta64(1, 'm')), 2),
                    "attempt_count": attempt_count,
                    "small_amount_count": small_count,
                    "failed_or_declined_count": failed_count,
                    "min_amount": float(np.min(win_amounts)),
                    "max_amount": float(np.max(win_amounts)),
                    "total_amount": float(np.sum(win_amounts)),
                    "first_timestamp": pd.to_datetime(win_ts[0]).strftime("%Y-%m-%d %H:%M:%S"),
                    "last_timestamp": pd.to_datetime(win_ts[-1]).strftime("%Y-%m-%d %H:%M:%S")
                }

    entities = {
        "account_id": raw_account_id,
        "devices": devices,
        "ips": ips,
        "merchants": merchants
    }

    if detected:
        explanation = (
            f"Detected CARD_TESTING on account {raw_account_id}: "
            f"{best_metrics['attempt_count']} attempts ({best_metrics['small_amount_count']} <= ₹{small_amount_max:.2f}) "
            f"within a {best_metrics['window_duration_minutes']}-minute window."
        )
    else:
        explanation = f"No CARD_TESTING pattern detected on account {raw_account_id}."

    return format_pattern_result(
        pattern_name="CARD_TESTING",
        detected=detected,
        score=best_score,
        evidence=best_evidence,
        entities=entities,
        transactions=best_window_txs,
        metrics=best_metrics,
        explanation=explanation
    )
