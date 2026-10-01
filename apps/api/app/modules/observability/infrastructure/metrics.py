"""
RegimeX Observability — Platform Telemetry & Metrics
====================================================
Prometheus metrics instruments adhering strictly to the bounded cardinality policy.

Cardinality Safety:
- Never includes unbounded labels: symbol, request_id, user_id, trace_id, timestamps,
  feature vectors, free-form error messages.
- Permitted dimensions: provider, model, component, operation, status, severity, category.
"""

from __future__ import annotations

import logging

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)

logger = logging.getLogger(__name__)


class MetricsRegistry:
    """
    Encapsulates platform Prometheus metric collectors with idempotency protection.
    """

    def __init__(self, registry: CollectorRegistry = REGISTRY) -> None:
        self.registry = registry

        # Helper to avoid "Duplicated timeseries in CollectorRegistry" in reloads / test runs
        def _get_or_create_counter(name: str, documentation: str, labelnames: list[str]) -> Counter:
            try:
                return Counter(
                    name=name,
                    documentation=documentation,
                    labelnames=labelnames,
                    registry=self.registry,
                )
            except ValueError:
                collector = self.registry._names_to_collectors.get(name)
                if isinstance(collector, Counter):
                    return collector
                # Look in collector name mappings
                for col in self.registry._collector_to_names:
                    if name in self.registry._collector_to_names[col] and isinstance(col, Counter):
                        return col
                # Fallback to direct registry get
                return Counter(name=name, documentation=documentation, labelnames=labelnames)

        def _get_or_create_gauge(name: str, documentation: str, labelnames: list[str]) -> Gauge:
            try:
                return Gauge(
                    name=name,
                    documentation=documentation,
                    labelnames=labelnames,
                    registry=self.registry,
                )
            except ValueError:
                collector = self.registry._names_to_collectors.get(name)
                if isinstance(collector, Gauge):
                    return collector
                for col in self.registry._collector_to_names:
                    if name in self.registry._collector_to_names[col] and isinstance(col, Gauge):
                        return col
                return Gauge(name=name, documentation=documentation, labelnames=labelnames)

        # ---------------------------------------------------------------------
        # Data Health Metrics
        # ---------------------------------------------------------------------
        self.data_health_checks_total = _get_or_create_counter(
            name="regimex_data_health_checks_total",
            documentation="Total number of evaluated market data health checks",
            labelnames=["status", "provider"],
        )
        self.data_health_failures_total = _get_or_create_counter(
            name="regimex_data_health_failures_total",
            documentation="Count of data health failures classified by cause and provider",
            labelnames=["failure_type", "provider"],
        )
        self.data_freshness_seconds = _get_or_create_gauge(
            name="regimex_data_freshness_seconds",
            documentation="Age in seconds of the latest observation relative to evaluation time",
            labelnames=["calendar_id", "status"],
        )
        self.data_quality_violations_total = _get_or_create_counter(
            name="regimex_data_quality_violations_total",
            documentation="Data quality violations detected by category and severity",
            labelnames=["category", "severity"],
        )

        # ---------------------------------------------------------------------
        # Model Health Metrics
        # ---------------------------------------------------------------------
        self.model_health_checks_total = _get_or_create_counter(
            name="regimex_model_health_checks_total",
            documentation="Total regime model health checks evaluated",
            labelnames=["model", "status"],
        )
        self.model_health_failures_total = _get_or_create_counter(
            name="regimex_model_health_failures_total",
            documentation="Model health checks resulting in unhealthy or degraded status",
            labelnames=["model", "failure_type"],
        )
        self.model_prediction_failures_total = _get_or_create_counter(
            name="regimex_model_prediction_failures_total",
            documentation="Total model prediction errors or output invariant violations",
            labelnames=["model", "reason"],
        )
        self.model_low_confidence_total = _get_or_create_counter(
            name="regimex_model_low_confidence_total",
            documentation="Count of model predictions falling below low-confidence threshold",
            labelnames=["model"],
        )
        self.model_drift = _get_or_create_gauge(
            name="regimex_model_drift",
            documentation="Statistical divergence metric for regime model prediction distributions",
            labelnames=["model", "metric"],
        )
        self.data_drift = _get_or_create_gauge(
            name="regimex_data_drift",
            documentation="Feature distribution drift divergence metric",
            labelnames=["feature", "metric"],
        )

    def record_data_health(
        self,
        status: str,
        provider: str = "yahoo_finance",
        freshness_seconds: float | None = None,
        calendar_id: str = "nyse",
    ) -> None:
        """Record telemetry for a data health check."""
        clean_status = status.upper()
        clean_provider = provider.lower()
        self.data_health_checks_total.labels(status=clean_status, provider=clean_provider).inc()

        if clean_status in ("DEGRADED", "UNHEALTHY", "STALE"):
            self.data_health_failures_total.labels(
                failure_type=clean_status.lower(), provider=clean_provider
            ).inc()

        if freshness_seconds is not None and freshness_seconds >= 0:
            self.data_freshness_seconds.labels(
                calendar_id=calendar_id.lower(), status=clean_status
            ).set(freshness_seconds)

    def record_quality_violations(self, category: str, severity: str, count: int = 1) -> None:
        """Record data quality violations."""
        if count > 0:
            self.data_quality_violations_total.labels(
                category=category.lower(),
                severity=severity.lower(),
            ).inc(count)

    def record_model_health(
        self,
        model_id: str,
        status: str,
        drift_score: float | None = None,
        low_confidence_count: int = 0,
    ) -> None:
        """Record telemetry for a model health check."""
        clean_model = model_id.lower()
        clean_status = status.upper()

        self.model_health_checks_total.labels(model=clean_model, status=clean_status).inc()

        if clean_status in ("DEGRADED", "UNHEALTHY"):
            self.model_health_failures_total.labels(
                model=clean_model, failure_type=clean_status.lower()
            ).inc()

        if low_confidence_count > 0:
            self.model_low_confidence_total.labels(model=clean_model).inc(low_confidence_count)

        if drift_score is not None and drift_score >= 0:
            self.model_drift.labels(model=clean_model, metric="jsd").set(drift_score)

    def record_prediction_failure(self, model_id: str, reason: str = "invariant_violation") -> None:
        """Record an invariant violation or execution exception during prediction."""
        self.model_prediction_failures_total.labels(
            model=model_id.lower(),
            reason=reason.lower(),
        ).inc()

    def record_feature_drift(self, feature: str, drift_score: float) -> None:
        """Record continuous feature drift score."""
        self.data_drift.labels(feature=feature.lower(), metric="psi").set(drift_score)

    def render_latest(self) -> bytes:
        """Generate Prometheus exposition format bytes."""
        return generate_latest(self.registry)


# Global singleton instance for application metrics
metrics: MetricsRegistry = MetricsRegistry()
