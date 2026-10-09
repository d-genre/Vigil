"""
VIGIL ML Module (ml/)

Provides CatBoost classifier ML screening and feature engineering.
Aligned with VIGIL architecture.
"""

from .data_loader import load_transactions, load_train, load_val, load_test
from .features import generate_features
from .train_catboost import train_catboost_model, get_feature_columns
from .train_logistic import train_logistic_pipeline

__all__ = [
    "load_transactions",
    "load_train",
    "load_val",
    "load_test",
    "generate_features",
    "train_catboost_model",
    "get_feature_columns",
    "train_logistic_pipeline",
]


