"""Job management endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from snowsar.api.schemas import (
    JobCreateRequest,
    JobListResponse,
    JobResponse,
    JobStatus,
)

router = APIRouter()

# In-memory job store (replaced by database in production)
_jobs: dict[str, JobResponse] = {}


@router.post("/jobs", status_code=201)
def create_job(request: JobCreateRequest) -> JobResponse:
    """Submit a new snow depth retrieval job."""
    job_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC)

    job = JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        created_at=now,
        updated_at=now,
        bbox=request.bbox,
        start_date=request.start_date,
        end_date=request.end_date,
        algorithms=request.algorithms,
        backend=request.backend,
        resolution_m=request.resolution_m,
    )
    _jobs[job_id] = job

    # TODO: Enqueue Celery task here
    # from snowsar.jobs.tasks import run_retrieval
    # run_retrieval.delay(job_id, request.model_dump())

    return job


@router.get("/jobs")
def list_jobs() -> JobListResponse:
    """List all jobs."""
    jobs = list(_jobs.values())
    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> JobResponse:
    """Get job status and details."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str) -> None:
    """Cancel or delete a job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    del _jobs[job_id]
