"""
FRAUD-RING RADAR Fraud Patterns Package (backend/fraud_patterns/)
Exports fraud pattern detection modules.
"""

from .card_testing import detect_card_testing

__all__ = ["detect_card_testing"]
