"""
FRAUD-RING RADAR
MULE_CHAIN Fraud Pattern Detector (backend/fraud_patterns/mule_chain.py)

Detects suspicious network money-flow structures where an intermediary account 
receives funds from one or more upstream source accounts and subsequently transfers 
or forwards funds onward to downstream recipient accounts.

Operates deterministically without relying on fraud labels.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Set, Tuple
import numpy as np
import pandas as pd

from .common import (
    load_transactions_clean,
    format_pattern_result,
    build_evidence_item,
    PROJECT_ROOT
)

DEFAULT_WINDOW_HOURS = 48.0
DEFAULT_SCORE_THRESHOLD = 50.0
DEFAULT_MAX_PATH_LENGTH = 3

def detect_mule_chain(
    account_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    transactions_df: Optional[pd.DataFrame] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects MULE_CHAIN money-flow pattern for a target account or anchor transaction.

    Parameters:
      account_id: Target account identifier (e.g. 'C0006865' or 'ACCOUNT:C0006865').
      transaction_id: Optional anchor transaction ID.
      as_of_timestamp: Optional point-in-time upper bound timestamp.
      transactions_df: Optional DataFrame of transactions. If None, loads clean transactions.
      config: Custom configuration overrides (window_hours, score_threshold, max_path_length).
    """
    cfg = config or {}
    window_hours = float(cfg.get("window_hours", DEFAULT_WINDOW_HOURS))
    score_threshold = float(cfg.get("score_threshold", DEFAULT_SCORE_THRESHOLD))
    max_path_length = int(cfg.get("max_path_length", DEFAULT_MAX_PATH_LENGTH))

    # Load dataset
    if transactions_df is None:
        df = load_transactions_clean()
    else:
        df = transactions_df.copy()
        if 'ts' not in df.columns and 'timestamp' in df.columns:
            df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # Resolve account_id if only transaction_id is provided
    target_account = None
    if account_id is not None:
        target_account = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)
    elif transaction_id is not None and not df.empty and 'transaction_id' in df.columns:
        match_tx = df[df['transaction_id'] == transaction_id]
        if not match_tx.empty:
            target_account = str(match_tx['nameOrig'].iloc[0])

    empty_entities = {
        "target_account": target_account or "",
        "upstream_accounts": [],
        "downstream_accounts": [],
        "devices": [],
        "ips": []
    }

    empty_metrics = {
        "unique_upstream_senders": 0,
        "unique_downstream_recipients": 0,
        "incoming_count": 0,
        "outgoing_count": 0,
        "total_incoming_amount": 0.0,
        "total_outgoing_amount": 0.0,
        "flow_through_ratio": 0.0,
        "flow_through_pairs_count": 0,
        "min_time_diff_minutes": None
    }

    if df.empty or target_account is None:
        return _build_result(
            detected=False, score=0.0, evidence=[], entities=empty_entities,
            transactions=[], metrics=empty_metrics, paths=[],
            account_id=target_account, transaction_id=transaction_id,
            as_of_timestamp=as_of_timestamp,
            explanation=f"No valid account specified or transactions dataset is empty."
        )

    # Determine Point-in-Time Cutoff
    cutoff_ts = None
    if as_of_timestamp is not None:
        cutoff_ts = pd.to_datetime(as_of_timestamp, errors='coerce')
    elif transaction_id is not None and not df.empty:
        anchor_tx = df[df['transaction_id'] == transaction_id]
        if not anchor_tx.empty:
            cutoff_ts = anchor_tx['ts'].iloc[0]

    # Apply strict Point-in-Time filtering: timestamp <= cutoff_ts
    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        df = df[df['ts'] <= cutoff_ts].copy()

    if df.empty:
        return _build_result(
            detected=False, score=0.0, evidence=[], entities=empty_entities,
            transactions=[], metrics=empty_metrics, paths=[],
            account_id=target_account, transaction_id=transaction_id,
            as_of_timestamp=as_of_timestamp,
            explanation=f"No point-in-time transactions available as of {cutoff_ts} for account {target_account}."
        )

    if cutoff_ts is None or pd.isnull(cutoff_ts):
        cutoff_ts = df['ts'].max()

    window_start = cutoff_ts - pd.Timedelta(hours=window_hours)

    # Filter P2P account transfers (nameDest starts with 'C' and nameOrig != nameDest)
    p2p_df = df[
        df['nameDest'].astype(str).str.startswith('C') & 
        (df['nameOrig'] != df['nameDest'])
    ].copy()

    # Incoming to target_account within evaluation window
    inc_df = p2p_df[
        (p2p_df['nameDest'] == target_account) & 
        (p2p_df['ts'] >= window_start) & 
        (p2p_df['ts'] <= cutoff_ts)
    ].sort_values('ts')

    # Outgoing from target_account within evaluation window
    out_df = p2p_df[
        (p2p_df['nameOrig'] == target_account) & 
        (p2p_df['ts'] >= window_start) & 
        (p2p_df['ts'] <= cutoff_ts)
    ].sort_values('ts')

    # Collect unique counterparties
    upstream_senders = sorted(inc_df['nameOrig'].dropna().unique().tolist()) if not inc_df.empty else []
    downstream_recipients = sorted(out_df['nameDest'].dropna().unique().tolist()) if not out_df.empty else []

    inc_count = len(inc_df)
    out_count = len(out_df)
    inc_amount = float(inc_df['amount'].sum()) if inc_count > 0 else 0.0
    out_amount = float(out_df['amount'].sum()) if out_count > 0 else 0.0
    flow_ratio = float(out_amount / inc_amount) if inc_amount > 0 else 0.0

    # Devices & IPs associated with these transactions
    all_account_txs = pd.concat([inc_df, out_df]).drop_duplicates(subset=['transaction_id']) if (inc_count > 0 or out_count > 0) else pd.DataFrame()
    devices = sorted(all_account_txs['device_id'].dropna().unique().tolist()) if not all_account_txs.empty and 'device_id' in all_account_txs.columns else []
    ips = sorted(all_account_txs['ip_address'].dropna().unique().tolist()) if not all_account_txs.empty and 'ip_address' in all_account_txs.columns else []
    tx_ids = sorted(all_account_txs['transaction_id'].tolist()) if not all_account_txs.empty else []

    # Find Flow-Through Pairs and Build Paths (A -> M -> C)
    flow_pairs = []
    paths = []
    min_time_diff_min = None

    if inc_count > 0 and out_count > 0:
        for inc_row in inc_df.itertuples():
            inc_sender = str(inc_row.nameOrig)
            inc_t = inc_row.ts
            inc_amt = float(inc_row.amount)
            inc_id = str(inc_row.transaction_id)

            # Match with subsequent outgoing transactions within window_hours
            matching_out = out_df[out_df['ts'] >= inc_t]
            for out_row in matching_out.itertuples():
                out_recip = str(out_row.nameDest)
                if out_recip == inc_sender:
                    continue # Skip simple back-and-forth round trip
                
                out_t = out_row.ts
                out_amt = float(out_row.amount)
                out_id = str(out_row.transaction_id)

                diff_sec = (out_t - inc_t).total_seconds()
                diff_min = diff_sec / 60.0

                if diff_sec <= window_hours * 3600.0:
                    flow_pairs.append((inc_id, out_id, diff_min))
                    if min_time_diff_min is None or diff_min < min_time_diff_min:
                        min_time_diff_min = diff_min

                    paths.append({
                        "path_nodes": [inc_sender, target_account, out_recip],
                        "transaction_ids": [inc_id, out_id],
                        "amounts": [inc_amt, out_amt],
                        "timestamps": [str(inc_t), str(out_t)],
                        "time_diff_minutes": round(diff_min, 2)
                    })

    # Sort paths deterministically
    paths = sorted(paths, key=lambda p: (p["timestamps"][0], p["path_nodes"][0], p["path_nodes"][2]))

    # Deterministic Scoring (0-100)
    score = 0.0
    evidence = []

    # 1. Upstream Diversity (max 30 pts)
    n_up = len(upstream_senders)
    if n_up >= 2:
        up_score = min(30.0, 15.0 * n_up)
        score += up_score
        evidence.append(build_evidence_item(
            evidence_type="MULTIPLE_UPSTREAM_SENDERS",
            description=f"Received funds from {n_up} distinct upstream accounts.",
            value=n_up, threshold=2, transaction_ids=inc_df['transaction_id'].tolist()
        ))

    # 2. Downstream Diversity (max 30 pts)
    n_down = len(downstream_recipients)
    if n_down >= 2:
        down_score = min(30.0, 15.0 * n_down)
        score += down_score
        evidence.append(build_evidence_item(
            evidence_type="MULTIPLE_DOWNSTREAM_RECIPIENTS",
            description=f"Transferred funds onward to {n_down} distinct downstream accounts.",
            value=n_down, threshold=2, transaction_ids=out_df['transaction_id'].tolist()
        ))

    # 3. Flow-Through Pair & Temporal Proximity (max 30 pts)
    n_pairs = len(flow_pairs)
    if n_pairs > 0:
        score += 20.0
        evidence.append(build_evidence_item(
            evidence_type="FLOW_THROUGH_SEQUENCES",
            description=f"Observed {n_pairs} flow-through sequence(s) from incoming to outgoing transfers.",
            value=n_pairs, threshold=1, transaction_ids=[p[0] for p in flow_pairs] + [p[1] for p in flow_pairs]
        ))
        if min_time_diff_min is not None and min_time_diff_min <= 60.0:
            score += 10.0
            evidence.append(build_evidence_item(
                evidence_type="RAPID_FLOW_THROUGH",
                description=f"Fastest flow-through occurred within {min_time_diff_min:.1f} minutes.",
                value=round(min_time_diff_min, 1), threshold=60.0, transaction_ids=[]
            ))

    # 4. Flow-Through Volume Ratio (max 10 pts)
    if 0.5 <= flow_ratio <= 1.5 and inc_amount > 0 and out_amount > 0:
        score += 10.0
        evidence.append(build_evidence_item(
            evidence_type="HIGH_FLOW_THROUGH_RATIO",
            description=f"Flow-through ratio is {flow_ratio:.2f} (outgoing/incoming total volume).",
            value=round(flow_ratio, 2), threshold=0.5, transaction_ids=[]
        ))

    detected = score >= score_threshold

    metrics = {
        "unique_upstream_senders": n_up,
        "unique_downstream_recipients": n_down,
        "incoming_count": inc_count,
        "outgoing_count": out_count,
        "total_incoming_amount": round(inc_amount, 2),
        "total_outgoing_amount": round(out_amount, 2),
        "flow_through_ratio": round(flow_ratio, 4),
        "flow_through_pairs_count": n_pairs,
        "min_time_diff_minutes": round(min_time_diff_min, 2) if min_time_diff_min is not None else None
    }

    entities = {
        "target_account": target_account,
        "upstream_accounts": upstream_senders,
        "downstream_accounts": downstream_recipients,
        "devices": devices,
        "ips": ips
    }

    if detected:
        explanation = (
            f"Detected MULE_CHAIN pattern involving suspected intermediary {target_account}: "
            f"Received funds from {n_up} upstream account(s) and forwarded to {n_down} downstream account(s) "
            f"across {n_pairs} flow-through sequence(s) (Score: {score:.1f})."
        )
    else:
        explanation = f"No significant MULE_CHAIN pattern detected for account {target_account}."

    return _build_result(
        detected=detected, score=score, evidence=evidence, entities=entities,
        transactions=tx_ids, metrics=metrics, paths=paths,
        account_id=target_account, transaction_id=transaction_id,
        as_of_timestamp=as_of_timestamp, explanation=explanation
    )


def _build_result(
    detected: bool,
    score: float,
    evidence: List[Dict[str, Any]],
    entities: Dict[str, Any],
    transactions: List[str],
    metrics: Dict[str, Any],
    paths: List[Dict[str, Any]],
    account_id: Optional[str],
    transaction_id: Optional[str],
    as_of_timestamp: Optional[Union[str, pd.Timestamp]],
    explanation: str
) -> Dict[str, Any]:
    """Helper to construct stable MULE_CHAIN result schema."""
    base_res = format_pattern_result(
        pattern_name="MULE_CHAIN",
        detected=detected,
        score=score,
        evidence=evidence,
        entities=entities,
        transactions=transactions,
        metrics=metrics,
        explanation=explanation
    )
    base_res["account_id"] = account_id
    base_res["transaction_id"] = transaction_id
    base_res["as_of_timestamp"] = str(as_of_timestamp) if as_of_timestamp is not None else None
    base_res["paths"] = paths
    return base_res
