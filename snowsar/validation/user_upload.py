"""Parse user-supplied point snow observations (CSV or GeoJSON)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Literal

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from snowsar.exceptions import ValidationError

REQUIRED_COLUMNS = {"station_id", "longitude", "latitude", "date", "snow_depth_m"}


def _as_bytes(source: str | Path | bytes) -> bytes:
    if isinstance(source, bytes):
        return source
    return Path(source).read_bytes()


def _coerce_observations(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        msg = f"missing required columns: {sorted(missing)}"
        raise ValidationError(msg)
    out = pd.DataFrame(
        {
            "station_id": df["station_id"].astype(str),
            "longitude": pd.to_numeric(df["longitude"], errors="coerce"),
            "latitude": pd.to_numeric(df["latitude"], errors="coerce"),
            "date": pd.to_datetime(df["date"], errors="coerce").dt.date,
            "snow_depth_m": pd.to_numeric(df["snow_depth_m"], errors="coerce"),
        }
    )
    dropped = out.isna().any(axis=1).sum()
    if dropped:
        out = out.dropna().reset_index(drop=True)
    if out.empty:
        msg = "no valid observations after coercion (check types/missing values)"
        raise ValidationError(msg)
    return out


def parse_csv(source: str | Path | bytes) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Parse a CSV of point snow observations.

    Required columns: ``station_id``, ``longitude``, ``latitude``, ``date``,
    ``snow_depth_m``. ``longitude``/``latitude`` must be in EPSG:4326.

    Returns:
        ``(stations, observations)`` — the stations GeoDataFrame (one row per
        unique ``station_id``) and the long-form observations DataFrame.
    """
    data = _as_bytes(source)
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception as exc:
        msg = f"failed to read CSV: {exc}"
        raise ValidationError(msg) from exc

    obs = _coerce_observations(df)
    return _split(obs)


def parse_geojson(source: str | Path | bytes) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Parse a GeoJSON FeatureCollection of point snow observations.

    Each feature must be a Point with properties ``station_id``, ``date``, and
    ``snow_depth_m``. Coordinates are taken from the geometry (lon, lat).
    """
    data = _as_bytes(source)
    try:
        geo = json.loads(data)
    except Exception as exc:
        msg = f"failed to parse GeoJSON: {exc}"
        raise ValidationError(msg) from exc

    if not isinstance(geo, dict) or geo.get("type") != "FeatureCollection":
        msg = "GeoJSON must be a FeatureCollection"
        raise ValidationError(msg)

    records: list[dict[str, object]] = []
    for feature in geo.get("features", []):
        geom = feature.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        props = feature.get("properties") or {}
        records.append(
            {
                "station_id": props.get("station_id"),
                "longitude": float(coords[0]),
                "latitude": float(coords[1]),
                "date": props.get("date"),
                "snow_depth_m": props.get("snow_depth_m"),
            }
        )

    if not records:
        msg = "no Point features with required properties found"
        raise ValidationError(msg)

    obs = _coerce_observations(pd.DataFrame(records))
    return _split(obs)


def _split(obs: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    station_rows = (
        obs[["station_id", "longitude", "latitude"]]
        .drop_duplicates(subset="station_id")
        .reset_index(drop=True)
    )
    stations = gpd.GeoDataFrame(
        {
            "station_id": station_rows["station_id"],
            "name": station_rows["station_id"],
            "elevation_m": 0.0,
            "latitude": station_rows["latitude"].astype(float),
            "longitude": station_rows["longitude"].astype(float),
        },
        geometry=[
            Point(lon, lat)
            for lon, lat in zip(station_rows["longitude"], station_rows["latitude"], strict=True)
        ],
        crs="EPSG:4326",
    )
    observations = obs[["station_id", "date", "snow_depth_m"]].copy()
    return stations, observations


def parse(
    source: str | Path | bytes,
    *,
    format: Literal["csv", "geojson"],
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Dispatch to the CSV or GeoJSON parser by explicit format."""
    if format == "csv":
        return parse_csv(source)
    if format == "geojson":
        return parse_geojson(source)
    msg = f"unknown format: {format!r}"
    raise ValidationError(msg)
