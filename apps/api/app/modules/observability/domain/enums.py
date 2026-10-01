"""
RegimeX Observability — Health & Monitoring Enums
=================================================
Deterministic operational states and classification enums for data and model health.

Architectural Position:
- Pure domain layer: standard library only.
- Zero dependencies on frameworks, databases, or transport layers.
"""

from __future__ import annotations

from enum import StrEnum


class HealthStatus(StrEnum):
    """
    Deterministic operational health status.

    States:
      - HEALTHY: Normal operation, SLA met, constraints satisfied.
      - DEGRADED: Operational but experiencing non-fatal issues (warnings, drift, latency).
      - UNHEALTHY: Critical failure, contract violation, or broken invariants.
      - STALE: Data age exceeds staleness threshold (when market was expected to trade).
      - UNKNOWN: Insufficient observations or uninitialized state.
    """

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class ProviderStatus(StrEnum):
    """
    Operational availability status of upstream market data providers.

    States:
      - AVAILABLE: Provider responding successfully with acceptable latency.
      - DEGRADED: Provider experiencing sporadic failures or elevated latency.
      - UNAVAILABLE: Provider repeatedly failing or unreachable.
      - UNKNOWN: Provider registered but not yet polled or evaluated.
    """

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class PipelineStage(StrEnum):
    """
    Distinct operational stages across the market data and analytics pipeline.
    """

    PROVIDER = "provider"
    INGESTION = "ingestion"
    VALIDATION = "validation"
    NORMALIZATION = "normalization"
    STORAGE = "storage"
    FEATURES = "features"


class DriftMethod(StrEnum):
    """
    Statistical methodology used to quantify distribution drift.
    """

    JENSEN_SHANNON = "jensen_shannon"
    PSI = "psi"
    TOTAL_VARIATION = "total_variation"
