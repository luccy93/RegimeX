"""Unit tests for Data Health, Provider Health, and Pipeline Health Monitoring.

Tests cover:
- Fresh data evaluation
- Stale data evaluation
- Calendar-aware market closed evaluation (NYSE weekend / after hours)
- Missing and duplicate observations
- Validity evaluation consuming V06 QualityReport
- Provider health tracking (success, failure streaks, latency, state transitions)
- Pipeline stage health tracking
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualityReport,
    QualitySeverity,
    QualityStatistics,
    QualityStatus,
)
from app.modules.observability.application.data_health import DataHealthMonitor
from app.modules.observability.application.pipeline_health import PipelineHealthMonitor
from app.modules.observability.application.provider_health import ProviderHealthMonitor
from app.modules.observability.domain.enums import HealthStatus, PipelineStage, ProviderStatus


def test_data_freshness_when_fresh() -> None:
    """Fresh observation within threshold during trading hours is HEALTHY."""
    monitor = DataHealthMonitor(freshness_threshold_seconds=300, stale_threshold_seconds=3600)
    now = datetime(2026, 10, 1, 15, 0, 0, tzinfo=UTC)
    obs_time = datetime(2026, 10, 1, 14, 58, 0, tzinfo=UTC)

    # Mock calendar to indicate market open
    mock_cal = MagicMock()
    mock_cal.is_market_open.return_value = True

    snapshot = monitor.evaluate_freshness(
        latest_observation_time=obs_time,
        as_of=now,
        calendar=mock_cal,
        calendar_id="nyse",
    )

    assert snapshot.status == HealthStatus.HEALTHY
    assert snapshot.freshness_seconds == 120.0
    assert snapshot.market_open is True


def test_data_freshness_when_market_closed() -> None:
    """Market closed with latest bar matching scheduled close is HEALTHY, not stale."""
    monitor = DataHealthMonitor(freshness_threshold_seconds=300, stale_threshold_seconds=3600)
    # Sunday evening
    now = datetime(2026, 10, 4, 20, 0, 0, tzinfo=UTC)
    # Friday close
    friday_close = datetime(2026, 10, 2, 20, 0, 0, tzinfo=UTC)

    mock_cal = MagicMock()
    mock_cal.is_market_open.return_value = False
    mock_cal.calendar_id = "nyse"
    mock_cal.expected_trading_days.return_value = [friday_close.date()]
    mock_cal.is_trading_day.return_value = False

    snapshot = monitor.evaluate_freshness(
        latest_observation_time=friday_close,
        as_of=now,
        calendar=mock_cal,
        calendar_id="nyse",
    )

    assert snapshot.status == HealthStatus.HEALTHY
    assert snapshot.market_open is False
    assert snapshot.reason is not None and "close" in snapshot.reason.lower()


def test_data_freshness_stale_during_open() -> None:
    """Observation older than stale threshold during market hours is STALE."""
    monitor = DataHealthMonitor(freshness_threshold_seconds=300, stale_threshold_seconds=1800)
    now = datetime(2026, 10, 1, 16, 0, 0, tzinfo=UTC)
    obs_time = datetime(2026, 10, 1, 14, 0, 0, tzinfo=UTC)  # 2 hours old

    mock_cal = MagicMock()
    mock_cal.is_market_open.return_value = True

    snapshot = monitor.evaluate_freshness(
        latest_observation_time=obs_time,
        as_of=now,
        calendar=mock_cal,
        calendar_id="nyse",
    )

    assert snapshot.status == HealthStatus.STALE
    assert snapshot.freshness_seconds == 7200.0


def test_data_completeness_evaluation() -> None:
    """Evaluates expected vs received rows and flags missing rows."""
    monitor = DataHealthMonitor()

    # 100% complete
    healthy = monitor.evaluate_completeness(
        expected_rows=100,
        received_rows=100,
        missing_rows=0,
        duplicate_rows=0,
    )
    assert healthy.status == HealthStatus.HEALTHY
    assert healthy.missing_rows == 0
    assert healthy.completeness_ratio == 1.0

    # Missing rows
    degraded = monitor.evaluate_completeness(
        expected_rows=100,
        received_rows=92,
        missing_rows=8,
        duplicate_rows=2,
    )
    assert degraded.status == HealthStatus.DEGRADED
    assert degraded.missing_rows == 8
    assert degraded.duplicate_rows == 2


def test_data_validity_from_quality_report() -> None:
    """Consumes V06 QualityReport without inventing competing rules."""
    monitor = DataHealthMonitor()

    # Clean report
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
    clean_snapshot = monitor.evaluate_validity(clean_report)
    assert clean_snapshot.status == HealthStatus.HEALTHY
    assert clean_snapshot.is_valid is True
    assert clean_snapshot.critical_issues_count == 0
    assert clean_snapshot.warning_issues_count == 0

    # Report with critical anomaly
    bad_report = QualityReport(
        symbol="SPY",
        status=QualityStatus.FAIL,
        statistics=QualityStatistics(
            total_records=100,
            valid_records=99,
            critical_count=1,
            warning_count=0,
            info_count=0,
        ),
        issues=(
            QualityIssue(
                rule_id="DQ-OHLC-001",
                category=QualityCategory.OHLC,
                severity=QualitySeverity.CRITICAL,
                message="High < Low anomaly detected",
                symbol="SPY",
            ),
        ),
    )
    bad_snapshot = monitor.evaluate_validity(bad_report)
    assert bad_snapshot.status == HealthStatus.UNHEALTHY
    assert bad_snapshot.is_valid is False
    assert bad_snapshot.critical_issues_count == 1
    assert "DQ-OHLC-001" in bad_snapshot.failed_rule_ids


def test_provider_health_tracking() -> None:
    """Tracks provider request counts, failures, latency, and status transitions."""
    monitor = ProviderHealthMonitor()

    # Initial state
    initial = monitor.get_provider_snapshot("yahoo_finance")
    assert initial.status == ProviderStatus.UNKNOWN

    # Record successes
    monitor.record_request("yahoo_finance", success=True, latency_ms=100.0)
    monitor.record_request("yahoo_finance", success=True, latency_ms=150.0)

    snap = monitor.get_provider_snapshot("yahoo_finance")
    assert snap.status == ProviderStatus.AVAILABLE
    assert snap.request_count == 2
    assert snap.success_count == 2
    assert snap.failure_count == 0
    assert snap.avg_latency_ms == 125.0

    # Record consecutive failures
    monitor.record_request(
        "yahoo_finance", success=False, error_category="HTTP 503", latency_ms=50.0
    )
    monitor.record_request(
        "yahoo_finance", success=False, error_category="HTTP 503", latency_ms=50.0
    )
    monitor.record_request(
        "yahoo_finance", success=False, error_category="HTTP 503", latency_ms=50.0
    )

    failing_snap = monitor.get_provider_snapshot("yahoo_finance")
    assert failing_snap.status == ProviderStatus.UNAVAILABLE
    assert failing_snap.consecutive_failures == 3

    # Recovery
    for _ in range(10):
        monitor.record_request("yahoo_finance", success=True, latency_ms=100.0)
    recovered_snap = monitor.get_provider_snapshot("yahoo_finance")
    assert recovered_snap.consecutive_failures == 0
    assert recovered_snap.status != ProviderStatus.UNAVAILABLE


def test_pipeline_health_tracking() -> None:
    """Tracks end-to-end pipeline stages and derives overall operational status."""
    monitor = PipelineHealthMonitor()

    # Initial state: all stages healthy
    snap = monitor.get_pipeline_snapshot()
    assert snap.overall_status == HealthStatus.HEALTHY
    assert len(snap.stages) == 6

    # Update one stage to DEGRADED
    monitor.record_stage_status(
        stage=PipelineStage.FEATURES,
        status=HealthStatus.DEGRADED,
        details={"reason": "Missing volatility indicators for secondary symbols"},
    )

    updated = monitor.get_pipeline_snapshot()
    assert updated.overall_status == HealthStatus.DEGRADED
    assert updated.stages[PipelineStage.FEATURES.value].status == HealthStatus.DEGRADED

    # Update a stage to UNHEALTHY
    monitor.record_stage_status(
        stage=PipelineStage.STORAGE,
        status=HealthStatus.UNHEALTHY,
        details={"reason": "Disk write timeout"},
    )
    unhealthy_snap = monitor.get_pipeline_snapshot()
    assert unhealthy_snap.overall_status == HealthStatus.UNHEALTHY
