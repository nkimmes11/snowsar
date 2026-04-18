"""Result-download endpoints (GeoTIFF, NetCDF, point query)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from snowsar.api.results_store import get as get_result
from snowsar.output.geotiff import write_geotiff
from snowsar.output.netcdf import write_netcdf
from snowsar.output.point_query import Point, query_points

router = APIRouter()


class PointQuery(BaseModel):
    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    id: str | None = None


class PointsRequest(BaseModel):
    points: list[PointQuery]
    method: str = Field(default="nearest", pattern="^(nearest|linear)$")


@router.get("/jobs/{job_id}/results/geotiff")
def download_geotiff(job_id: str, variable: str = "snow_depth") -> FileResponse:
    """Download a single variable as GeoTIFF (temporal mean if multi-time)."""
    ds = get_result(job_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Result not found")

    tmp = Path(tempfile.mkstemp(suffix=".tif", prefix=f"snowsar_{job_id}_")[1])
    write_geotiff(ds, tmp, variable=variable)
    return FileResponse(tmp, media_type="image/tiff", filename=f"{job_id}_{variable}.tif")


@router.get("/jobs/{job_id}/results/netcdf")
def download_netcdf(job_id: str) -> FileResponse:
    """Download the full result Dataset as CF-1.8 NetCDF-4."""
    ds = get_result(job_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Result not found")

    tmp = Path(tempfile.mkstemp(suffix=".nc", prefix=f"snowsar_{job_id}_")[1])
    write_netcdf(ds, tmp, title=f"SnowSAR retrieval {job_id}")
    return FileResponse(tmp, media_type="application/x-netcdf", filename=f"{job_id}.nc")


@router.post("/jobs/{job_id}/results/points")
def sample_points(job_id: str, request: PointsRequest) -> list[dict[str, object]]:
    """Sample the result Dataset at user-supplied lon/lat points."""
    ds = get_result(job_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Result not found")

    points = [Point(lon=p.lon, lat=p.lat, id=p.id) for p in request.points]
    df = query_points(ds, points, method=request.method)  # type: ignore[arg-type]
    records: list[dict[str, object]] = df.to_dict(orient="records")
    return records
