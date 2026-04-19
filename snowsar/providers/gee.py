"""Google Earth Engine data provider for Sentinel-1 SAR data.

Uses the preprocessed COPERNICUS/S1_GRD collection and GEE-hosted
ancillary datasets (Copernicus DEM, PROBA-V FCF, IMS snow cover).
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


class GEEProvider:
    """DataProvider implementation using Google Earth Engine.

    Accesses Sentinel-1 GRD from COPERNICUS/S1_GRD and ancillary data
    from GEE-hosted collections.
    """

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

    def query_scenes(self, aoi: AOI, temporal_range: TemporalRange) -> list[SceneMetadata]:
        """Discover Sentinel-1 IW GRD scenes via GEE."""
        ee = self._ee
        bounds = aoi.bounds
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

    def load_sar(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load Sentinel-1 gamma0 VV/VH from GEE."""
        ee = self._ee
        bounds = aoi.bounds
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

        # Convert to list of images and process
        image_list = collection.toList(collection.size())
        count = collection.size().getInfo()

        if count == 0:
            msg = f"No Sentinel-1 scenes found for AOI {bounds} in {temporal_range}"
            raise DataProviderError(msg)

        logger.info("Loading %d Sentinel-1 scenes from GEE", count)

        # Build arrays from GEE — each image becomes a time step
        times: list[date] = []
        vv_arrays: list[np.ndarray] = []
        vh_arrays: list[np.ndarray] = []
        angle_arrays: list[np.ndarray] = []

        proj = ee.Projection("EPSG:4326").atScale(self._scale_m)
        for i in range(count):
            img = ee.Image(image_list.get(i)).reproject(proj)
            props = img.getInfo()["properties"]
            # GEE returns system:time_start as a millisecond epoch integer,
            # not an ISO string — divide by 1000 for seconds.
            ts_ms = props.get("system:time_start")
            if ts_ms is None:
                acq_date = date(1970, 1, 1)
            elif isinstance(ts_ms, (int, float)):
                acq_date = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC).date()
            else:
                # Defensive: fall back to string parsing if GEE ever returns ISO.
                acq_date = date.fromisoformat(str(ts_ms)[:10])
            times.append(acq_date)

            # Sample at ~100m resolution
            data = img.sampleRectangle(region=roi, defaultValue=0).getInfo()

            vv_arrays.append(np.array(data["properties"]["VV"]))
            vh_arrays.append(np.array(data["properties"]["VH"]))
            angle_arrays.append(np.array(data["properties"]["angle"]))

        # Stack into 3D arrays (time, y, x)
        vv = np.stack(vv_arrays)
        vh = np.stack(vh_arrays)
        angle = np.stack(angle_arrays)

        ny, nx = vv.shape[1], vv.shape[2]
        west, south, east, north = aoi.bounds
        # Linear lon/lat over the AOI so GeoTIFF/NetCDF output is
        # georeferenced; xarray/NetCDF also requires datetime64 on the time
        # coord (Python date objects aren't serializable).
        ys = np.linspace(south, north, ny, dtype=np.float64)
        xs = np.linspace(west, east, nx, dtype=np.float64)
        time64 = np.array([np.datetime64(t) for t in times], dtype="datetime64[ns]")
        ds = xr.Dataset(
            {
                "gamma0_vv": (["time", "y", "x"], vv.astype(np.float32)),
                "gamma0_vh": (["time", "y", "x"], vh.astype(np.float32)),
                "incidence_angle": (["time", "y", "x"], angle.astype(np.float32)),
            },
            coords={"time": time64, "y": ys, "x": xs},
            attrs={
                "crs": aoi.crs,
                "platform": "Sentinel-1",
                "source": "GEE:COPERNICUS/S1_GRD",
            },
        )
        return ds

    def load_ancillary(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load DEM, forest cover, and snow cover from GEE collections."""
        ee = self._ee
        bounds = aoi.bounds
        roi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])

        # Copernicus DEM GLO-30 is published as an ImageCollection (one Image
        # per tile); mosaic before use. Reproject to scale_m to stay under the
        # sampleRectangle pixel cap and match the grid used by load_sar().
        proj = ee.Projection("EPSG:4326").atScale(self._scale_m)
        dem = ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic().reproject(proj)
        terrain = ee.Terrain.products(dem)

        dem_data = dem.sampleRectangle(region=roi, defaultValue=0).getInfo()
        terrain_data = (
            terrain.select(["slope", "aspect"])
            .reproject(proj)
            .sampleRectangle(region=roi, defaultValue=0)
            .getInfo()
        )

        elevation = np.array(dem_data["properties"]["DEM"], dtype=np.float32)
        slope = np.array(terrain_data["properties"]["slope"], dtype=np.float32)
        aspect = np.array(terrain_data["properties"]["aspect"], dtype=np.float32)

        ny, nx = elevation.shape

        # Forest cover fraction — use Copernicus Global Land Cover
        # Simplified: initialize with zeros, to be refined with actual FCF dataset
        fcf = np.zeros((ny, nx), dtype=np.float32)

        # Snow cover — initialize with ones (assume snow present, mask later)
        snow = np.ones((ny, nx), dtype=np.uint8)

        west, south, east, north = aoi.bounds
        ys = np.linspace(south, north, ny, dtype=np.float64)
        xs = np.linspace(west, east, nx, dtype=np.float64)
        ds = xr.Dataset(
            {
                "elevation": (["y", "x"], elevation),
                "slope": (["y", "x"], slope),
                "aspect": (["y", "x"], aspect),
                "forest_cover_fraction": (["y", "x"], fcf),
                "snow_cover": (["y", "x"], snow),
            },
            coords={"y": ys, "x": xs},
            attrs={"crs": aoi.crs},
        )
        return ds

    def load_full(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load SAR + ancillary data merged into a single Dataset."""
        sar = self.load_sar(aoi, temporal_range)
        ancillary = self.load_ancillary(aoi, temporal_range)

        # Broadcast ancillary (2D) across SAR time dimension
        return xr.merge([sar, ancillary])
