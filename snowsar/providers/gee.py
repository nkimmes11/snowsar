"""Google Earth Engine data provider for Sentinel-1 SAR data.

Uses GEE-hosted collections:
  * ``COPERNICUS/S1_GRD`` — Sentinel-1 GRD (VV/VH/angle)
  * ``COPERNICUS/DEM/GLO30`` — Copernicus DEM GLO-30
  * ``COPERNICUS/Landcover/100m/Proba-V-C3/Global`` — PROBA-V forest cover
  * ``MODIS/061/MOD10A1`` — MODIS daily snow cover (NDSI)

CRS
---
GEE output is always EPSG:4326 under the current sampling model. The
provider normalizes the input AOI's bounds to 4326 (via pyproj) if the
AOI is declared in another CRS, and sets ``attrs["crs"] = "EPSG:4326"``
unconditionally. Downstream callers that want another CRS should
reproject the output Dataset themselves.

Batching
--------
All pixel fetches use a single ``sampleRectangle().getInfo()`` per
Dataset. Scene metadata (count, ids, timestamps) is fetched in one
bundled ``ee.Dictionary().getInfo()``. Total round-trips per job:
2 for SAR + 1 for ancillary = 3, regardless of scene count.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

import numpy as np
import xarray as xr

from snowsar.exceptions import DataProviderError
from snowsar.types import AOI, SceneMetadata, TemporalRange

logger = logging.getLogger(__name__)


def _initialize_ee(project: str | None = None) -> Any:
    """Initialize the Earth Engine API, returning the ee module."""
    try:
        import ee
    except ImportError as exc:
        msg = "earthengine-api is required for the GEE backend: pip install earthengine-api"
        raise DataProviderError(msg) from exc

    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
    except Exception as exc:
        detail = str(exc)
        if "no project" in detail.lower() or "project=" in detail.lower():
            msg = (
                "Earth Engine requires a Google Cloud project. Set the "
                "SNOWSAR_GEE_PROJECT environment variable to your project ID "
                "and restart the API server."
            )
        elif "authorize" in detail.lower() or "authenticate" in detail.lower():
            msg = (
                "Earth Engine is not authenticated on this machine. Run "
                "`earthengine authenticate` (or `ee.Authenticate()` in Python) "
                "and restart the API server."
            )
        else:
            msg = f"Failed to initialize Earth Engine: {detail}"
        raise DataProviderError(msg) from exc
    return ee


# ---------------------------------------------------------------------------
# Pure helpers (no ee dependency) — unit-testable without a live GEE session.
# ---------------------------------------------------------------------------


def _ensure_4326_bounds(
    bounds: tuple[float, float, float, float],
    src_crs: str,
) -> tuple[float, float, float, float]:
    """Return AOI bounds (w, s, e, n) in EPSG:4326 regardless of the declared CRS.

    If ``src_crs`` already names 4326 the bounds are returned unchanged.
    Otherwise the four corners are transformed via pyproj and the bounding
    envelope of the transformed corners is returned.
    """
    normalized = (src_crs or "").upper()
    if normalized in {"EPSG:4326", "4326", "WGS84", "EPSG:WGS84"}:
        return bounds
    from pyproj import Transformer

    transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    west, south, east, north = bounds
    xs: list[float] = []
    ys: list[float] = []
    for x, y in ((west, south), (west, north), (east, south), (east, north)):
        tx, ty = transformer.transform(x, y)
        xs.append(tx)
        ys.append(ty)
    return (min(xs), min(ys), max(xs), max(ys))


def _parse_time_ms(ts_ms: Any) -> date:
    """Parse GEE ``system:time_start`` into a date. Tolerates ISO fallback + None."""
    if ts_ms is None:
        return date(1970, 1, 1)
    if isinstance(ts_ms, (int, float)):
        return datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=UTC).date()
    return date.fromisoformat(str(ts_ms)[:10])


def _extract_sar_bands(
    sample_props: dict[str, Any],
    scene_ids: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pull per-scene VV/VH/angle arrays out of a ``toBands().sampleRectangle()`` payload.

    GEE's ``ImageCollection.toBands()`` prefixes each band with the source
    image's ``system:index``. If a given ``<id>_<band>`` key is absent this
    helper falls back to the ordinal ``<i>_<band>`` pattern GEE uses when
    indices are missing or duplicated.
    """

    def _fetch(key_id: str, i: int, band: str) -> np.ndarray:
        primary = f"{key_id}_{band}"
        if primary in sample_props:
            return np.asarray(sample_props[primary], dtype=np.float32)
        fallback = f"{i}_{band}"
        if fallback in sample_props:
            return np.asarray(sample_props[fallback], dtype=np.float32)
        msg = f"toBands sample is missing band for scene {key_id!r} ({primary}/{fallback})"
        raise KeyError(msg)

    vv = np.stack([_fetch(sid, i, "VV") for i, sid in enumerate(scene_ids)])
    vh = np.stack([_fetch(sid, i, "VH") for i, sid in enumerate(scene_ids)])
    angle = np.stack([_fetch(sid, i, "angle") for i, sid in enumerate(scene_ids)])
    return vv, vh, angle


