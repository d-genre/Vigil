"""
Detector Adapters Package (backend/adapters/)
Provides translation adapters mapping Stage 8B/8C detector outputs to VIGIL schemas.
"""

from .detector_adapter import (
    adapt_detector_result_to_vigil_pattern,
    evaluate_all_seven_vigil_patterns,
    map_detector_score_to_confidence,
)

__all__ = [
    "adapt_detector_result_to_vigil_pattern",
    "evaluate_all_seven_vigil_patterns",
    "map_detector_score_to_confidence",
]
