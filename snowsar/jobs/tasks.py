"""Celery task definitions.

Imported lazily — only when execution_mode == 'celery' does the API
enqueue via these. Unit + integration tests drive the executor directly
and never import this module, which keeps Celery/Redis out of the
default test path.
"""

from __future__ import annotations

from typing import Any

from snowsar.api.schemas import JobCreateRequest
from snowsar.jobs.executor import run_job
from snowsar.jobs.worker import celery_app


@celery_app.task(name="snowsar.run_retrieval")  # type: ignore[untyped-decorator]
def run_retrieval(job_id: str, request_payload: dict[str, Any]) -> None:
    """Celery wrapper around the synchronous executor."""
    request = JobCreateRequest.model_validate(request_payload)
    run_job(job_id, request)