def _extract_ancillary_bands(sample_props: dict[str, Any]) -> dict[str, np.ndarray]:
    """Pull elevation/slope/aspect/forest_cover_fraction/snow_cover out of a combined sample."""
    return {
        "elevation": np.asarray(sample_props["DEM"], dtype=np.float32),
        "slope": np.asarray(sample_props["slope"], dtype=np.float32),
        "aspect": np.asarray(sample_props["aspect"], dtype=np.float32),
        "forest_cover_fraction": np.asarray(
            sample_props["forest_cover_fraction"], dtype=np.float32
        ),
        "snow_cover": np.asarray(sample_props["snow_cover"], dtype=np.uint8),
    }


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GEEProvider:
    """DataProvider implementation using Google Earth Engine."""

    def __init__(
        self,
        project: str | None = None,
        scale_m: int = 100,
        **_kwargs: object,
    ) -> None:
        self._ee = _initialize_ee(project)
        # sampleRectangle is capped at 262144 pixels per request; sampling at
        # native Sentinel-1 resolution (~10 m) exceeds that for any realistic
        # AOI. Reproject to scale_m (default 100 m) before sampling.
        self._scale_m = scale_m

    # -- scene discovery ----------------------------------------------------

    def query_scenes(self, aoi: AOI, temporal_range: TemporalRange) -> list[SceneMetadata]:
        """Discover Sentinel-1 IW GRD scenes via GEE."""
        ee = self._ee
        bounds = _ensure_4326_bounds(aoi.bounds, str(aoi.crs))
        roi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])

        collection = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi)
            .filterDate(
                temporal_range.start.isoformat(),
                temporal_range.end.isoformat(),
            )
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        )

        info = collection.getInfo()
        scenes: list[SceneMetadata] = []
        from shapely.geometry import shape

        for feature in info.get("features", []):
            props = feature["properties"]
            ts_ms = props.get("system:time_start")
            if isinstance(ts_ms, (int, float)):
                acq_date = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC).date()
            else:
                acq_date = date(1970, 1, 1)
            scenes.append(
                SceneMetadata(
                    scene_id=props.get("system:index", ""),
                    platform=props.get("platform_number", ""),
                    orbit_number=props.get("orbitNumber_start", 0),
                    acquisition_date=acq_date,
                    relative_orbit=props.get("relativeOrbitNumber_start", 0),
                    geometry=shape(feature.get("geometry", {})),
                )
            )
        return scenes

    # -- SAR ----------------------------------------------------------------

    def load_sar(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load Sentinel-1 gamma0 VV/VH from GEE in 2 round-trips."""
        ee = self._ee
        bounds = _ensure_4326_bounds(aoi.bounds, str(aoi.crs))
        roi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])

        collection = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi)
            .filterDate(
                temporal_range.start.isoformat(),
                temporal_range.end.isoformat(),
            )
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .select(["VV", "VH", "angle"])
        )

        proj = ee.Projection("EPSG:4326").atScale(self._scale_m)

        # Round-trip 1: bundle count + ids + times into one server-side dict.
        meta = ee.Dictionary(
            {
                "count": collection.size(),
                "ids": collection.aggregate_array("system:index"),
                "times": collection.aggregate_array("system:time_start"),
            }
        ).getInfo()
        count = int(meta.get("count", 0))

        if count == 0:
            msg = f"No Sentinel-1 scenes found for AOI {bounds} in {temporal_range}"
            raise DataProviderError(msg)

        scene_ids: list[str] = [str(s) for s in meta.get("ids", [])]
        time_ms_list: list[Any] = list(meta.get("times", []))

        logger.info("Loading %d Sentinel-1 scenes from GEE (batched, 2 round-trips)", count)

        # Reproject each image so sampleRectangle stays under the 262k-pixel cap,
        # then stack the whole collection into one multi-band image.
        stacked = collection.map(lambda img: img.reproject(proj)).toBands()

        # Round-trip 2: a single sampleRectangle for every scene's pixels.
        sample = stacked.sampleRectangle(region=roi, defaultValue=0).getInfo()
        sample_props = sample["properties"]

        vv, vh, angle = _extract_sar_bands(sample_props, scene_ids)
        times = [_parse_time_ms(t) for t in time_ms_list]

        ny, nx = vv.shape[1], vv.shape[2]
        west, south, east, north = bounds
        # Linear lon/lat over the (4326-normalized) AOI. datetime64[ns] is
        # required by xarray/NetCDF; Python date objects aren't serializable.
        ys = np.linspace(south, north, ny, dtype=np.float64)
        xs = np.linspace(west, east, nx, dtype=np.float64)
        time64 = np.array([np.datetime64(t) for t in times], dtype="datetime64[ns]")
        return xr.Dataset(
            {
                "gamma0_vv": (["time", "y", "x"], vv.astype(np.float32)),
                "gamma0_vh": (["time", "y", "x"], vh.astype(np.float32)),
                "incidence_angle": (["time", "y", "x"], angle.astype(np.float32)),
            },
            coords={"time": time64, "y": ys, "x": xs},
            attrs={
                "crs": "EPSG:4326",
                "platform": "Sentinel-1",
                "source": "GEE:COPERNICUS/S1_GRD",
            },
        )

    # -- ancillary ----------------------------------------------------------

    def _build_ancillary_image(self, temporal_range: TemporalRange) -> Any:
        """Stack DEM + slope + aspect + FCF + snow_cover into one reprojected image.

        * FCF: ``COPERNICUS/Landcover/100m/Proba-V-C3/Global`` band
          ``tree-coverfraction`` (percent 0-100) → fraction 0-1.
        * Snow cover: ``MODIS/061/MOD10A1`` band ``NDSI_Snow_Cover`` reduced
          by ``.max()`` across the temporal range, then thresholded at NDSI ≥ 40
          (the standard MODIS snow-flagging convention) → binary uint8.
        """
        ee = self._ee
        proj = ee.Projection("EPSG:4326").atScale(self._scale_m)

        dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic().reproject(proj)
        terrain = ee.Terrain.products(dem).select(["slope", "aspect"]).reproject(proj)

        fcf = (
            ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global")
            .select("tree-coverfraction")
            .mosaic()
            .divide(100.0)
            .rename("forest_cover_fraction")
            .reproject(proj)
        )

        snow_mask = (
            ee.ImageCollection("MODIS/061/MOD10A1")
            .filterDate(
                temporal_range.start.isoformat(),
                temporal_range.end.isoformat(),
            )
            .select("NDSI_Snow_Cover")
            .max()
            .gte(40)
            .rename("snow_cover")
            .reproject(proj)
        )

        return dem.addBands(terrain).addBands(fcf).addBands(snow_mask)

    def load_ancillary(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load DEM + terrain + FCF + snow mask from GEE in 1 round-trip."""
        ee = self._ee
        bounds = _ensure_4326_bounds(aoi.bounds, str(aoi.crs))
        roi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])

        combined = self._build_ancillary_image(temporal_range)
        sample = combined.sampleRectangle(region=roi, defaultValue=0).getInfo()
        sample_props = sample["properties"]

        bands = _extract_ancillary_bands(sample_props)
        ny, nx = bands["elevation"].shape
        west, south, east, north = bounds
        ys = np.linspace(south, north, ny, dtype=np.float64)
        xs = np.linspace(west, east, nx, dtype=np.float64)

        return xr.Dataset(
            {name: (["y", "x"], arr) for name, arr in bands.items()},
            coords={"y": ys, "x": xs},
            attrs={"crs": "EPSG:4326"},
        )

    # -- convenience --------------------------------------------------------

    def load_full(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load SAR + ancillary data merged into a single Dataset."""
        sar = self.load_sar(aoi, temporal_range)
        ancillary = self.load_ancillary(aoi, temporal_range)
        return xr.merge([sar, ancillary])
