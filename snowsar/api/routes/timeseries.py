"""Time-series aggregation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from snowsar.api.results_store import get as get_result
from snowsar.output.timeseries import extract_timeseries

router = APIRouter()


@router.get("/jobs/{job_id}/results/timeseries")
def get_timeseries(
    job_id: str,
    variable: str = "snow_depth",
    method: str = Query(default="mean", pattern="^(mean|median|max|min)$"),
    valid_only: bool = True,
) -> list[dict[str, object]]:
    """Return a spatially aggregated time-series for a retrieval result."""
    ds = get_result(job_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Result not found")

    df = extract_timeseries(
        ds,
        variable=variable,
        method=method,  # type: ignore[arg-type]
        valid_only=valid_only,
    )
    df = df.reset_index()
    records: list[dict[str, object]] = df.to_dict(orient="records")
    return records
