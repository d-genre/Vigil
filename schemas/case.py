"""
Case & Decision Pydantic Data Models.
Shared schema representing database case entities and human review decisions.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Case(BaseModel):
    """Database model for a flagged investigation case."""

    case_id: str = Field(..., description="Unique case identifier")
    transaction_id: str = Field(..., description="Associated transaction ID")
    risk_score: float = Field(..., description="Calculated composite risk score (0-100)")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, HIGH")
    status: str = Field("PENDING_REVIEW", description="Case status: PENDING_REVIEW, RESOLVED")
    decision: Optional[str] = Field(None, description="Recorded decision: APPROVE, HOLD, ESCALATE, BLOCK")
    analyst_notes: Optional[str] = Field(None, description="Analyst comments and reasoning")
    created_at: str = Field(..., description="Case creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")


class HumanDecisionRequest(BaseModel):
    """Payload for analyst decision submission endpoint."""

    action: str = Field(..., description="Action chosen: APPROVE, HOLD, ESCALATE, BLOCK")
    reason: str = Field(..., description="Mandatory rationale for auditor trail")
    analyst_id: str = Field(..., description="ID of human investigator submitting decision")


class HumanDecisionResponse(BaseModel):
    """Response returned upon successfully recording human analyst decision."""

    case_id: str = Field(..., description="Target case ID")
    status: str = Field("RESOLVED", description="Updated case status")
    decision: str = Field(..., description="Recorded action")
    updated_at: str = Field(..., description="Resolution timestamp (ISO 8601)")
