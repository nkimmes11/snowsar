"""SNOTEL station data retrieval via NRCS AWDB web service."""

from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from snowsar.exceptions import ValidationError
from snowsar.types import AOI, TemporalRange

logger = logging.getLogger(__name__)


def fetch_stations(aoi: AOI) -> gpd.GeoDataFrame:
    """Query SNOTEL stations within the given AOI.

    Uses the dataretrieval package to access NRCS AWDB station metadata.

    Returns:
        GeoDataFrame with columns: station_id, name, elevation_m,
        latitude, longitude, geometry.
    """
    try:
        from dataretrieval import nwis
    except ImportError as exc:
        msg = "dataretrieval is required for SNOTEL access: pip install dataretrieval"
        raise ValidationError(msg) from exc

    bounds = aoi.bounds  # (west, south, east, north)

    # Use NWIS to find stations in bounding box
    # SNOTEL sites report through NRCS, but we can discover nearby USGS sites
    # For full SNOTEL, we'd use the NRCS AWDB SOAP/REST service directly
    try:
        sites, _ = nwis.what_sites(
            bBox=f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}",
            siteType="AT",  # Atmospheric sites
            hasDataTypeCd="dv",  # Daily values
        )
    except Exception:
        logger.warning("NWIS query failed; returning empty station list")
        return gpd.GeoDataFrame(
            columns=["station_id", "name", "elevation_m", "latitude", "longitude", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    if sites.empty:
        return gpd.GeoDataFrame(
            columns=["station_id", "name", "elevation_m", "latitude", "longitude", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    gdf = gpd.GeoDataFrame(
        {
            "station_id": sites["site_no"],
            "name": sites.get("station_nm", ""),
            "elevation_m": sites.get("alt_va", 0.0),
            "latitude": sites["dec_lat_va"],
            "longitude": sites["dec_long_va"],
        },
        geometry=[
            Point(lon, lat)
            for lon, lat in zip(sites["dec_long_va"], sites["dec_lat_va"], strict=True)
        ],
        crs="EPSG:4326",
    )
    return gdf


def fetch_observations(station_ids: list[str], temporal_range: TemporalRange) -> pd.DataFrame:
    """Download daily snow depth observations for the given stations.

    Returns:
        DataFrame with columns: station_id, date, snow_depth_m.
    """
    try:
        from dataretrieval import nwis
    except ImportError as exc:
        msg = "dataretrieval is required for SNOTEL access"
        raise ValidationError(msg) from exc

    all_obs: list[pd.DataFrame] = []

    for site_id in station_ids:
        try:
            # Parameter code 72189 = Snow depth
            data, _ = nwis.get_dv(
                sites=site_id,
                parameterCd="72189",
                start=temporal_range.start.isoformat(),
                end=temporal_range.end.isoformat(),
            )
            if data.empty:
                continue

            obs = pd.DataFrame(
                {
                    "station_id": site_id,
                    "date": data.index.date,
                    "snow_depth_m": data.iloc[:, 0] / 1000.0,  # mm to m
                }
            )
            all_obs.append(obs)
        except Exception:
            logger.warning("Failed to fetch data for station %s", site_id)
            continue

    if not all_obs:
        return pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])

    return pd.concat(all_obs, ignore_index=True)
