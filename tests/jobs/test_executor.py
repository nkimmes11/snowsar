"""Unit tests for the synchronous job executor."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from snowsar.api import results_store
from snowsar.api.schemas import BBox, JobCreateRequest, JobResponse, JobStatus
from snowsar.jobs import store as job_store
from snowsar.jobs.executor import run_job


def _seed_pending_job(job_id: str, body: JobCreateRequest) -> None:
    now = datetime.now(tz=UTC)
    job_store.put(
        JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            bbox=body.bbox,
            start_date=body.start_date,
            end_date=body.end_date,
            algorithms=body.algorithms,
            backend=body.backend,
            resolution_m=body.resolution_m,
        ),
    )


@pytest.fixture(autouse=True)
def _isolate_state() -> Iterator[None]:
    job_store.clear()
    results_store.clear()
    yield
    job_store.clear()
    results_store.clear()


@pytest.fixture
def fixture_body() -> JobCreateRequest:
    return JobCreateRequest.model_validate(
        {
            "bbox": BBox(west=-120.5, south=37.5, east=-120.0, north=38.0).model_dump(),
            "start_date": "2024-01-01",
            "end_date": "2024-02-29",
            "algorithms": ["lievens"],
            "backend": "fixture",
            "resolution_m": 100,
        },
    )


class TestRunJob:
    def test_happy_path_completes_and_writes_result(self, fixture_body: JobCreateRequest) -> None:
        job_id = "job-happy"
        _seed_pending_job(job_id, fixture_body)

        run_job(job_id, fixture_body)

        final = job_store.get(job_id)
        assert final is not None
        assert final.status == JobStatus.COMPLETED
        assert final.error_message in (None, "")
        ds = results_store.get(job_id)
        assert ds is not None
        assert "snow_depth" in ds.data_vars

    def test_unknown_algorithm_marks_job_failed(self, fixture_body: JobCreateRequest) -> None:
        job_id = "job-bad-algo"
        bad_body = fixture_body.model_copy(update={"algorithms": ["not-an-algo"]})
        _seed_pending_job(job_id, bad_body)

        run_job(job_id, bad_body)

        final = job_store.get(job_id)
        assert final is not None
        assert final.status == JobStatus.FAILED
        assert final.error_message is not None
        assert "not-an-algo" in final.error_message

    def test_unknown_backend_marks_job_failed(self, fixture_body: JobCreateRequest) -> None:
        job_id = "job-bad-backend"
        bad_body = fixture_body.model_copy(update={"backend": "nonsense"})
        _seed_pending_job(job_id, bad_body)

        run_job(job_id, bad_body)

        final = job_store.get(job_id)
        assert final is not None
        assert final.status == JobStatus.FAILED
        assert final.error_message is not None
        assert "nonsense" in final.error_message
