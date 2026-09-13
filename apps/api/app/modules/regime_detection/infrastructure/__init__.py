"""
RegimeX Regime Detection — Infrastructure Layer
==============================================
Adapters, concrete ML model implementations, and third-party integrations.
"""

from app.modules.regime_detection.infrastructure.models.kmeans import KMeansRegimeDetector

__all__ = ["KMeansRegimeDetector"]
