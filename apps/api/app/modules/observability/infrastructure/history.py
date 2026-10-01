"""
RegimeX Observability — Health History Repository
=================================================
In-memory bounded circular storage for historical health measurements and snapshots.

Guarantees:
- Strictly bounded memory: uses collections.deque with maxlen.
- Thread-safe append / inspection via Python GIL guarantees.
- Zero external database dependencies; supports isolated testing.
"""

from __future__ import annotations

from collections import defaultdict, deque

from app.modules.observability.domain.models import (
    DataHealthSnapshot,
    ModelHealthSnapshot,
    ProviderHealthSnapshot,
    SystemHealthSummarySnapshot,
)


class HealthHistoryRepository:
    """
    In-memory bounded history repository for health measurements.
    """

    def __init__(self, limit: int = 50) -> None:
        self._limit = max(5, limit)
        self._data_history: dict[str, deque[DataHealthSnapshot]] = defaultdict(
            lambda: deque(maxlen=self._limit)
        )
        self._model_history: dict[str, deque[ModelHealthSnapshot]] = defaultdict(
            lambda: deque(maxlen=self._limit)
        )
        self._provider_history: dict[str, deque[ProviderHealthSnapshot]] = defaultdict(
            lambda: deque(maxlen=self._limit)
        )
        self._summary_history: deque[SystemHealthSummarySnapshot] = deque(maxlen=self._limit)

    def record_data_health(self, snapshot: DataHealthSnapshot) -> None:
        """Store a data health snapshot for an instrument symbol."""
        key = snapshot.symbol.upper()
        self._data_history[key].append(snapshot)

    def get_data_health_history(self, symbol: str) -> list[DataHealthSnapshot]:
        """Return historical snapshots for an instrument in chronological order."""
        key = symbol.upper()
        return list(self._data_history[key])

    def get_latest_data_health(self, symbol: str) -> DataHealthSnapshot | None:
        """Return the most recent data health snapshot for a symbol."""
        key = symbol.upper()
        history = self._data_history[key]
        return history[-1] if history else None

    def list_monitored_symbols(self) -> list[str]:
        """Return all instrument symbols with recorded health history."""
        return sorted(self._data_history.keys())

    def record_model_health(self, snapshot: ModelHealthSnapshot) -> None:
        """Store a model health snapshot."""
        key = snapshot.model_id.lower()
        self._model_history[key].append(snapshot)

    def get_model_health_history(self, model_id: str) -> list[ModelHealthSnapshot]:
        """Return historical snapshots for a model in chronological order."""
        key = model_id.lower()
        return list(self._model_history[key])

    def get_latest_model_health(self, model_id: str) -> ModelHealthSnapshot | None:
        """Return the most recent snapshot for a model."""
        key = model_id.lower()
        history = self._model_history[key]
        return history[-1] if history else None

    def list_monitored_models(self) -> list[str]:
        """Return all model IDs with recorded health history."""
        return sorted(self._model_history.keys())

    def record_provider_health(self, snapshot: ProviderHealthSnapshot) -> None:
        """Store a provider health snapshot."""
        key = snapshot.provider_id.lower()
        self._provider_history[key].append(snapshot)

    def get_provider_health_history(self, provider_id: str) -> list[ProviderHealthSnapshot]:
        """Return historical snapshots for a provider."""
        key = provider_id.lower()
        return list(self._provider_history[key])

    def get_latest_provider_health(self, provider_id: str) -> ProviderHealthSnapshot | None:
        """Return the most recent snapshot for a provider."""
        key = provider_id.lower()
        history = self._provider_history[key]
        return history[-1] if history else None

    def list_monitored_providers(self) -> list[str]:
        """Return all provider IDs with recorded health history."""
        return sorted(self._provider_history.keys())

    def record_summary(self, snapshot: SystemHealthSummarySnapshot) -> None:
        """Store a system-level summary snapshot."""
        self._summary_history.append(snapshot)

    def get_latest_summary(self) -> SystemHealthSummarySnapshot | None:
        """Return the most recent system health summary."""
        return self._summary_history[-1] if self._summary_history else None

    def clear(self) -> None:
        """Reset all in-memory histories (used primarily in tests)."""
        self._data_history.clear()
        self._model_history.clear()
        self._provider_history.clear()
        self._summary_history.clear()
