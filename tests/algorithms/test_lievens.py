"""Tests for the Lievens empirical change-detection algorithm."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.algorithms.lievens import (
    LievensAlgorithm,
    apply_fcf_weighting,
    compute_cross_pol_ratio,
    compute_reference_backscatter,
    generate_quality_flags,
    scale_to_snow_depth,
    temporal_aggregate,
)
from snowsar.types import AlgorithmID, Backend, QualityFlag


class TestLievensAlgorithm:
    def test_algorithm_metadata(self) -> None:
        algo = LievensAlgorithm()
        assert algo.algorithm_id == AlgorithmID.LIEVENS
        assert algo.name != ""
        assert Backend.GEE in algo.supported_backends
        assert Backend.LOCAL in algo.supported_backends

    def test_validate_input(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = LievensAlgorithm()
        algo.validate_input(synthetic_sar_dataset)  # should not raise

    def test_validate_input_missing_vars(self) -> None:
        algo = LievensAlgorithm()
        ds = xr.Dataset({"gamma0_vv": xr.DataArray([1.0])})
        with pytest.raises(ValueError, match="missing required variables"):
            algo.validate_input(ds)

    def test_run_returns_required_outputs(
        self, synthetic_sar_dataset: xr.Dataset
    ) -> None:
        algo = LievensAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        assert "snow_depth" in result
        assert "quality_flag" in result
        assert "uncertainty" in result

    def test_run_output_dimensions_match_input(
        self, synthetic_sar_dataset: xr.Dataset
    ) -> None:
        algo = LievensAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        assert set(result["snow_depth"].dims) == set(synthetic_sar_dataset["gamma0_vv"].dims)
        for dim in synthetic_sar_dataset["gamma0_vv"].dims:
            assert result["snow_depth"].sizes[dim] == synthetic_sar_dataset["gamma0_vv"].sizes[dim]

    def test_run_snow_depth_non_negative(
        self, synthetic_sar_dataset: xr.Dataset
    ) -> None:
        algo = LievensAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        valid = result["snow_depth"].values[~np.isnan(result["snow_depth"].values)]
        assert (valid >= 0).all()

    def test_run_with_custom_params(
        self, synthetic_sar_dataset: xr.Dataset
    ) -> None:
        algo = LievensAlgorithm()
        result = algo.run(
            synthetic_sar_dataset,
            params={"coeff_a": 1.0, "coeff_b": 0.0, "coeff_c": 0.0},
        )
        assert "snow_depth" in result

    def test_run_preserves_attributes(
        self, synthetic_sar_dataset: xr.Dataset
    ) -> None:
        algo = LievensAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        assert result.attrs["algorithm"] == "lievens"
        assert "crs" in result.attrs


class TestCrossPolarizationRatio:
    def test_cr_computation(self) -> None:
        vh = xr.DataArray([-20.0, -18.0, -22.0])
        vv = xr.DataArray([-10.0, -8.0, -12.0])
        cr = compute_cross_pol_ratio(vh, vv)
        np.testing.assert_allclose(cr.values, [-10.0, -10.0, -10.0])

    def test_cr_shape_preserved(self, synthetic_sar_dataset: xr.Dataset) -> None:
        cr = compute_cross_pol_ratio(
            synthetic_sar_dataset["gamma0_vh"],
            synthetic_sar_dataset["gamma0_vv"],
        )
        assert cr.shape == synthetic_sar_dataset["gamma0_vh"].shape


class TestReferenceBackscatter:
    def test_default_uses_first_timestep(
        self, synthetic_sar_dataset: xr.Dataset
    ) -> None:
        cr = compute_cross_pol_ratio(
            synthetic_sar_dataset["gamma0_vh"],
            synthetic_sar_dataset["gamma0_vv"],
        )
        cr_ref, vv_ref = compute_reference_backscatter(
            synthetic_sar_dataset, cr, reference_period=None
        )
        # Should be 2D (no time dimension)
        assert "time" not in cr_ref.dims
        assert "time" not in vv_ref.dims


class TestFCFWeighting:
    def test_no_forest(self) -> None:
        delta_cr = xr.DataArray([1.0, 2.0])
        delta_vv = xr.DataArray([0.5, 1.0])
        fcf = xr.DataArray([0.0, 0.0])
        result = apply_fcf_weighting(delta_cr, delta_vv, fcf)
        # With FCF=0, result should equal delta_cr
        np.testing.assert_allclose(result.values, delta_cr.values)

    def test_full_forest(self) -> None:
        delta_cr = xr.DataArray([1.0, 2.0])
        delta_vv = xr.DataArray([0.5, 1.0])
        fcf = xr.DataArray([1.0, 1.0])
        result = apply_fcf_weighting(delta_cr, delta_vv, fcf)
        # With FCF=1, result should equal delta_vv
        np.testing.assert_allclose(result.values, delta_vv.values)

    def test_mixed_forest(self) -> None:
        delta_cr = xr.DataArray([2.0])
        delta_vv = xr.DataArray([1.0])
        fcf = xr.DataArray([0.5])
        result = apply_fcf_weighting(delta_cr, delta_vv, fcf)
        np.testing.assert_allclose(result.values, [1.5])  # 0.5*2 + 0.5*1


class TestTemporalAggregate:
    def test_single_timestep(self) -> None:
        da = xr.DataArray([[1.0, 2.0]], dims=["time", "x"], coords={"time": [0]})
        result = temporal_aggregate(da, alpha=0.5)
        np.testing.assert_allclose(result.values, [[1.0, 2.0]])

    def test_recursive_filter(self) -> None:
        da = xr.DataArray(
            [[1.0], [1.0], [1.0]],
            dims=["time", "x"],
            coords={"time": [0, 1, 2]},
        )
        result = temporal_aggregate(da, alpha=0.5)
        # t=0: 1.0, t=1: 0.5*1 + 0.5*1 = 1.0, t=2: 0.5*1 + 0.5*1 = 1.0
        np.testing.assert_allclose(result.values, [[1.0], [1.0], [1.0]])

    def test_accumulation(self) -> None:
        da = xr.DataArray(
            [[2.0], [0.0], [0.0]],
            dims=["time", "x"],
            coords={"time": [0, 1, 2]},
        )
        result = temporal_aggregate(da, alpha=0.5)
        # t=0: 2.0, t=1: 0.5*0 + 0.5*2 = 1.0, t=2: 0.5*0 + 0.5*1 = 0.5
        np.testing.assert_allclose(result.values, [[2.0], [1.0], [0.5]])


class TestScaleToSnowDepth:
    def test_zero_index(self) -> None:
        si = xr.DataArray([0.0])
        sd = scale_to_snow_depth(si, a=2.0, b=0.5, c=0.1)
        np.testing.assert_allclose(sd.values, [0.1])

    def test_negative_clipped(self) -> None:
        si = xr.DataArray([-10.0])
        sd = scale_to_snow_depth(si, a=1.0, b=0.0, c=0.0)
        assert float(sd.values[0]) == 0.0

    def test_positive_index(self) -> None:
        si = xr.DataArray([1.0])
        sd = scale_to_snow_depth(si, a=2.0, b=0.5, c=0.1)
        # 2*1 + 0.5*1 + 0.1 = 2.6
        np.testing.assert_allclose(sd.values, [2.6])


class TestQualityFlags:
    def test_all_valid(self) -> None:
        ds = xr.Dataset({
            "snow_cover": xr.DataArray([1, 1]),
            "forest_cover_fraction": xr.DataArray([0.1, 0.2]),
        })
        sd = xr.DataArray([1.0, 2.0])
        flags = generate_quality_flags(ds, sd, fcf_threshold=0.5)
        assert (flags.values == QualityFlag.VALID).all()

    def test_high_forest_flagged(self) -> None:
        ds = xr.Dataset({
            "snow_cover": xr.DataArray([1]),
            "forest_cover_fraction": xr.DataArray([0.8]),
        })
        sd = xr.DataArray([1.0])
        flags = generate_quality_flags(ds, sd, fcf_threshold=0.5)
        assert int(flags.values[0]) == QualityFlag.HIGH_FOREST
