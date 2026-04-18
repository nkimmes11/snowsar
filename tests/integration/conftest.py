"""Fixtures for integration tests.

Integration tests exercise multiple components together (algorithms,
providers, API) using larger synthetic datasets that better approximate
real SAR scene characteristics.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest
import xarray as xr


@pytest.fixture
def integration_sar_dataset() -> xr.Dataset:
    """A larger synthetic SAR dataset for integration tests.

    Contains 6 time steps spanning a winter season at 12-day intervals
    (Sentinel-1 revisit) on a 20x20 spatial grid.
    """
    rng = np.random.default_rng(seed=123)
    nt, ny, nx = 6, 20, 20

    times = [
        date(2024, 1, 1),
        date(2024, 1, 13),
        date(2024, 1, 25),
        date(2024, 2, 6),
        date(2024, 2, 18),
        date(2024, 3, 1),
    ]
    ys = np.linspace(37.5, 38.0, ny)
    xs = np.linspace(-120.5, -120.0, nx)

    # SAR backscatter with a seasonal trend (VH decreases slightly as snow accumulates)
    vv_base = rng.uniform(-12, -6, (ny, nx))
    vh_base = rng.uniform(-22, -14, (ny, nx))
    seasonal = np.linspace(0, -1.5, nt)

    gamma0_vv = np.zeros((nt, ny, nx), dtype=np.float32)
    gamma0_vh = np.zeros((nt, ny, nx), dtype=np.float32)
    for t in range(nt):
        gamma0_vv[t] = vv_base + seasonal[t] + rng.normal(0, 0.3, (ny, nx))
        gamma0_vh[t] = vh_base + seasonal[t] * 0.5 + rng.normal(0, 0.3, (ny, nx))

    ds = xr.Dataset(
        {
            "gamma0_vv": (["time", "y", "x"], gamma0_vv),
            "gamma0_vh": (["time", "y", "x"], gamma0_vh),
            "incidence_angle": (
                ["time", "y", "x"],
                rng.uniform(30, 45, (nt, ny, nx)).astype(np.float32),
            ),
            "elevation": (
                ["y", "x"],
                rng.uniform(1500, 3500, (ny, nx)).astype(np.float32),
            ),
            "slope": (
                ["y", "x"],
                rng.uniform(0, 45, (ny, nx)).astype(np.float32),
            ),
            "aspect": (
                ["y", "x"],
                rng.uniform(0, 360, (ny, nx)).astype(np.float32),
            ),
            "forest_cover_fraction": (
                ["y", "x"],
                rng.uniform(0, 0.4, (ny, nx)).astype(np.float32),
            ),
            "snow_cover": (
                ["y", "x"],
                rng.choice([0, 1], size=(ny, nx), p=[0.1, 0.9]).astype(np.uint8),
            ),
        },
        coords={
            "time": times,
            "y": ys,
            "x": xs,
        },
        attrs={
            "crs": "EPSG:4326",
            "platform": "Sentinel-1",
            "source": "integration_test_data",
        },
    )
    return ds


@pytest.fixture
def integration_ml_dataset(integration_sar_dataset: xr.Dataset) -> xr.Dataset:
    """Integration dataset extended with ML-only ancillary variables."""
    rng = np.random.default_rng(seed=321)
    ds = integration_sar_dataset.copy()
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    nt = ds.sizes["time"]
    ds["temperature_2m"] = (
        ("time", "y", "x"),
        rng.uniform(250, 280, (nt, ny, nx)).astype(np.float32),
    )
    ds["land_cover_class"] = (
        ("y", "x"),
        rng.integers(10, 100, size=(ny, nx)).astype(np.uint8),
    )
    return ds
