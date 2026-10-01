"""API Integration tests for Health Monitoring endpoints (V23 Commit 02).

Tests cover:
- GET /api/v1/health/summary
- GET /api/v1/health/data
- GET /api/v1/health/data/{symbol} (200 healthy and 200 UNKNOWN state)
- GET /api/v1/health/models
- GET /api/v1/health/models/{model_id} (200 healthy and 200 UNKNOWN state)
- GET /api/v1/health/providers
- GET /api/v1/health/pipeline
- GET /metrics (Prometheus exposition endpoint)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from app.core.dependencies import health_monitoring_service_dep
from app.modules.data_quality.domain.models import (
    QualityReport,
    QualityStatistics,
    QualityStatus,
)
from app.modules.observability.application.service import (
    HealthMonitoringService,
    get_health_monitoring_service,
)
from fastapi.testclient import TestClient


@pytest.fixture
def health_service(test_app) -> HealthMonitoringService:
    """Retrieve the application's singleton health service."""
    service = test_app.dependency_overrides.get(
        health_monitoring_service_dep, get_health_monitoring_service()
    )
    return cast(HealthMonitoringService, service)


def test_get_health_summary(client: TestClient) -> None:
    """GET /api/v1/health/summary returns platform-wide operational health status."""
    response = client.get("/api/v1/health/summary")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data
    assert "market_data" in data["components"]
    assert "models" in data["components"]
    assert "providers" in data["components"]
    assert "pipeline" in data["components"]


def test_get_data_health_list_and_symbol(
    client: TestClient, health_service: HealthMonitoringService
) -> None:
    """GET /api/v1/health/data and GET /api/v1/health/data/{symbol}."""
    # UNKNOWN status for unmonitored symbol
    unknown_resp = client.get("/api/v1/health/data/NONEXISTENT_XYZ")
    assert unknown_resp.status_code == 200
    assert unknown_resp.json()["status"] == "UNKNOWN"

    # Seed health observation with clean validation report
    now = datetime.now(tz=UTC)
    clean_report = QualityReport(
        symbol="SPY",
        status=QualityStatus.PASS,
        statistics=QualityStatistics(
            total_records=100,
            valid_records=100,
            critical_count=0,
            warning_count=0,
            info_count=0,
        ),
        issues=(),
    )
    health_service.record_data_health_evaluation(
        symbol="SPY",
        latest_observation_time=now,
        expected_rows=100,
        received_rows=100,
        validation_report=clean_report,
        calendar_id="nyse",
        provider_id="yahoo_finance",
    )

    # Test list endpoint
    list_resp = client.get("/api/v1/health/data")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    symbols = [item["symbol"] for item in list_data["items"]]
    assert "SPY" in symbols

    # Test single symbol endpoint
    sym_resp = client.get("/api/v1/health/data/SPY")
    assert sym_resp.status_code == 200
    sym_data = sym_resp.json()
    assert sym_data["symbol"] == "SPY"
    assert sym_data["status"] == "HEALTHY"
    assert "freshness" in sym_data
    assert "completeness" in sym_data
    assert "validity" in sym_data
    assert sym_data["completeness"]["expected_rows"] == 100


def test_get_model_health_list_and_detail(
    client: TestClient, health_service: HealthMonitoringService
) -> None:
    """GET /api/v1/health/models and GET /api/v1/health/models/{model_id}."""
    # UNKNOWN status for unmonitored model
    unknown_resp = client.get("/api/v1/health/models/unmonitored_abc")
    assert unknown_resp.status_code == 200
    assert unknown_resp.json()["status"] == "UNKNOWN"

    # Seed model health with stable predictions and high confidence
    health_service.record_model_health_evaluation(
        model_id="kmeans",
        predictions=[0] * 20 + [1] * 20,
        k_clusters=2,
        confidences=[0.90] * 40,
    )

    # Test list endpoint
    list_resp = client.get("/api/v1/health/models")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    models = [item["model_id"] for item in list_data["items"]]
    assert "kmeans" in models

    # Test detail endpoint
    detail_resp = client.get("/api/v1/health/models/kmeans")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["model_id"] == "kmeans"
    assert detail_data["status"] == "HEALTHY"
    assert "validity" in detail_data
    assert "stability" in detail_data
    assert "regime_distribution" in detail_data
    assert detail_data["validity"]["valid_predictions"] == 40


def test_get_providers_health(client: TestClient, health_service: HealthMonitoringService) -> None:
    """GET /api/v1/health/providers returns operational vendor API health."""
    health_service.record_provider_request(
        provider_id="yahoo_finance",
        success=True,
        latency_ms=125.0,
    )

    resp = client.get("/api/v1/health/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    pids = [p["provider_id"] for p in data["items"]]
    assert "yahoo_finance" in pids


def test_get_pipeline_health(client: TestClient, health_service: HealthMonitoringService) -> None:
    """GET /api/v1/health/pipeline returns all stages of the data processing pipeline."""
    resp = client.get("/api/v1/health/pipeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_status" in data
    assert "stages" in data
    assert "ingestion" in data["stages"]
    assert "validation" in data["stages"]
    assert "normalization" in data["stages"]
    assert "storage" in data["stages"]
    assert "features" in data["stages"]


def test_get_prometheus_metrics(client: TestClient) -> None:
    """GET /metrics returns Prometheus exposition format."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    text = resp.text
    assert "regimex_data_health_checks_total" in text
    assert "regimex_model_health_checks_total" in text
