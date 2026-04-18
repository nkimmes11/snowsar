"""CF-1.8 compliant NetCDF-4 writer for retrieval result Datasets."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

CF_CONVENTIONS = "CF-1.8"

VARIABLE_ATTRS: dict[str, dict[str, str]] = {
    "snow_depth": {
        "long_name": "Snow depth",
        "standard_name": "surface_snow_thickness",
        "units": "m",
    },
    "quality_flag": {
        "long_name": "Per-pixel quality flag",
        "units": "1",
        "flag_values": "0 1 2 3 4 5",
        "flag_meanings": (
            "valid wet_snow insufficient_sar high_forest low_coherence outside_range"
        ),
    },
    "uncertainty": {
        "long_name": "Snow depth uncertainty (1 sigma)",
        "units": "m",
    },
}


def write_netcdf(
    ds: xr.Dataset,
    path: str | Path,
    *,
    title: str | None = None,
    compress_level: int = 4,
) -> Path:
    """Write a retrieval Dataset to CF-1.8 compliant NetCDF-4.

    Applies standard CF attributes to known variables, stamps
    ``Conventions``, ``history``, and ``created`` global attributes, and
    enables zlib compression.

    Args:
        ds: Retrieval result Dataset.
        path: Output path (``.nc`` extension recommended).
        title: Optional dataset title.
        compress_level: zlib compression level (0-9).
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    annotated = ds.copy()

    for var, attrs in VARIABLE_ATTRS.items():
        if var in annotated:
            annotated[var].attrs.update(attrs)

    # CF-compliant coordinate attributes (best-effort — only set when missing)
    if "x" in annotated.coords and "standard_name" not in annotated["x"].attrs:
        annotated["x"].attrs.update({"standard_name": "projection_x_coordinate", "units": "m"})
    if "y" in annotated.coords and "standard_name" not in annotated["y"].attrs:
        annotated["y"].attrs.update({"standard_name": "projection_y_coordinate", "units": "m"})
    if "time" in annotated.coords and "standard_name" not in annotated["time"].attrs:
        annotated["time"].attrs.update({"standard_name": "time"})

    now = datetime.now(tz=UTC).isoformat()
    annotated.attrs["Conventions"] = CF_CONVENTIONS
    annotated.attrs["created"] = now
    existing_history = annotated.attrs.get("history", "")
    history_line = f"{now}: written by snowsar.output.netcdf\n{existing_history}"
    annotated.attrs["history"] = history_line.strip()
    if title:
        annotated.attrs["title"] = title

    encoding: dict[str, dict[str, Any]] = {}
    for var_key in annotated.data_vars:
        var = str(var_key)
        enc: dict[str, Any] = {"zlib": True, "complevel": compress_level}
        if np.issubdtype(annotated[var].dtype, np.floating):
            enc["_FillValue"] = np.float32(np.nan)
        encoding[var] = enc

    annotated.to_netcdf(out, engine="netcdf4", encoding=encoding)
    return out
