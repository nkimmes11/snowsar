"""Shared fixtures for comparison tests."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.types import QualityFlag


def _make_ds(seed: int, bias: float = 0.0) -> xr.Dataset:
    rng = np.random.default_rng(seed=seed)
    nt, ny, nx = 3, 5, 5
    times = np.array(["2024-01-01", "2024-01-13", "2024-01-25"], dtype="datetime64[ns]")
    ys = np.linspace(37.5, 38.0, ny)
    xs = np.linspace(-120.5, -120.0, nx)
    snow_depth = rng.uniform(0, 3, (nt, ny, nx)).astype(np.float32) + np.float32(bias)
    quality = np.full((nt, ny, nx), QualityFlag.VALID, dtype=np.uint8)
    quality[0, 0, 0] = QualityFlag.WET_SNOW
    return xr.Dataset(
        {
            "snow_depth": (["time", "y", "x"], snow_depth),
            "quality_flag": (["time", "y", "x"], quality),
        },
        coords={"time": times, "y": ys, "x": xs},
        attrs={"crs": "EPSG:4326"},
    )


@pytest.fixture
def ds_a() -> xr.Dataset:
    return _make_ds(seed=1)


@pytest.fixture
def ds_b() -> xr.Dataset:
    return _make_ds(seed=2, bias=0.2)


@pytest.fixture
def ds_identical_to_a(ds_a: xr.Dataset) -> xr.Dataset:
    return ds_a.copy(deep=True)
