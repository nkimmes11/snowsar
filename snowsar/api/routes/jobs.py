"""Job management endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from snowsar.api.schemas import (
    JobCreateRequest,
    JobListResponse,
    JobResponse,
    JobStatus,
)
from snowsar.config import Settings
from snowsar.jobs import store as job_store

router = APIRouter()


def _enqueue(job_id: str, request: JobCreateRequest, background: BackgroundTasks) -> None:
    """Dispatch the job to the configured execution backend."""
    settings = Settings()
    if settings.execution_mode == "celery":
        # Import lazily so tests + dev don't need celery/redis running.
        from snowsar.jobs.tasks import run_retrieval

        run_retrieval.delay(job_id, request.model_dump(mode="json"))
        return

    # Default: FastAPI BackgroundTasks runs after the response is sent,
    # in the same process. Suitable for single-worker dev/test.
    from snowsar.jobs.executor import run_job

    background.add_task(run_job, job_id, request)


@router.post("/jobs", status_code=201)
def create_job(request: JobCreateRequest, background: BackgroundTasks) -> JobResponse:
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
    job_store.put(job)
    _enqueue(job_id, request, background)
    return job


@router.get("/jobs")
def list_jobs() -> JobListResponse:
    """List all jobs."""
    jobs = job_store.list_all()
    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> JobResponse:
    """Get job status and details."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str) -> None:
    """Cancel or delete a job."""
    if not job_store.delete(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
