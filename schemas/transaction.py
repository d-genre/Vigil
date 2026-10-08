"""
Transaction Pydantic Data Models.
Shared schema representing financial transactions across Vigil modules.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """Core transaction model representing incoming financial transactions."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    account_id: str = Field(..., description="Initiating account or customer ID")
    amount: float = Field(..., description="Monetary value of transaction")
    merchant_id: Optional[str] = Field(None, description="Recipient merchant ID")
    device_id: Optional[str] = Field(None, description="Client device fingerprint ID")
    ip: Optional[str] = Field(None, description="Client IP address")
    location: Optional[str] = Field(None, description="Geographic location / city")
    beneficiary_id: Optional[str] = Field(None, description="Target recipient account ID")


class MLPrediction(BaseModel):
    """Screening output model returned by CatBoost ML model."""

    transaction_id: str = Field(..., description="Target transaction ID")
    fraud_probability: float = Field(..., ge=0.0, le=1.0, description="Fraud likelihood (0.0 to 1.0)")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    model_version: Optional[str] = Field("catboost_v1.0", description="Model identifier")
