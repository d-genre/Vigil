"""
FRAUD-RING RADAR
Fraud Patterns Shared Module (backend/fraud_patterns/common.py)

Provides standard result schema structures, severity calculation helpers,
and shared data loading utilities for pattern detectors.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRANSACTIONS_CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "raw_clean" / "transactions_clean.csv"


def load_transactions_clean(data_path: Optional[Path] = None) -> pd.DataFrame:
    """Loads cleaned transactions dataset with parsed datetime timestamps."""
    path = data_path or TRANSACTIONS_CLEAN_PATH
    df = pd.read_csv(path)
    df['ts'] = pd.to_datetime(df['timestamp'])
    return df


def calculate_severity(score: float) -> str:
    """Categorizes rule-based score into severity levels."""
    if score >= 80.0:
        return "CRITICAL"
    elif score >= 60.0:
        return "HIGH"
    elif score >= 40.0:
        return "MEDIUM"
    elif score > 0.0:
        return "LOW"
    return "NONE"


def build_evidence_item(
    evidence_type: str,
    description: str,
    value: Any,
    threshold: Any,
    transaction_ids: List[str],
    event_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Formats a structured evidence item."""
    return {
        "evidence_type": evidence_type,
        "description": description,
        "value": value,
        "threshold": threshold,
        "transaction_ids": transaction_ids,
        "event_ids": event_ids or []
    }


def format_pattern_result(
    pattern_name: str,
    detected: bool,
    score: float,
    evidence: List[Dict[str, Any]],
    entities: Dict[str, Any],
    transactions: List[str],
    metrics: Dict[str, Any],
    explanation: str
) -> Dict[str, Any]:
    """Formats standard pattern detection result schema."""
    bounded_score = float(max(0.0, min(100.0, round(score, 2))))
    return {
        "pattern_name": pattern_name,
        "detected": detected,
        "score": bounded_score,
        "severity": calculate_severity(bounded_score),
        "evidence": evidence,
        "entities": entities,
        "transactions": transactions,
        "metrics": metrics,
        "explanation": explanation
    }
