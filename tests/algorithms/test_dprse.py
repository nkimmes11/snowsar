"""Tests for the DpRSE dual-polarimetric snow depth algorithm."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.algorithms.dprse import (
    DpRSEAlgorithm,
    apply_conditioning_factor,
    compute_coherency_elements,
    compute_degree_of_polarization,
    compute_dprvi,
    compute_soil_purity,
    generate_quality_flags,
    regression_to_snow_depth,
)
from snowsar.types import AlgorithmID, Backend, QualityFlag


class TestDpRSEAlgorithm:
    def test_algorithm_metadata(self) -> None:
        algo = DpRSEAlgorithm()
        assert algo.algorithm_id == AlgorithmID.DPRSE
        assert algo.name != ""
        assert Backend.GEE in algo.supported_backends
        assert Backend.LOCAL in algo.supported_backends

    def test_validate_input(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        algo.validate_input(synthetic_sar_dataset)  # should not raise

    def test_validate_input_missing_vars(self) -> None:
        algo = DpRSEAlgorithm()
        ds = xr.Dataset({"gamma0_vv": xr.DataArray([1.0])})
        with pytest.raises(ValueError, match="missing required variables"):
            algo.validate_input(ds)

    def test_run_returns_required_outputs(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        assert "snow_depth" in result
        assert "quality_flag" in result
        assert "uncertainty" in result

    def test_run_output_dimensions_match_input(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        assert set(result["snow_depth"].dims) == set(synthetic_sar_dataset["gamma0_vv"].dims)
        for dim in synthetic_sar_dataset["gamma0_vv"].dims:
            assert result["snow_depth"].sizes[dim] == synthetic_sar_dataset["gamma0_vv"].sizes[dim]

    def test_run_snow_depth_non_negative(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        valid = result["snow_depth"].values[~np.isnan(result["snow_depth"].values)]
        assert (valid >= 0).all()

    def test_run_with_custom_params(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(
            synthetic_sar_dataset,
            params={"regression_slope": 3.0, "regression_intercept": 0.0},
        )
        assert "snow_depth" in result

    def test_run_preserves_attributes(self, synthetic_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(synthetic_sar_dataset)
        assert result.attrs["algorithm"] == "dprse"
        assert "crs" in result.attrs


class TestCoherencyElements:
    def test_span_is_sum(self) -> None:
        vv = xr.DataArray([1.0, 2.0, 3.0])
        vh = xr.DataArray([0.5, 1.0, 1.5])
        _c11, _c22, span = compute_coherency_elements(vv, vh)
        np.testing.assert_allclose(span.values, [1.5, 3.0, 4.5])

    def test_c11_is_vv(self) -> None:
        vv = xr.DataArray([1.0, 2.0])
        vh = xr.DataArray([0.5, 1.0])
        c11, _, _ = compute_coherency_elements(vv, vh)
        np.testing.assert_allclose(c11.values, vv.values)


class TestDegreeOfPolarization:
    def test_equal_channels_gives_zero(self) -> None:
        """Equal power in both channels = fully depolarized = DoP 0."""
        c11 = xr.DataArray([1.0, 1.0])
        c22 = xr.DataArray([1.0, 1.0])
        span = c11 + c22
        dop = compute_degree_of_polarization(c11, c22, span)
        np.testing.assert_allclose(dop.values, [0.0, 0.0])

    def test_single_channel_gives_one(self) -> None:
        """All power in one channel = fully polarized = DoP 1."""
        c11 = xr.DataArray([1.0])
        c22 = xr.DataArray([0.0])
        span = c11 + c22
        dop = compute_degree_of_polarization(c11, c22, span)
        np.testing.assert_allclose(dop.values, [1.0])

    def test_clipped_to_0_1(self) -> None:
        c11 = xr.DataArray([0.3])
        c22 = xr.DataArray([0.7])
        span = c11 + c22
        dop = compute_degree_of_polarization(c11, c22, span)
        assert float(dop.values[0]) >= 0.0
        assert float(dop.values[0]) <= 1.0


class TestSoilPurity:
    def test_all_copol(self) -> None:
        """All power in co-pol = soil purity 1."""
        c11 = xr.DataArray([1.0])
        span = xr.DataArray([1.0])
        purity = compute_soil_purity(c11, span)
        np.testing.assert_allclose(purity.values, [1.0])

    def test_equal_channels(self) -> None:
        """Equal power = soil purity 0.5."""
        c11 = xr.DataArray([1.0])
        span = xr.DataArray([2.0])
        purity = compute_soil_purity(c11, span)
        np.testing.assert_allclose(purity.values, [0.5])

    def test_zero_span_safe(self) -> None:
        """Zero span should not produce NaN/Inf."""
        c11 = xr.DataArray([0.0])
        span = xr.DataArray([0.0])
        purity = compute_soil_purity(c11, span)
        assert np.isfinite(purity.values[0])


class TestDpRVI:
    def test_fully_polarized_gives_low_dprvi(self) -> None:
        """Fully polarized signal (DoP=1) should give low DpRVI."""
        dop = xr.DataArray([1.0])
        span = xr.DataArray([1.0])
        dprvi = compute_dprvi(dop, span)
        assert float(dprvi.values[0]) == 0.0

    def test_depolarized_gives_high_dprvi(self) -> None:
        """Depolarized signal (DoP=0) should give high DpRVI."""
        dop = xr.DataArray([0.0])
        span = xr.DataArray([1.0])
        dprvi = compute_dprvi(dop, span)
        assert float(dprvi.values[0]) == 1.0

    def test_range_0_1(self) -> None:
        dop = xr.DataArray([0.0, 0.5, 1.0])
        span = xr.DataArray([1.0, 1.0, 1.0])
        dprvi = compute_dprvi(dop, span)
        assert (dprvi.values >= 0.0).all()
        assert (dprvi.values <= 1.0).all()


class TestConditioningFactor:
    def test_no_soil_preserves_dprvi(self) -> None:
        """With soil purity 0, DpRVIc should equal DpRVI."""
        dprvi = xr.DataArray([0.5, 0.8])
        soil = xr.DataArray([0.0, 0.0])
        dprvic = apply_conditioning_factor(dprvi, soil)
        np.testing.assert_allclose(dprvic.values, dprvi.values)

    def test_high_soil_suppresses(self) -> None:
        """With soil purity 1, DpRVIc should be 0."""
        dprvi = xr.DataArray([0.5, 0.8])
        soil = xr.DataArray([1.0, 1.0])
        dprvic = apply_conditioning_factor(dprvi, soil)
        np.testing.assert_allclose(dprvic.values, [0.0, 0.0])

    def test_exponent_effect(self) -> None:
        """Higher exponent should suppress soil effect more aggressively."""
        dprvi = xr.DataArray([0.8])
        soil = xr.DataArray([0.5])
        dprvic_1 = apply_conditioning_factor(dprvi, soil, exponent=1.0)
        dprvic_2 = apply_conditioning_factor(dprvi, soil, exponent=2.0)
        # (1-0.5)^2 = 0.25 < (1-0.5)^1 = 0.5, so higher exponent gives smaller result
        assert float(dprvic_2.values[0]) < float(dprvic_1.values[0])


class TestRegressionToSnowDepth:
    def test_basic_regression(self) -> None:
        dprvic = xr.DataArray([0.0, 0.5, 1.0])
        sd = regression_to_snow_depth(dprvic, slope=5.0, intercept=-0.5)
        np.testing.assert_allclose(sd.values, [0.0, 2.0, 4.5])

    def test_negative_clipped(self) -> None:
        dprvic = xr.DataArray([0.0])
        sd = regression_to_snow_depth(dprvic, slope=5.0, intercept=-1.0)
        assert float(sd.values[0]) == 0.0


class TestDpRSEQualityFlags:
    def test_all_valid(self) -> None:
        ds = xr.Dataset(
            {
                "snow_cover": xr.DataArray([1, 1]),
                "forest_cover_fraction": xr.DataArray([0.0, 0.05]),
            }
        )
        sd = xr.DataArray([1.0, 2.0])
        soil = xr.DataArray([0.3, 0.4])
        flags = generate_quality_flags(ds, sd, soil, fcf_threshold=0.1)
        assert (flags.values == QualityFlag.VALID).all()

    def test_forest_flagged(self) -> None:
        ds = xr.Dataset(
            {
                "snow_cover": xr.DataArray([1]),
                "forest_cover_fraction": xr.DataArray([0.5]),
            }
        )
        sd = xr.DataArray([1.0])
        soil = xr.DataArray([0.3])
        flags = generate_quality_flags(ds, sd, soil, fcf_threshold=0.1)
        assert int(flags.values[0]) == QualityFlag.HIGH_FOREST

    def test_high_soil_purity_flagged(self) -> None:
        ds = xr.Dataset(
            {
                "snow_cover": xr.DataArray([1]),
                "forest_cover_fraction": xr.DataArray([0.0]),
            }
        )
        sd = xr.DataArray([1.0])
        soil = xr.DataArray([0.9])
        flags = generate_quality_flags(ds, sd, soil, soil_purity_threshold=0.7)
        assert int(flags.values[0]) == QualityFlag.OUTSIDE_RANGE

    def test_wet_snow_flagged(self) -> None:
        ds = xr.Dataset(
            {
                "snow_cover": xr.DataArray([0]),
                "forest_cover_fraction": xr.DataArray([0.0]),
            }
        )
        sd = xr.DataArray([1.0])
        soil = xr.DataArray([0.3])
        flags = generate_quality_flags(ds, sd, soil)
        assert int(flags.values[0]) == QualityFlag.WET_SNOW
