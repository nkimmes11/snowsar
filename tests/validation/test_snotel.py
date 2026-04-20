"""Tests for SNOTEL validation module (NRCS AWDB HTTP calls mocked)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from snowsar.types import AOI, TemporalRange
from snowsar.validation import snotel

# Three SNOTEL-like stations: two inside a CO/ID bbox, one in AK outside it.
# Elevation is in feet (AWDB native units); latitude/longitude are EPSG:4326.
STATIONS_FIXTURE: list[dict[str, Any]] = [
    {
        "stationTriplet": "301:ID:SNTL",
        "name": "Example Station A",
        "latitude": 45.0,
        "longitude": -115.0,
        "elevation": 5000.0,
        "networkCode": "SNTL",
    },
    {
        "stationTriplet": "302:CO:SNTL",
        "name": "Example Station B",
        "latitude": 39.5,
        "longitude": -105.5,
        "elevation": 9842.52,  # ≈ 3000 m
        "networkCode": "SNTL",
    },
    {
        "stationTriplet": "999:AK:SNTL",
        "name": "Far Alaska",
        "latitude": 62.5,
        "longitude": -150.0,
        "elevation": 2000.0,
        "networkCode": "SNTL",
    },
]

# SNWD reported in inches. 39.37 in → 1.00 m; 78.74 in → 2.00 m.
DATA_FIXTURE: list[dict[str, Any]] = [
    {
        "stationTriplet": "301:ID:SNTL",
        "data": [
            {
                "stationElement": {"elementCode": "SNWD", "duration": "DAILY"},
                "values": [
                    {"date": "2024-01-01", "value": 39.37, "flag": "V"},
                    {"date": "2024-01-02", "value": 78.74, "flag": "V"},
                ],
            }
        ],
    },
    {
        "stationTriplet": "302:CO:SNTL",
        "data": [
            {
                "stationElement": {"elementCode": "SNWD", "duration": "DAILY"},
                "values": [
                    {"date": "2024-01-01", "value": 19.685, "flag": "V"},  # 0.5 m
                ],
            }
        ],
    },
]


class TestFetchStations:
    def test_filters_by_bbox_to_single_station(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(snotel, "_http_get_json", lambda url: STATIONS_FIXTURE)
        # CO-only bbox: only the 302:CO:SNTL station should survive.
        aoi = AOI.from_bbox(-106.0, 39.0, -105.0, 40.0)
        gdf = snotel.fetch_stations(aoi)
        assert set(gdf["station_id"]) == {"302:CO:SNTL"}
        assert str(gdf.crs).endswith("4326")
        # Elevation must be converted ft→m (9842.52 ft ≈ 3000 m).
        row = gdf.iloc[0]
        assert row["elevation_m"] == pytest.approx(3000.0, abs=0.1)
        assert row["latitude"] == pytest.approx(39.5)
        assert row["longitude"] == pytest.approx(-105.5)

    def test_returns_multiple_when_bbox_covers_several(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snotel, "_http_get_json", lambda url: STATIONS_FIXTURE)
        aoi = AOI.from_bbox(-120.0, 35.0, -100.0, 50.0)  # wide CONUS slice
        gdf = snotel.fetch_stations(aoi)
        assert set(gdf["station_id"]) == {"301:ID:SNTL", "302:CO:SNTL"}

    def test_empty_bbox_returns_empty_gdf(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(snotel, "_http_get_json", lambda url: STATIONS_FIXTURE)
        aoi = AOI.from_bbox(0.0, 0.0, 1.0, 1.0)  # equatorial Africa — no SNOTEL
        gdf = snotel.fetch_stations(aoi)
        assert gdf.empty
        assert str(gdf.crs).endswith("4326")

    def test_http_failure_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(url: str) -> Any:
            raise RuntimeError("AWDB 503")

        monkeypatch.setattr(snotel, "_http_get_json", boom)
        gdf = snotel.fetch_stations(AOI.from_bbox(-106.0, 39.0, -105.0, 40.0))
        assert gdf.empty
        assert str(gdf.crs).endswith("4326")


class TestFetchObservations:
    def test_parses_json_and_converts_inches_to_meters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snotel, "_http_get_json", lambda url: DATA_FIXTURE)
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 2))
        df = snotel.fetch_observations(["301:ID:SNTL", "302:CO:SNTL"], tr)
        assert len(df) == 3
        assert set(df["station_id"]) == {"301:ID:SNTL", "302:CO:SNTL"}
        # 39.37 in → 1.0 m, 78.74 in → 2.0 m — verify max is ~2.0 m.
        assert df["snow_depth_m"].max() == pytest.approx(2.0, abs=1e-3)
        assert df["snow_depth_m"].min() == pytest.approx(0.5, abs=1e-3)

    def test_empty_station_list_short_circuits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        called = {"n": 0}

        def spy(url: str) -> Any:
            called["n"] += 1
            return []

        monkeypatch.setattr(snotel, "_http_get_json", spy)
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 2))
        df = snotel.fetch_observations([], tr)
        assert df.empty
        assert called["n"] == 0  # no HTTP call when no stations

    def test_http_failure_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(url: str) -> Any:
            raise RuntimeError("AWDB timeout")

        monkeypatch.setattr(snotel, "_http_get_json", boom)
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 2))
        df = snotel.fetch_observations(["301:ID:SNTL"], tr)
        assert df.empty
        assert list(df.columns) == ["station_id", "date", "snow_depth_m"]

    def test_skips_null_values_and_bad_dates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        bad_payload: list[dict[str, Any]] = [
            {
                "stationTriplet": "301:ID:SNTL",
                "data": [
                    {
                        "stationElement": {"elementCode": "SNWD"},
                        "values": [
                            {"date": "2024-01-01", "value": None},  # null value
                            {"date": "not-a-date", "value": 10.0},  # bad date
                            {"date": "2024-01-03", "value": 39.37},  # good → 1 m
                        ],
                    }
                ],
            }
        ]
        monkeypatch.setattr(snotel, "_http_get_json", lambda url: bad_payload)
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 3))
        df = snotel.fetch_observations(["301:ID:SNTL"], tr)
        assert len(df) == 1
        assert df.iloc[0]["snow_depth_m"] == pytest.approx(1.0, abs=1e-3)
