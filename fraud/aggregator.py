"""
FRAUD-RING RADAR
Unified Evidence & Pattern Aggregation Engine (backend/fraud_patterns/aggregator.py)

Aggregates results from Stage 8B pattern detectors.
"""

from typing import Dict, Any, Optional, Union
import pandas as pd
import copy
import logging
import math

from .card_testing import detect_card_testing
from .account_takeover import detect_account_takeover
from .mule_chain import detect_mule_chain
from .impossible_travel import detect_impossible_travel
from .device_syndicate import detect_device_syndicate
from .velocity_burst import detect_velocity_burst
from .rapid_drain import detect_rapid_drain
from .common import calculate_severity

logger = logging.getLogger(__name__)

# Constants for Execution Status
STATUS_SUCCESS_FLAGGED = "SUCCESS_FLAGGED"
STATUS_SUCCESS_CLEAN = "SUCCESS_CLEAN"
STATUS_SKIPPED_MISSING_DATA = "SKIPPED_MISSING_DATA"
STATUS_ERROR = "ERROR"

DETECTORS = {
    "CARD_TESTING": detect_card_testing,
    "ACCOUNT_TAKEOVER": detect_account_takeover,
    "MULE_CHAIN": detect_mule_chain,
    "IMPOSSIBLE_TRAVEL": detect_impossible_travel,
    "DEVICE_SYNDICATE": detect_device_syndicate,
    "VELOCITY_BURST": detect_velocity_burst,
    "RAPID_DRAIN": detect_rapid_drain
}

def _determine_execution_status(detector_name: str, result: Dict[str, Any]) -> str:
    """Determines execution status based on observable output without parsing explanation strings."""
    if not isinstance(result, dict):
        return STATUS_ERROR
        
    if result.get("detected", False):
        return STATUS_SUCCESS_FLAGGED
        
    m = result.get("metrics", {})
    e = result.get("entities", {})
    
    # Heuristics to detect if the detector actually evaluated data or returned its empty schema
    is_missing = False
    if detector_name == "CARD_TESTING":
        is_missing = not (e.get("devices") or e.get("ips") or e.get("merchants"))
    elif detector_name == "ACCOUNT_TAKEOVER":
        is_missing = m.get("baseline_devices", 0) == 0 and m.get("baseline_ips", 0) == 0 and not e.get("devices")
    elif detector_name == "MULE_CHAIN":
        is_missing = m.get("incoming_count", 0) == 0 and m.get("outgoing_count", 0) == 0
    elif detector_name == "IMPOSSIBLE_TRAVEL":
        is_missing = m.get("valid_location_pairs", 0) == 0 and m.get("missing_location_pairs", 0) == 0
    elif detector_name == "DEVICE_SYNDICATE":
        is_missing = m.get("max_accounts_per_device", 0) == 0 and not e.get("devices")
    elif detector_name == "VELOCITY_BURST":
        is_missing = m.get("max_tx_count_5m", 0) == 0 and m.get("max_tx_count_1h", 0) == 0
    elif detector_name == "RAPID_DRAIN":
        is_missing = m.get("outgoing_sum_1h", 0) == 0 and m.get("drain_ratio_1h", 0) == 0 and not e.get("destinations")
        
    if is_missing:
        return STATUS_SKIPPED_MISSING_DATA
        
    return STATUS_SUCCESS_CLEAN

def _aggregate_score(detector_results: Dict[str, Dict[str, Any]]) -> float:
    """
    Conservative, deterministic aggregation bounded to [0, 100].
    Does not naively sum scores. Evaluates transaction overlap.
    """
    flagged = [res for res in detector_results.values() if res.get("detected") and res.get("score", 0) > 0]
    if not flagged:
        return 0.0
        
    # Sort by score descending
    flagged.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    base_res = flagged[0]
    overall = float(base_res.get("score", 0.0))
    seen_txs = set(base_res.get("transactions", []))
    
    for res in flagged[1:]:
        txs = set(res.get("transactions", []))
        if not txs:
            overall += 10.0
        else:
            unique_txs = txs - seen_txs
            if len(unique_txs) > 0:
                overall += 15.0 # Unique evidence adds more risk
            else:
                overall += 5.0  # Overlapping evidence adds marginal risk
        seen_txs.update(txs)
        
    return float(max(0.0, min(100.0, round(overall, 2))))

