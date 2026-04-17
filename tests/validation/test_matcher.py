"""Tests for spatial and temporal matching."""

from __future__ import annotations

from datetime import date

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Point

from snowsar.validation.matcher import spatial_match, temporal_match


class TestSpatialMatch:
    def test_exact_match(self) -> None:
        stations = gpd.GeoDataFrame(
            {"station_id": ["S1"]},
            geometry=[Point(-120.25, 37.75)],
            crs="EPSG:4326",
        )
        ds = xr.Dataset(
            {"snow_depth": (["y", "x"], np.ones((3, 3)))},
            coords={
                "y": [37.5, 37.75, 38.0],
                "x": [-120.5, -120.25, -120.0],
            },
        )
        matches = spatial_match(stations, ds)
        assert len(matches) == 1
        assert matches.iloc[0]["nearest_y_idx"] == 1
        assert matches.iloc[0]["nearest_x_idx"] == 1

    def test_too_far(self) -> None:
        stations = gpd.GeoDataFrame(
            {"station_id": ["S1"]},
            geometry=[Point(-115.0, 40.0)],  # Far from the grid
            crs="EPSG:4326",
        )
        ds = xr.Dataset(
            {"snow_depth": (["y", "x"], np.ones((3, 3)))},
            coords={
                "y": [37.5, 37.75, 38.0],
                "x": [-120.5, -120.25, -120.0],
            },
        )
        matches = spatial_match(stations, ds, max_distance_deg=0.01)
        assert len(matches) == 0


class TestTemporalMatch:
    def test_exact_date_match(self) -> None:
        obs = pd.DataFrame(
            {
                "station_id": ["S1"],
                "date": [date(2024, 1, 13)],
                "snow_depth_m": [1.5],
            }
        )
        ds = xr.Dataset(
            {"snow_depth": (["time"], [0.0, 0.0, 0.0])},
            coords={"time": [date(2024, 1, 1), date(2024, 1, 13), date(2024, 1, 25)]},
        )
        matched = temporal_match(obs, ds, tolerance_days=1)
        assert len(matched) == 1
        assert matched.iloc[0]["matched_time_idx"] == 1

    def test_no_match_outside_tolerance(self) -> None:
        obs = pd.DataFrame(
            {
                "station_id": ["S1"],
                "date": [date(2024, 1, 7)],
                "snow_depth_m": [1.0],
            }
        )
        ds = xr.Dataset(
            {"snow_depth": (["time"], [0.0, 0.0])},
            coords={"time": [date(2024, 1, 1), date(2024, 1, 13)]},
        )
        matched = temporal_match(obs, ds, tolerance_days=1)
        assert len(matched) == 0
