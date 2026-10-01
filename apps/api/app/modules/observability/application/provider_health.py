"""
RegimeX Observability — Provider Health Monitor
===============================================
Tracks operational metrics and health status for upstream market data providers.

Guarantees:
- Bounded provider identifiers.
- Never stores arbitrary exception messages, API keys, or credentials.
- Purely operational monitoring: does not modify provider execution behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.observability.domain.enums import ProviderStatus
from app.modules.observability.domain.models import ProviderHealthSnapshot


class ProviderMetricsAccumulator:
    """
    In-memory state tracker for a single provider's operational requests.
    """

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.consecutive_failures = 0
        self.total_latency_ms = 0.0
        self.last_successful_request: datetime | None = None
        self.last_failure: datetime | None = None
        self.last_error_category: str | None = None

    def record(
        self,
        success: bool,
        latency_ms: float,
        error_category: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        ts = timestamp or datetime.now(tz=UTC)
        self.request_count += 1
        self.total_latency_ms += max(0.0, latency_ms)

        if success:
            self.success_count += 1
            self.consecutive_failures = 0
            self.last_successful_request = ts
        else:
            self.failure_count += 1
            self.consecutive_failures += 1
            self.last_failure = ts
            self.last_error_category = (error_category or "unknown_error").strip().lower()[:50]

    def to_snapshot(self) -> ProviderHealthSnapshot:
        if self.request_count == 0:
            status = ProviderStatus.UNKNOWN
            fail_rate = 0.0
            avg_lat = 0.0
        else:
            fail_rate = float(self.failure_count / self.request_count)
            avg_lat = float(self.total_latency_ms / self.request_count)

            if self.consecutive_failures >= 3 or (self.request_count >= 4 and fail_rate >= 0.25):
                status = ProviderStatus.UNAVAILABLE
            elif self.consecutive_failures > 0 or fail_rate > 0.05 or avg_lat > 3000.0:
                status = ProviderStatus.DEGRADED
            else:
                status = ProviderStatus.AVAILABLE

        return ProviderHealthSnapshot(
            provider_id=self.provider_id,
            status=status,
            request_count=self.request_count,
            success_count=self.success_count,
            failure_count=self.failure_count,
            consecutive_failures=self.consecutive_failures,
            failure_rate=fail_rate,
            avg_latency_ms=avg_lat,
            last_successful_request=self.last_successful_request,
            last_failure=self.last_failure,
            last_error_category=self.last_error_category,
        )


class ProviderHealthMonitor:
    """
    Registry of provider accumulators monitoring all configured market data providers.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ProviderMetricsAccumulator] = {}

    def _get_or_create(self, provider_id: str) -> ProviderMetricsAccumulator:
        pid = provider_id.strip().lower()
        if pid not in self._providers:
            self._providers[pid] = ProviderMetricsAccumulator(pid)
        return self._providers[pid]

    def record_request(
        self,
        provider_id: str,
        success: bool,
        latency_ms: float = 0.0,
        error_category: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record an operation result for a market data provider."""
        acc = self._get_or_create(provider_id)
        acc.record(
            success=success,
            latency_ms=latency_ms,
            error_category=error_category,
            timestamp=timestamp,
        )

    def get_provider_snapshot(self, provider_id: str) -> ProviderHealthSnapshot:
        """Evaluate and return a provider health snapshot."""
        acc = self._get_or_create(provider_id)
        return acc.to_snapshot()

    def get_all_snapshots(self) -> list[ProviderHealthSnapshot]:
        """Return health snapshots for all monitored providers."""
        return [acc.to_snapshot() for acc in self._providers.values()]
