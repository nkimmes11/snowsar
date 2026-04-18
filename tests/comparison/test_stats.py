"""Tests for cross-algorithm comparison statistics."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.comparison.stats import compute_pairwise_stats, difference_map
from snowsar.exceptions import AlgorithmError


class TestComputePairwiseStats:
    def test_identical_datasets(self, ds_a: xr.Dataset, ds_identical_to_a: xr.Dataset) -> None:
        stats = compute_pairwise_stats(ds_a, ds_identical_to_a)
        assert stats.bias == pytest.approx(0.0)
        assert stats.rmse == pytest.approx(0.0)
        assert stats.mae == pytest.approx(0.0)
        assert stats.pearson_r == pytest.approx(1.0)
        assert stats.std_ratio == pytest.approx(1.0)
        assert stats.agreement_rate == pytest.approx(1.0)
        assert stats.count > 0

    def test_constant_offset_bias(self, ds_a: xr.Dataset) -> None:
        ds_shifted = ds_a.copy(deep=True)
        ds_shifted["snow_depth"] = ds_shifted["snow_depth"] + np.float32(0.5)
        stats = compute_pairwise_stats(ds_shifted, ds_a)
        assert stats.bias == pytest.approx(0.5, abs=1e-5)
        assert stats.rmse == pytest.approx(0.5, abs=1e-5)
        assert stats.pearson_r == pytest.approx(1.0, abs=1e-5)
        assert stats.std_ratio == pytest.approx(1.0, abs=1e-5)

    def test_valid_only_masks_non_valid(self, ds_a: xr.Dataset, ds_b: xr.Dataset) -> None:
        stats_all = compute_pairwise_stats(ds_a, ds_b, valid_only=False)
        stats_valid = compute_pairwise_stats(ds_a, ds_b, valid_only=True)
        # valid_only drops the seeded WET_SNOW pixel, so count decreases
        assert stats_valid.count < stats_all.count

    def test_missing_variable_raises(self, ds_a: xr.Dataset, ds_b: xr.Dataset) -> None:
        with pytest.raises(AlgorithmError, match="missing"):
            compute_pairwise_stats(ds_a, ds_b, variable="does_not_exist")

    def test_non_overlapping_grids_raise(self, ds_a: xr.Dataset) -> None:
        ds_shifted = ds_a.assign_coords(x=ds_a["x"] + 50, y=ds_a["y"] + 50)
        with pytest.raises(AlgorithmError, match="no overlapping"):
            compute_pairwise_stats(ds_a, ds_shifted)

    def test_agreement_rate_tolerance(self, ds_a: xr.Dataset) -> None:
        ds_shifted = ds_a.copy(deep=True)
        ds_shifted["snow_depth"] = ds_shifted["snow_depth"] + np.float32(0.05)
        # Tolerance 0.1 -> everything within tolerance -> rate == 1
        stats_loose = compute_pairwise_stats(ds_shifted, ds_a, agreement_tolerance_m=0.1)
        # Tolerance 0.01 -> nothing within tolerance -> rate == 0
        stats_tight = compute_pairwise_stats(ds_shifted, ds_a, agreement_tolerance_m=0.01)
        assert stats_loose.agreement_rate == pytest.approx(1.0)
        assert stats_tight.agreement_rate == pytest.approx(0.0)


class TestDifferenceMap:
    def test_returns_dataarray_with_same_shape(self, ds_a: xr.Dataset, ds_b: xr.Dataset) -> None:
        diff = difference_map(ds_a, ds_b)
        assert diff.shape == ds_a["snow_depth"].shape
        assert diff.name == "snow_depth_diff"

    def test_zero_for_identical(self, ds_a: xr.Dataset, ds_identical_to_a: xr.Dataset) -> None:
        diff = difference_map(ds_a, ds_identical_to_a, valid_only=False)
        assert np.allclose(diff.values, 0.0)

    def test_masks_non_valid_when_valid_only(self, ds_a: xr.Dataset, ds_b: xr.Dataset) -> None:
        diff = difference_map(ds_a, ds_b, valid_only=True)
        # Seeded WET_SNOW pixel at [0,0,0] must be NaN
        assert np.isnan(diff.values[0, 0, 0])
