"""Shared fixtures for output-module tests."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.types import QualityFlag


@pytest.fixture
def synthetic_result_dataset() -> xr.Dataset:
    """A retrieval-output-shaped Dataset with snow_depth, quality_flag, uncertainty.

    Shape: 3 time steps, 5x5 spatial grid in projected coordinates (meters).
    """
    rng = np.random.default_rng(seed=7)
    nt, ny, nx = 3, 5, 5

    times = np.array(["2024-01-01", "2024-01-13", "2024-01-25"], dtype="datetime64[ns]")
    ys = np.linspace(4_100_000.0, 4_110_000.0, ny, dtype=np.float64)
    xs = np.linspace(500_000.0, 510_000.0, nx, dtype=np.float64)

    snow_depth = rng.uniform(0, 3, (nt, ny, nx)).astype(np.float32)
    # Seed a handful of NaNs and flag them non-valid
    snow_depth[0, 0, 0] = np.nan
    quality = np.full((nt, ny, nx), QualityFlag.VALID, dtype=np.uint8)
    quality[0, 0, 0] = QualityFlag.INSUFFICIENT_SAR
    quality[1, 2, 2] = QualityFlag.WET_SNOW

    ds = xr.Dataset(
        {
            "snow_depth": (["time", "y", "x"], snow_depth),
            "quality_flag": (["time", "y", "x"], quality),
            "uncertainty": (
                ["time", "y", "x"],
                rng.uniform(0.05, 0.5, (nt, ny, nx)).astype(np.float32),
            ),
        },
        coords={"time": times, "y": ys, "x": xs},
        attrs={"crs": "EPSG:32611", "algorithm": "lievens"},
    )
    return ds


@pytest.fixture
def result_dataset_lonlat(synthetic_result_dataset: xr.Dataset) -> xr.Dataset:
    """Same result Dataset but with lon/lat axes and EPSG:4326."""
    ny = synthetic_result_dataset.sizes["y"]
    nx = synthetic_result_dataset.sizes["x"]
    ds = synthetic_result_dataset.assign_coords(
        y=np.linspace(37.5, 38.0, ny),
        x=np.linspace(-120.5, -120.0, nx),
    )
    ds.attrs["crs"] = "EPSG:4326"
    return ds
