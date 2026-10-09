"""
VIGIL ML Module (ml/)

Provides CatBoost classifier ML screening and feature engineering.
Aligned with VIGIL architecture.
"""

from backend.ml.train_catboost import train_catboost_model, evaluate_catboost_model
from backend.ml.logistic_baseline import train_logistic_baseline

__all__ = [
    "train_catboost_model",
    "evaluate_catboost_model",
    "train_logistic_baseline",
]
