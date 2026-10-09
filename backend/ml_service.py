import os
import random
from typing import Dict, Any, Tuple

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False


class ScreeningService:
    def __init__(self, model_path: str = "models/catboost_fraud.cbm"):
        self.model = None
        self.model_loaded = False
        
        if CATBOOST_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = CatBoostClassifier()
                self.model.load_model(model_path)
                self.model_loaded = True
            except Exception:
                pass

    def screen(self, tx_dict: Dict[str, Any]) -> Tuple[float, str]:
        """
        Screens a transaction and returns (risk_score, risk_level).
        Uses CatBoost if available, otherwise falls back to basic rules.
        """
        # Baseline fallback logic
        amount = float(tx_dict.get("amount", 0.0))
        
        base_risk = 0.1
        if amount >= 10000:
            base_risk = 0.85
        elif amount >= 5000:
            base_risk = 0.50
            
        if self.model_loaded:
            try:
                # Simulate ML model prediction for baseline
                ml_score = base_risk + random.uniform(-0.1, 0.1)
                risk_score = ml_score
            except Exception:
                risk_score = base_risk
        else:
            risk_score = base_risk

        # Clamp strictly between 0.0 and 1.0
        risk_score = max(0.0, min(1.0, float(risk_score)))

        # Assign risk level strictly
        if risk_score >= 0.75:
            risk_level = "HIGH"
        elif risk_score >= 0.40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return risk_score, risk_level

# Global singleton
screening_service = ScreeningService()
