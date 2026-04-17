"""DataProvider protocol — the core abstraction for SAR data access.

All providers must return standardized xarray.Datasets regardless of
whether data comes from Google Earth Engine or local ASF downloads.
"""

from __future__ import annotations

from typing import Protocol

import xarray as xr

from snowsar.types import AOI, SceneMetadata, TemporalRange


class DataProvider(Protocol):
    """Abstract interface for SAR data access and preprocessing.

    Output Datasets must contain these data variables:
        - gamma0_vv: float32, dB, gamma-nought VV backscatter
        - gamma0_vh: float32, dB, gamma-nought VH backscatter
        - incidence_angle: float32, degrees
        - elevation: float32, meters (from DEM)
        - slope: float32, degrees
        - aspect: float32, degrees
        - forest_cover_fraction: float32, 0-1
        - snow_cover: uint8, binary mask

    Coordinates: x, y (projected CRS), time
    Attributes: crs, orbit_number, scene_ids, platform
    """

    def query_scenes(self, aoi: AOI, temporal_range: TemporalRange) -> list[SceneMetadata]:
        """Discover available SAR scenes overlapping the AOI and date range."""
        ...

    def load_sar(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load preprocessed SAR backscatter as a standardized Dataset.

        Variables: gamma0_vv, gamma0_vh, incidence_angle.
        """
        ...

    def load_ancillary(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load ancillary data: DEM derivatives, forest cover, snow cover.

        Variables: elevation, slope, aspect, forest_cover_fraction, snow_cover.
        """
        ...

    def load_full(self, aoi: AOI, temporal_range: TemporalRange) -> xr.Dataset:
        """Load SAR + ancillary data merged into a single Dataset.

        Convenience method combining load_sar() and load_ancillary().
        """
        ...
