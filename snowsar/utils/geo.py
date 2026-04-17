"""Geospatial utility functions."""

from __future__ import annotations

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def reproject_geometry(geom: BaseGeometry, src_crs: str, dst_crs: str) -> BaseGeometry:
    """Reproject a shapely geometry between coordinate reference systems."""
    if src_crs == dst_crs:
        return geom
    transformer = Transformer.from_crs(
        CRS.from_user_input(src_crs),
        CRS.from_user_input(dst_crs),
        always_xy=True,
    )
    return transform(transformer.transform, geom)


def estimate_utm_crs(longitude: float, latitude: float) -> str:
    """Estimate the UTM CRS EPSG code for a given lon/lat point."""
    zone_number = int((longitude + 180) / 6) + 1
    if latitude >= 0:
        return f"EPSG:326{zone_number:02d}"
    return f"EPSG:327{zone_number:02d}"


def bbox_area_km2(west: float, south: float, east: float, north: float) -> float:
    """Approximate area of a lon/lat bounding box in square kilometers.

    Uses a simple equirectangular approximation suitable for quick size checks.
    """
    import math

    mid_lat = math.radians((south + north) / 2)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(mid_lat)
    width = abs(east - west) * km_per_deg_lon
    height = abs(north - south) * km_per_deg_lat
    return width * height
