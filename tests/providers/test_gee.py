"""Unit tests for the GEE provider's pure helpers.

The live ee round-trip is covered by manual browser testing (documented
in memory/project_status.md); these tests exercise the data-transform
logic that was previously embedded in long methods and is now isolated
into module-level helpers as part of Step 1.3b.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from snowsar.providers.gee import (
    _ensure_4326_bounds,
    _extract_ancillary_bands,
    _extract_sar_bands,
    _parse_time_ms,
)


class TestEnsure4326Bounds:
    def test_returns_bounds_unchanged_for_4326(self) -> None:
        bounds = (-105.5, 39.0, -105.0, 39.5)
        assert _ensure_4326_bounds(bounds, "EPSG:4326") == bounds

    def test_accepts_4326_variants(self) -> None:
        bounds = (-105.5, 39.0, -105.0, 39.5)
        for crs in ("EPSG:4326", "epsg:4326", "4326", "WGS84"):
            assert _ensure_4326_bounds(bounds, crs) == bounds

    def test_transforms_utm_bounds_to_4326(self) -> None:
        # UTM Zone 13N bounds straddling the 500000 m central meridian (which
        # is -105° E). Transformed bounds should land in central Colorado.
        utm_bounds = (489000.0, 4422000.0, 509000.0, 4433000.0)
        west, south, east, north = _ensure_4326_bounds(utm_bounds, "EPSG:32613")
        # Envelope should sit within a generous Colorado box.
        assert -106.0 < west < -104.0, f"west={west}"
        assert -106.0 < east < -104.0, f"east={east}"
        assert 39.0 < south < 41.0, f"south={south}"
        assert 39.0 < north < 41.0, f"north={north}"
        # Envelope must be well-ordered and actually transformed (not a no-op).
        assert west < east
        assert south < north
        assert west != utm_bounds[0]

    def test_unknown_crs_raises(self) -> None:
        # Unknown/empty CRS must fail fast via pyproj rather than silently
        # returning the input bounds as if they were 4326.
        import pyproj

        bounds = (-105.5, 39.0, -105.0, 39.5)
        with pytest.raises(pyproj.exceptions.CRSError):
            _ensure_4326_bounds(bounds, "not-a-real-crs")


class TestParseTimeMs:
    def test_millisecond_epoch_int(self) -> None:
        # 2024-01-15 00:00:00 UTC == 1705276800000 ms
        assert _parse_time_ms(1705276800000) == date(2024, 1, 15)

    def test_millisecond_epoch_float(self) -> None:
        assert _parse_time_ms(1705276800000.0) == date(2024, 1, 15)

    def test_none_returns_epoch(self) -> None:
        assert _parse_time_ms(None) == date(1970, 1, 1)

    def test_iso_fallback(self) -> None:
        # Defensive path: GEE sometimes returns ISO strings for older assets.
        assert _parse_time_ms("2024-01-15T12:34:56") == date(2024, 1, 15)


class TestExtractSarBands:
    def _make_sample(self, scene_ids: list[str], ny: int, nx: int) -> dict[str, object]:
        """Build a toBands()-style payload with per-scene VV/VH/angle."""
        props: dict[str, object] = {}
        for i, sid in enumerate(scene_ids):
            props[f"{sid}_VV"] = [[i * 1.0 + c * 0.01 for c in range(nx)] for _ in range(ny)]
            props[f"{sid}_VH"] = [[i * 2.0 + c * 0.01 for c in range(nx)] for _ in range(ny)]
            props[f"{sid}_angle"] = [[30.0 + i for _ in range(nx)] for _ in range(ny)]
        return props

    def test_stacks_in_scene_order(self) -> None:
        scene_ids = ["S1A_A", "S1A_B", "S1A_C"]
        props = self._make_sample(scene_ids, ny=4, nx=5)
        vv, vh, angle = _extract_sar_bands(props, scene_ids)
        assert vv.shape == (3, 4, 5)
        assert vv.dtype == np.float32
        # Values in first column of each scene encode the scene index.
        assert vv[0, 0, 0] == pytest.approx(0.0)
        assert vv[1, 0, 0] == pytest.approx(1.0)
        assert vv[2, 0, 0] == pytest.approx(2.0)
        assert vh[1, 0, 0] == pytest.approx(2.0)  # 1 * 2.0
        assert angle[2, 0, 0] == pytest.approx(32.0)

    def test_falls_back_to_ordinal_prefix(self) -> None:
        # When toBands drops system:index and uses ordinals, keys look like
        # "0_VV", "1_VV", … The extractor must fall through to that pattern.
        props: dict[str, object] = {}
        for i in range(2):
            props[f"{i}_VV"] = [[float(i)]]
            props[f"{i}_VH"] = [[float(i * 10)]]
            props[f"{i}_angle"] = [[30.0 + i]]
        scene_ids = ["ignored_a", "ignored_b"]
        vv, vh, angle = _extract_sar_bands(props, scene_ids)
        assert vv.shape == (2, 1, 1)
        assert vh[1, 0, 0] == pytest.approx(10.0)
        assert angle[0, 0, 0] == pytest.approx(30.0)

    def test_missing_band_raises_keyerror(self) -> None:
        # Neither <id>_<band> nor <i>_<band> present → actionable KeyError.
        props: dict[str, object] = {"S1A_A_VV": [[0.0]]}
        with pytest.raises(KeyError, match="missing band"):
            _extract_sar_bands(props, ["S1A_A"])


class TestExtractAncillaryBands:
    def test_returns_all_five_layers_with_correct_dtypes(self) -> None:
        props: dict[str, object] = {
            "DEM": [[1000.0, 1100.0], [1200.0, 1300.0]],
            "slope": [[5.0, 6.0], [7.0, 8.0]],
            "aspect": [[90.0, 180.0], [270.0, 0.0]],
            "forest_cover_fraction": [[0.0, 0.5], [0.25, 0.75]],
            "snow_cover": [[0, 1], [1, 0]],
        }
        bands = _extract_ancillary_bands(props)
        assert set(bands.keys()) == {
            "elevation",
            "slope",
            "aspect",
            "forest_cover_fraction",
            "snow_cover",
        }
        assert bands["elevation"].dtype == np.float32
        assert bands["forest_cover_fraction"].dtype == np.float32
        assert bands["snow_cover"].dtype == np.uint8
        # FCF should stay in 0-1 fraction range after the divide-by-100
        # that happens server-side (not in this helper, but we document
        # the contract: helper is unit-consistent with caller expectations).
        assert 0.0 <= float(bands["forest_cover_fraction"].min()) <= 1.0
        assert 0.0 <= float(bands["forest_cover_fraction"].max()) <= 1.0
        # Snow cover is binary.
        assert set(np.unique(bands["snow_cover"]).tolist()) <= {0, 1}
