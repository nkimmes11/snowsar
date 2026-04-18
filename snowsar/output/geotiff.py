"""GeoTIFF writer for retrieval result Datasets."""

from __future__ import annotations

from pathlib import Path

import rioxarray  # noqa: F401  # registers the .rio accessor
import xarray as xr

from snowsar.exceptions import AlgorithmError


def write_geotiff(
    ds: xr.Dataset,
    path: str | Path,
    variable: str = "snow_depth",
    time_index: int | None = None,
    compress: str = "lzw",
) -> Path:
    """Write a single variable (optionally for one timestep) to GeoTIFF.

    Args:
        ds: Retrieval result Dataset with spatial dims ``y``, ``x`` and
            optional ``time`` dim.
        path: Output path.
        variable: Variable to write.
        time_index: If the Dataset has a time dimension, the index to
            extract. If None and a time dimension exists, the temporal
            mean is written.
        compress: GDAL compression keyword (e.g., "lzw", "deflate", "none").
    """
    if variable not in ds:
        msg = f"variable {variable!r} not found in Dataset"
        raise AlgorithmError(msg)

    da = ds[variable]

    if "time" in da.dims:
        if time_index is not None:
            da = da.isel(time=time_index)
        else:
            da = da.mean(dim="time", skipna=True)

    crs = ds.attrs.get("crs", "EPSG:4326")
    da = da.rio.write_crs(crs)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    da.rio.to_raster(out, compress=compress)
    return out
