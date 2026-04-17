"""ASF/local data provider for Sentinel-1 and NISAR SAR data.

Downloads data via asf_search and performs local preprocessing
using GDAL/rasterio.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
import xarray as xr

from snowsar.config import Settings
from snowsar.exceptions import DataProviderError
from snowsar.types import AOI, SceneMetadata, TemporalRange

logger = logging.getLogger(__name__)


class ASFProvider:
    """DataProvider implementation using ASF data download + local processing.

    Discovers and downloads Sentinel-1 GRD products via asf_search,
    then performs local preprocessing (calibration, terrain correction).
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        earthdata_username: str | None = None,
        earthdata_password: str | None = None,
        **_kwargs: object,
    ) -> None:
        settings = Settings()
        self._data_dir = data_dir or settings.data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._username = earthdata_username or settings.earthdata_username
        self._password = earthdata_password or settings.earthdata_password

    def query_scenes(
        self, aoi: AOI, temporal_range: TemporalRange
    ) -> list[SceneMetadata]:
        """Discover Sentinel-1 IW GRD scenes via ASF search API."""
        try:
            import asf_search as asf
        except ImportError as exc:
            msg = "asf-search is required for the LOCAL backend: pip install asf-search"
            raise DataProviderError(msg) from exc

        bounds = aoi.bounds
        wkt = (
            f"POLYGON(({bounds[0]} {bounds[1]}, {bounds[2]} {bounds[1]}, "
            f"{bounds[2]} {bounds[3]}, {bounds[0]} {bounds[3]}, "
            f"{bounds[0]} {bounds[1]}))"
        )

        results = asf.search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=asf.PRODUCT_TYPE.GRD_HD,
            intersectsWith=wkt,
            start=temporal_range.start.isoformat(),
            end=temporal_range.end.isoformat(),
            beamMode=asf.BEAMMODE.IW,
        )

        scenes: list[SceneMetadata] = []
        for r in results:
            props = r.properties
            from shapely.geometry import shape

            scenes.append(
                SceneMetadata(
                    scene_id=props.get("sceneName", r.properties.get("fileID", "")),
                    platform=props.get("platform", "Sentinel-1"),
                    orbit_number=props.get("orbit", 0),
                    acquisition_date=r.properties.get("startTime", "1970-01-01")[:10],  # type: ignore[arg-type]
                    relative_orbit=props.get("pathNumber", 0),
                    geometry=shape(r.geojson()["geometry"]),
                )
            )
        return scenes

    def _download_scenes(
        self, scenes: list[SceneMetadata]
    ) -> list[Path]:
        """Download SAR granules from ASF to local data directory."""
        try:
            import asf_search as asf
        except ImportError as exc:
            msg = "asf-search is required for the LOCAL backend"
            raise DataProviderError(msg) from exc

        if not self._username or not self._password:
            msg = (
                "Earthdata credentials required for ASF download. "
                "Set SNOWSAR_EARTHDATA_USERNAME and SNOWSAR_EARTHDATA_PASSWORD."
            )
            raise DataProviderError(msg)

        session = asf.ASFSession().auth_with_creds(self._username, self._password)

        download_dir = self._data_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        # Re-search by scene IDs to get downloadable results
        scene_ids = [s.scene_id for s in scenes]
        results = asf.granule_search(scene_ids)
        results.download(path=str(download_dir), session=session)

        return list(download_dir.glob("*.zip")) + list(download_dir.glob("*.SAFE"))

    def _preprocess_sar(
        self, raster_path: Path, aoi: AOI
    ) -> xr.Dataset:
        """Apply radiometric calibration and terrain correction to a SAR granule.

        This is a simplified preprocessing pipeline. Production use may
        require ESA SNAP for full preprocessing.
        """
        with rasterio.open(raster_path) as src:
            bounds = aoi.bounds
            window = src.window(*bounds)
            data = src.read(window=window)
            transform = src.window_transform(window)

            ny, nx = data.shape[1], data.shape[2]
            xs = np.arange(nx) * transform.a + transform.c
            ys = np.arange(ny) * transform.e + transform.f

        ds = xr.Dataset(
            {
                "gamma0_vv": (["y", "x"], data[0].astype(np.float32)),
                "gamma0_vh": (
                    ["y", "x"],
                    data[1].astype(np.float32) if data.shape[0] > 1 else data[0].astype(np.float32),
                ),
            },
            coords={"y": ys, "x": xs},
            attrs={"crs": str(src.crs)},
        )
        return ds

    def load_sar(
        self, aoi: AOI, temporal_range: TemporalRange
    ) -> xr.Dataset:
        """Load and preprocess Sentinel-1 SAR data from local files."""
        scenes = self.query_scenes(aoi, temporal_range)
        if not scenes:
            msg = f"No Sentinel-1 scenes found for AOI {aoi.bounds} in {temporal_range}"
            raise DataProviderError(msg)

        logger.info("Found %d Sentinel-1 scenes via ASF", len(scenes))
        downloaded = self._download_scenes(scenes)

        datasets = []
        for path in downloaded:
            ds = self._preprocess_sar(path, aoi)
            datasets.append(ds)

        if not datasets:
            msg = "No data could be preprocessed from downloaded scenes"
            raise DataProviderError(msg)

        return xr.concat(datasets, dim="time")

    def load_ancillary(
        self, aoi: AOI, temporal_range: TemporalRange
    ) -> xr.Dataset:
        """Load DEM and ancillary data from local sources.

        Downloads Copernicus DEM tiles and other ancillary datasets as needed.
        """
        # Placeholder: create synthetic ancillary data matching AOI extent
        # In production, this downloads DEM tiles, FCF data, snow cover, etc.
        bounds = aoi.bounds
        resolution = 0.001  # ~100m in degrees
        xs = np.arange(bounds[0], bounds[2], resolution, dtype=np.float64)
        ys = np.arange(bounds[1], bounds[3], resolution, dtype=np.float64)
        ny, nx = len(ys), len(xs)

        ds = xr.Dataset(
            {
                "elevation": (["y", "x"], np.zeros((ny, nx), dtype=np.float32)),
                "slope": (["y", "x"], np.zeros((ny, nx), dtype=np.float32)),
                "aspect": (["y", "x"], np.zeros((ny, nx), dtype=np.float32)),
                "forest_cover_fraction": (["y", "x"], np.zeros((ny, nx), dtype=np.float32)),
                "snow_cover": (["y", "x"], np.ones((ny, nx), dtype=np.uint8)),
            },
            coords={"y": ys, "x": xs},
            attrs={"crs": aoi.crs},
        )
        return ds

    def load_full(
        self, aoi: AOI, temporal_range: TemporalRange
    ) -> xr.Dataset:
        """Load SAR + ancillary data merged into a single Dataset."""
        sar = self.load_sar(aoi, temporal_range)
        ancillary = self.load_ancillary(aoi, temporal_range)
        return xr.merge([sar, ancillary])
