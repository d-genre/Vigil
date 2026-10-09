"""
Investigation Pydantic v2 Data Models.
Shared schema representing complete investigation state and agent memory.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from schemas.transaction import Transaction, MLPrediction
from schemas.evidence import EvidenceItem, CounterEvidenceItem, SimilarAttackResult


class FraudPatternType(str, Enum):
    """Supported fraud pattern types in Vigil."""
    CARD_TESTING = "CARD_TESTING"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    MULE_CHAIN = "MULE_CHAIN"
    SYNTHETIC_IDENTITY = "SYNTHETIC_IDENTITY"
    PUSH_PAYMENT_SCAM = "PUSH_PAYMENT_SCAM"
    BENEFICIARY_ATO = "BENEFICIARY_ATO"
    COORDINATED_FRAUD_RING = "COORDINATED_FRAUD_RING"
    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"
    DEVICE_SYNDICATE = "DEVICE_SYNDICATE"
    VELOCITY_BURST = "VELOCITY_BURST"


class FraudPatternResult(BaseModel):
    """Result of evaluating a specific fraud pattern detector."""

    model_config = ConfigDict(frozen=False)

    pattern_name: Union[FraudPatternType, str] = Field(..., description="Fraud pattern name or type")
    detected: bool = Field(..., description="Whether pattern threshold was triggered")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    matched_rules: List[str] = Field(default_factory=list, description="Triggered rule IDs")
    details: Dict[str, Any] = Field(default_factory=dict, description="Pattern metadata")


class GraphPath(BaseModel):
    """Suspicious path or cycle detected in NetworkX transaction graph."""

    model_config = ConfigDict(frozen=False)

    path_id: str = Field(..., description="Path identifier")
    nodes: List[str] = Field(..., description="Ordered list of account/device/IP node IDs")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Edge relationships and transaction IDs")
    path_type: str = Field(..., description="Classification (e.g. MULE_CHAIN, SHARED_DEVICE_RING, CYCLE, DEVICE_SYNDICATE)")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Path risk score")


class GraphAnalysisResult(BaseModel):
    """Network topology analysis results from NetworkX graph engine."""

    model_config = ConfigDict(frozen=False)

    account_id: str = Field(..., description="Target account ID")
    is_ring_member: bool = Field(False, description="True if account is part of a fraud ring")
    ring_id: Optional[str] = Field(None, description="Identified fraud ring ID")
    hub_score: float = Field(0.0, ge=0.0, le=1.0, description="Network centrality score")
    graph_paths: List[GraphPath] = Field(default_factory=list, description="Detected suspicious graph paths")
    suspicious_connections: List[Dict[str, Any]] = Field(default_factory=list, description="Connected entities")


class InvestigationCase(BaseModel):
    """Comprehensive investigation case schema linking all findings."""

    model_config = ConfigDict(frozen=False)

    case_id: str = Field(..., description="Unique case identifier")
    transaction: Transaction = Field(..., description="Target transaction under investigation")
    ml_risk_score: Optional[MLPrediction] = Field(None, description="CatBoost screening result")
    matched_patterns: List[FraudPatternResult] = Field(default_factory=list, description="Matched fraud patterns")
    graph_analysis: Optional[GraphAnalysisResult] = Field(None, description="Graph findings and paths")
    evidences: List[EvidenceItem] = Field(default_factory=list, description="Collected risk indicators")
    counter_evidences: List[CounterEvidenceItem] = Field(default_factory=list, description="Collected counter-evidence")
    similar_cases: List[SimilarAttackResult] = Field(default_factory=list, description="Similar cases from FAISS vector memory")
    risk_score: float = Field(0.0, ge=0.0, le=100.0, description="Composite aggregate risk score (0-100)")
    ai_explanation: Optional[str] = Field(None, description="Grounded LLM explanation and reasoning summary")
    recommended_action: str = Field("HOLD", description="Recommended action: APPROVE, HOLD, ESCALATE, BLOCK")
    status: str = Field("PENDING_REVIEW", description="Status: INVESTIGATING, PENDING_REVIEW, RESOLVED")


# Alias for backward compatibility
InvestigationState = InvestigationCase
