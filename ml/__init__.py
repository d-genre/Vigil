"""
VIGIL ML Module (ml/)

Provides CatBoost classifier ML screening and feature engineering.
Aligned with VIGIL architecture.
"""

from .train_catboost import train_catboost_model
from .train_logistic import train_logistic_pipeline
from .excel_loader import (
    load_provided_dataset,
    load_provided_csv_dataset,
    load_provided_excel_dataset,
    validate_excel_dataset,
)
from .data_preparation import (
    run_data_preparation_pipeline,
    prepare_features_and_target,
    create_reproducible_splits,
    validate_input_schema,
    get_model_feature_matrix,
    MODEL_FEATURE_ALLOWLIST,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)

__all__ = [
    "train_catboost_model",
    "train_logistic_pipeline",
    "load_provided_dataset",
    "load_provided_csv_dataset",
    "load_provided_excel_dataset",
    "validate_excel_dataset",
    "run_data_preparation_pipeline",
    "prepare_features_and_target",
    "create_reproducible_splits",
    "validate_input_schema",
    "get_model_feature_matrix",
    "MODEL_FEATURE_ALLOWLIST",
    "CATEGORICAL_FEATURES",
    "NUMERIC_FEATURES",
]

