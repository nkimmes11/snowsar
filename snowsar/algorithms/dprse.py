"""DpRSE dual-polarimetric radar snow estimation algorithm.

Implements the DpRSE framework based on:
  - DpRSE (2024) International Journal of Applied Earth Observation
    and Geoinformation, 129, 103862.

Uses the dual-polarimetric radar vegetation index with a conditioning
factor (DpRVIc) to estimate snow depth from Sentinel-1 GRD data.
The method enhances snow volume scattering signal and suppresses soil
interference. Applicable to treeless/low-vegetation areas only.

Reference implementation: Figshare DOI 10.6084/m9.figshare.25376578.v1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import xarray as xr

from snowsar.types import AlgorithmID, Backend, QualityFlag
from snowsar.utils.raster import SAR_VARIABLES, db_to_linear, validate_dataset


@dataclass
class DpRSEParams:
    """Configuration parameters for the DpRSE algorithm."""

    # DpRVIc conditioning factor exponent
    conditioning_exponent: float = 1.0

    # Soil purity threshold (0-1); pixels with soil purity above this are masked
    soil_purity_threshold: float = 0.7

    # Forest cover fraction threshold; pixels above this are masked
    fcf_threshold: float = 0.1

    # Empirical regression coefficients: SD = slope * DpRVIc + intercept
    regression_slope: float = 5.0
    regression_intercept: float = -0.5

    # Maximum valid snow depth (meters)
    max_snow_depth: float = 20.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DpRSEParams:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class DpRSEAlgorithm:
    """DpRSE dual-polarimetric snow depth retrieval.

    Uses the DpRVIc (dual-polarimetric radar vegetation index with
    conditioning factor) to estimate snow depth from Sentinel-1 C-band
    data. Designed for treeless areas where soil scattering interferes
    with standard cross-polarization methods.
    """

    @property
    def algorithm_id(self) -> AlgorithmID:
        return AlgorithmID.DPRSE

    @property
    def name(self) -> str:
        return "DpRSE Dual-Polarimetric"

    @property
    def description(self) -> str:
        return (
            "Dual-polarimetric radar snow estimation using the DpRVIc index. "
            "Based on Sentinel-1 GRD data; applicable to treeless areas only."
        )

    @property
    def supported_backends(self) -> list[Backend]:
        return [Backend.GEE, Backend.LOCAL]

    def validate_input(self, ds: xr.Dataset) -> None:
        """Verify the input Dataset has required SAR variables."""
        validate_dataset(ds, required=SAR_VARIABLES)

    def run(self, ds: xr.Dataset, params: dict[str, Any] | None = None) -> xr.Dataset:
        """Execute the DpRSE snow depth retrieval.

        Args:
            ds: Input Dataset with SAR backscatter (in dB) and ancillary data.
            params: Optional parameter overrides (keys match DpRSEParams fields).

        Returns:
            Dataset with snow_depth, quality_flag, and uncertainty variables.
        """
        self.validate_input(ds)
        p = DpRSEParams(**params) if params else DpRSEParams()

        # Step 1: Convert dB to linear power
        vv_linear = db_to_linear(ds["gamma0_vv"])
        vh_linear = db_to_linear(ds["gamma0_vh"])

        # Step 2: Compute pseudo-coherency matrix elements
        c11, c22, span = compute_coherency_elements(vv_linear, vh_linear)

        # Step 3: Compute degree of polarization and soil purity
        dop = compute_degree_of_polarization(c11, c22, span)
        soil_purity = compute_soil_purity(c11, span)

        # Step 4: Compute DpRVI base index
        dprvi = compute_dprvi(dop, span)

        # Step 5: Apply conditioning factor to get DpRVIc
        dprvic = apply_conditioning_factor(dprvi, soil_purity, exponent=p.conditioning_exponent)

        # Step 6: Map DpRVIc to snow depth via empirical regression
        snow_depth = regression_to_snow_depth(
            dprvic, slope=p.regression_slope, intercept=p.regression_intercept
        )

        # Step 7: Generate quality flags
        quality_flag = generate_quality_flags(
            ds,
            snow_depth,
            soil_purity,
            soil_purity_threshold=p.soil_purity_threshold,
            fcf_threshold=p.fcf_threshold,
            max_snow_depth=p.max_snow_depth,
        )

        # Step 8: Mask invalid pixels
        snow_depth = snow_depth.where(quality_flag == QualityFlag.VALID)

        # Assemble output Dataset
        result = xr.Dataset(
            {
                "snow_depth": snow_depth.astype(np.float32),
                "quality_flag": quality_flag.astype(np.uint8),
                "uncertainty": (
                    snow_depth.dims,
                    np.full_like(snow_depth.values, np.nan, dtype=np.float32),
                ),
            },
            coords=ds.coords,
            attrs={
                **ds.attrs,
                "algorithm": "dprse",
                "algorithm_version": "1.0",
                "regression": f"slope={p.regression_slope}, intercept={p.regression_intercept}",
            },
        )
        return result


def compute_coherency_elements(
    vv_linear: xr.DataArray,
    vh_linear: xr.DataArray,
) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    """Compute pseudo-coherency matrix elements from dual-pol linear power.

    For GRD intensity data (no phase), the 2x2 coherency matrix reduces to
    diagonal elements:
        C11 = |VV|^2  (co-pol power)
        C22 = |VH|^2  (cross-pol power)
        span = C11 + C22  (total power)

    Returns:
        Tuple of (C11, C22, span).
    """
    c11 = vv_linear
    c22 = vh_linear
    span = c11 + c22
    return c11, c22, span


def compute_degree_of_polarization(
    c11: xr.DataArray,
    c22: xr.DataArray,
    span: xr.DataArray,
) -> xr.DataArray:
    """Compute the degree of polarization from coherency matrix elements.

    For GRD data (no off-diagonal terms), the degree of polarization
    simplifies to:
        DoP = |C11 - C22| / span

    Values range from 0 (completely depolarized) to 1 (fully polarized).
    Snow volume scattering produces depolarization (lower DoP).
    """
    safe_span = span.where(span > 0, 1e-10)
    dop: xr.DataArray = xr.DataArray(np.abs(c11 - c22)) / safe_span
    return dop.clip(0.0, 1.0)


def compute_soil_purity(
    c11: xr.DataArray,
    span: xr.DataArray,
) -> xr.DataArray:
    """Compute the soil purity metric.

    Soil purity = C11 / span — the fraction of total power in the co-pol
    channel. High values indicate dominant surface/soil scattering with
    minimal depolarization (little snow volume scattering).
    """
    safe_span = span.where(span > 0, 1e-10)
    purity: xr.DataArray = c11 / safe_span
    return purity.clip(0.0, 1.0)


def compute_dprvi(
    dop: xr.DataArray,
    span: xr.DataArray,
) -> xr.DataArray:
    """Compute the dual-polarimetric radar vegetation index (DpRVI).

    DpRVI = 1 - DoP * (span_normalized)

    where span_normalized is span divided by its maximum value.
    DpRVI is sensitive to volume scattering from snow and vegetation.
    Higher values indicate more depolarization (more volume scattering).
    """
    span_max = span.max()
    safe_max = float(span_max) if float(span_max) > 0 else 1e-10
    span_norm = span / safe_max

    dprvi: xr.DataArray = 1.0 - dop * span_norm
    return dprvi.clip(0.0, 1.0)


def apply_conditioning_factor(
    dprvi: xr.DataArray,
    soil_purity: xr.DataArray,
    exponent: float = 1.0,
) -> xr.DataArray:
    """Apply conditioning factor to DpRVI to suppress soil scattering.

    DpRVIc = DpRVI * (1 - soil_purity)^exponent

    The conditioning factor reduces the index value where soil scattering
    dominates (high soil purity), enhancing the snow volume scattering signal.
    """
    conditioning = (1.0 - soil_purity) ** exponent
    dprvic: xr.DataArray = dprvi * conditioning
    return dprvic


def regression_to_snow_depth(
    dprvic: xr.DataArray,
    slope: float = 5.0,
    intercept: float = -0.5,
) -> xr.DataArray:
    """Map DpRVIc to snow depth via empirical linear regression.

    SD = slope * DpRVIc + intercept

    Negative values are clipped to zero. Coefficients should be calibrated
    regionally against in-situ observations.
    """
    sd: xr.DataArray = slope * dprvic + intercept
    return sd.clip(min=0.0)


def generate_quality_flags(
    ds: xr.Dataset,
    snow_depth: xr.DataArray,
    soil_purity: xr.DataArray,
    soil_purity_threshold: float = 0.7,
    fcf_threshold: float = 0.1,
    max_snow_depth: float = 20.0,
) -> xr.DataArray:
    """Generate per-pixel quality flags for DpRSE retrieval.

    Flags:
        VALID (0): Pixel passes all checks.
        WET_SNOW (1): Snow cover mask indicates no snow (possible wet snow).
        HIGH_FOREST (3): Forest cover fraction exceeds threshold.
        OUTSIDE_RANGE (5): Snow depth negative or exceeds maximum, or
                          soil purity above threshold.
    """
    flags = xr.full_like(snow_depth, QualityFlag.VALID, dtype=np.uint8)

    # Flag wet snow (no snow cover)
    if "snow_cover" in ds:
        flags = flags.where(ds["snow_cover"] != 0, QualityFlag.WET_SNOW)

    # Flag forested areas (DpRSE is for treeless areas)
    if "forest_cover_fraction" in ds:
        flags = flags.where(ds["forest_cover_fraction"] <= fcf_threshold, QualityFlag.HIGH_FOREST)

    # Flag high soil purity (dominant soil scattering, unreliable retrieval)
    flags = flags.where(soil_purity <= soil_purity_threshold, QualityFlag.OUTSIDE_RANGE)

    # Flag unreasonable snow depth
    valid_range = (snow_depth >= 0) & (snow_depth <= max_snow_depth)
    flags = flags.where(valid_range, QualityFlag.OUTSIDE_RANGE)

    return flags
