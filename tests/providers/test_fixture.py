"""Unit tests for FixtureProvider."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from snowsar.providers.fixture import FixtureProvider
from snowsar.providers.registry import get_provider
from snowsar.types import AOI, Backend, TemporalRange

REQUIRED_VARS = {
    "gamma0_vv",
    "gamma0_vh",
    "incidence_angle",
    "elevation",
    "slope",
    "aspect",
    "forest_cover_fraction",
    "snow_cover",
}


@pytest.fixture
def aoi() -> AOI:
    return AOI.from_bbox(-120.5, 37.5, -120.0, 38.0)


@pytest.fixture
def temporal_range() -> TemporalRange:
    return TemporalRange(start=date(2024, 1, 1), end=date(2024, 2, 29))


class TestFixtureProvider:
    def test_load_full_has_required_variables(
        self, aoi: AOI, temporal_range: TemporalRange
    ) -> None:
        ds = FixtureProvider().load_full(aoi, temporal_range)
        assert REQUIRED_VARS.issubset(ds.data_vars)
        assert ds.attrs["crs"] == "EPSG:4326"
        # Time axis non-trivial so time-series endpoints return >1 row.
        assert ds.sizes["time"] >= 2

    def test_dtypes_match_provider_contract(self, aoi: AOI, temporal_range: TemporalRange) -> None:
        ds = FixtureProvider().load_full(aoi, temporal_range)
        for var in ("gamma0_vv", "gamma0_vh", "incidence_angle", "elevation"):
            assert ds[var].dtype == np.float32, var
        assert ds["snow_cover"].dtype == np.uint8

    def test_registry_returns_fixture_provider(self) -> None:
        provider = get_provider(Backend.FIXTURE)
        assert isinstance(provider, FixtureProvider)

    def test_deterministic_across_calls(self, aoi: AOI, temporal_range: TemporalRange) -> None:
        a = FixtureProvider().load_full(aoi, temporal_range)
        b = FixtureProvider().load_full(aoi, temporal_range)
        np.testing.assert_array_equal(a["gamma0_vv"].values, b["gamma0_vv"].values)

    def test_query_scenes_returns_nonempty(self, aoi: AOI, temporal_range: TemporalRange) -> None:
        scenes = FixtureProvider().query_scenes(aoi, temporal_range)
        assert len(scenes) >= 1
        assert all(s.platform == "Sentinel-1" for s in scenes)
