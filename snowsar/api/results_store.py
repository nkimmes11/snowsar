"""In-process store for job result Datasets.

Temporary backing for the result-download endpoints until a persistent
store (database blob or object storage) is wired up.
"""

from __future__ import annotations

import xarray as xr

_results: dict[str, xr.Dataset] = {}


def put(job_id: str, ds: xr.Dataset) -> None:
    _results[job_id] = ds


def get(job_id: str) -> xr.Dataset | None:
    return _results.get(job_id)


def clear() -> None:
    _results.clear()
