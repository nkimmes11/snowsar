"""Shared pytest fixtures for SnowSAR test suite."""

from datetime import date

import numpy as np
import pytest
import xarray as xr

from snowsar.types import AOI, TemporalRange


@pytest.fixture
def sample_aoi() -> AOI:
    """A small AOI in the Sierra Nevada for testing."""
    return AOI.from_bbox(-120.5, 37.5, -120.0, 38.0)


@pytest.fixture
def sample_temporal_range() -> TemporalRange:
    """A short temporal range for testing."""
    return TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 31))


@pytest.fixture
def synthetic_sar_dataset() -> xr.Dataset:
    """A synthetic SAR dataset matching the DataProvider contract.

    Contains realistic value ranges for all required variables.
    Shape: 3 time steps, 10x10 spatial grid.
    """
    rng = np.random.default_rng(42)
    nt, ny, nx = 3, 10, 10

    times = [date(2024, 1, 1), date(2024, 1, 13), date(2024, 1, 25)]
    ys = np.linspace(37.5, 38.0, ny)
    xs = np.linspace(-120.5, -120.0, nx)

    ds = xr.Dataset(
        {
            # SAR backscatter in dB (typical range: -25 to 0 dB)
            "gamma0_vv": (
                ["time", "y", "x"],
                rng.uniform(-15, -5, (nt, ny, nx)).astype(np.float32),
            ),
            "gamma0_vh": (
                ["time", "y", "x"],
                rng.uniform(-25, -12, (nt, ny, nx)).astype(np.float32),
            ),
            "incidence_angle": (
                ["time", "y", "x"],
                rng.uniform(30, 45, (nt, ny, nx)).astype(np.float32),
            ),
            # Ancillary (2D, broadcast across time)
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
                rng.uniform(0, 0.8, (ny, nx)).astype(np.float32),
            ),
            "snow_cover": (
                ["y", "x"],
                rng.choice([0, 1], size=(ny, nx), p=[0.2, 0.8]).astype(np.uint8),
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
            "source": "synthetic_test_data",
        },
    )
    return ds
