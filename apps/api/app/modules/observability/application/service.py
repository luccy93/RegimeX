"""
RegimeX Observability — Health Monitoring Orchestration Service
===============================================================
Central service coordinating data health, model health, provider health, pipeline
tracking, and historical snapshot buffers.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.modules.data_quality.domain.models import QualityReport
from app.modules.observability.application.data_health import DataHealthMonitor
from app.modules.observability.application.model_health import ModelHealthMonitor
from app.modules.observability.application.pipeline_health import PipelineHealthMonitor
from app.modules.observability.application.provider_health import ProviderHealthMonitor
from app.modules.observability.domain.enums import HealthStatus, ProviderStatus
from app.modules.observability.domain.models import (
    DataHealthSnapshot,
    ModelHealthSnapshot,
    PipelineHealthSnapshot,
    ProviderHealthSnapshot,
    SystemHealthSummarySnapshot,
)
from app.modules.observability.infrastructure.history import HealthHistoryRepository


class HealthMonitoringService:
    """
    Central orchestration facade for all operational health monitoring.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        history_repo: HealthHistoryRepository | None = None,
    ) -> None:
        cfg = settings or get_settings()
        self.settings = cfg
        self.history = history_repo or HealthHistoryRepository(
            limit=cfg.observability_history_limit
        )

        self.data_monitor = DataHealthMonitor(
            default_calendar_id="nyse",
            freshness_threshold_seconds=float(cfg.data_freshness_threshold_seconds),
            stale_threshold_seconds=float(cfg.data_stale_threshold_seconds),
        )
        self.provider_monitor = ProviderHealthMonitor()
        self.pipeline_monitor = PipelineHealthMonitor()
        self.model_monitor = ModelHealthMonitor(
            health_window=cfg.model_health_window,
            low_confidence_threshold=cfg.model_low_confidence_threshold,
            drift_threshold=cfg.model_drift_threshold,
        )

    # -------------------------------------------------------------------------
    # Data Health Methods
    # -------------------------------------------------------------------------

    def record_data_health_evaluation(
        self,
        symbol: str,
        latest_observation_time: datetime | None,
        expected_rows: int,
        received_rows: int,
        missing_rows: int = 0,
        duplicate_rows: int = 0,
        validation_report: QualityReport | None = None,
        provider_id: str | None = None,
        calendar_id: str = "nyse",
    ) -> DataHealthSnapshot:
        """Evaluate and persist a data health snapshot for a market instrument."""
        freshness = self.data_monitor.evaluate_freshness(
            latest_observation_time=latest_observation_time,
            calendar_id=calendar_id,
        )
        completeness = self.data_monitor.evaluate_completeness(
            expected_rows=expected_rows,
            received_rows=received_rows,
            missing_rows=missing_rows,
            duplicate_rows=duplicate_rows,
        )
        validity = self.data_monitor.evaluate_validity(report=validation_report)

        provider_snapshot = (
            self.provider_monitor.get_provider_snapshot(provider_id) if provider_id else None
        )
        pipeline_snapshot = self.pipeline_monitor.get_pipeline_snapshot()

        snapshot = self.data_monitor.evaluate_data_health(
            symbol=symbol,
            freshness=freshness,
            completeness=completeness,
            validity=validity,
            provider=provider_snapshot,
            pipeline=pipeline_snapshot,
        )
        self.history.record_data_health(snapshot)
        return snapshot

    def get_data_health(self, symbol: str) -> DataHealthSnapshot:
        """
        Retrieve the latest data health snapshot for a symbol, or synthesize
        a default baseline if not yet evaluated.
        """
        existing = self.history.get_latest_data_health(symbol)
        if existing is not None:
            return existing

        # Synthesize baseline snapshot
        freshness = self.data_monitor.evaluate_freshness(latest_observation_time=None)
        completeness = self.data_monitor.evaluate_completeness(expected_rows=0, received_rows=0)
        validity = self.data_monitor.evaluate_validity(report=None)
        pipeline = self.pipeline_monitor.get_pipeline_snapshot()

        snapshot = self.data_monitor.evaluate_data_health(
            symbol=symbol,
            freshness=freshness,
            completeness=completeness,
            validity=validity,
            pipeline=pipeline,
        )
        self.history.record_data_health(snapshot)
        return snapshot

    def list_all_data_health(self) -> list[DataHealthSnapshot]:
        """List latest data health snapshots across all monitored instruments."""
        symbols = self.history.list_monitored_symbols()
        if not symbols:
            # Provide SPY default baseline if empty
            default_spy = self.get_data_health("SPY")
            return [default_spy]
        return [self.get_data_health(sym) for sym in symbols]

    # -------------------------------------------------------------------------
    # Model Health Methods
    # -------------------------------------------------------------------------

    def record_model_health_evaluation(
        self,
        model_id: str,
        predictions: Sequence[int],
        k_clusters: int,
        probabilities: Sequence[Sequence[float] | None] | None = None,
        confidences: Sequence[float | None] | None = None,
        reference_predictions: Sequence[int] | None = None,
    ) -> ModelHealthSnapshot:
        """Evaluate and persist a model health snapshot."""
        snapshot = self.model_monitor.evaluate_model_health(
            model_id=model_id,
            predictions=predictions,
            k_clusters=k_clusters,
            probabilities=probabilities,
            confidences=confidences,
            reference_predictions=reference_predictions,
        )
        self.history.record_model_health(snapshot)
        return snapshot

    def get_model_health(self, model_id: str) -> ModelHealthSnapshot:
        """
        Retrieve latest model health snapshot for a model, or synthesize
        a default baseline if not yet evaluated.
        """
        existing = self.history.get_latest_model_health(model_id)
        if existing is not None:
            return existing

        # Synthesize baseline snapshot for model
        snapshot = self.model_monitor.evaluate_model_health(
            model_id=model_id,
            predictions=(),
            k_clusters=4,
        )
        self.history.record_model_health(snapshot)
        return snapshot

    def list_all_model_health(self) -> list[ModelHealthSnapshot]:
        """List latest health snapshots across all standard regime models."""
        standard_models = ["kmeans", "gmm", "hmm", "ensemble"]
        results: list[ModelHealthSnapshot] = []
        for mid in standard_models:
            results.append(self.get_model_health(mid))
        return results

    # -------------------------------------------------------------------------
    # Provider & Pipeline Methods
    # -------------------------------------------------------------------------

    def record_provider_request(
        self,
        provider_id: str,
        success: bool,
        latency_ms: float = 0.0,
        error_category: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record an operational request for an upstream provider."""
        self.provider_monitor.record_request(
            provider_id=provider_id,
            success=success,
            latency_ms=latency_ms,
            error_category=error_category,
            timestamp=timestamp,
        )

    def get_provider_health(self, provider_id: str) -> ProviderHealthSnapshot:
        """Retrieve health snapshot for an upstream provider."""
        return self.provider_monitor.get_provider_snapshot(provider_id)

    def list_all_providers_health(self) -> list[ProviderHealthSnapshot]:
        """List health snapshots for all monitored providers."""
        snaps = self.provider_monitor.get_all_snapshots()
        if not snaps:
            # Return baseline yahoo_finance provider
            return [self.provider_monitor.get_provider_snapshot("yahoo_finance")]
        return snaps

    def get_pipeline_health(self) -> PipelineHealthSnapshot:
        """Retrieve consolidated data pipeline health snapshot."""
        return self.pipeline_monitor.get_pipeline_snapshot()

    # -------------------------------------------------------------------------
    # System Summary Method
    # -------------------------------------------------------------------------

    def get_system_summary(self) -> SystemHealthSummarySnapshot:
        """
        Aggregate operational health status across data, models, providers, and pipelines.
        """
        data_snaps = self.list_all_data_health()
        model_snaps = self.list_all_model_health()
        provider_snaps = self.list_all_providers_health()
        pipeline_snap = self.get_pipeline_health()

        # Compute composite status for each domain
        def _aggregate_status(statuses: Sequence[HealthStatus]) -> HealthStatus:
            if HealthStatus.UNHEALTHY in statuses:
                return HealthStatus.UNHEALTHY
            if HealthStatus.STALE in statuses:
                return HealthStatus.STALE
            if HealthStatus.DEGRADED in statuses:
                return HealthStatus.DEGRADED
            if all(s == HealthStatus.HEALTHY for s in statuses):
                return HealthStatus.HEALTHY
            return HealthStatus.UNKNOWN

        data_status = _aggregate_status([d.status for d in data_snaps])
        model_status = _aggregate_status([m.status for m in model_snaps])

        prov_statuses = [p.status for p in provider_snaps]
        if ProviderStatus.UNAVAILABLE in prov_statuses:
            overall_prov = ProviderStatus.UNAVAILABLE
        elif ProviderStatus.DEGRADED in prov_statuses:
            overall_prov = ProviderStatus.DEGRADED
        elif all(p == ProviderStatus.AVAILABLE for p in prov_statuses):
            overall_prov = ProviderStatus.AVAILABLE
        else:
            overall_prov = ProviderStatus.UNKNOWN

        # Consolidated platform status
        dom_statuses = [data_status, model_status, pipeline_snap.overall_status]
        if overall_prov == ProviderStatus.UNAVAILABLE:
            dom_statuses.append(HealthStatus.UNHEALTHY)
        elif overall_prov == ProviderStatus.DEGRADED:
            dom_statuses.append(HealthStatus.DEGRADED)

        system_status = _aggregate_status(dom_statuses)

        active_models = tuple(m.model_id for m in model_snaps)
        active_providers = tuple(p.provider_id for p in provider_snaps)

        summary_snap = SystemHealthSummarySnapshot(
            status=system_status,
            timestamp=datetime.now(tz=UTC),
            data_health_status=data_status,
            model_health_status=model_status,
            provider_status=overall_prov,
            pipeline_status=pipeline_snap.overall_status,
            active_models=active_models,
            active_providers=active_providers,
            details={
                "monitored_data_symbols": [d.symbol for d in data_snaps],
                "models_count": len(model_snaps),
                "providers_count": len(provider_snaps),
                "pipeline_stages_count": len(pipeline_snap.stages),
            },
        )
        self.history.record_summary(summary_snap)
        return summary_snap


# Global singleton instance for application use
_default_health_service: HealthMonitoringService | None = None


def get_health_monitoring_service() -> HealthMonitoringService:
    """Return the global HealthMonitoringService singleton."""
    global _default_health_service
    if _default_health_service is None:
        _default_health_service = HealthMonitoringService()
    return _default_health_service
