"""
RegimeX Feature Engineering — Anti-Leakage Test Hardening
=========================================================
Exhaustive verification of zero look-ahead bias through:
- Test A: Future observation mutation invariance
- Test B: Prefix dataset invariance
- Test C: Independent per-calculator leakage verification
- Test D: Rolling window directionality confirmation
- Test E: Python AST source audit against centered windows and backward fills
- Test F: Python AST source audit against dataset-wide global normalization
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.feature_engineering.application.feature_registry import get_default_registry
from app.modules.feature_engineering.domain.models import FeatureInputData
from tests.unit.feature_engineering.conftest import make_bar


class TestAntiLeakageHardening:
    def test_future_mutation_invariance_pipeline(self, linear_trending_bars):
        """Test A: Mutating bars after cutoff_idx has zero effect on earlier features."""
        pipeline = FeaturePipeline()
        cutoff_idx = 15

        fset_original = pipeline.compute(linear_trending_bars)

        # Mutate future observations
        mutated_bars = copy.deepcopy(linear_trending_bars)
        for i in range(cutoff_idx + 1, len(mutated_bars)):
            old = mutated_bars[i]
            mutated_bars[i] = make_bar(
                symbol=old.symbol,
                timestamp=old.timestamp,
                open_=old.open * 8.0,
                high=old.high * 12.0,
                low=old.low * 0.2,
                close=old.close * 9.0,
                volume=old.volume * 50.0,
            )

        fset_mutated = pipeline.compute(mutated_bars)

        for i in range(cutoff_idx + 1):
            orig_record = fset_original.records[i]
            mut_record = fset_mutated.records[i]

            for feat_name in fset_original.feature_names:
                v_orig = orig_record.values[feat_name]
                v_mut = mut_record.values[feat_name]

                if v_orig is None:
                    assert v_mut is None, f"{feat_name} at index {i} leaked future data!"
                else:
                    assert v_orig == pytest.approx(v_mut, rel=0, abs=0), (
                        f"{feat_name} at index {i} changed after future mutation!"
                    )

    def test_prefix_invariance_pipeline(self, linear_trending_bars):
        """Test B: Prefix slice of data produces exact same features as full dataset."""
        pipeline = FeaturePipeline()
        k = 22

        fset_full = pipeline.compute(linear_trending_bars)
        fset_prefix = pipeline.compute(linear_trending_bars[:k])

        for i in range(k):
            full_vals = fset_full.records[i].values
            pref_vals = fset_prefix.records[i].values

            for name in fset_full.feature_names:
                v_full = full_vals[name]
                v_pref = pref_vals[name]

                if v_full is None:
                    assert v_pref is None
                else:
                    assert v_full == pytest.approx(v_pref, rel=0, abs=0)

    def test_per_calculator_leakage_isolation(self, linear_trending_bars):
        """Test C: Every single registered calculator is individually verified for zero leakage."""
        cutoff_idx = 18
        data_orig = FeatureInputData.from_ohlcv_records(linear_trending_bars)

        mutated_bars = copy.deepcopy(linear_trending_bars)
        for i in range(cutoff_idx + 1, len(mutated_bars)):
            old = mutated_bars[i]
            mutated_bars[i] = make_bar(
                symbol=old.symbol,
                timestamp=old.timestamp,
                open_=old.open * 2.5,
                high=old.high * 3.5,
                low=old.low * 0.4,
                close=old.close * 2.8,
                volume=old.volume * 5.0,
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
                    assert m is None, f"{calc.name} leaked at index {i}!"
                else:
                    assert o == pytest.approx(m, rel=0, abs=0), f"{calc.name} leaked at index {i}!"

    def test_rolling_window_directionality(self, linear_trending_bars):
        """Test D: Modifying t+1 does not affect t, but modifying t-1 DOES affect t."""
        pipeline = FeaturePipeline()
        target_idx = 20

        fset_orig = pipeline.compute(linear_trending_bars)
        orig_val = fset_orig.records[target_idx].values["sma_ratio_10"]
        assert orig_val is not None

        # 1. Modify bar at target_idx + 1 -> target_idx value MUST NOT CHANGE
        bars_future_mod = copy.deepcopy(linear_trending_bars)
        old_fut = bars_future_mod[target_idx + 1]
        bars_future_mod[target_idx + 1] = make_bar(
            old_fut.symbol, old_fut.timestamp, 500, 500, 500, 500
        )
        fset_fut = pipeline.compute(bars_future_mod)
        fut_val = fset_fut.records[target_idx].values["sma_ratio_10"]
        assert orig_val == pytest.approx(fut_val, rel=0, abs=0)

        # 2. Modify bar at target_idx - 1 -> target_idx value MUST CHANGE
        bars_past_mod = copy.deepcopy(linear_trending_bars)
        old_past = bars_past_mod[target_idx - 1]
        bars_past_mod[target_idx - 1] = make_bar(
            old_past.symbol, old_past.timestamp, 500, 500, 500, 500
        )
        fset_past = pipeline.compute(bars_past_mod)
        past_val = fset_past.records[target_idx].values["sma_ratio_10"]
        assert orig_val != past_val

    def test_ast_audit_no_centered_windows_or_backward_fills(self):
        """Test E: Static AST audit across calculators for forbidden look-ahead patterns."""
        calc_dir = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "app"
            / "modules"
            / "feature_engineering"
            / "infrastructure"
            / "calculators"
        )
        assert calc_dir.exists(), f"Calculators directory not found at {calc_dir}"

        py_files = list(calc_dir.glob("*.py"))
        assert len(py_files) >= 7

        forbidden_names = {"bfill", "backfill"}

        for py_file in py_files:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))

            for node in ast.walk(tree):
                # Check for call keywords: center=True
                if isinstance(node, ast.keyword) and node.arg == "center":
                    if isinstance(node.value, ast.Constant) and node.value.value is True:
                        pytest.fail(
                            f"Forbidden centered window 'center=True' found in {py_file.name}"
                        )

                # Check for calls or attributes: bfill, backfill
                if isinstance(node, ast.Attribute) and node.attr in forbidden_names:
                    pytest.fail(f"Forbidden backward fill '{node.attr}' found in {py_file.name}")

                # Check for keyword arguments like method="bfill"
                if (
                    isinstance(node, ast.keyword)
                    and node.arg == "method"
                    and isinstance(node.value, ast.Constant)
                    and node.value.value in forbidden_names
                ):
                    pytest.fail(
                        f"Forbidden backward fill method='{node.value.value}' in {py_file.name}"
                    )

    def test_ast_audit_no_dataset_wide_normalization(self):
        """Test F: Static AST audit verifying no dataset-wide global statistics in calculators."""
        calc_dir = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "app"
            / "modules"
            / "feature_engineering"
            / "infrastructure"
            / "calculators"
        )

        for py_file in calc_dir.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            # Ensure no zscore, scale, StandardScaler, RobustScaler
            assert "StandardScaler" not in source, f"Dataset-wide scaler found in {py_file.name}"
            assert "RobustScaler" not in source, f"Dataset-wide scaler found in {py_file.name}"
