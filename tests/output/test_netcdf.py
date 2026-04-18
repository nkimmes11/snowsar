"""Tests for the CF-compliant NetCDF writer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from snowsar.output.netcdf import CF_CONVENTIONS, write_netcdf


class TestWriteNetCDF:
    def test_file_created(self, synthetic_result_dataset: xr.Dataset, tmp_path: Path) -> None:
        out = tmp_path / "result.nc"
        result_path = write_netcdf(synthetic_result_dataset, out)
        assert result_path == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_round_trip_preserves_data(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        out = tmp_path / "roundtrip.nc"
        write_netcdf(synthetic_result_dataset, out)
        loaded = xr.open_dataset(out)
        try:
            np.testing.assert_allclose(
                loaded["snow_depth"].values,
                synthetic_result_dataset["snow_depth"].values,
                equal_nan=True,
            )
            np.testing.assert_array_equal(
                loaded["quality_flag"].values,
                synthetic_result_dataset["quality_flag"].values,
            )
        finally:
            loaded.close()

    def test_cf_conventions_attr(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        out = tmp_path / "cf.nc"
        write_netcdf(synthetic_result_dataset, out)
        loaded = xr.open_dataset(out)
        try:
            assert loaded.attrs.get("Conventions") == CF_CONVENTIONS
            assert "created" in loaded.attrs
            assert "history" in loaded.attrs
        finally:
            loaded.close()

    def test_variable_attributes_applied(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        out = tmp_path / "attrs.nc"
        write_netcdf(synthetic_result_dataset, out)
        loaded = xr.open_dataset(out)
        try:
            assert loaded["snow_depth"].attrs.get("units") == "m"
            assert loaded["snow_depth"].attrs.get("standard_name") == "surface_snow_thickness"
            assert "flag_meanings" in loaded["quality_flag"].attrs
        finally:
            loaded.close()

    def test_title_attribute(self, synthetic_result_dataset: xr.Dataset, tmp_path: Path) -> None:
        out = tmp_path / "titled.nc"
        write_netcdf(synthetic_result_dataset, out, title="Test retrieval")
        loaded = xr.open_dataset(out)
        try:
            assert loaded.attrs.get("title") == "Test retrieval"
        finally:
            loaded.close()

    def test_compression_level_accepted(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        """All zlib levels (0-9) produce a valid, readable NetCDF file."""
        for level in (0, 4, 9):
            out = tmp_path / f"c{level}.nc"
            write_netcdf(synthetic_result_dataset, out, compress_level=level)
            loaded = xr.open_dataset(out)
            try:
                assert "snow_depth" in loaded
            finally:
                loaded.close()
