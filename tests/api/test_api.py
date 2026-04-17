"""Tests for the FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient

from snowsar.api.app import create_app

client = TestClient(create_app())


class TestHealthEndpoint:
    def test_health_check(self) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAlgorithmsEndpoint:
    def test_list_algorithms(self) -> None:
        response = client.get("/api/v1/algorithms")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        ids = [a["id"] for a in data]
        assert "lievens" in ids


class TestJobsEndpoint:
    def test_create_job(self) -> None:
        response = client.post(
            "/api/v1/jobs",
            json={
                "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "algorithms": ["lievens"],
                "backend": "gee",
                "resolution_m": 100,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert "job_id" in data

    def test_get_job(self) -> None:
        # Create a job first
        create_resp = client.post(
            "/api/v1/jobs",
            json={
                "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        job_id = create_resp.json()["job_id"]

        # Retrieve it
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["job_id"] == job_id

    def test_get_nonexistent_job(self) -> None:
        response = client.get("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_list_jobs(self) -> None:
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data

    def test_delete_job(self) -> None:
        # Create then delete
        create_resp = client.post(
            "/api/v1/jobs",
            json={
                "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        job_id = create_resp.json()["job_id"]

        del_resp = client.delete(f"/api/v1/jobs/{job_id}")
        assert del_resp.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_job(self) -> None:
        response = client.delete("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404

    def test_create_job_invalid_bbox(self) -> None:
        response = client.post(
            "/api/v1/jobs",
            json={
                "bbox": {"west": -200, "south": 37.5, "east": -120.0, "north": 38.0},
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert response.status_code == 422
