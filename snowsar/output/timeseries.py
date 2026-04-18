"""Spatial aggregation of multi-time retrieval Datasets into time-series."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
import xarray as xr

from snowsar.exceptions import AlgorithmError
from snowsar.types import QualityFlag

AggregateMethod = Literal["mean", "median", "max", "min"]


def extract_timeseries(
    ds: xr.Dataset,
    *,
    variable: str = "snow_depth",
    method: AggregateMethod = "mean",
    valid_only: bool = True,
) -> pd.DataFrame:
    """Reduce a spatial field to one value per timestep.

    Args:
        ds: Retrieval result Dataset with a ``time`` dimension.
        variable: Variable to aggregate (must have a ``time`` dim).
        method: Aggregation method applied over ``y``/``x``.
        valid_only: If True and ``quality_flag`` is present, non-valid
            pixels are excluded from the aggregate.

    Returns:
        DataFrame indexed by time with columns ``value``, ``n_valid``,
        ``n_total``, ``std``.
    """
    if variable not in ds:
        msg = f"variable {variable!r} not found in Dataset"
        raise AlgorithmError(msg)

    da = ds[variable]
    if "time" not in da.dims:
        msg = f"variable {variable!r} has no time dimension; nothing to reduce"
        raise AlgorithmError(msg)

    spatial_dims = [d for d in da.dims if d != "time"]
    if valid_only and "quality_flag" in ds:
        mask = ds["quality_flag"] == QualityFlag.VALID
        da = da.where(mask)

    reducer = {
        "mean": da.mean,
        "median": da.median,
        "max": da.max,
        "min": da.min,
    }[method]
    value = reducer(dim=spatial_dims, skipna=True)
    std = da.std(dim=spatial_dims, skipna=True)
    n_total = int(np.prod([da.sizes[d] for d in spatial_dims]))
    n_valid = da.notnull().sum(dim=spatial_dims)

    df = pd.DataFrame(
        {
            "value": value.values,
            "std": std.values,
            "n_valid": n_valid.values.astype(int),
            "n_total": n_total,
        },
        index=pd.Index(da["time"].values, name="time"),
    )
    return df
