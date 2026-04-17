"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(Enum):
    """Status of a retrieval job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BBox(BaseModel):
    """Bounding box in lon/lat."""

    west: float = Field(..., ge=-180, le=180)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)


class JobCreateRequest(BaseModel):
    """Request body for creating a new retrieval job."""

    bbox: BBox
    start_date: date
    end_date: date
    algorithms: list[str] = Field(default=["lievens"])
    backend: str = Field(default="gee")
    resolution_m: int = Field(default=100, ge=10, le=10000)
    algorithm_params: dict[str, object] = Field(default_factory=dict)


class JobResponse(BaseModel):
    """Response body for job status and details."""

    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime | None = None
    bbox: BBox
    start_date: date
    end_date: date
    algorithms: list[str]
    backend: str
    resolution_m: int
    error_message: str | None = None


class JobListResponse(BaseModel):
    """Response body for listing jobs."""

    jobs: list[JobResponse]
    total: int
