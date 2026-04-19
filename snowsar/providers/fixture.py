"""Deterministic fixture DataProvider for local dev + tests.

Produces a small synthetic xarray.Dataset that satisfies the
DataProvider contract so the full pipeline can run without GEE
credentials or SAR downloads. Not suitable for scientific use.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import xarray as xr

from snowsar.types import AOI, SceneMetadata, TemporalRange

# Grid dimensions for fixture output. Small enough for fast tests,
# large enough that algorithms produce non-degenerate results.
_GRID_SIZE = 32
_NUM_TIMES = 6  # ≈ one Sentinel-1 repeat cycle per step over ~two months

# RNG seed kept constant so the same (aoi, temporal_range) returns the
# same array — makes tests deterministic.
_SEED = 2026


def _dates_between(start: date, end: date, count: int) -> list[date]:
    """Evenly spaced dates spanning [start, end] inclusive."""
    if count <= 1:
        return [start]
    span_days = max((end - start).days, count - 1)
    step = span_days / (count - 1)
    return [start + timedelta(days=round(i * step)) for i in range(count)]


class FixtureProvider:
    """Synthetic data provider used when backend=='fixture'."""

    def __init__(self, **_kwargs: object) -> None:
        # Accepts and ignores backend-specific kwargs (e.g. scale_m from the
        # executor) so the registry can hand them to every provider uniformly.
        pass

    def query_scenes(self, aoi: AOI, temporal_range: TemporalRange) -> list[SceneMetadata]:
        from shapely.geometry import box

        west, south, east, north = aoi.bounds
        geom = box(west, south, east, north)
        dates = _dates_between(temporal_range.start, temporal_range.end, _NUM_TIMES)
        return [
            SceneMetadata(
                scene_id=f"FIXTURE_{i:03d}",
                platform="Sentinel-1",
                orbit_number=1000 + i,
                acquisition_date=d,
                relative_orbit=42,
                geometry=geom,
            )
            for i, d in enumerate(dates)
        ]

    def load_sar(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        return self.load_full(aoi, temporal_range)[["gamma0_vv", "gamma0_vh", "incidence_angle"]]

    def load_ancillary(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        full = self.load_full(aoi, temporal_range)
        return full[["elevation", "slope", "aspect", "forest_cover_fraction", "snow_cover"]]

    def load_full(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        rng = np.random.default_rng(_SEED)
        west, south, east, north = aoi.bounds
        ny = nx = _GRID_SIZE
        ys = np.linspace(south, north, ny, dtype=np.float64)
        xs = np.linspace(west, east, nx, dtype=np.float64)
        date_list = _dates_between(temporal_range.start, temporal_range.end, _NUM_TIMES)
        # xarray/NetCDF cannot serialize Python date objects — use datetime64.
        times = np.array([np.datetime64(d) for d in date_list], dtype="datetime64[ns]")
        nt = len(times)

        elevation = rng.uniform(1000, 3000, (ny, nx)).astype(np.float32)
        slope = rng.uniform(0, 35, (ny, nx)).astype(np.float32)
        aspect = rng.uniform(0, 360, (ny, nx)).astype(np.float32)
        fcf = rng.uniform(0, 0.6, (ny, nx)).astype(np.float32)
        snow_cover = rng.choice([0, 1], size=(ny, nx), p=[0.25, 0.75]).astype(np.uint8)

        gamma0_vv = rng.uniform(-14, -6, (nt, ny, nx)).astype(np.float32)
        gamma0_vh = rng.uniform(-23, -13, (nt, ny, nx)).astype(np.float32)
        incidence = rng.uniform(32, 44, (nt, ny, nx)).astype(np.float32)

        return xr.Dataset(
            {
                "gamma0_vv": (["time", "y", "x"], gamma0_vv),
                "gamma0_vh": (["time", "y", "x"], gamma0_vh),
                "incidence_angle": (["time", "y", "x"], incidence),
                "elevation": (["y", "x"], elevation),
                "slope": (["y", "x"], slope),
                "aspect": (["y", "x"], aspect),
                "forest_cover_fraction": (["y", "x"], fcf),
                "snow_cover": (["y", "x"], snow_cover),
            },
            coords={"time": times, "y": ys, "x": xs},
            attrs={
                "crs": "EPSG:4326",
                "platform": "Sentinel-1",
                "source": "FixtureProvider",
                "orbit_number": 1000,
                "scene_ids": ",".join(f"FIXTURE_{i:03d}" for i in range(nt)),
                # Preserve the date list for any consumer that needs it.
                "start_date": str(temporal_range.start),
                "end_date": str(temporal_range.end),
            },
        )
