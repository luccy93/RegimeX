"""
RegimeX Data Quality — Application Package
==========================================
Validation pipeline, configuration, and rule orchestration.
"""

from app.modules.data_quality.application.config import ValidationConfig
from app.modules.data_quality.application.pipeline import MarketDataValidationPipeline
from app.modules.data_quality.application.rules import (
    CalendarValidationRule,
    DuplicateDetectionRule,
    GapDetectionRule,
    OHLCIntegrityRule,
    OrderingValidationRule,
    SchemaValidationRule,
    StalenessDetectionRule,
    TimestampIntegrityRule,
    VolumeValidationRule,
)

__all__ = [
    "ValidationConfig",
    "MarketDataValidationPipeline",
    "SchemaValidationRule",
    "TimestampIntegrityRule",
    "OHLCIntegrityRule",
    "VolumeValidationRule",
    "DuplicateDetectionRule",
    "OrderingValidationRule",
    "CalendarValidationRule",
    "GapDetectionRule",
    "StalenessDetectionRule",
]
