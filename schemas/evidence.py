"""
Evidence Pydantic v2 Data Models.
Shared schema representing positive risk evidence and mitigating counter-evidence.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    """Pydantic v2 model for positive risk indicator evidence."""

    model_config = ConfigDict(frozen=False)

    id: str = Field(..., description="Unique evidence identifier")
    type: str = Field(..., description="Type of evidence (e.g., SUSPICIOUS_DEVICE_SHARING, HIGH_VELOCITY)")
    description: str = Field(..., description="Human-readable description of detected signal")
    source: str = Field(..., description="Originating module (ml, fraud_rules, graph_analysis, behavioral)")
    timestamp: str = Field(..., description="ISO 8601 detection timestamp")
    related_entity: Optional[str] = Field(None, description="Associated account, device, IP, or merchant ID")
    observed_value: Optional[str] = Field(None, description="Observed metric value or value delta")
    severity: str = Field(..., description="Severity level: CRITICAL, HIGH, MEDIUM, LOW")

    @property
    def signal_type(self) -> str:
        return self.type

    @property
    def evidence_id(self) -> str:
        return self.id

    @property
    def category(self) -> str:
        return "INDICATOR"

    @property
    def weight(self) -> float:
        if self.severity == "CRITICAL":
            return 1.0
        elif self.severity == "HIGH":
            return 0.85
        elif self.severity == "MEDIUM":
            return 0.50
        return 0.25


class CounterEvidenceItem(BaseModel):
    """Pydantic v2 model for mitigating counter-evidence (why NOT to block)."""

    model_config = ConfigDict(frozen=False)

    id: str = Field(..., description="Unique counter-evidence identifier")
    type: str = Field(..., description="Type of counter-evidence (e.g., KYC_VERIFIED, HISTORICAL_LEGITIMATE_PATTERN)")
    description: str = Field(..., description="Human-readable rationale supporting legitimacy")
    source: str = Field(..., description="Originating module or data source")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    related_entity: Optional[str] = Field(None, description="Associated account, device, or IP ID")
    observed_value: Optional[str] = Field(None, description="Observed metric or verification record")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Mitigation strength weight (0.0 to 1.0)")

    @property
    def signal_type(self) -> str:
        return self.type

    @property
    def evidence_id(self) -> str:
        return self.id

    @property
    def category(self) -> str:
        return "COUNTER_EVIDENCE"

    @property
    def weight(self) -> float:
        return self.relevance_score


class SimilarAttackResult(BaseModel):
    """Historical attack pattern match from FAISS vector memory."""

    model_config = ConfigDict(frozen=False)

    attack_id: str = Field(..., description="Historical attack signature identifier")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Vector similarity score (0.0 to 1.0)")
    pattern_type: str = Field(..., description="Matched fraud pattern category")
    historical_outcome: str = Field(..., description="Recorded resolution (e.g. CONFIRMED_FRAUD, FALSE_POSITIVE)")
    key_features: List[str] = Field(default_factory=list, description="Shared key feature tags")
