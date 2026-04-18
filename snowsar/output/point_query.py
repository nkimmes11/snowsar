"""Point sampling of retrieval result Datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

from snowsar.exceptions import AlgorithmError

SampleMethod = Literal["nearest", "linear"]

DEFAULT_VARIABLES: tuple[str, ...] = ("snow_depth", "quality_flag", "uncertainty")


@dataclass(frozen=True)
class Point:
    """A query point with optional identifier."""

    lon: float
    lat: float
    id: str | None = None


def query_points(
    ds: xr.Dataset,
    points: list[Point],
    *,
    method: SampleMethod = "nearest",
    variables: tuple[str, ...] = DEFAULT_VARIABLES,
    src_crs: str = "EPSG:4326",
) -> pd.DataFrame:
    """Sample Dataset variables at user-supplied points.

    Args:
        ds: Retrieval result Dataset with spatial coords ``x`` and ``y``.
        points: Query points (lon/lat by default).
        method: ``"nearest"`` or ``"linear"``. Integer-typed variables
            (e.g., ``quality_flag``) are always sampled with nearest.
        variables: Variables to sample. Missing variables are silently
            skipped.
        src_crs: CRS of the input points.

    Returns:
        Long-format DataFrame with columns ``point_id``, ``lon``, ``lat``,
        ``time`` (if present), plus one column per sampled variable.
    """
    if not points:
        msg = "points list is empty"
        raise AlgorithmError(msg)

    available = [v for v in variables if v in ds]
    if not available:
        msg = f"none of the requested variables found in Dataset: {variables}"
        raise AlgorithmError(msg)

    dst_crs = ds.attrs.get("crs", "EPSG:4326")
    if src_crs != dst_crs:
        transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        xs, ys = transformer.transform([p.lon for p in points], [p.lat for p in points])
        xs_arr = np.asarray(xs, dtype=float)
        ys_arr = np.asarray(ys, dtype=float)
    else:
        xs_arr = np.asarray([p.lon for p in points], dtype=float)
        ys_arr = np.asarray([p.lat for p in points], dtype=float)

    ids = [p.id if p.id is not None else f"p{i}" for i, p in enumerate(points)]
    x_da = xr.DataArray(xs_arr, dims="point", coords={"point": ids})
    y_da = xr.DataArray(ys_arr, dims="point", coords={"point": ids})

    sampled_vars: dict[str, xr.DataArray] = {}
    for var in available:
        da = ds[var]
        eff_method: SampleMethod = (
            "nearest" if method == "nearest" or np.issubdtype(da.dtype, np.integer) else "linear"
        )
        sampled_vars[var] = da.interp(x=x_da, y=y_da, method=eff_method)

    sampled_ds = xr.Dataset(sampled_vars)
    df = sampled_ds.to_dataframe().reset_index()
    df = df.rename(columns={"point": "point_id"})
    df["lon"] = df["point_id"].map(dict(zip(ids, [p.lon for p in points], strict=True)))
    df["lat"] = df["point_id"].map(dict(zip(ids, [p.lat for p in points], strict=True)))

    ordered = ["point_id", "lon", "lat"]
    if "time" in df.columns:
        ordered.append("time")
    ordered.extend(available)
    return df[ordered]
