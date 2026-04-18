"""Tests for GHCN-D validation module (HTTP calls mocked)."""

from __future__ import annotations

from datetime import date

import pytest

from snowsar.types import AOI, TemporalRange
from snowsar.validation import ghcnd

# Fixed-width ghcnd-stations.txt sample. Positions match the NCEI spec
# (ID 1-11, LAT 13-20, LON 22-30, ELEV 32-37, STATE 39-40, NAME 42-71).
STATIONS_FIXTURE = (
    "USW00003017  40.0000 -105.3000 1640.0 CO BOULDER                        \n"
    "USW00003018  39.5000 -105.1000 1500.0 CO DENVER                         \n"
    "USW00094240  47.4500 -122.3100   10.0 WA SEATTLE                        \n"
)

CSV_FIXTURE = (
    "STATION,DATE,SNWD\n"
    "USW00003017,2024-01-01,500\n"  # 0.5 m
    "USW00003017,2024-01-02,600\n"  # 0.6 m
    "USW00003018,2024-01-01,300\n"
)


class TestFetchStations:
    def test_filters_by_bbox(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ghcnd, "_http_get", lambda url: STATIONS_FIXTURE)
        aoi = AOI.from_bbox(-106.0, 39.0, -105.0, 40.5)
        gdf = ghcnd.fetch_stations(aoi)
        assert set(gdf["station_id"]) == {"USW00003017", "USW00003018"}
        assert gdf.crs is not None
        assert str(gdf.crs).endswith("4326")

    def test_empty_when_no_stations_in_bbox(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ghcnd, "_http_get", lambda url: STATIONS_FIXTURE)
        aoi = AOI.from_bbox(0.0, 0.0, 1.0, 1.0)
        gdf = ghcnd.fetch_stations(aoi)
        assert gdf.empty

    def test_http_failure_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(url: str) -> str:
            raise RuntimeError("network down")

        monkeypatch.setattr(ghcnd, "_http_get", boom)
        gdf = ghcnd.fetch_stations(AOI.from_bbox(-106.0, 39.0, -105.0, 40.5))
        assert gdf.empty
        assert gdf.crs is not None


class TestFetchObservations:
    def test_parses_csv_and_converts_mm_to_m(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ghcnd, "_http_get", lambda url: CSV_FIXTURE)
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 2))
        df = ghcnd.fetch_observations(["USW00003017", "USW00003018"], tr)
        assert len(df) == 3
        assert df["snow_depth_m"].max() == pytest.approx(0.6)
        assert set(df["station_id"]) == {"USW00003017", "USW00003018"}

    def test_empty_station_list(self) -> None:
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 2))
        df = ghcnd.fetch_observations([], tr)
        assert df.empty

    def test_http_failure_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(url: str) -> str:
            raise RuntimeError("500 server error")

        monkeypatch.setattr(ghcnd, "_http_get", boom)
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 2))
        df = ghcnd.fetch_observations(["USW00003017"], tr)
        assert df.empty
