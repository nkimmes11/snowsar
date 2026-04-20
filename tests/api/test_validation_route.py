"""Regression tests for `_run_station_validation` dim-order robustness.

Covers the bug surfaced during Step 1.6b manual testing: once SNOTEL
actually returned stations, the positional indexing in
``_run_station_validation`` (``arr[t, y, x]``) blew up when the result
Dataset's ``snow_depth`` ndarray had a non-canonical dim order (e.g.
``(y, x, time)`` after xarray broadcasts inside the algorithm). The fix
uses ``.isel(time=, y=, x=)`` which binds by dim name.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from fastapi.testclient import TestClient
from shapely.geometry import Point

from snowsar.api import results_store
from snowsar.api.app import create_app
from snowsar.api.results_store import clear as clear_results
from snowsar.jobs import store as job_store
from snowsar.validation import snotel


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


def _make_result_ds(dim_order: tuple[str, str, str]) -> xr.Dataset:
    """Build a minimal result Dataset with the given snow_depth dim order.

    ``snow_depth[t, y, x] = t * 10 + y + x * 0.01`` so every cell has a
    unique, predictable value. The station at (lon=-105.25, lat=39.25)
    lands on y_idx=2, x_idx=2 of a 5x5 grid, and observation date
    2024-01-02 → time_idx=1. Expected value: 1*10 + 2 + 2*0.01 = 12.02.
    """
    times = np.array(
        [np.datetime64(date(2024, 1, 1) + pd.Timedelta(days=i)) for i in range(3)],
        dtype="datetime64[ns]",
    )
    ys = np.linspace(39.0, 39.5, 5, dtype=np.float64)  # indices 0..4
    xs = np.linspace(-105.5, -105.0, 5, dtype=np.float64)
    # Build canonical (time, y, x) data then transpose to the requested order.
    vals = np.empty((len(times), len(ys), len(xs)), dtype=np.float32)
    for t in range(len(times)):
        for y in range(len(ys)):
            for x in range(len(xs)):
                vals[t, y, x] = t * 10.0 + y + x * 0.01
    da = xr.DataArray(vals, dims=("time", "y", "x"), coords={"time": times, "y": ys, "x": xs})
    da = da.transpose(*dim_order)
    return xr.Dataset({"snow_depth": da})


_STATION: dict[str, Any] = {
    "stationTriplet": "777:CO:SNTL",
    "name": "Regression Station",
    "latitude": 39.25,
    "longitude": -105.25,
    "elevation": 10000.0,
    "networkCode": "SNTL",
}

_OBS_PAYLOAD: list[dict[str, Any]] = [
    {
        "stationTriplet": "777:CO:SNTL",
        "data": [
            {
                "stationElement": {"elementCode": "SNWD"},
                "values": [
                    # 47.24 in ≈ 1.2 m; obs_date 2024-01-02 → time_idx=1.
                    {"date": "2024-01-02", "value": 47.24},
                ],
            }
        ],
    }
]


def _seed_job(job_id: str, dim_order: tuple[str, str, str]) -> None:
    results_store.put(job_id, _make_result_ds(dim_order))


@pytest.mark.parametrize(
    "dim_order",
    [
        ("time", "y", "x"),  # canonical
        ("y", "x", "time"),  # the order that broke before the fix
        ("x", "time", "y"),  # arbitrary permutation
    ],
)
def test_snotel_validation_is_dim_order_robust(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    dim_order: tuple[str, str, str],
) -> None:
    job_id = "regression-" + "-".join(dim_order)
    _seed_job(job_id, dim_order)

    # Stub the NRCS AWDB fetches so the route uses the same station/obs
    # regardless of real network state.
    def fake_stations(_aoi: Any) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            [
                {
                    "station_id": "777:CO:SNTL",
                    "name": _STATION["name"],
                    "elevation_m": 3000.0,
                    "latitude": 39.25,
                    "longitude": -105.25,
                }
            ],
            geometry=[Point(-105.25, 39.25)],
            crs="EPSG:4326",
        )

    def fake_obs(_ids: list[str], _tr: Any) -> pd.DataFrame:
        return pd.DataFrame(
            [{"station_id": "777:CO:SNTL", "date": date(2024, 1, 2), "snow_depth_m": 1.2}]
        )

    monkeypatch.setattr(snotel, "fetch_stations", fake_stations)
    monkeypatch.setattr(snotel, "fetch_observations", fake_obs)

    resp = client.post(
        f"/api/v1/jobs/{job_id}/validation/snotel",
        json={
            "bbox": {"west": -105.5, "south": 39.0, "east": -105.0, "north": 39.5},
            "date_range": {"start": "2024-01-01", "end": "2024-01-03"},
            "max_distance_deg": 0.5,
            "tolerance_days": 1,
        },
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["stations_found"] == 1
    assert payload["observations_found"] == 1
    assert payload["matched_count"] == 1
    pair = payload["pairs"][0]
    # Expected predicted value: t=1, y_idx=2, x_idx=2 → 1*10 + 2 + 2*0.01 = 12.02.
    assert pair["predicted_m"] == pytest.approx(12.02, abs=1e-4)
    assert pair["observed_m"] == pytest.approx(1.2, abs=1e-6)
