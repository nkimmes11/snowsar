"""Output writers and query helpers for retrieval results.

Modules:
    geotiff: GeoTIFF writers for a single time slice.
    netcdf: CF-1.8 compliant NetCDF-4 writer for multi-time results.
    timeseries: Spatial aggregation into a per-timestep DataFrame.
    point_query: Nearest-neighbor and bilinear sampling at user-supplied points.
"""

from snowsar.output.geotiff import write_geotiff
from snowsar.output.netcdf import write_netcdf
from snowsar.output.point_query import query_points
from snowsar.output.timeseries import extract_timeseries

__all__ = [
    "extract_timeseries",
    "query_points",
    "write_geotiff",
    "write_netcdf",
]
