import os
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("vigil.backend.ml_service")

# Try importing CatBoost if installed
try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False


class ScreeningService:
    """
    Decoupled Screening Service for transaction risk assessment.
    Attempts to use trained ML models or inference modules from `ml/`.
    Falls back gracefully to standard baseline heuristics if unavailable.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.predict_fn = None
        self.mode = "FALLBACK"

        # 1. Attempt to dynamic import ml.predict
        try:
            import ml.predict as ml_predict
            if hasattr(ml_predict, "predict"):
                self.predict_fn = ml_predict.predict
                self.mode = "ML_PREDICT_MODULE"
                logger.info("Successfully imported inference function from ml.predict")
        except (ImportError, ModuleNotFoundError):
            logger.info("Module ml.predict not found; checking for CatBoost model artifacts.")
        except Exception as e:
            logger.warning(f"Error importing ml.predict: {e}")

        # 2. If ml.predict function not loaded, check for saved CatBoost model binary
        if not self.predict_fn and CATBOOST_AVAILABLE:
            candidate_paths = [
                model_path,
                "models/catboost_fraud.cbm",
                "ml/models/catboost_fraud.cbm",
                "data/catboost_fraud.cbm",
            ]
            valid_paths = [p for p in candidate_paths if p and os.path.exists(p)]

            if valid_paths:
                chosen_path = valid_paths[0]
                try:
                    cb_model = CatBoostClassifier()
                    cb_model.load_model(chosen_path)
                    self.model = cb_model
                    self.mode = "CATBOOST_ARTIFACT"
                    logger.info(f"Successfully loaded CatBoost model from {chosen_path}")
                except Exception as e:
                    logger.warning(f"Failed to load CatBoost artifact at {chosen_path}: {e}")

        # 3. Log initial operational state
        if self.mode == "FALLBACK":
            logger.info("ScreeningService initialized in Degraded Mode (Baseline Heuristics active)")
        else:
            logger.info(f"ScreeningService initialized in ML Mode ({self.mode})")

    def _extract_features(self, tx_dict: Dict[str, Any]) -> list:
        """
        Extract numeric features from transaction dictionary for CatBoost model if needed.
        """
        amount = float(tx_dict.get("amount", 0.0))
        return [amount]

    def _fallback_heuristic(self, tx_dict: Dict[str, Any]) -> float:
        """
        Baseline risk heuristic based on transaction properties.
        Guarantees non-crashing risk scoring when ML models/helpers are absent.
        """
        amount = float(tx_dict.get("amount", 0.0))
        tx_type = str(tx_dict.get("transaction_type", "TRANSFER")).upper()

        # Base score based on amount thresholds
        if amount >= 100000.0:
            score = 0.95
        elif amount >= 50000.0:
            score = 0.85
        elif amount >= 10000.0:
            score = 0.75
        elif amount >= 5000.0:
            score = 0.50
        elif amount >= 1000.0:
            score = 0.30
        else:
            score = 0.10

        # Adjust score slightly for high risk transaction types
        if tx_type in ["CASH_OUT", "WIRE_TRANSFER", "CRYPTO_PURCHASE"]:
            score = min(1.0, score + 0.10)

        return score

    def screen(self, tx_dict: Dict[str, Any]) -> Tuple[float, str]:
        """
        Screens a transaction and returns (risk_score, risk_level).

        Args:
            tx_dict: Dictionary containing transaction data.

        Returns:
            Tuple of (risk_score: float [0.0 - 1.0], risk_level: str)
            where risk_level is one of ["CRITICAL", "HIGH", "MEDIUM", "LOW"].
        """
        raw_score = None

        # 1. Try ml.predict inference function if available
        if self.predict_fn:
            try:
                result = self.predict_fn(tx_dict)
                if isinstance(result, (float, int)):
                    raw_score = float(result)
                elif isinstance(result, tuple) and len(result) >= 1:
                    raw_score = float(result[0])
                elif isinstance(result, dict):
                    raw_score = float(result.get("fraud_probability", result.get("risk_score", 0.0)))
                elif hasattr(result, "fraud_probability"):
                    raw_score = float(result.fraud_probability)
            except Exception as e:
                logger.warning(f"Error during ml.predict execution, falling back to baseline heuristic: {e}")

        # 2. Try CatBoost model if available and no score yet
        if raw_score is None and self.model:
            try:
                features = self._extract_features(tx_dict)
                probs = self.model.predict_proba([features])
                if len(probs) > 0 and len(probs[0]) > 1:
                    raw_score = float(probs[0][1])
                else:
                    raw_score = float(probs[0][0])
            except Exception as e:
                logger.warning(f"Error during CatBoost model prediction, falling back to baseline heuristic: {e}")

        # 3. Fallback heuristic if ML inference was unavailable or failed
        if raw_score is None:
            raw_score = self._fallback_heuristic(tx_dict)

        # Clamp risk score strictly between 0.0 and 1.0
        risk_score = round(max(0.0, min(1.0, float(raw_score))), 4)

        # Determine risk level tier based on shared contract:
        # CRITICAL: score >= 0.90
        # HIGH: 0.70 <= score < 0.90
        # MEDIUM: 0.40 <= score < 0.70
        # LOW: score < 0.40
        if risk_score >= 0.90:
            risk_level = "CRITICAL"
        elif risk_score >= 0.70:
            risk_level = "HIGH"
        elif risk_score >= 0.40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return risk_score, risk_level


# Global singleton instance export
screening_service = ScreeningService()

