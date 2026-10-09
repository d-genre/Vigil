"""
FRAUD-RING RADAR
Velocity Burst Fraud Pattern Detector (backend/fraud_patterns/velocity_burst.py)

Identifies VELOCITY_BURST patterns where an account exhibits abnormal high-frequency
transaction volume or rapid cumulative spending spikes within short temporal windows (e.g. 5m, 1h),
under strict point-in-time and label-independent safeguards.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

from .common import (
    load_transactions_clean,
    format_pattern_result,
    build_evidence_item,
    PROJECT_ROOT
)


def detect_velocity_burst(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects VELOCITY_BURST pattern for a specific account.

    Parameters:
        account_id: Identifier of the account to investigate.
        transactions_df: Optional transactions dataframe (defaults to loading transactions_clean.csv).
        transaction_id: Optional transaction anchor to investigate.
        as_of_timestamp: Optional point-in-time cutoff.
        config: Optional parameter dictionary (score_threshold, count_5m_threshold, count_1h_threshold, amount_1h_threshold).

    Returns:
        Dict adhering to project standard pattern detection schema.
    """
    cfg = config or {}
    score_threshold = float(cfg.get("score_threshold", 50.0))
    threshold_5m_count = int(cfg.get("threshold_5m_count", 5))
    threshold_1h_count = int(cfg.get("threshold_1h_count", 6))
    threshold_1h_amount = float(cfg.get("threshold_1h_amount", 25000.0))

    raw_account_id = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)

    empty_entities = {
        "account_id": raw_account_id
    }
    empty_metrics = {
        "max_tx_count_5m": 0,
        "max_tx_count_1h": 0,
        "max_amount_sum_1h": 0.0
    }

    # 1. Load Data
    if transactions_df is None:
        tx_df = load_transactions_clean()
    else:
        tx_df = transactions_df.copy()
        if 'ts' not in tx_df.columns and 'timestamp' in tx_df.columns:
            tx_df['ts'] = pd.to_datetime(tx_df['timestamp'], errors='coerce')

    if tx_df.empty or 'nameOrig' not in tx_df.columns:
        return format_pattern_result(
            "VELOCITY_BURST", False, 0.0, [], empty_entities, [], empty_metrics, "Empty transaction dataframe."
        )

    acc_tx_df = tx_df[tx_df['nameOrig'] == raw_account_id].copy()
    if acc_tx_df.empty:
        return format_pattern_result(
            "VELOCITY_BURST", False, 0.0, [], empty_entities, [], empty_metrics, f"No transactions found for account {raw_account_id}."
        )

    # 2. Point-in-Time Cutoff Determination
    cutoff_ts = None
    if as_of_timestamp is not None:
        cutoff_ts = pd.to_datetime(as_of_timestamp, errors='coerce')

    anchor_ts = None
    if transaction_id is not None:
        anchor_tx = acc_tx_df[acc_tx_df['transaction_id'] == transaction_id]
        if not anchor_tx.empty:
            anchor_ts = anchor_tx['ts'].iloc[0]
            if cutoff_ts is None or (pd.notnull(anchor_ts) and anchor_ts < cutoff_ts):
                cutoff_ts = anchor_ts
        else:
            return format_pattern_result(
                "VELOCITY_BURST", False, 0.0, [], empty_entities, [], empty_metrics, f"Transaction {transaction_id} not found."
            )

    # Filter strictly to eligible transactions prior to cutoff
    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        acc_tx_df = acc_tx_df[acc_tx_df['ts'] <= cutoff_ts].copy()

    if acc_tx_df.empty:
        return format_pattern_result(
            "VELOCITY_BURST", False, 0.0, [], empty_entities, [], empty_metrics, "No eligible transactions prior to cutoff."
        )

    acc_tx_df = acc_tx_df.dropna(subset=['ts']).sort_values('ts')
    
    # 3. Calculate Rolling Velocity Windows
    evidence = []
    max_score = 0.0
    max_5m_count = 0
    max_1h_count = 0
    max_1h_amount = 0.0
    all_relevant_tx_ids = set(acc_tx_df['transaction_id'].unique())

    # If anchor transaction_id is provided, evaluate velocity ending at anchor_ts
    # Otherwise, evaluate peak velocity across all timestamps prior to cutoff
    eval_timestamps = [anchor_ts] if (transaction_id and anchor_ts and pd.notnull(anchor_ts)) else acc_tx_df['ts'].unique()

    tss = acc_tx_df['ts'].values
    amts = acc_tx_df['amount'].values if 'amount' in acc_tx_df.columns else np.zeros(len(acc_tx_df))
    tx_ids = acc_tx_df['transaction_id'].values

    for cur_t in eval_timestamps:
        if pd.isnull(cur_t):
            continue
        cur_t_dt = pd.to_datetime(cur_t)

        # 5-minute window [cur_t - 5m, cur_t]
        mask_5m = (tss <= cur_t_dt) & (tss >= cur_t_dt - pd.Timedelta(minutes=5))
        count_5m = int(mask_5m.sum())
        txs_5m = list(tx_ids[mask_5m])

        # 1-hour window [cur_t - 1h, cur_t]
        mask_1h = (tss <= cur_t_dt) & (tss >= cur_t_dt - pd.Timedelta(hours=1))
        count_1h = int(mask_1h.sum())
        amount_1h = float(amts[mask_1h].sum())
        txs_1h = list(tx_ids[mask_1h])

        max_5m_count = max(max_5m_count, count_5m)
        max_1h_count = max(max_1h_count, count_1h)
        max_1h_amount = max(max_1h_amount, amount_1h)

        # Score calculations for this timestamp
        window_score = 0.0
        reasons = []

        # 5-minute count rule
        if count_5m >= threshold_5m_count:
            window_score = max(window_score, 75.0)
            reasons.append(f"Short-window velocity burst: {count_5m} transactions in 5 minutes (Threshold: {threshold_5m_count})")
        elif count_5m >= 3:
            window_score = max(window_score, 45.0)
            reasons.append(f"Elevated 5-minute transaction activity: {count_5m} transactions")

        # 1-hour count rule
        if count_1h >= 10:
            window_score = max(window_score, 85.0)
            reasons.append(f"High-frequency 1-hour velocity: {count_1h} transactions in 1 hour (Threshold: 10)")
        elif count_1h >= threshold_1h_count:
            window_score = max(window_score, 65.0)
            reasons.append(f"Elevated 1-hour transaction velocity: {count_1h} transactions in 1 hour (Threshold: {threshold_1h_count})")
        elif count_1h >= 4:
            window_score = max(window_score, 30.0)

        # 1-hour cumulative amount rule
        if amount_1h >= 50000.0:
            window_score = max(window_score, 85.0)
            reasons.append(f"Extreme cumulative volume spike: ${amount_1h:,.2f} spent in 1 hour (Threshold: $50,000.00)")
        elif amount_1h >= threshold_1h_amount:
            window_score = max(window_score, 65.0)
            reasons.append(f"High cumulative volume spike: ${amount_1h:,.2f} spent in 1 hour (Threshold: ${threshold_1h_amount:,.2f})")

        # Combined multi-window acceleration boost
        if count_5m >= 4 and amount_1h >= threshold_1h_amount:
            window_score = min(100.0, window_score + 15.0)
            reasons.append("Combined high-frequency and high-volume burst acceleration")

        if window_score > max_score:
            max_score = window_score

        if window_score >= 45.0 and reasons:
            evidence_type = "HIGH_VELOCITY_BURST" if window_score >= 60.0 else "ELEVATED_TRANSACTION_FREQUENCY"
            evidence.append(build_evidence_item(
                evidence_type=evidence_type,
                description=f"Velocity burst at {cur_t_dt.strftime('%Y-%m-%d %H:%M:%S')}: {'; '.join(reasons)}",
                value=count_5m,
                threshold=threshold_5m_count,
                transaction_ids=txs_5m if count_5m >= 3 else txs_1h
            ))

    detected = max_score >= score_threshold

    if detected:
        explanation = f"Detected velocity burst with peak {max_5m_count} tx/5m, {max_1h_count} tx/1h, and ${max_1h_amount:,.2f} volume in 1h."
    elif max_5m_count > 1 or max_1h_count > 1:
        explanation = f"Low velocity activity ({max_5m_count} tx/5m, {max_1h_count} tx/1h), below risk threshold."
    else:
        explanation = "No velocity burst detected."

    metrics = {
        "max_tx_count_5m": max_5m_count,
        "max_tx_count_1h": max_1h_count,
        "max_amount_sum_1h": float(round(max_1h_amount, 2))
    }

    return format_pattern_result(
        pattern_name="VELOCITY_BURST",
        detected=detected,
        score=max_score,
        evidence=evidence,
        entities=empty_entities,
        transactions=list(all_relevant_tx_ids),
        metrics=metrics,
        explanation=explanation
    )
