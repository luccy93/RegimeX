"""
RegimeX Feature Engineering — Feature Registry Unit Tests
=========================================================
"""

from __future__ import annotations

import pytest
from app.modules.feature_engineering.application.feature_registry import (
    FeatureRegistry,
    get_default_registry,
)
from app.modules.feature_engineering.domain.errors import (
    DuplicateFeatureError,
    FeatureNotFoundError,
)
from app.modules.feature_engineering.infrastructure.calculators.returns import (
    SimpleReturnCalculator,
)


class TestFeatureRegistry:
    def test_register_and_get(self):
        registry = FeatureRegistry()
        calc = SimpleReturnCalculator(1)
        registry.register(calc)

        assert registry.contains("return_1")
        assert len(registry) == 1
        assert registry.get("return_1") is calc

    def test_duplicate_registration_raises(self):
        registry = FeatureRegistry()
        calc = SimpleReturnCalculator(1)
        registry.register(calc)

        with pytest.raises(DuplicateFeatureError) as exc_info:
            registry.register(SimpleReturnCalculator(1))
        assert "return_1" in str(exc_info.value)

    def test_get_non_existent_raises(self):
        registry = FeatureRegistry()
        with pytest.raises(FeatureNotFoundError) as exc_info:
            registry.get("unknown_feat")
        assert "unknown_feat" in str(exc_info.value)

    def test_list_is_sorted(self):
        registry = FeatureRegistry()
        registry.register(SimpleReturnCalculator(5))
        registry.register(SimpleReturnCalculator(1))
        registry.register(SimpleReturnCalculator(10))

        definitions = registry.list()
        names = [d.name for d in definitions]
        assert names == ["return_1", "return_10", "return_5"]

    def test_unregister(self):
        registry = FeatureRegistry()
        calc = SimpleReturnCalculator(1)
        registry.register(calc)
        registry.unregister("return_1")

        assert not registry.contains("return_1")
        assert len(registry) == 0

    def test_unregister_unknown_raises(self):
        registry = FeatureRegistry()
        with pytest.raises(FeatureNotFoundError):
            registry.unregister("not_registered")

    def test_default_registry_baseline_features(self):
        registry = get_default_registry()
        expected = [
            "return_1",
            "return_5",
            "return_10",
            "return_20",
            "volatility_10",
            "volatility_20",
            "volatility_20_annualized",
            "momentum_10",
            "momentum_20",
            "sma_ratio_10",
            "sma_ratio_20",
            "ema_ratio_20",
            "volume_change_1",
            "volume_ratio_20",
            "high_low_range",
            "true_range",
            "normalized_true_range",
        ]
        for name in expected:
            assert registry.contains(name), f"Default registry missing baseline feature: {name}"
