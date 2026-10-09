from typing import Dict, Any, List

class ActionRecommendationEngine:
    """
    Vigil Action Recommendation Engine.
    Evaluates final risk scores, detected attack patterns, and supporting evidence
    to output standardized human-review decisions: APPROVE, HOLD, ESCALATE, or BLOCK.
    Ensures safe human-in-the-loop review routing.
    """
    
    # Standardized action definitions
    ACTION_APPROVE = "APPROVE"
    ACTION_HOLD = "HOLD"
    ACTION_ESCALATE = "ESCALATE"
    ACTION_BLOCK = "BLOCK"

    def __init__(self):
        # Risk score thresholds
        self.threshold_block = 0.85
        self.threshold_escalate = 0.70
        self.threshold_hold = 0.40

        # High-severity patterns that warrant automatic BLOCK or ESCALATE overrides
        self.critical_patterns = [
            "Coordinated Fraud Ring",
            "Account Takeover",
            "Mule Account Chain",
            "Push Payment Fraud"
        ]

    def evaluate_case(self, risk_score: float, detected_pattern: str, evidence: List[str], counter_evidence: List[str]) -> Dict[str, Any]:
        """
        Evaluates the case constraints to recommend an action.
        
        Args:
            risk_score (float): Normalized risk score from ML / Detectors (0.0 to 1.0)
            detected_pattern (str): The primary fraud pattern detected (or 'None')
            evidence (List[str]): List of positive risk indicators
            counter_evidence (List[str]): List of mitigating/normalizing factors
            
        Returns:
            Dict containing recommended action, routing instructions, and reasoning.
        """
        
        # 1. Evaluate baseline evidence weight
        evidence_weight = len(evidence) - len(counter_evidence)
        
        # 2. Determine initial action purely based on risk score and evidence weight
        if risk_score >= self.threshold_block or evidence_weight >= 3:
            recommended_action = self.ACTION_BLOCK
            reasoning = f"Critical risk score ({risk_score:.2f}) or overwhelming negative evidence detected."
            requires_analyst = False  # Blocks can be automated for severe threats
            
        elif risk_score >= self.threshold_escalate or (detected_pattern in ["Synthetic Identity", "Mule Account Chain"]):
            recommended_action = self.ACTION_ESCALATE
            reasoning = f"High risk score ({risk_score:.2f}) or complex pattern requiring manual review."
            requires_analyst = True
            
        elif risk_score >= self.threshold_hold:
            recommended_action = self.ACTION_HOLD
            reasoning = f"Medium risk score ({risk_score:.2f}) detected. Pausing for automated verification (e.g., OTP)."
            requires_analyst = False
            
        else:
            recommended_action = self.ACTION_APPROVE
            reasoning = f"Low risk score ({risk_score:.2f}) and normal behavioral baseline."
            requires_analyst = False

        # 3. Pattern-based overrides (Safety constraints)
        # Never automatically approve if a critical pattern is explicitly flagged, regardless of score
        if recommended_action == self.ACTION_APPROVE and any(p in detected_pattern for p in self.critical_patterns):
            recommended_action = self.ACTION_ESCALATE
            reasoning = f"Override: Low risk score, but flagged for severe pattern ({detected_pattern}). Escalated for safety."
            requires_analyst = True
            
        # If strong counter-evidence exists on a BLOCK, downgrade to ESCALATE for human review
        if recommended_action == self.ACTION_BLOCK and len(counter_evidence) >= 2:
            recommended_action = self.ACTION_ESCALATE
            reasoning = f"Override: Critical risk, but strong counter-evidence exists. Routing to human analyst."
            requires_analyst = True

        return {
            "recommended_action": recommended_action,
            "requires_human_analyst": requires_analyst,
            "reasoning": reasoning,
            "risk_score": risk_score,
            "primary_pattern": detected_pattern
        }


# Example usage for testing integration
if __name__ == "__main__":
    recommender = ActionRecommendationEngine()
    
    # Test Case 1: Legitimate Baseline
    res1 = recommender.evaluate_case(
        risk_score=0.15,
        detected_pattern="None",
        evidence=[],
        counter_evidence=["Established device footprint", "Normal geolocation"]
    )
    print("Test 1 (Legitimate):", res1['recommended_action'])
    
    # Test Case 2: Coordinated Ring (Block)
    res2 = recommender.evaluate_case(
        risk_score=0.92,
        detected_pattern="Coordinated Fraud Ring",
        evidence=["Multiple accounts shared IP", "High velocity transfer"],
        counter_evidence=[]
    )
    print("Test 2 (Fraud Ring):", res2['recommended_action'])
    
    # Test Case 3: High Risk but with Counter Evidence (Escalate)
    res3 = recommender.evaluate_case(
        risk_score=0.88,
        detected_pattern="Account Takeover",
        evidence=["New device login", "Large transfer"],
        counter_evidence=["Biometric auth succeeded", "Recipient is known historical beneficiary"]
    )
    print("Test 3 (High Risk + Counter Evidence):", res3['recommended_action'])
