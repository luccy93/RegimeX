"""Unit tests for Observability Prometheus Metrics Registry and Telemetry.

Tests cover:
- Metric emission for data health, freshness, quality violations
- Metric emission for model health, failures, confidence, and drift
- Verification of bounded labels on all instruments
- Verification of Prometheus exposition format output
"""

from app.modules.observability.infrastructure.metrics import MetricsRegistry
from prometheus_client import CollectorRegistry


def test_metrics_registry_initialization_and_labels() -> None:
    """Verifies that all Prometheus metric instruments enforce bounded labels."""
    custom_reg = CollectorRegistry()
    reg = MetricsRegistry(registry=custom_reg)

    # Check bounded label names
    assert set(reg.data_health_checks_total._labelnames) == {"status", "provider"}
    assert set(reg.data_health_failures_total._labelnames) == {"failure_type", "provider"}
    assert set(reg.data_freshness_seconds._labelnames) == {"calendar_id", "status"}
    assert set(reg.data_quality_violations_total._labelnames) == {"category", "severity"}
    assert set(reg.model_health_checks_total._labelnames) == {"model", "status"}
    assert set(reg.model_health_failures_total._labelnames) == {"model", "failure_type"}
    assert set(reg.model_prediction_failures_total._labelnames) == {"model", "reason"}
    assert set(reg.model_low_confidence_total._labelnames) == {"model"}
    assert set(reg.model_drift._labelnames) == {"model", "metric"}
    assert set(reg.data_drift._labelnames) == {"feature", "metric"}

    # Cardinality guarantee: ensure high cardinality fields are never labels
    forbidden = {"symbol", "request_id", "user_id", "trace_id", "timestamp"}
    for collector in [
        reg.data_health_checks_total,
        reg.data_health_failures_total,
        reg.data_freshness_seconds,
        reg.data_quality_violations_total,
        reg.model_health_checks_total,
        reg.model_health_failures_total,
        reg.model_prediction_failures_total,
        reg.model_low_confidence_total,
        reg.model_drift,
        reg.data_drift,
    ]:
        for lbl in collector._labelnames:
            assert lbl not in forbidden, f"Forbidden label '{lbl}' found on collector"


def test_record_data_health_metrics() -> None:
    """Tests recording data health checks, failures, and freshness gauges."""
    custom_reg = CollectorRegistry()
    reg = MetricsRegistry(registry=custom_reg)

    reg.record_data_health(
        status="HEALTHY",
        provider="yahoo_finance",
        freshness_seconds=150.0,
        calendar_id="nyse",
    )
    reg.record_data_health(
        status="STALE",
        provider="yahoo_finance",
        freshness_seconds=7500.0,
        calendar_id="nyse",
    )

    rendered = reg.render_latest().decode("utf-8")
    assert "regimex_data_health_checks_total" in rendered
    assert 'status="HEALTHY"' in rendered
    assert 'status="STALE"' in rendered
    assert "regimex_data_freshness_seconds" in rendered
    assert "regimex_data_health_failures_total" in rendered


def test_record_model_health_metrics() -> None:
    """Tests recording model health checks, low confidence counters, and drift gauges."""
    custom_reg = CollectorRegistry()
    reg = MetricsRegistry(registry=custom_reg)

    reg.record_model_health(
        model_id="kmeans",
        status="HEALTHY",
        drift_score=0.03,
        low_confidence_count=0,
    )
    reg.record_model_health(
        model_id="gmm",
        status="DEGRADED",
        drift_score=0.28,
        low_confidence_count=5,
    )
    reg.record_prediction_failure(
        model_id="hmm",
        reason="invalid_probability_vector",
    )

    rendered = reg.render_latest().decode("utf-8")
    assert "regimex_model_health_checks_total" in rendered
    assert 'model="kmeans"' in rendered
    assert 'model="gmm"' in rendered
    assert "regimex_model_drift" in rendered
    assert "regimex_model_low_confidence_total" in rendered
    assert "regimex_model_prediction_failures_total" in rendered
    assert 'reason="invalid_probability_vector"' in rendered


def test_record_feature_drift_and_quality_violations() -> None:
    """Tests recording feature PSI drift and data quality violations."""
    custom_reg = CollectorRegistry()
    reg = MetricsRegistry(registry=custom_reg)

    reg.record_feature_drift(feature="volatility_21d", drift_score=0.12)
    reg.record_quality_violations(category="ohlc", severity="critical", count=2)

    rendered = reg.render_latest().decode("utf-8")
    assert "regimex_data_drift" in rendered
    assert 'feature="volatility_21d"' in rendered
    assert "regimex_data_quality_violations_total" in rendered
    assert 'category="ohlc"' in rendered
    assert 'severity="critical"' in rendered
