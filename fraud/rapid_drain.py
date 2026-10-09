"""
FRAUD-RING RADAR
Rapid Drain / Beneficiary Abuse Fraud Pattern Detector (backend/fraud_patterns/rapid_drain.py)

Identifies RAPID_DRAIN and BENEFICIARY_ABUSE patterns where an account experiences
a sudden high-ratio depletion of funds or large outgoing transfers shortly following
the addition of a new beneficiary, under strict point-in-time and label-independent safeguards.
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

EVENTS_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "events_clean.csv"
ACCOUNTS_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "accounts_clean.csv"
BENEFICIARIES_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "beneficiaries_clean.csv"

OUTGOING_TYPES: Set[str] = {"TRANSFER", "CASH_OUT", "PAYMENT", "DEBIT"}


def load_events_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    path = data_path or EVENTS_CLEAN_PATH
    if not path.exists():
        return pd.DataFrame(columns=['event_id', 'timestamp', 'account_id', 'event_type'])
    df = pd.read_csv(path)
    df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df


def load_accounts_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    path = data_path or ACCOUNTS_CLEAN_PATH
    if not path.exists():
        return pd.DataFrame(columns=['account_id', 'monthly_income', 'avg_transaction_amount'])
    return pd.read_csv(path)


def load_beneficiaries_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    path = data_path or BENEFICIARIES_CLEAN_PATH
    if not path.exists():
        return pd.DataFrame(columns=['beneficiary_id', 'account_id', 'beneficiary_account', 'created_at'])
    df = pd.read_csv(path)
    df['ts'] = pd.to_datetime(df['created_at'], errors='coerce')
    return df


def detect_rapid_drain(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    events_df: Optional[pd.DataFrame] = None,
    accounts_df: Optional[pd.DataFrame] = None,
    beneficiaries_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects RAPID_DRAIN / BENEFICIARY_ABUSE pattern for a specific account.

    Parameters:
        account_id: Identifier of the account to investigate.
        transactions_df: Optional transactions dataframe.
        events_df: Optional security events dataframe.
        accounts_df: Optional account profile dataframe.
        beneficiaries_df: Optional beneficiary records dataframe.
        transaction_id: Optional transaction anchor.
        as_of_timestamp: Optional point-in-time cutoff.
        config: Optional parameters dict (score_threshold, window_hours, drain_ratio_threshold, benef_window_hours).

    Returns:
        Dict adhering to standard pattern detection schema.
    """
    cfg = config or {}
    score_threshold = float(cfg.get("score_threshold", 50.0))
    window_hours = float(cfg.get("window_hours", 1.0))
    benef_window_hours = float(cfg.get("benef_window_hours", 24.0))
    drain_ratio_threshold = float(cfg.get("drain_ratio_threshold", 0.8))

    raw_account_id = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)

    empty_entities = {
        "account_id": raw_account_id,
        "beneficiaries": [],
        "destinations": []
    }
    empty_metrics = {
        "drain_ratio_1h": 0.0,
        "outgoing_sum_1h": 0.0,
        "beneficiary_added_24h": False,
        "distinct_recipients_1h": 0
    }

    # 1. Load Data
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

    if accounts_df is None:
        acc_meta_df = load_accounts_clean()
    else:
        acc_meta_df = accounts_df.copy()

    if beneficiaries_df is None:
        ben_df = load_beneficiaries_clean()
    else:
        ben_df = beneficiaries_df.copy()
        if 'ts' not in ben_df.columns and 'created_at' in ben_df.columns:
            ben_df['ts'] = pd.to_datetime(ben_df['created_at'], errors='coerce')

    if tx_df.empty or 'nameOrig' not in tx_df.columns:
        return format_pattern_result(
            "RAPID_DRAIN", False, 0.0, [], empty_entities, [], empty_metrics, "Empty transaction dataframe."
        )

    acc_tx_df = tx_df[tx_df['nameOrig'] == raw_account_id].copy()
    if acc_tx_df.empty:
        return format_pattern_result(
            "RAPID_DRAIN", False, 0.0, [], empty_entities, [], empty_metrics, f"No transactions found for account {raw_account_id}."
        )

    # Get account income / baseline
    monthly_income = 5000.0  # Default baseline fallback
    if not acc_meta_df.empty and 'account_id' in acc_meta_df.columns:
        acc_meta = acc_meta_df[acc_meta_df['account_id'] == raw_account_id]
        if not acc_meta.empty:
            val = acc_meta['monthly_income'].iloc[0]
            if pd.notnull(val) and float(val) > 0:
                monthly_income = float(val)

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
                "RAPID_DRAIN", False, 0.0, [], empty_entities, [], empty_metrics, f"Transaction {transaction_id} not found."
            )

    # Filter all DataFrames strictly to eligible prior history
    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        acc_tx_df = acc_tx_df[acc_tx_df['ts'] <= cutoff_ts].copy()
        if not ev_df.empty and 'ts' in ev_df.columns:
            ev_df = ev_df[ev_df['ts'] <= cutoff_ts].copy()
        if not ben_df.empty and 'ts' in ben_df.columns:
            ben_df = ben_df[ben_df['ts'] <= cutoff_ts].copy()

    if acc_tx_df.empty:
        return format_pattern_result(
            "RAPID_DRAIN", False, 0.0, [], empty_entities, [], empty_metrics, "No eligible transactions prior to cutoff."
        )

    acc_tx_df = acc_tx_df.dropna(subset=['ts']).sort_values('ts')

    # 3. Security Events & Beneficiary Additions Check
    acc_events = ev_df[ev_df['account_id'] == raw_account_id] if not ev_df.empty and 'account_id' in ev_df.columns else pd.DataFrame()
    acc_bens = ben_df[ben_df['account_id'] == raw_account_id] if not ben_df.empty and 'account_id' in ben_df.columns else pd.DataFrame()

    benef_addition_ts_list = []
    if not acc_events.empty and 'event_type' in acc_events.columns:
        benef_events = acc_events[acc_events['event_type'] == 'BENEFICIARY_ADDED']
        if not benef_events.empty:
            benef_addition_ts_list.extend(benef_events['ts'].dropna().tolist())

    if not acc_bens.empty and 'ts' in acc_bens.columns:
        benef_addition_ts_list.extend(acc_bens['ts'].dropna().tolist())

    # 4. Outgoing Transactions & Drain Calculation
    outgoing_tx = acc_tx_df[acc_tx_df['type'].isin(OUTGOING_TYPES)].copy() if 'type' in acc_tx_df.columns else acc_tx_df.copy()

    if outgoing_tx.empty:
        return format_pattern_result(
            "RAPID_DRAIN", False, 0.0, [], empty_entities, [tx_id for tx_id in acc_tx_df['transaction_id']], empty_metrics, "No outgoing transactions found for account."
        )

    evidence = []
    max_score = 0.0
    max_drain_ratio = 0.0
    max_outgoing_sum_1h = 0.0
    beneficiary_added_24h_flag = False
    max_destinations_count = 0
    all_destinations = set()
    all_beneficiaries = set()
    all_relevant_tx_ids = set(acc_tx_df['transaction_id'].unique())

    if not acc_bens.empty and 'beneficiary_account' in acc_bens.columns:
        all_beneficiaries = set(acc_bens['beneficiary_account'].dropna().unique())

    # Timestamps to evaluate
    eval_timestamps = [anchor_ts] if (transaction_id and anchor_ts and pd.notnull(anchor_ts)) else outgoing_tx['ts'].unique()

    tss = outgoing_tx['ts'].values
    amts = outgoing_tx['amount'].values if 'amount' in outgoing_tx.columns else np.zeros(len(outgoing_tx))
    tx_ids = outgoing_tx['transaction_id'].values
    dests = outgoing_tx['nameDest'].values if 'nameDest' in outgoing_tx.columns else np.array([""] * len(outgoing_tx))

    for cur_t in eval_timestamps:
        if pd.isnull(cur_t):
            continue
        cur_t_dt = pd.to_datetime(cur_t)

        # 1-hour rolling window [cur_t - 1h, cur_t]
        mask_1h = (tss <= cur_t_dt) & (tss >= cur_t_dt - pd.Timedelta(hours=window_hours))
        if not mask_1h.any():
            continue

        sum_1h = float(amts[mask_1h].sum())
        txs_1h = list(tx_ids[mask_1h])
        dests_1h = set(dests[mask_1h]) - {""}
        all_destinations.update(dests_1h)

        drain_ratio = float(sum_1h / monthly_income) if monthly_income > 0 else 0.0

        max_outgoing_sum_1h = max(max_outgoing_sum_1h, sum_1h)
        max_drain_ratio = max(max_drain_ratio, drain_ratio)
        max_destinations_count = max(max_destinations_count, len(dests_1h))

        # Check beneficiary addition within 24h prior to cur_t_dt
        recent_benef_added = False
        for b_ts in benef_addition_ts_list:
            if b_ts <= cur_t_dt and (cur_t_dt - b_ts) <= pd.Timedelta(hours=benef_window_hours):
                recent_benef_added = True
                beneficiary_added_24h_flag = True
                break

        # Calculate score for this window
        window_score = 0.0
        reasons = []

        if drain_ratio >= 2.0:
            window_score = 85.0
            reasons.append(f"Extreme rapid account drain: ${sum_1h:,.2f} outgoing in {window_hours:.0f}h ({drain_ratio*100:.0f}% of monthly income)")
        elif drain_ratio >= drain_ratio_threshold:
            window_score = 70.0
            reasons.append(f"High rapid account drain: ${sum_1h:,.2f} outgoing in {window_hours:.0f}h ({drain_ratio*100:.0f}% of monthly income)")
        elif drain_ratio >= 0.4:
            window_score = 40.0
            reasons.append(f"Moderate account drain ratio: {drain_ratio*100:.0f}% of monthly income in {window_hours:.0f}h")

        # Beneficiary Abuse booster / interaction
        if recent_benef_added:
            if drain_ratio >= 0.5:
                window_score = max(window_score, 90.0)
                reasons.append(f"Beneficiary abuse: rapid funds drain shortly following beneficiary addition within {benef_window_hours:.0f}h")
            else:
                window_score = min(100.0, window_score + 25.0)
                reasons.append(f"Outgoing transfer shortly following beneficiary addition within {benef_window_hours:.0f}h")

        # Multi-recipient destination booster
        if len(dests_1h) >= 3 and drain_ratio >= 0.5:
            window_score = min(100.0, window_score + 10.0)
            reasons.append(f"Multi-recipient rapid drain: funds split across {len(dests_1h)} distinct destination accounts")

        if window_score > max_score:
            max_score = window_score

        if window_score >= 40.0 and reasons:
            evidence_type = "BENEFICIARY_DRAIN_ABUSE" if recent_benef_added else "RAPID_ACCOUNT_DRAIN"
            evidence.append(build_evidence_item(
                evidence_type=evidence_type,
                description=f"Drain event at {cur_t_dt.strftime('%Y-%m-%d %H:%M:%S')}: {'; '.join(reasons)}",
                value=round(drain_ratio, 2),
                threshold=drain_ratio_threshold,
                transaction_ids=txs_1h
            ))

    detected = max_score >= score_threshold

    if detected:
        explanation = f"Detected rapid account drain / beneficiary abuse with peak drain ratio {max_drain_ratio*100:.0f}% and ${max_outgoing_sum_1h:,.2f} outgoing in {window_hours:.0f}h."
    elif max_drain_ratio > 0:
        explanation = f"Low account drain ratio ({max_drain_ratio*100:.0f}%), below risk threshold."
    else:
        explanation = "No rapid account drain detected."

    metrics = {
        "drain_ratio_1h": float(round(max_drain_ratio, 2)),
        "outgoing_sum_1h": float(round(max_outgoing_sum_1h, 2)),
        "beneficiary_added_24h": beneficiary_added_24h_flag,
        "distinct_recipients_1h": max_destinations_count
    }

    entities = {
        "account_id": raw_account_id,
        "beneficiaries": list(all_beneficiaries),
        "destinations": list(all_destinations)
    }

    return format_pattern_result(
        pattern_name="RAPID_DRAIN",
        detected=detected,
        score=max_score,
        evidence=evidence,
        entities=entities,
        transactions=list(all_relevant_tx_ids),
        metrics=metrics,
        explanation=explanation
    )
