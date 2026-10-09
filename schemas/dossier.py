from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal

class ProsecutionEvidence(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    indicator: str = Field(..., description="The fraud indicator or anomaly detected")
    observation: str = Field(..., description="Detailed observation or metric")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(..., description="Severity level of this evidence")

class DefenseCounterEvidence(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    indicator: str = Field(..., description="The mitigating factor or valid baseline indicator")
    observation: str = Field(..., description="Detailed observation or metric")
    significance: Literal["STRONG", "MODERATE", "WEAK"] = Field(..., description="Significance level of this counter-evidence")

class DossierReport(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    transaction_id: str = Field(..., description="Target transaction ID")
    catboost_score: float = Field(..., description="Original ML risk score")
    risk_tier: Literal["CRITICAL", "ELEVATED", "LOW"] = Field(..., description="Final risk tier determined by the engine")
    confidence_percentage: int = Field(..., ge=0, le=100, description="Confidence level of the recommendation (0-100)")
    
    evidence_prosecution: List[ProsecutionEvidence] = Field(..., description="Points supporting fraud")
    counter_evidence_defense: List[DefenseCounterEvidence] = Field(..., description="Points supporting legitimacy")
    
    graph_corroboration: str = Field(..., description="Summary of campaign/ring metrics from graph analysis")
    detailed_analysis: str = Field(..., description="In-depth explanation of the ML reasoning, graph patterns, and overall fraud logic.")
    recommended_action: Literal["DECLINE_AND_FREEZE", "STEP_UP_VERIFICATION", "APPROVE_AND_CALIBRATE"] = Field(..., description="Judicial decision")
    executive_analyst_summary: str = Field(..., description="Concise 2-sentence summary of the case and rationale")
