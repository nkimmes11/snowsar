"""Tests for snowsar.utils modules."""

from datetime import date

import numpy as np
import pytest
import xarray as xr

from snowsar.utils.geo import bbox_area_km2, estimate_utm_crs, reproject_geometry
from snowsar.utils.raster import (
    REQUIRED_VARIABLES,
    db_to_linear,
    linear_to_db,
    validate_dataset,
)
from snowsar.utils.temporal import day_of_year_encoding, sentinel1_prior_dates, snow_season_range


class TestGeo:
    def test_estimate_utm_north(self) -> None:
        crs = estimate_utm_crs(-119.5, 37.5)
        assert crs == "EPSG:32611"

    def test_estimate_utm_south(self) -> None:
        crs = estimate_utm_crs(-70.0, -33.0)
        assert crs == "EPSG:32719"

    def test_reproject_same_crs(self) -> None:
        from shapely.geometry import box

        geom = box(0, 0, 1, 1)
        result = reproject_geometry(geom, "EPSG:4326", "EPSG:4326")
        assert result.equals(geom)

    def test_reproject_to_utm(self) -> None:
        from shapely.geometry import Point

        pt = Point(-119.5, 37.5)
        result = reproject_geometry(pt, "EPSG:4326", "EPSG:32611")
        # UTM coordinates should be in meters, much larger than degrees
        assert result.x > 100_000

    def test_bbox_area(self) -> None:
        # 1 degree x 1 degree near equator ~ 12,321 km²
        area = bbox_area_km2(0, 0, 1, 1)
        assert 10_000 < area < 13_000


class TestRaster:
    def test_db_to_linear_roundtrip(self) -> None:
        db = xr.DataArray([-10.0, 0.0, 10.0])
        linear = db_to_linear(db)
        back = linear_to_db(linear)
        np.testing.assert_allclose(back.values, db.values, atol=1e-10)

    def test_validate_dataset_passes(self) -> None:
        ds = xr.Dataset({var: xr.DataArray([1.0]) for var in REQUIRED_VARIABLES})
        validate_dataset(ds)  # should not raise

    def test_validate_dataset_missing(self) -> None:
        ds = xr.Dataset({"gamma0_vv": xr.DataArray([1.0])})
        with pytest.raises(ValueError, match="missing required variables"):
            validate_dataset(ds)

    def test_validate_custom_required(self) -> None:
        ds = xr.Dataset({"snow_depth": xr.DataArray([1.0])})
        validate_dataset(ds, required=frozenset({"snow_depth"}))


class TestTemporal:
    def test_sentinel1_prior_dates(self) -> None:
        acq = date(2024, 3, 1)
        priors = sentinel1_prior_dates(acq)
        assert len(priors) == 4
        assert priors[0] == date(2024, 2, 24)  # 6 days prior
        assert priors[-1] == date(2024, 2, 6)  # 24 days prior

    def test_snow_season_range(self) -> None:
        start, end = snow_season_range(2024)
        assert start == date(2023, 10, 1)
        assert end == date(2024, 6, 30)

    def test_doy_encoding_range(self) -> None:
        sin_val, cos_val = day_of_year_encoding(date(2024, 6, 15))
        # sin and cos should be in [-1, 1]
        assert -1.0 <= sin_val <= 1.0
        assert -1.0 <= cos_val <= 1.0
        # sin² + cos² ≈ 1
        assert pytest.approx(sin_val**2 + cos_val**2, abs=1e-10) == 1.0
