"""Tests for user-upload validation parser (CSV + GeoJSON)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from snowsar.exceptions import ValidationError
from snowsar.validation import user_upload

CSV_GOOD = (
    b"station_id,longitude,latitude,date,snow_depth_m\n"
    b"S1,-120.3,37.7,2024-01-01,0.50\n"
    b"S1,-120.3,37.7,2024-01-13,0.62\n"
    b"S2,-120.2,37.8,2024-01-01,0.30\n"
)

CSV_MISSING_COLUMN = b"station_id,latitude,date,snow_depth_m\nS1,37.7,2024-01-01,0.5\n"


def _geojson_bytes(features: list[dict[str, Any]]) -> bytes:
    return json.dumps({"type": "FeatureCollection", "features": features}).encode("utf-8")


class TestParseCsv:
    def test_parses_valid_csv_into_stations_and_observations(self) -> None:
        stations, observations = user_upload.parse_csv(CSV_GOOD)
        assert set(stations["station_id"]) == {"S1", "S2"}
        assert len(observations) == 3
        assert str(stations.crs).endswith("4326")

    def test_missing_required_column_raises(self) -> None:
        with pytest.raises(ValidationError, match="missing required columns"):
            user_upload.parse_csv(CSV_MISSING_COLUMN)

    def test_malformed_csv_raises(self) -> None:
        # Binary noise that can't be parsed as CSV
        with pytest.raises(ValidationError):
            user_upload.parse_csv(b"\x00\x01\x02\nnot,csv,at,all\n")


class TestParseGeojson:
    def test_parses_valid_feature_collection(self) -> None:
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-120.3, 37.7]},
                "properties": {
                    "station_id": "S1",
                    "date": "2024-01-01",
                    "snow_depth_m": 0.5,
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-120.2, 37.8]},
                "properties": {
                    "station_id": "S2",
                    "date": "2024-01-01",
                    "snow_depth_m": 0.3,
                },
            },
        ]
        stations, observations = user_upload.parse_geojson(_geojson_bytes(features))
        assert set(stations["station_id"]) == {"S1", "S2"}
        assert len(observations) == 2

    def test_skips_non_point_features(self) -> None:
        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                },
                "properties": {
                    "station_id": "poly",
                    "date": "2024-01-01",
                    "snow_depth_m": 0.1,
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-120.3, 37.7]},
                "properties": {
                    "station_id": "S1",
                    "date": "2024-01-01",
                    "snow_depth_m": 0.5,
                },
            },
        ]
        stations, _ = user_upload.parse_geojson(_geojson_bytes(features))
        assert set(stations["station_id"]) == {"S1"}

    def test_non_feature_collection_raises(self) -> None:
        with pytest.raises(ValidationError, match="FeatureCollection"):
            user_upload.parse_geojson(b'{"type": "Feature"}')

    def test_empty_feature_collection_raises(self) -> None:
        with pytest.raises(ValidationError, match="no Point features"):
            user_upload.parse_geojson(_geojson_bytes([]))


class TestParseDispatch:
    def test_csv_format(self) -> None:
        stations, _ = user_upload.parse(CSV_GOOD, format="csv")
        assert not stations.empty

    def test_unknown_format_raises(self) -> None:
        with pytest.raises(ValidationError, match="unknown format"):
            user_upload.parse(CSV_GOOD, format="xml")  # type: ignore[arg-type]
