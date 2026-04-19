"""End-to-end integration test: POST /jobs -> execution -> result download.

Exercises JobParameters -> FixtureProvider -> Lievens algorithm ->
results_store -> GeoTIFF/NetCDF/time-series endpoints. This is the
pipeline test that Step 1.8 was supposed to deliver but did not.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from snowsar.api.app import create_app
from snowsar.api.results_store import clear as clear_results
from snowsar.jobs import store as job_store

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolate_state() -> Iterator[None]:
    job_store.clear()
    clear_results()
    yield
    job_store.clear()
    clear_results()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _submit_and_wait(client: TestClient, body: dict[str, object]) -> dict[str, object]:
    resp = client.post("/api/v1/jobs", json=body)
    assert resp.status_code == 201, resp.text
    job = resp.json()
    # With BackgroundTasks under TestClient, the executor runs before
    # the response context closes — so by the time the first follow-up
    # GET returns, the job status has been updated.
    get_resp = client.get(f"/api/v1/jobs/{job['job_id']}")
    assert get_resp.status_code == 200
    updated: dict[str, object] = get_resp.json()
    return updated


class TestPipelineEndToEnd:
    BODY: ClassVar[dict[str, object]] = {
        "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
        "start_date": "2024-01-01",
        "end_date": "2024-02-29",
        "algorithms": ["lievens"],
        "backend": "fixture",
        "resolution_m": 100,
    }

    def test_job_runs_to_completion(self, client: TestClient) -> None:
        updated = _submit_and_wait(client, self.BODY)
        assert updated["status"] == "completed", updated
        assert updated.get("error_message") in (None, "")

    def test_geotiff_download_returns_bytes(self, client: TestClient) -> None:
        updated = _submit_and_wait(client, self.BODY)
        job_id = updated["job_id"]
        resp = client.get(f"/api/v1/jobs/{job_id}/results/geotiff")
        assert resp.status_code == 200
        # GeoTIFFs start with II* (little-endian) or MM\0* (big-endian)
        assert resp.content[:2] in (b"II", b"MM")
        assert len(resp.content) > 200

    def test_netcdf_download_returns_bytes(self, client: TestClient) -> None:
        updated = _submit_and_wait(client, self.BODY)
        job_id = updated["job_id"]
        resp = client.get(f"/api/v1/jobs/{job_id}/results/netcdf")
        assert resp.status_code == 200
        # NetCDF-4 is HDF5-backed: starts with \x89HDF; classic NetCDF
        # starts with "CDF". Accept either.
        head = resp.content[:4]
        assert head == b"\x89HDF" or head[:3] == b"CDF", head

    def test_timeseries_returns_records(self, client: TestClient) -> None:
        updated = _submit_and_wait(client, self.BODY)
        job_id = updated["job_id"]
        resp = client.get(f"/api/v1/jobs/{job_id}/results/timeseries")
        assert resp.status_code == 200
        rows = resp.json()
        assert isinstance(rows, list)
        assert len(rows) >= 1
        # extract_timeseries() returns {time, value, std, n_valid, n_total}
        assert "time" in rows[0]
        assert "value" in rows[0]
        assert "n_valid" in rows[0]

    def test_failed_job_is_reported_with_error_message(self, client: TestClient) -> None:
        # Send a bogus algorithm id so the executor fails during coercion.
        body = {**self.BODY, "algorithms": ["not-a-real-algorithm"]}
        updated = _submit_and_wait(client, body)
        assert updated["status"] == "failed"
        assert updated.get("error_message"), updated
