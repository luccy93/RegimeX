"""
RegimeX Feature Engineering — No Look-Ahead Bias Regression Tests
================================================================
MANDATORY ARCHITECTURAL VERIFICATION:
Guarantees that every feature at timestamp t depends strictly on observations <= t.
Future observations (t+1, t+2, ...) must NEVER affect past or present feature values.
"""

from __future__ import annotations

import copy

import pytest
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.feature_engineering.application.feature_registry import get_default_registry
from app.modules.feature_engineering.domain.models import FeatureInputData
from tests.unit.feature_engineering.conftest import make_bar


class TestNoLookAheadBias:
    def test_future_bar_mutation_invariance_all_features(self, linear_trending_bars):
        """
        Hard platform invariant:
        Features computed for bars 0..t must be bit-for-bit identical regardless of
        how bars t+1..N are modified.
        """
        pipeline = FeaturePipeline()
        cutoff_idx = 20

        # Run 1: original dataset
        fset_original = pipeline.compute(linear_trending_bars)

        # Run 2: create modified copy where observations after cutoff_idx are radically mutated
        mutated_bars = copy.deepcopy(linear_trending_bars)
        for i in range(cutoff_idx + 1, len(mutated_bars)):
            old = mutated_bars[i]
            # Radically shock price and volume
            mutated_bars[i] = make_bar(
                symbol=old.symbol,
                timestamp=old.timestamp,
                open_=old.open * 5.0,
                high=old.high * 10.0,
                low=old.low * 0.1,
                close=old.close * 7.5,
                volume=old.volume * 100.0,
            )

        fset_mutated = pipeline.compute(mutated_bars)

        assert fset_original.record_count == fset_mutated.record_count

        # For every bar up to and including cutoff_idx, all feature values must be IDENTICAL
        for i in range(cutoff_idx + 1):
            orig_vals = fset_original.records[i].values
            mutated_vals = fset_mutated.records[i].values

            assert orig_vals.keys() == mutated_vals.keys()

            for feat_name, orig_val in orig_vals.items():
                mut_val = mutated_vals[feat_name]
                if orig_val is None:
                    assert mut_val is None, (
                        f"Look-ahead violation for {feat_name} at index {i}: "
                        f"original was None, mutated became {mut_val}"
                    )
                else:
                    assert orig_val == pytest.approx(mut_val, rel=0, abs=0), (
                        f"Look-ahead violation for {feat_name} at index {i}: "
                        f"original={orig_val}, mutated={mut_val}"
                    )

    def test_prefix_slice_invariance(self, linear_trending_bars):
        """
        Computing features on a prefix slice [0..k] must yield the exact same records
        as the first k records of [0..N].
        """
        pipeline = FeaturePipeline()
        k = 25

        fset_full = pipeline.compute(linear_trending_bars)
        fset_prefix = pipeline.compute(linear_trending_bars[:k])

        assert fset_prefix.record_count == k

        for i in range(k):
            full_vals = fset_full.records[i].values
            prefix_vals = fset_prefix.records[i].values

            for feat_name, full_val in full_vals.items():
                pref_val = prefix_vals[feat_name]
                if full_val is None:
                    assert pref_val is None
                else:
                    assert full_val == pytest.approx(pref_val, rel=0, abs=0)

    def test_all_individual_calculators_zero_lookahead(self, linear_trending_bars):
        """
        Verify every individual calculator registered in the default registry
        adheres to the zero-lookahead invariant.
        """
        cutoff_idx = 20
        data_orig = FeatureInputData.from_ohlcv_records(linear_trending_bars)

        # Build mutated FeatureInputData
        mutated_bars = copy.deepcopy(linear_trending_bars)
        for i in range(cutoff_idx + 1, len(mutated_bars)):
            old = mutated_bars[i]
            mutated_bars[i] = make_bar(
                symbol=old.symbol,
                timestamp=old.timestamp,
                open_=old.open * 3.0,
                high=old.high * 4.0,
                low=old.low * 0.5,
                close=old.close * 2.0,
                volume=old.volume * 10.0,
            )
        data_mut = FeatureInputData.from_ohlcv_records(mutated_bars)

        registry = get_default_registry()
        for feat_def in registry.list():
            calc = registry.get(feat_def.name)
            res_orig = calc.calculate(data_orig)
            res_mut = calc.calculate(data_mut)

            assert len(res_orig) == len(res_mut)

            for i in range(cutoff_idx + 1):
                o = res_orig[i]
                m = res_mut[i]
                if o is None:
                    assert m is None, (
                        f"Calculator {calc.name} violated look-ahead at index {i}: "
                        f"orig was None, mutated was {m}"
                    )
                else:
                    assert o == pytest.approx(m, rel=0, abs=0), (
                        f"Calculator {calc.name} violated look-ahead at index {i}: "
                        f"orig={o}, mutated={m}"
                    )