def run_all_detectors(
    account_id: str,
    transactions_df: Optional[pd.DataFrame] = None,
    events_df: Optional[pd.DataFrame] = None,
    devices_df: Optional[pd.DataFrame] = None,
    cities_df: Optional[pd.DataFrame] = None,
    accounts_df: Optional[pd.DataFrame] = None,
    beneficiaries_df: Optional[pd.DataFrame] = None,
    transaction_id: Optional[str] = None,
    as_of_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    configs: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Executes all available Stage 8B detectors on the given account context.
    
    Returns an aggregate schema summarizing overall risk, maintaining strict point-in-time boundaries,
    and handling missing data or exceptions safely per-detector.
    """
    configs = configs or {}
    results = {}
    statuses = {}
    
    # Store original dataframes references to verify immutability externally if needed
    kwargs_map = {
        "CARD_TESTING": {"transactions_df": transactions_df},
        "ACCOUNT_TAKEOVER": {"transactions_df": transactions_df, "events_df": events_df},
        "MULE_CHAIN": {"transactions_df": transactions_df},
        "IMPOSSIBLE_TRAVEL": {"transactions_df": transactions_df, "cities_df": cities_df},
        "DEVICE_SYNDICATE": {"transactions_df": transactions_df, "devices_df": devices_df},
        "VELOCITY_BURST": {"transactions_df": transactions_df},
        "RAPID_DRAIN": {
            "transactions_df": transactions_df, 
            "events_df": events_df, 
            "accounts_df": accounts_df, 
            "beneficiaries_df": beneficiaries_df
        }
    }

    unique_flagged_txs = set()

    for name, func in DETECTORS.items():
        detector_config = configs.get(name, {})
        detector_kwargs = kwargs_map.get(name, {})
        
        try:
            # We copy kwargs just in case, though pandas dataframes are passed by reference.
            # The detectors are expected to not mutate them (verified in tests).
            res = func(
                account_id=account_id,
                transaction_id=transaction_id,
                as_of_timestamp=as_of_timestamp,
                config=detector_config,
                **detector_kwargs
            )
            
            # Defensive deepcopy to prevent aggregator modification from affecting detector internal state
            safe_res = copy.deepcopy(res)
            
            # Check for malformed results
            if not isinstance(safe_res, dict) or "detected" not in safe_res:
                raise ValueError("Malformed detector result schema")
                
            score = safe_res.get("score")
            if score is None or isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ValueError(f"Malformed score type: {type(score)}")
            if not math.isfinite(score) or not (0.0 <= score <= 100.0):
                raise ValueError(f"Malformed score value: {score}")
                
            txs = safe_res.get("transactions")
            if not isinstance(txs, list):
                raise ValueError(f"Malformed transactions collection type: {type(txs)}")
            for tx in txs:
                if not isinstance(tx, str) or not tx.strip():
                    raise ValueError(f"Malformed transaction ID: {tx}")
                
            status = _determine_execution_status(name, safe_res)
            
            if status == STATUS_SUCCESS_FLAGGED:
                unique_flagged_txs.update(txs)
                
            results[name] = safe_res
            statuses[name] = status
            
        except Exception as e:
            logger.error(f"Detector {name} failed: {e}")
            statuses[name] = STATUS_ERROR
            results[name] = {
                "pattern_name": name,
                "detected": False,
                "score": 0.0,
                "severity": "NONE",
                "evidence": [],
                "entities": {},
                "transactions": [],
                "metrics": {},
                "explanation": f"Execution failed: {str(e)}"
            }

    overall_score = _aggregate_score(results)

    return {
        "account_id": account_id,
        "evaluated_at": str(as_of_timestamp) if as_of_timestamp is not None else None,
        "overall_score": overall_score,
        "overall_severity": calculate_severity(overall_score),
        "total_unique_flagged_transactions": len(unique_flagged_txs),
        "detector_results": results,
        "execution_status": statuses
    }
