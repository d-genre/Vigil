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

CITIES_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "cities_clean.csv"

def load_cities_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    path = data_path or CITIES_CLEAN_PATH
    if not path.exists():
        from ml import data_loader
        return data_loader.load_cities(processed=True)
    return pd.read_csv(path)

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth surface."""
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
            return np.nan
        R = 6371.0 # km
        lat1_r, lon1_r, lat2_r, lon2_r = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2_r - lat1_r
        dlon = lon2_r - lon1_r
        a = np.sin(dlat/2)**2 + np.cos(lat1_r)*np.cos(lat2_r)*np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c
    except (ValueError, TypeError):
        return np.nan

def detect_impossible_travel(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    cities_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detects IMPOSSIBLE_TRAVEL pattern for a specific account.
    """
    cfg = config or {}
    score_threshold = float(cfg.get("score_threshold", 50.0))
    suspicious_speed_kmh = float(cfg.get("suspicious_speed_kmh", 800.0))
    implausible_speed_kmh = float(cfg.get("implausible_speed_kmh", 1000.0))
    min_distance_km = float(cfg.get("min_distance_km", 100.0))

    raw_account_id = account_id.replace("ACCOUNT:", "") if isinstance(account_id, str) else str(account_id)

    # Load data
    if transactions_df is None:
        tx_df = load_transactions_clean()
    else:
        tx_df = transactions_df.copy()
        if 'ts' not in tx_df.columns and 'timestamp' in tx_df.columns:
            tx_df['ts'] = pd.to_datetime(tx_df['timestamp'], errors='coerce')
            
    if cities_df is None:
        c_df = load_cities_clean()
    else:
        c_df = cities_df.copy()

    empty_entities = {"account_id": raw_account_id, "cities": []}
    empty_metrics = {
        "max_speed_kmh": 0.0,
        "max_distance_km": 0.0,
        "valid_location_pairs": 0,
        "missing_location_pairs": 0
    }

    if tx_df.empty or 'nameOrig' not in tx_df.columns:
        return format_pattern_result(
            "IMPOSSIBLE_TRAVEL", False, 0.0, [], empty_entities, [], empty_metrics, "Empty transaction dataframe."
        )

    acc_tx_df = tx_df[tx_df['nameOrig'] == raw_account_id].copy()
    
    if acc_tx_df.empty:
        return format_pattern_result(
            "IMPOSSIBLE_TRAVEL", False, 0.0, [], empty_entities, [], empty_metrics, f"No transactions found for account {raw_account_id}."
        )

    # Point-in-time safety
    cutoff_ts = None
    if as_of_timestamp is not None:
        cutoff_ts = pd.to_datetime(as_of_timestamp, errors='coerce')
    
    investigated_tx_ts = None
    if transaction_id is not None:
        anchor_tx = acc_tx_df[acc_tx_df['transaction_id'] == transaction_id]
        if not anchor_tx.empty:
            investigated_tx_ts = anchor_tx['ts'].iloc[0]
            if cutoff_ts is None or (pd.notnull(investigated_tx_ts) and investigated_tx_ts < cutoff_ts):
                cutoff_ts = investigated_tx_ts
        else:
            return format_pattern_result(
                "IMPOSSIBLE_TRAVEL", False, 0.0, [], empty_entities, [], empty_metrics, f"Transaction {transaction_id} not found."
            )

    if cutoff_ts is not None and pd.notnull(cutoff_ts):
        acc_tx_df = acc_tx_df[acc_tx_df['ts'] <= cutoff_ts]

    if acc_tx_df.empty:
        return format_pattern_result(
            "IMPOSSIBLE_TRAVEL", False, 0.0, [], empty_entities, [], empty_metrics, "No eligible transactions prior to cutoff."
        )
        
    acc_tx_df = acc_tx_df.dropna(subset=['ts']).sort_values('ts')
    
    # Drop completely identical transactions to avoid zero-time/zero-distance noise
    acc_tx_df = acc_tx_df.drop_duplicates(subset=['transaction_id'])
    
    if len(acc_tx_df) < 2:
        return format_pattern_result(
            "IMPOSSIBLE_TRAVEL", False, 0.0, [], empty_entities, [tx_id for tx_id in acc_tx_df['transaction_id']], empty_metrics, "Not enough transactions to compare travel."
        )

    # Merge coordinates
    acc_tx_df = acc_tx_df.merge(c_df[['city', 'country', 'lat', 'lon']], on=['city', 'country'], how='left')

    # If transaction_id is provided, only evaluate pairs ending in this transaction
    if transaction_id:
        idx = acc_tx_df[acc_tx_df['transaction_id'] == transaction_id].index
        if len(idx) > 0:
            target_idx = idx[0]
            pos = acc_tx_df.index.get_loc(target_idx)
            if pos > 0:
                acc_tx_df = acc_tx_df.iloc[[pos-1, pos]]
            else:
                return format_pattern_result(
                    "IMPOSSIBLE_TRAVEL", False, 0.0, [], empty_entities, [transaction_id], empty_metrics, "No preceding transaction to compare."
                )

    # Evaluate consecutive pairs
    acc_tx_df['prev_tx_id'] = acc_tx_df['transaction_id'].shift(1)
    acc_tx_df['prev_ts'] = acc_tx_df['ts'].shift(1)
    acc_tx_df['prev_lat'] = acc_tx_df['lat'].shift(1)
    acc_tx_df['prev_lon'] = acc_tx_df['lon'].shift(1)
    acc_tx_df['prev_city'] = acc_tx_df['city'].shift(1)
    
    pairs = acc_tx_df.iloc[1:].copy()
    
    max_score = 0.0
    evidence = []
    cities_involved = set()
    all_tx_ids = set()
    
    valid_pairs_count = 0
    missing_pairs_count = 0
    max_speed_observed = 0.0
    max_dist_observed = 0.0
    
    for _, row in pairs.iterrows():
        tx_curr = row['transaction_id']
        tx_prev = row['prev_tx_id']
        ts_curr = row['ts']
        ts_prev = row['prev_ts']
        
        all_tx_ids.add(tx_curr)
        all_tx_ids.add(tx_prev)
        
        if pd.notnull(row['city']):
            cities_involved.add(row['city'])
        if pd.notnull(row['prev_city']):
            cities_involved.add(row['prev_city'])
            
        lat1, lon1 = row['prev_lat'], row['prev_lon']
        lat2, lon2 = row['lat'], row['lon']
        
        if pd.isnull(lat1) or pd.isnull(lon1) or pd.isnull(lat2) or pd.isnull(lon2):
            missing_pairs_count += 1
            continue
            
        dist_km = haversine(lat1, lon1, lat2, lon2)
        if pd.isnull(dist_km):
            missing_pairs_count += 1
            continue
            
        valid_pairs_count += 1
        max_dist_observed = max(max_dist_observed, dist_km)
        
        elapsed_h = (ts_curr - ts_prev).total_seconds() / 3600.0
        
        pair_score = 0.0
        speed_kmh = 0.0
        reason = ""
        
        if elapsed_h <= 0:
            if dist_km > min_distance_km:
                pair_score = 85.0
                reason = "Concurrent transactions at distant locations"
                speed_kmh = float('inf')
        else:
            speed_kmh = dist_km / elapsed_h
            if dist_km > min_distance_km:
                if speed_kmh >= implausible_speed_kmh:
                    pair_score = 85.0
                    reason = "Highly implausible travel speed"
                elif speed_kmh >= suspicious_speed_kmh:
                    pair_score = 60.0
                    reason = "Suspicious travel speed"
                    
        max_speed_observed = max(max_speed_observed, speed_kmh if speed_kmh != float('inf') else 0)
        
        if pair_score > 0:
            if pair_score > max_score:
                max_score = pair_score
                
            evidence.append(build_evidence_item(
                evidence_type="IMPLAUSIBLE_TRAVEL_SPEED" if pair_score >= 80 else "SUSPICIOUS_TRAVEL_SPEED",
                description=f"{reason}: {dist_km:.1f} km in {elapsed_h:.2f} hours (Implied: {speed_kmh:.1f} km/h)",
                value=speed_kmh,
                threshold=implausible_speed_kmh if pair_score >= 80 else suspicious_speed_kmh,
                transaction_ids=[tx_prev, tx_curr]
            ))
            
    detected = max_score >= score_threshold
    
    if detected:
        explanation = f"Detected impossible travel with max speed {max_speed_observed:.1f} km/h."
    elif missing_pairs_count > 0 and valid_pairs_count == 0:
        explanation = "Insufficient evidence: missing or invalid geographic data."
    else:
        explanation = "No suspicious travel detected."

    metrics = {
        "max_speed_kmh": max_speed_observed,
        "max_distance_km": max_dist_observed,
        "valid_location_pairs": valid_pairs_count,
        "missing_location_pairs": missing_pairs_count
    }

    entities = {
        "account_id": raw_account_id,
        "cities": list(cities_involved)
    }

    return format_pattern_result(
        pattern_name="IMPOSSIBLE_TRAVEL",
        detected=detected,
        score=max_score,
        evidence=evidence,
        entities=entities,
        transactions=list(all_tx_ids),
        metrics=metrics,
        explanation=explanation
    )
