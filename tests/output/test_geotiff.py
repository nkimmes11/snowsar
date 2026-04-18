"""Tests for the GeoTIFF writer."""

from __future__ import annotations

from pathlib import Path

import pytest
import rasterio
import xarray as xr

from snowsar.exceptions import AlgorithmError
from snowsar.output.geotiff import write_geotiff


class TestWriteGeoTIFF:
    def test_writes_file(self, synthetic_result_dataset: xr.Dataset, tmp_path: Path) -> None:
        out = tmp_path / "snow_depth.tif"
        result_path = write_geotiff(synthetic_result_dataset, out)
        assert result_path == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_temporal_mean_when_no_index(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        out = tmp_path / "mean.tif"
        write_geotiff(synthetic_result_dataset, out)
        with rasterio.open(out) as src:
            assert src.count == 1  # Single-band output from temporal mean
            assert src.width == synthetic_result_dataset.sizes["x"]
            assert src.height == synthetic_result_dataset.sizes["y"]

    def test_specific_time_index(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        out = tmp_path / "t1.tif"
        write_geotiff(synthetic_result_dataset, out, time_index=1)
        with rasterio.open(out) as src:
            assert src.count == 1

    def test_crs_preserved(self, synthetic_result_dataset: xr.Dataset, tmp_path: Path) -> None:
        out = tmp_path / "crs.tif"
        write_geotiff(synthetic_result_dataset, out)
        with rasterio.open(out) as src:
            assert src.crs is not None
            assert "32611" in str(src.crs)

    def test_unknown_variable_raises(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        with pytest.raises(AlgorithmError, match="not found"):
            write_geotiff(synthetic_result_dataset, tmp_path / "bad.tif", variable="nope")

    def test_single_time_dataset(
        self, synthetic_result_dataset: xr.Dataset, tmp_path: Path
    ) -> None:
        ds = synthetic_result_dataset.isel(time=0, drop=True)
        out = tmp_path / "single.tif"
        write_geotiff(ds, out)
        assert out.exists()
