"""Validation and cross-algorithm comparison endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from snowsar.api.results_store import get as get_result
from snowsar.comparison.stats import compute_pairwise_stats, difference_map
from snowsar.types import AOI, TemporalRange
from snowsar.validation import ghcnd, matcher, metrics, snotel, user_upload

router = APIRouter()


class BBox(BaseModel):
    west: float = Field(..., ge=-180, le=180)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)

    def to_aoi(self) -> AOI:
        return AOI.from_bbox(self.west, self.south, self.east, self.north)


class DateRange(BaseModel):
    start: date
    end: date

    def to_temporal_range(self) -> TemporalRange:
        return TemporalRange(start=self.start, end=self.end)


class StationValidationRequest(BaseModel):
    bbox: BBox
    date_range: DateRange
    max_distance_deg: float = 0.05
    tolerance_days: int = 1


class CompareRequest(BaseModel):
    variable: str = "snow_depth"
    valid_only: bool = True
    agreement_tolerance_m: float = 0.1
    return_difference_map: bool = False


def _run_station_validation(
    job_id: str,
    stations: pd.DataFrame,
    observations: pd.DataFrame,
    *,
    max_distance_deg: float,
    tolerance_days: int,
) -> dict[str, object]:
    ds = get_result(job_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Result not found")

    if stations.empty or observations.empty:
        return {
            "metrics": metrics.compute_metrics(np.array([]), np.array([])).to_dict(),
            "matched_count": 0,
            "stations_found": len(stations),
            "observations_found": len(observations),
        }

    spatial = matcher.spatial_match(stations, ds, max_distance_deg=max_distance_deg)
    temporal = matcher.temporal_match(observations, ds, tolerance_days=tolerance_days)

    if spatial.empty or temporal.empty:
        return {
            "metrics": metrics.compute_metrics(np.array([]), np.array([])).to_dict(),
            "matched_count": 0,
            "stations_found": len(stations),
            "observations_found": len(observations),
        }

    merged = temporal.merge(spatial, on="station_id", how="inner")
    if merged.empty:
        return {
            "metrics": metrics.compute_metrics(np.array([]), np.array([])).to_dict(),
            "matched_count": 0,
            "stations_found": len(stations),
            "observations_found": len(observations),
        }

    # Use dim-labeled indexing so dim order in the result Dataset doesn't
    # matter. xarray broadcasts during algorithm execution can permute the
    # underlying ndarray (e.g. Lievens output surfaces as (y, x, time));
    # .isel() binds by name and is robust to those permutations.
    da = ds["snow_depth"]
    predicted = np.array(
        [
            float(
                da.isel(
                    time=int(r.matched_time_idx),
                    y=int(r.nearest_y_idx),
                    x=int(r.nearest_x_idx),
                ).values
            )
            for r in merged.itertuples(index=False)
        ],
        dtype=np.float64,
    )
    observed = merged["obs_snow_depth_m"].to_numpy(dtype=np.float64)

    m = metrics.compute_metrics(predicted, observed)
    pairs: list[dict[str, object]] = [
        {
            "station_id": str(row.station_id),
            "obs_date": row.obs_date.isoformat() if row.obs_date else None,
            "observed_m": float(row.obs_snow_depth_m),
            "predicted_m": float(pred),
        }
        for row, pred in zip(merged.itertuples(index=False), predicted, strict=True)
    ]
    return {
        "metrics": m.to_dict(),
        "matched_count": int(m.count),
        "stations_found": len(stations),
        "observations_found": len(observations),
        "pairs": pairs,
    }


@router.post("/jobs/{job_id}/validation/snotel")
def validate_snotel(job_id: str, request: StationValidationRequest) -> dict[str, object]:
    aoi = request.bbox.to_aoi()
    tr = request.date_range.to_temporal_range()
    stations = snotel.fetch_stations(aoi)
    station_ids = stations["station_id"].tolist() if not stations.empty else []
    observations = (
        snotel.fetch_observations(station_ids, tr)
        if station_ids
        else pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])
    )
    return _run_station_validation(
        job_id,
        stations,
        observations,
        max_distance_deg=request.max_distance_deg,
        tolerance_days=request.tolerance_days,
    )


@router.post("/jobs/{job_id}/validation/ghcnd")
def validate_ghcnd(job_id: str, request: StationValidationRequest) -> dict[str, object]:
    aoi = request.bbox.to_aoi()
    tr = request.date_range.to_temporal_range()
    stations = ghcnd.fetch_stations(aoi)
    station_ids = stations["station_id"].tolist() if not stations.empty else []
    observations = (
        ghcnd.fetch_observations(station_ids, tr)
        if station_ids
        else pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])
    )
    return _run_station_validation(
        job_id,
        stations,
        observations,
        max_distance_deg=request.max_distance_deg,
        tolerance_days=request.tolerance_days,
    )


@router.post("/jobs/{job_id}/validation/upload")
async def validate_upload(
    job_id: str,
    file: UploadFile = File(...),  # noqa: B008 — FastAPI dependency-injection idiom
    format: Literal["csv", "geojson"] = Form(...),
    max_distance_deg: float = Form(0.05),
    tolerance_days: int = Form(1),
) -> dict[str, object]:
    content = await file.read()
    stations, observations = user_upload.parse(content, format=format)
    return _run_station_validation(
        job_id,
        stations,
        observations,
        max_distance_deg=max_distance_deg,
        tolerance_days=tolerance_days,
    )


@router.post("/jobs/{job_id}/compare/{other_job_id}")
def compare_jobs(
    job_id: str,
    other_job_id: str,
    request: CompareRequest | None = None,
) -> dict[str, object]:
    req = request or CompareRequest()
    ds_a = get_result(job_id)
    ds_b = get_result(other_job_id)
    if ds_a is None:
        raise HTTPException(status_code=404, detail=f"Result not found: {job_id}")
    if ds_b is None:
        raise HTTPException(status_code=404, detail=f"Result not found: {other_job_id}")

    stats = compute_pairwise_stats(
        ds_a,
        ds_b,
        variable=req.variable,
        valid_only=req.valid_only,
        agreement_tolerance_m=req.agreement_tolerance_m,
    )
    payload: dict[str, object] = {
        "job_a": job_id,
        "job_b": other_job_id,
        "variable": req.variable,
        "stats": stats.to_dict(),
    }
    if req.return_difference_map:
        diff = difference_map(ds_a, ds_b, variable=req.variable, valid_only=req.valid_only)
        payload["difference_map"] = {
            "shape": list(diff.shape),
            "dims": list(diff.dims),
            "values": diff.values.tolist(),
        }
    return payload
