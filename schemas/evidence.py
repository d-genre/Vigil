"""
Evidence Pydantic Data Models.
Shared schema representing structured indicators and counter-evidence.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Single evidence signal (indicator or counter-evidence)."""

    evidence_id: str = Field(..., description="Unique evidence identifier")
    signal_type: str = Field(..., description="Classification of evidence signal")
    category: str = Field(..., description="INDICATOR (supports risk) or COUNTER_EVIDENCE (supports approval)")
    description: str = Field(..., description="Human-readable explanation of signal")
    weight: float = Field(..., ge=0.0, le=1.0, description="Confidence or severity weight")
    source: str = Field(..., description="Origin module: ml, fraud_rules, graph_analysis, behavioral")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contextual key-value metrics")


class SimilarAttackResult(BaseModel):
    """Historical attack pattern match returned from vector memory."""

    attack_id: str = Field(..., description="Historical attack signature ID")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Vector similarity score")
    pattern_type: str = Field(..., description="Matched fraud pattern type")
    historical_outcome: str = Field(..., description="Recorded resolution outcome")
    key_features: List[str] = Field(default_factory=list, description="Shared feature tags")
