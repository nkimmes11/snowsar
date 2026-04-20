"""SNOTEL station data retrieval via the NRCS AWDB REST API.

SNOTEL stations are operated by NRCS/USDA (not USGS). They are *not*
hosted by the USGS NWIS service the previous implementation queried,
which is why that version always returned zero stations.

The authoritative public REST service is AWDB:

    https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/

Endpoints used here:
  * ``GET /stations?networkCodes=SNTL`` — full SNOTEL inventory
  * ``GET /data?stationTriplets=...&elements=SNWD&duration=DAILY&...``
    — daily snow-depth observations

AWDB reports SNWD in inches and station elevation in feet. Both are
converted to SI (meters) before return so callers see the same units
as the GHCN-D module.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from snowsar.types import AOI, TemporalRange

logger = logging.getLogger(__name__)

AWDB_BASE_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1"

_INCHES_TO_METERS = 0.0254
_FEET_TO_METERS = 0.3048

_STATION_COLUMNS = ["station_id", "name", "elevation_m", "latitude", "longitude", "geometry"]
_OBS_COLUMNS = ["station_id", "date", "snow_depth_m"]


def _http_get_json(url: str) -> Any:
    """GET ``url`` and parse the response body as JSON. Separated for test mocking."""
    with urlopen(url, timeout=60) as resp:
        raw: bytes = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def _empty_stations_gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        columns=_STATION_COLUMNS,
        geometry="geometry",
        crs="EPSG:4326",
    )


def fetch_stations(aoi: AOI) -> gpd.GeoDataFrame:
    """Return SNOTEL stations within the given AOI bounding box.

    Queries ``/stations?networkCodes=SNTL`` and applies a bounding-box
    filter client-side (AWDB's bbox query parameters vary by service
    version; filtering locally is simpler and robust).

    Returns:
        GeoDataFrame with columns ``station_id``, ``name``, ``elevation_m``,
        ``latitude``, ``longitude``, ``geometry`` (EPSG:4326). ``station_id``
        is the AWDB station triplet (e.g. ``"301:ID:SNTL"``) — pass the
        same values to :func:`fetch_observations`.
    """
    url = f"{AWDB_BASE_URL}/stations?" + urlencode({"networkCodes": "SNTL"})
    try:
        stations = _http_get_json(url)
    except Exception as exc:
        logger.warning("NRCS AWDB station fetch failed: %s", exc)
        return _empty_stations_gdf()

    if not isinstance(stations, list) or not stations:
        return _empty_stations_gdf()

    west, south, east, north = aoi.bounds
    records: list[dict[str, Any]] = []
    for s in stations:
        lat = s.get("latitude")
        lon = s.get("longitude")
        if lat is None or lon is None:
            continue
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            continue
        if not (south <= lat_f <= north and west <= lon_f <= east):
            continue
        elev_raw = s.get("elevation")
        try:
            elev_m = float(elev_raw) * _FEET_TO_METERS if elev_raw is not None else 0.0
        except (TypeError, ValueError):
            elev_m = 0.0
        records.append(
            {
                "station_id": str(s.get("stationTriplet", "")),
                "name": str(s.get("name", "")),
                "elevation_m": elev_m,
                "latitude": lat_f,
                "longitude": lon_f,
            }
        )

    if not records:
        return _empty_stations_gdf()

    df = pd.DataFrame(records)
    geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"], strict=True)]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def fetch_observations(
    station_ids: list[str],
    temporal_range: TemporalRange,
) -> pd.DataFrame:
    """Download daily SNWD observations for the given SNOTEL station triplets.

    Args:
        station_ids: AWDB station triplets (e.g. ``"301:ID:SNTL"``) as
            returned by :func:`fetch_stations`.
        temporal_range: Inclusive date range.

    Returns:
        DataFrame with columns ``station_id``, ``date``, ``snow_depth_m``
        (values in meters).
    """
    if not station_ids:
        return pd.DataFrame(columns=_OBS_COLUMNS)

    query = urlencode(
        {
            "stationTriplets": ",".join(station_ids),
            "elements": "SNWD",
            "duration": "DAILY",
            "beginDate": temporal_range.start.isoformat(),
            "endDate": temporal_range.end.isoformat(),
        }
    )
    url = f"{AWDB_BASE_URL}/data?{query}"

    try:
        payload = _http_get_json(url)
    except Exception as exc:
        logger.warning("NRCS AWDB data fetch failed: %s", exc)
        return pd.DataFrame(columns=_OBS_COLUMNS)

    if not isinstance(payload, list):
        return pd.DataFrame(columns=_OBS_COLUMNS)

    rows: list[dict[str, Any]] = []
    for station_obj in payload:
        if not isinstance(station_obj, dict):
            continue
        triplet = str(station_obj.get("stationTriplet", ""))
        data_blocks = station_obj.get("data") or []
        for block in data_blocks:
            if not isinstance(block, dict):
                continue
            element = block.get("stationElement") or {}
            # Some AWDB responses echo the element code inside the block; skip
            # anything that isn't SNWD when the field is present.
            code = element.get("elementCode") if isinstance(element, dict) else None
            if code not in (None, "SNWD"):
                continue
            for v in block.get("values") or []:
                if not isinstance(v, dict):
                    continue
                val = v.get("value")
                d = v.get("date")
                if val is None or d is None:
                    continue
                try:
                    depth_m = float(val) * _INCHES_TO_METERS
                    day = date.fromisoformat(str(d)[:10])
                except (TypeError, ValueError):
                    continue
                rows.append({"station_id": triplet, "date": day, "snow_depth_m": depth_m})

    if not rows:
        return pd.DataFrame(columns=_OBS_COLUMNS)

    return pd.DataFrame(rows, columns=_OBS_COLUMNS)
