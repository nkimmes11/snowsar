"""End-to-end tests of the output pipeline and API download endpoints."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
import xarray as xr
from fastapi.testclient import TestClient

from snowsar.algorithms.lievens import LievensAlgorithm
from snowsar.api.app import create_app
from snowsar.api.results_store import clear as clear_results
from snowsar.api.results_store import put as put_result
from snowsar.output.geotiff import write_geotiff
from snowsar.output.netcdf import write_netcdf
from snowsar.output.point_query import Point, query_points
from snowsar.output.timeseries import extract_timeseries

pytestmark = pytest.mark.integration


def _to_datetime_coords(ds: xr.Dataset) -> xr.Dataset:
    """Convert Python-date time coord to datetime64 so NetCDF serializes cleanly."""
    if "time" in ds.coords and ds["time"].dtype == object:
        dates = np.asarray(ds["time"].values)
        nano = np.array([np.datetime64(d, "ns") for d in dates])
        return ds.assign_coords(time=nano)
    return ds


@pytest.fixture
def lievens_result(integration_sar_dataset: xr.Dataset) -> xr.Dataset:
    """Run the Lievens algorithm to get a realistic result Dataset."""
    result = LievensAlgorithm().run(integration_sar_dataset)
    return _to_datetime_coords(result)


class TestOutputPipeline:
    def test_geotiff_netcdf_timeseries_point_query(
        self, lievens_result: xr.Dataset, tmp_path: Path
    ) -> None:
        """Drive the full pipeline: run an algorithm, then write + query all formats."""
        tif = tmp_path / "out.tif"
        nc = tmp_path / "out.nc"

        write_geotiff(lievens_result, tif)
        with rasterio.open(tif) as src:
            assert src.count == 1

        write_netcdf(lievens_result, nc, title="integration")
        loaded = xr.open_dataset(nc)
        try:
            assert loaded.attrs.get("Conventions") == "CF-1.8"
            assert "snow_depth" in loaded
        finally:
            loaded.close()

        ts = extract_timeseries(lievens_result)
        assert len(ts) == lievens_result.sizes["time"]

        pts_df = query_points(
            lievens_result,
            [
                Point(lon=-120.3, lat=37.7, id="center"),
                Point(lon=-120.45, lat=37.55, id="sw"),
            ],
        )
        assert set(pts_df["point_id"].unique()) == {"center", "sw"}


class TestAPIResultEndpoints:
    @pytest.fixture
    def client_with_result(self, lievens_result: xr.Dataset) -> TestClient:
        clear_results()
        put_result("job-abc", lievens_result)
        return TestClient(create_app())

    def test_netcdf_download(self, client_with_result: TestClient, tmp_path: Path) -> None:
        resp = client_with_result.get("/api/v1/jobs/job-abc/results/netcdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/x-netcdf"
        # Save and re-open to confirm it's a valid NetCDF
        nc = tmp_path / "downloaded.nc"
        nc.write_bytes(resp.content)
        loaded = xr.open_dataset(nc)
        try:
            assert "snow_depth" in loaded
        finally:
            loaded.close()

    def test_geotiff_download(self, client_with_result: TestClient, tmp_path: Path) -> None:
        resp = client_with_result.get("/api/v1/jobs/job-abc/results/geotiff")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/tiff"

    def test_timeseries_endpoint(self, client_with_result: TestClient) -> None:
        resp = client_with_result.get(
            "/api/v1/jobs/job-abc/results/timeseries",
            params={"method": "mean"},
        )
        assert resp.status_code == 200
        records = resp.json()
        assert isinstance(records, list)
        assert len(records) >= 1
        assert {"value", "n_valid", "n_total"}.issubset(records[0].keys())

    def test_points_endpoint(self, client_with_result: TestClient) -> None:
        body = {
            "points": [
                {"lon": -120.3, "lat": 37.7, "id": "A"},
                {"lon": -120.1, "lat": 37.9, "id": "B"},
            ],
            "method": "nearest",
        }
        resp = client_with_result.post("/api/v1/jobs/job-abc/results/points", json=body)
        assert resp.status_code == 200
        records = resp.json()
        ids = {r["point_id"] for r in records}
        assert ids == {"A", "B"}

    def test_missing_result_returns_404(self) -> None:
        clear_results()
        client = TestClient(create_app())
        resp = client.get("/api/v1/jobs/no-such-job/results/netcdf")
        assert resp.status_code == 404
