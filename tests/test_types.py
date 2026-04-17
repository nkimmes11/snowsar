"""Tests for snowsar.types."""

from datetime import date

import pytest
from shapely.geometry import box

from snowsar.types import (
    AOI,
    AlgorithmID,
    Backend,
    JobParameters,
    QualityFlag,
    SnowClass,
    TemporalRange,
)


class TestAOI:
    def test_from_bbox(self) -> None:
        aoi = AOI.from_bbox(-120.0, 37.0, -119.0, 38.0)
        assert aoi.crs == "EPSG:4326"
        assert aoi.bounds == pytest.approx((-120.0, 37.0, -119.0, 38.0))

    def test_from_geometry(self) -> None:
        geom = box(0, 0, 1, 1)
        aoi = AOI(geometry=geom, crs="EPSG:32610")
        assert aoi.crs == "EPSG:32610"
        assert aoi.bounds == (0.0, 0.0, 1.0, 1.0)

    def test_frozen(self) -> None:
        aoi = AOI.from_bbox(0, 0, 1, 1)
        with pytest.raises(AttributeError):
            aoi.crs = "EPSG:32610"  # type: ignore[misc]


class TestTemporalRange:
    def test_valid_range(self) -> None:
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 3, 31))
        assert tr.days == 90

    def test_same_day(self) -> None:
        tr = TemporalRange(start=date(2024, 1, 1), end=date(2024, 1, 1))
        assert tr.days == 0

    def test_invalid_range(self) -> None:
        with pytest.raises(ValueError, match=r"start .* must be <= end"):
            TemporalRange(start=date(2024, 6, 1), end=date(2024, 1, 1))


class TestEnums:
    def test_algorithm_ids(self) -> None:
        assert AlgorithmID.LIEVENS.value == "lievens"
        assert AlgorithmID.ML.value == "ml"
        assert AlgorithmID.DPRSE.value == "dprse"
        assert AlgorithmID.INSAR.value == "insar"

    def test_backends(self) -> None:
        assert Backend.GEE is not Backend.LOCAL

    def test_quality_flags_are_integers(self) -> None:
        assert int(QualityFlag.VALID) == 0
        assert int(QualityFlag.WET_SNOW) == 1
        assert int(QualityFlag.OUTSIDE_RANGE) == 5

    def test_snow_classes(self) -> None:
        assert len(SnowClass) == 6
        assert SnowClass.ALPINE.value == "alpine"


class TestJobParameters:
    def test_defaults(self) -> None:
        params = JobParameters(
            aoi=AOI.from_bbox(-120, 37, -119, 38),
            temporal_range=TemporalRange(date(2024, 1, 1), date(2024, 3, 31)),
            algorithms=[AlgorithmID.LIEVENS],
        )
        assert params.backend == Backend.GEE
        assert params.resolution_m == 100
        assert params.algorithm_params == {}
