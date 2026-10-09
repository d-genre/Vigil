"""
FRAUD-RING RADAR Fraud Patterns Package (fraud/)
Exports fraud pattern detection modules and Step 5 Investigation Engine.
"""

from .card_testing import detect_card_testing
from .account_takeover import detect_account_takeover
from .device_syndicate import detect_device_syndicate
from .impossible_travel import detect_impossible_travel
from .mule_chain import detect_mule_chain
from .rapid_drain import detect_rapid_drain
from .velocity_burst import detect_velocity_burst
from .aggregator import run_all_detectors

__all__ = [
    "detect_card_testing",
    "detect_account_takeover",
    "detect_device_syndicate",
    "detect_impossible_travel",
    "detect_mule_chain",
    "detect_rapid_drain",
    "detect_velocity_burst",
    "run_all_detectors",
]
