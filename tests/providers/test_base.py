"""Tests for DataProvider protocol and synthetic dataset compliance."""

from __future__ import annotations

import xarray as xr

from snowsar.utils.raster import REQUIRED_VARIABLES, validate_dataset


class TestSyntheticDataset:
    """Verify that the synthetic test fixture satisfies the DataProvider contract."""

    def test_has_all_required_variables(self, synthetic_sar_dataset: xr.Dataset) -> None:
        validate_dataset(synthetic_sar_dataset)

    def test_has_time_dimension(self, synthetic_sar_dataset: xr.Dataset) -> None:
        assert "time" in synthetic_sar_dataset.dims
        assert synthetic_sar_dataset.sizes["time"] == 3

    def test_has_spatial_dimensions(self, synthetic_sar_dataset: xr.Dataset) -> None:
        assert "y" in synthetic_sar_dataset.dims
        assert "x" in synthetic_sar_dataset.dims

    def test_has_crs_attribute(self, synthetic_sar_dataset: xr.Dataset) -> None:
        assert "crs" in synthetic_sar_dataset.attrs

    def test_sar_variables_are_3d(self, synthetic_sar_dataset: xr.Dataset) -> None:
        for var in ("gamma0_vv", "gamma0_vh", "incidence_angle"):
            assert set(synthetic_sar_dataset[var].dims) == {"time", "y", "x"}

    def test_ancillary_variables_are_2d(self, synthetic_sar_dataset: xr.Dataset) -> None:
        for var in ("elevation", "slope", "aspect", "forest_cover_fraction", "snow_cover"):
            assert set(synthetic_sar_dataset[var].dims) == {"y", "x"}

    def test_value_ranges(self, synthetic_sar_dataset: xr.Dataset) -> None:
        ds = synthetic_sar_dataset
        # Backscatter should be negative dB
        assert float(ds["gamma0_vv"].max()) < 0
        assert float(ds["gamma0_vh"].max()) < 0
        # FCF in [0, 1]
        assert float(ds["forest_cover_fraction"].min()) >= 0
        assert float(ds["forest_cover_fraction"].max()) <= 1
        # Snow cover binary
        assert set(ds["snow_cover"].values.flat) <= {0, 1}

    def test_required_variables_constant(self) -> None:
        expected = {
            "gamma0_vv",
            "gamma0_vh",
            "incidence_angle",
            "elevation",
            "slope",
            "aspect",
            "forest_cover_fraction",
            "snow_cover",
        }
        assert expected == REQUIRED_VARIABLES
