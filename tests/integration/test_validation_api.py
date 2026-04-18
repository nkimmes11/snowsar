"""Integration tests for validation + comparison API endpoints."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from datetime import date

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from fastapi.testclient import TestClient
from shapely.geometry import Point as ShapelyPoint

from snowsar.api.app import create_app
from snowsar.api.results_store import clear as clear_results
from snowsar.api.results_store import put as put_result
from snowsar.types import QualityFlag
from snowsar.validation import ghcnd as ghcnd_module
from snowsar.validation import snotel as snotel_module

pytestmark = pytest.mark.integration


def _make_result_ds(seed: int, bias: float = 0.0) -> xr.Dataset:
    rng = np.random.default_rng(seed=seed)
    nt, ny, nx = 3, 10, 10
    times = np.array(["2024-01-01", "2024-01-13", "2024-01-25"], dtype="datetime64[ns]")
    ys = np.linspace(37.5, 38.0, ny)
    xs = np.linspace(-120.5, -120.0, nx)
    snow_depth = rng.uniform(0.2, 1.5, (nt, ny, nx)).astype(np.float32) + np.float32(bias)
    quality = np.full((nt, ny, nx), QualityFlag.VALID, dtype=np.uint8)
    return xr.Dataset(
        {
            "snow_depth": (["time", "y", "x"], snow_depth),
            "quality_flag": (["time", "y", "x"], quality),
        },
        coords={"time": times, "y": ys, "x": xs},
        attrs={"crs": "EPSG:4326"},
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    clear_results()
    put_result("job-a", _make_result_ds(seed=11))
    put_result("job-b", _make_result_ds(seed=22, bias=0.3))
    yield TestClient(create_app())
    clear_results()


class TestCompareJobs:
    def test_returns_stats(self, client: TestClient) -> None:
        resp = client.post("/api/v1/jobs/job-a/compare/job-b")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["job_a"] == "job-a"
        assert payload["job_b"] == "job-b"
        stats = payload["stats"]
        assert stats["count"] > 0
        # bias should be roughly -0.3 (a - b, where b = a + 0.3 noise-wise)
        assert stats["bias"] < 0

    def test_missing_job_returns_404(self, client: TestClient) -> None:
        resp = client.post("/api/v1/jobs/job-a/compare/no-such-job")
        assert resp.status_code == 404

    def test_return_difference_map(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/jobs/job-a/compare/job-b",
            json={
                "variable": "snow_depth",
                "valid_only": True,
                "agreement_tolerance_m": 0.1,
                "return_difference_map": True,
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert "difference_map" in payload
        assert payload["difference_map"]["shape"] == [3, 10, 10]


class TestSnotelValidation:
    def test_uses_mocked_station_fetchers(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stations = gpd.GeoDataFrame(
            {
                "station_id": ["SNOTEL-1"],
                "name": ["Dummy"],
                "elevation_m": [2000.0],
                "latitude": [37.75],
                "longitude": [-120.25],
            },
            geometry=[ShapelyPoint(-120.25, 37.75)],
            crs="EPSG:4326",
        )
        obs = pd.DataFrame(
            {
                "station_id": ["SNOTEL-1", "SNOTEL-1"],
                "date": [date(2024, 1, 1), date(2024, 1, 13)],
                "snow_depth_m": [0.55, 0.70],
            }
        )
        monkeypatch.setattr(snotel_module, "fetch_stations", lambda aoi: stations)
        monkeypatch.setattr(snotel_module, "fetch_observations", lambda ids, tr: obs)
        resp = client.post(
            "/api/v1/jobs/job-a/validation/snotel",
            json={
                "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
                "date_range": {"start": "2024-01-01", "end": "2024-01-25"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["stations_found"] == 1
        assert body["matched_count"] >= 1


class TestGhcndValidation:
    def test_uses_mocked_fetchers(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stations = gpd.GeoDataFrame(
            {
                "station_id": ["USW00003017"],
                "name": ["BOULDER"],
                "elevation_m": [1640.0],
                "latitude": [37.75],
                "longitude": [-120.25],
            },
            geometry=[ShapelyPoint(-120.25, 37.75)],
            crs="EPSG:4326",
        )
        obs = pd.DataFrame(
            {
                "station_id": ["USW00003017"],
                "date": [date(2024, 1, 1)],
                "snow_depth_m": [0.5],
            }
        )
        monkeypatch.setattr(ghcnd_module, "fetch_stations", lambda aoi: stations)
        monkeypatch.setattr(ghcnd_module, "fetch_observations", lambda ids, tr: obs)
        resp = client.post(
            "/api/v1/jobs/job-a/validation/ghcnd",
            json={
                "bbox": {"west": -120.5, "south": 37.5, "east": -120.0, "north": 38.0},
                "date_range": {"start": "2024-01-01", "end": "2024-01-25"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["stations_found"] == 1


class TestUploadValidation:
    def test_csv_upload(self, client: TestClient) -> None:
        csv = (
            b"station_id,longitude,latitude,date,snow_depth_m\n"
            b"S1,-120.25,37.75,2024-01-01,0.55\n"
            b"S1,-120.25,37.75,2024-01-13,0.70\n"
        )
        resp = client.post(
            "/api/v1/jobs/job-a/validation/upload",
            data={"format": "csv"},
            files={"file": ("obs.csv", io.BytesIO(csv), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["stations_found"] == 1
        assert body["matched_count"] >= 1

    def test_geojson_upload(self, client: TestClient) -> None:
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-120.25, 37.75]},
                    "properties": {
                        "station_id": "S1",
                        "date": "2024-01-01",
                        "snow_depth_m": 0.55,
                    },
                }
            ],
        }
        resp = client.post(
            "/api/v1/jobs/job-a/validation/upload",
            data={"format": "geojson"},
            files={
                "file": (
                    "obs.geojson",
                    io.BytesIO(json.dumps(payload).encode()),
                    "application/geo+json",
                )
            },
        )
        assert resp.status_code == 200
        assert resp.json()["stations_found"] == 1

    def test_missing_job_returns_404(self, client: TestClient) -> None:
        csv = b"station_id,longitude,latitude,date,snow_depth_m\nS1,-120.25,37.75,2024-01-01,0.55\n"
        resp = client.post(
            "/api/v1/jobs/no-such-job/validation/upload",
            data={"format": "csv"},
            files={"file": ("obs.csv", io.BytesIO(csv), "text/csv")},
        )
        assert resp.status_code == 404
