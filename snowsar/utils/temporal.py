"""Temporal and orbit-related utility functions."""

from __future__ import annotations

from datetime import date, timedelta

# Sentinel-1 repeat cycle in days (single satellite)
S1_REPEAT_CYCLE = 12

# NISAR repeat cycle in days
NISAR_REPEAT_CYCLE = 12


def sentinel1_prior_dates(acquisition_date: date, max_gap_days: int = 24) -> list[date]:
    """Return candidate prior acquisition dates for Sentinel-1 change detection.

    The Lievens algorithm compares each acquisition to a prior one from the
    same relative orbit: 6, 12, 18, or 24 days earlier (dual/single satellite).
    """
    gaps = range(6, max_gap_days + 1, 6)
    return [acquisition_date - timedelta(days=g) for g in gaps]


def snow_season_range(water_year: int) -> tuple[date, date]:
    """Return the typical Northern Hemisphere snow season for a given water year.

    Water year N runs from October 1 of year N-1 through September 30 of year N.
    Snow season is approximated as October 1 through June 30.
    """
    start = date(water_year - 1, 10, 1)
    end = date(water_year, 6, 30)
    return start, end


def day_of_year_encoding(d: date) -> tuple[float, float]:
    """Encode day-of-year as sin/cos pair for cyclical feature representation.

    Used as ML features to capture seasonal patterns without discontinuity.
    """
    import math

    doy = d.timetuple().tm_yday
    angle = 2 * math.pi * doy / 365.25
    return math.sin(angle), math.cos(angle)
