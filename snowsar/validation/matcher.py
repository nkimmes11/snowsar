"""Spatial and temporal matching between station observations and SAR pixels."""

from __future__ import annotations

from datetime import date

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr


def spatial_match(
    stations: gpd.GeoDataFrame,
    result_ds: xr.Dataset,
    max_distance_deg: float = 0.01,
) -> pd.DataFrame:
    """Find the nearest SAR pixel for each station location.

    Args:
        stations: GeoDataFrame with station locations (geometry column).
        result_ds: Algorithm output Dataset with y, x coordinates.
        max_distance_deg: Maximum distance in degrees to consider a match.

    Returns:
        DataFrame with columns: station_id, nearest_y_idx, nearest_x_idx,
        distance_deg.
    """
    xs = result_ds.x.values
    ys = result_ds.y.values

    matches = []
    for _, station in stations.iterrows():
        lon = station.geometry.x
        lat = station.geometry.y

        # Find nearest grid cell
        x_idx = int(np.argmin(np.abs(xs - lon)))
        y_idx = int(np.argmin(np.abs(ys - lat)))

        distance = np.sqrt((xs[x_idx] - lon) ** 2 + (ys[y_idx] - lat) ** 2)

        if distance <= max_distance_deg:
            matches.append(
                {
                    "station_id": station["station_id"],
                    "nearest_y_idx": y_idx,
                    "nearest_x_idx": x_idx,
                    "distance_deg": float(distance),
                }
            )

    return pd.DataFrame(matches)


def temporal_match(
    observations: pd.DataFrame,
    result_ds: xr.Dataset,
    tolerance_days: int = 1,
) -> pd.DataFrame:
    """Align observation dates to nearest retrieval dates.

    Args:
        observations: DataFrame with date and snow_depth_m columns.
        result_ds: Algorithm output Dataset with time coordinate.
        tolerance_days: Maximum number of days between observation and retrieval.

    Returns:
        DataFrame with columns: station_id, obs_date, matched_time_idx,
        obs_snow_depth_m.
    """
    retrieval_dates = pd.to_datetime(result_ds.time.values).date

    matched = []
    for _, obs in observations.iterrows():
        obs_date = (
            obs["date"] if isinstance(obs["date"], date) else pd.Timestamp(obs["date"]).date()
        )

        # Find nearest retrieval date
        deltas = [abs((rd - obs_date).days) for rd in retrieval_dates]
        min_idx = int(np.argmin(deltas))
        min_delta = deltas[min_idx]

        if min_delta <= tolerance_days:
            matched.append(
                {
                    "station_id": obs["station_id"],
                    "obs_date": obs_date,
                    "matched_time_idx": min_idx,
                    "obs_snow_depth_m": obs["snow_depth_m"],
                }
            )

    return pd.DataFrame(matched)
