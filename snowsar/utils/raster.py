"""Raster and xarray utility functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import xarray as xr

if TYPE_CHECKING:
    from pathlib import Path


# Standard variable names expected in provider output Datasets
SAR_VARIABLES = frozenset(
    {
        "gamma0_vv",
        "gamma0_vh",
        "incidence_angle",
    }
)

ANCILLARY_VARIABLES = frozenset(
    {
        "elevation",
        "slope",
        "aspect",
        "forest_cover_fraction",
        "snow_cover",
    }
)

REQUIRED_VARIABLES = SAR_VARIABLES | ANCILLARY_VARIABLES

# Standard output variable names from algorithms
OUTPUT_VARIABLES = frozenset(
    {
        "snow_depth",
        "quality_flag",
        "uncertainty",
    }
)


def validate_dataset(ds: xr.Dataset, required: frozenset[str] | None = None) -> None:
    """Check that a Dataset contains the required variables.

    Raises ValueError if any required variables are missing.
    """
    required = required or REQUIRED_VARIABLES
    missing = required - set(ds.data_vars)
    if missing:
        msg = f"Dataset is missing required variables: {sorted(missing)}"
        raise ValueError(msg)


def db_to_linear(db_values: xr.DataArray) -> xr.DataArray:
    """Convert decibel values to linear power scale."""
    return 10.0 ** (db_values / 10.0)


def linear_to_db(linear_values: xr.DataArray) -> xr.DataArray:
    """Convert linear power values to decibels."""
    return 10.0 * np.log10(linear_values)


def write_geotiff(ds: xr.Dataset, variable: str, path: Path) -> None:
    """Write a single variable from a Dataset to a GeoTIFF file.

    Requires the Dataset to have CRS information set via rioxarray.
    """
    da = ds[variable]
    da.rio.to_raster(str(path))
