"""GHCN-Daily station data retrieval via NOAA NCEI Access Data Service.

The NCEI Access Data Service returns GHCN-D station summaries as CSV
without requiring an API token:

    https://www.ncei.noaa.gov/access/services/data/v1

Station metadata comes from the station-inventory text file:

    https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING
from urllib.parse import urlencode
from urllib.request import urlopen

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from snowsar.exceptions import ValidationError

if TYPE_CHECKING:
    from snowsar.types import AOI, TemporalRange

logger = logging.getLogger(__name__)

STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
ACCESS_SERVICE_URL = "https://www.ncei.noaa.gov/access/services/data/v1"

# ghcnd-stations.txt is a fixed-width file. Columns per the GHCN-D readme:
#   ID            1-11   Character
#   LATITUDE     13-20   Real
#   LONGITUDE    22-30   Real
#   ELEVATION    32-37   Real
#   STATE        39-40   Character
#   NAME         42-71   Character
_STATION_COLSPECS = [
    (0, 11),
    (12, 20),
    (21, 30),
    (31, 37),
    (38, 40),
    (41, 71),
]
_STATION_COLUMNS = ["station_id", "latitude", "longitude", "elevation_m", "state", "name"]


def _http_get(url: str) -> str:
    """Fetch a URL and return the response body as text. Separated for test mocking."""
    with urlopen(url, timeout=60) as resp:
        raw: bytes = resp.read()
    return raw.decode("utf-8", errors="replace")


def _load_station_inventory() -> pd.DataFrame:
    """Download and parse the full GHCN-D station inventory as a DataFrame."""
    text = _http_get(STATIONS_URL)
    df = pd.read_fwf(
        io.StringIO(text),
        colspecs=_STATION_COLSPECS,
        names=_STATION_COLUMNS,
        dtype={"station_id": str, "state": str, "name": str},
    )
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["elevation_m"] = pd.to_numeric(df["elevation_m"], errors="coerce")
    return df


def fetch_stations(aoi: AOI) -> gpd.GeoDataFrame:
    """Return GHCN-D stations within the given AOI bounding box.

    Args:
        aoi: Area of interest (must be in EPSG:4326 lon/lat).

    Returns:
        GeoDataFrame with columns ``station_id``, ``name``, ``elevation_m``,
        ``latitude``, ``longitude``, ``geometry`` (EPSG:4326).
    """
    try:
        inventory = _load_station_inventory()
    except Exception as exc:
        logger.warning("GHCN-D station inventory fetch failed: %s", exc)
        return gpd.GeoDataFrame(
            columns=["station_id", "name", "elevation_m", "latitude", "longitude", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    west, south, east, north = aoi.bounds
    inside = (
        (inventory["longitude"] >= west)
        & (inventory["longitude"] <= east)
        & (inventory["latitude"] >= south)
        & (inventory["latitude"] <= north)
    )
    hits = inventory.loc[inside].copy()

    if hits.empty:
        return gpd.GeoDataFrame(
            columns=["station_id", "name", "elevation_m", "latitude", "longitude", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    geometry = [
        Point(lon, lat) for lon, lat in zip(hits["longitude"], hits["latitude"], strict=True)
    ]
    gdf = gpd.GeoDataFrame(
        {
            "station_id": hits["station_id"].values,
            "name": hits["name"].fillna("").values,
            "elevation_m": hits["elevation_m"].fillna(0.0).astype(float).values,
            "latitude": hits["latitude"].astype(float).values,
            "longitude": hits["longitude"].astype(float).values,
        },
        geometry=geometry,
        crs="EPSG:4326",
    )
    return gdf


def fetch_observations(
    station_ids: list[str],
    temporal_range: TemporalRange,
) -> pd.DataFrame:
    """Download daily snow-depth (SNWD) observations for the given stations.

    GHCN-D reports SNWD in millimeters; values are converted to meters.

    Returns:
        DataFrame with columns ``station_id``, ``date``, ``snow_depth_m``.
    """
    if not station_ids:
        return pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])

    query = urlencode(
        {
            "dataset": "daily-summaries",
            "stations": ",".join(station_ids),
            "startDate": temporal_range.start.isoformat(),
            "endDate": temporal_range.end.isoformat(),
            "dataTypes": "SNWD",
            "format": "csv",
            "units": "metric",
        }
    )
    url = f"{ACCESS_SERVICE_URL}?{query}"

    try:
        body = _http_get(url)
    except Exception as exc:
        logger.warning("GHCN-D access service fetch failed: %s", exc)
        return pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])

    try:
        df = pd.read_csv(io.StringIO(body))
    except Exception as exc:
        msg = f"failed to parse GHCN-D CSV response: {exc}"
        raise ValidationError(msg) from exc

    if df.empty or "STATION" not in df.columns or "DATE" not in df.columns:
        return pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])
    if "SNWD" not in df.columns:
        return pd.DataFrame(columns=["station_id", "date", "snow_depth_m"])

    out = pd.DataFrame(
        {
            "station_id": df["STATION"].astype(str),
            "date": pd.to_datetime(df["DATE"]).dt.date,
            "snow_depth_m": pd.to_numeric(df["SNWD"], errors="coerce") / 1000.0,
        }
    )
    out = out.dropna(subset=["snow_depth_m"]).reset_index(drop=True)
    return out
