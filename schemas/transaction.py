"""
Transaction Pydantic v2 Data Models.
Shared schema representing incoming financial transactions and screening responses.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class Transaction(BaseModel):
    """Pydantic v2 model for incoming financial transactions."""

    model_config = ConfigDict(frozen=False, populate_by_name=True)

    transaction_id: str = Field(..., description="Unique transaction identifier")
    account_id: str = Field(..., description="Initiating customer or account ID")
    amount: float = Field(..., description="Monetary value of the transaction")
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR, INR)")
    device_id: Optional[str] = Field(default=None, description="Client device fingerprint ID")
    ip: Optional[str] = Field(default=None, description="Client IP address")
    beneficiary_id: Optional[str] = Field(default=None, description="Target recipient account ID")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    location: Optional[str] = Field(default=None, description="Geographic location / city")
    transaction_type: Optional[str] = Field(default="TRANSFER", description="Transaction type (e.g., PAYMENT, TRANSFER, CASH_OUT)")


class MLPrediction(BaseModel):
    """Screening prediction output returned by CatBoost classifier model."""

    model_config = ConfigDict(frozen=False)

    transaction_id: str = Field(..., description="Target transaction ID")
    fraud_probability: float = Field(..., ge=0.0, le=1.0, description="Fraud probability score (0.0 to 1.0)")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    model_version: str = Field(default="catboost_v1.0", description="Model version tag")
