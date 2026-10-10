from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional, Any

class ProsecutionEvidence(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    title: str = Field(default="Fraud Indicator", description="Short title of the fraud indicator")
    indicator: str = Field(default="Fraud Indicator", description="The fraud indicator or anomaly detected")
    description: str = Field(default="", description="Detailed observation or metric")
    observation: str = Field(default="", description="Detailed observation or metric")
    severity: str = Field(default="HIGH", description="Severity level (CRITICAL, HIGH, MEDIUM, LOW)")
    impact: float = Field(default=0.0, description="Directional risk impact (+0.0 to +1.0)")

class DefenseCounterEvidence(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    title: str = Field(default="Mitigating Factor", description="Short title of the mitigating factor")
    indicator: str = Field(default="Mitigating Factor", description="The mitigating factor or valid baseline indicator")
    description: str = Field(default="", description="Detailed observation or metric")
    observation: str = Field(default="", description="Detailed observation or metric")
    significance: str = Field(default="STRONG", description="Significance level (STRONG, MODERATE, WEAK)")

class ExplainabilityDriver(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    feature: str = Field(..., description="Feature identifier")
    value: str = Field(..., description="Observed feature value")
    shap_value: float = Field(..., description="SHAP risk contribution (+/-)")
    baseline_value: Optional[str] = Field(default=None, description="Historical user baseline value")
    directional_impact: Optional[str] = Field(default=None, description="Directional impact indicator (+/-)")

class DossierReport(BaseModel):
    model_config = ConfigDict(frozen=False, populate_by_name=True)
    
    transaction_id: str = Field(..., description="Target transaction ID")
    catboost_score: float = Field(..., description="Original ML risk score")
    risk_score: float = Field(..., description="Final risk score")
    risk_tier: str = Field(..., description="Final risk tier determined by the engine")
    verdict: str = Field(..., description="Judicial verdict (DECLINE_AND_FREEZE, STEP_UP_VERIFICATION, APPROVE_AND_CALIBRATE)")
    classification: str = Field(..., description="Transaction classification category")
    confidence_percentage: int = Field(default=92, ge=0, le=100, description="Confidence level of the recommendation (0-100)")
    
    executive_analyst_summary: str = Field(..., description="Multi-paragraph executive case narrative")
    executive_summary: str = Field(..., description="Executive case summary narrative")
    
    # 5 Mandatory Forensic Analytical Dimensions
    behavioral_diagnostics: str = Field(..., description="Behavioral & Velocity Diagnostics")
    network_infrastructure_forensics: str = Field(..., description="Device, Network & Infrastructure Forensics")
    graph_syndicate_assessment: str = Field(..., description="Graph Topology & Syndicate Association")
    mitigating_defense_factors: str = Field(..., description="Mitigating / Defense Factors evaluation")
    remediation_action_plan: List[str] = Field(default_factory=list, description="Definite Judicial Verdict & Step-by-step Action Plan")
    
    evidence_prosecution: List[ProsecutionEvidence] = Field(default_factory=list, description="Points supporting fraud")
    prosecution_evidence: List[ProsecutionEvidence] = Field(default_factory=list, description="Points supporting fraud")
    
    counter_evidence_defense: List[DefenseCounterEvidence] = Field(default_factory=list, description="Points supporting legitimacy")
    defense_evidence: List[DefenseCounterEvidence] = Field(default_factory=list, description="Points supporting legitimacy")
    
    graph_corroboration: str = Field(..., description="Summary of campaign/ring metrics from graph analysis")
    detailed_analysis: str = Field(..., description="In-depth analytical explanation of ML reasoning, graph patterns, and fraud logic.")
    explainability_drivers: List[ExplainabilityDriver] = Field(default_factory=list, description="Feature SHAP drivers")
    recommended_action: str = Field(..., description="Judicial decision")

