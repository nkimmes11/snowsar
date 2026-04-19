"""Integration test for the full API job lifecycle."""

from __future__ import annotations

from collections.abc import Iterator

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


@pytest.fixture
def job_request_body() -> dict[str, object]:
    return {
        "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "algorithms": ["lievens"],
        "backend": "fixture",
        "resolution_m": 100,
    }


class TestAPIJobLifecycle:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_algorithms_includes_all_implemented(self, client: TestClient) -> None:
        response = client.get("/api/v1/algorithms")
        assert response.status_code == 200
        data = response.json()
        ids = {a["id"] for a in data}
        assert "lievens" in ids
        assert "dprse" in ids

    def test_create_then_get_then_delete_job(
        self, client: TestClient, job_request_body: dict[str, object]
    ) -> None:
        create_resp = client.post("/api/v1/jobs", json=job_request_body)
        assert create_resp.status_code == 201
        job = create_resp.json()
        job_id = job["job_id"]
        assert job["status"] == "pending"
        assert job["algorithms"] == ["lievens"]

        get_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["job_id"] == job_id

        list_resp = client.get("/api/v1/jobs")
        assert list_resp.status_code == 200
        ids = [j["job_id"] for j in list_resp.json()["jobs"]]
        assert job_id in ids

        delete_resp = client.delete(f"/api/v1/jobs/{job_id}")
        assert delete_resp.status_code == 204

        get_after_delete = client.get(f"/api/v1/jobs/{job_id}")
        assert get_after_delete.status_code == 404

    def test_get_nonexistent_job_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/jobs/does-not-exist")
        assert response.status_code == 404

    def test_invalid_bbox_rejected(self, client: TestClient) -> None:
        body = {
            "bbox": {"west": -999, "south": 37.5, "east": -120.0, "north": 38.0},
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "algorithms": ["lievens"],
            "backend": "fixture",
            "resolution_m": 100,
        }
        response = client.post("/api/v1/jobs", json=body)
        assert response.status_code == 422
