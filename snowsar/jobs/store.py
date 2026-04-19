"""In-process job record store.

Separated from routes/jobs.py so the executor can update job records
without importing the route module (circular-import prevention).
A persistent SQL-backed implementation lives in snowsar.db and is
selected when DATABASE_URL is set.
"""

from __future__ import annotations

from datetime import UTC, datetime

from snowsar.api.schemas import JobResponse, JobStatus

_jobs: dict[str, JobResponse] = {}


def put(job: JobResponse) -> None:
    _jobs[job.job_id] = job


def get(job_id: str) -> JobResponse | None:
    return _jobs.get(job_id)


def delete(job_id: str) -> bool:
    return _jobs.pop(job_id, None) is not None


def list_all() -> list[JobResponse]:
    return list(_jobs.values())


def clear() -> None:
    _jobs.clear()


def update_status(
    job_id: str,
    status: JobStatus,
    *,
    error_message: str | None = None,
) -> JobResponse | None:
    """Mutate an existing job's status + updated_at in place."""
    existing = _jobs.get(job_id)
    if existing is None:
        return None
    updated = existing.model_copy(
        update={
            "status": status,
            "updated_at": datetime.now(tz=UTC),
            "error_message": error_message if error_message is not None else existing.error_message,
        },
    )
    _jobs[job_id] = updated
    return updated
