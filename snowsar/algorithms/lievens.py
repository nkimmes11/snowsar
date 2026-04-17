"""Lievens empirical change-detection algorithm for C-band SAR snow depth.

Re-implemented from the methodology described in:
  - Lievens et al. (2019) Nature Communications 10:4629
  - Lievens et al. (2022) The Cryosphere 16:159-177

References the spicy-snow package (Hoppinen et al., 2024) for algorithmic
details. This is an independent implementation conforming to the SnowSAR
DataProvider/Algorithm protocols.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import xarray as xr

from snowsar.types import AlgorithmID, Backend, QualityFlag
from snowsar.utils.raster import validate_dataset

# Default empirical coefficients from Lievens et al. (2022)
DEFAULT_A = 2.0
DEFAULT_B = 0.5
DEFAULT_C = 0.1


@dataclass
class LievensParams:
    """Configuration parameters for the Lievens algorithm."""

    # Empirical scaling coefficients
    coeff_a: float = DEFAULT_A
    coeff_b: float = DEFAULT_B
    coeff_c: float = DEFAULT_C

    # Temporal aggregation window (days)
    temporal_window_days: int = 12

    # Whether to apply forest cover fraction weighting
    fcf_weighting: bool = True

    # FCF threshold above which quality degrades
    fcf_threshold: float = 0.5

    # Reference period for baseline backscatter (None = auto-detect)
    reference_period: tuple[date, date] | None = None

    # Recursive filter weight for temporal smoothing (0-1)
    filter_alpha: float = 0.5

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LievensParams:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class LievensAlgorithm:
    """Lievens empirical change-detection snow depth retrieval.

    Uses temporal changes in C-band Sentinel-1 cross-polarization ratio
    to estimate snow depth. Applies forest cover fraction weighting to
    blend CR-based and VV-based signals per Lievens et al. (2022).
    """

    @property
    def algorithm_id(self) -> AlgorithmID:
        return AlgorithmID.LIEVENS

    @property
    def name(self) -> str:
        return "Lievens Empirical Change-Detection"

    @property
    def description(self) -> str:
        return (
            "Empirical change-detection algorithm using Sentinel-1 C-band "
            "cross-polarization ratio. Based on Lievens et al. (2019, 2022)."
        )

    @property
    def supported_backends(self) -> list[Backend]:
        return [Backend.GEE, Backend.LOCAL]

    def validate_input(self, ds: xr.Dataset) -> None:
        """Verify the input Dataset has required SAR and ancillary variables."""
        validate_dataset(ds)

    def run(self, ds: xr.Dataset, params: dict[str, Any] | None = None) -> xr.Dataset:
        """Execute the Lievens snow depth retrieval.

        Args:
            ds: Input Dataset with SAR backscatter and ancillary data.
            params: Optional parameter overrides (keys match LievensParams fields).

        Returns:
            Dataset with snow_depth, quality_flag, and uncertainty variables.
        """
        self.validate_input(ds)
        p = LievensParams(**params) if params else LievensParams()

        # Step 1: Compute cross-polarization ratio
        cr = compute_cross_pol_ratio(ds["gamma0_vh"], ds["gamma0_vv"])

        # Step 2: Compute reference backscatter
        cr_ref, vv_ref = compute_reference_backscatter(ds, cr, p.reference_period)

        # Step 3: Compute change from reference
        delta_cr = cr - cr_ref
        delta_vv = ds["gamma0_vv"] - vv_ref

        # Step 4: Apply FCF weighting (blend CR and VV signals)
        if p.fcf_weighting and "forest_cover_fraction" in ds:
            delta_sigma = apply_fcf_weighting(delta_cr, delta_vv, ds["forest_cover_fraction"])
        else:
            delta_sigma = delta_cr

        # Step 5: Temporal aggregation (recursive filter)
        snow_index = temporal_aggregate(delta_sigma, alpha=p.filter_alpha)

        # Step 6: Scale to snow depth
        snow_depth = scale_to_snow_depth(snow_index, p.coeff_a, p.coeff_b, p.coeff_c)

        # Step 7: Generate quality flags
        quality_flag = generate_quality_flags(ds, snow_depth, p.fcf_threshold)

        # Step 8: Apply masks (set snow_depth to NaN where invalid)
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
                "algorithm": "lievens",
                "algorithm_version": "1.0",
                "coefficients": f"A={p.coeff_a}, B={p.coeff_b}, C={p.coeff_c}",
            },
        )
        return result


def compute_cross_pol_ratio(gamma0_vh: xr.DataArray, gamma0_vv: xr.DataArray) -> xr.DataArray:
    """Compute cross-polarization ratio: CR = VH - VV (in dB)."""
    return gamma0_vh - gamma0_vv


def compute_reference_backscatter(
    ds: xr.Dataset,
    cr: xr.DataArray,
    reference_period: tuple[date, date] | None = None,
) -> tuple[xr.DataArray, xr.DataArray]:
    """Compute reference (baseline) backscatter from snow-free or early-season period.

    If reference_period is None, uses the first time step as reference.

    Returns:
        Tuple of (cr_reference, vv_reference) as 2D arrays (y, x).
    """
    if reference_period is not None:
        start, end = reference_period
        mask = (ds.time >= np.datetime64(start)) & (ds.time <= np.datetime64(end))
        cr_ref = cr.sel(time=mask).mean(dim="time")
        vv_ref = ds["gamma0_vv"].sel(time=mask).mean(dim="time")
    else:
        # Default: use the first time step
        cr_ref = cr.isel(time=0)
        vv_ref = ds["gamma0_vv"].isel(time=0)

    return cr_ref, vv_ref


def apply_fcf_weighting(
    delta_cr: xr.DataArray,
    delta_vv: xr.DataArray,
    fcf: xr.DataArray,
) -> xr.DataArray:
    """Apply forest cover fraction weighting per Lievens et al. (2022).

    In open areas (low FCF), CR-based change is more sensitive to snow.
    In forested areas (high FCF), VV-based change is more sensitive.

    delta_sigma = (1 - FCF) * delta_CR + FCF * delta_VV
    """
    return (1.0 - fcf) * delta_cr + fcf * delta_vv


def temporal_aggregate(
    delta_sigma: xr.DataArray,
    alpha: float = 0.5,
) -> xr.DataArray:
    """Accumulate snow index through the season using a recursive filter.

    SI(t) = alpha * delta_sigma(t) + (1 - alpha) * SI(t-1)

    This smooths noisy individual retrievals into a progressive
    snow accumulation signal.
    """
    times = delta_sigma.time.values
    result = np.zeros_like(delta_sigma.values)

    # Initialize first time step
    result[0] = delta_sigma.values[0]

    # Recursive accumulation
    for t in range(1, len(times)):
        result[t] = alpha * delta_sigma.values[t] + (1.0 - alpha) * result[t - 1]

    return xr.DataArray(
        result,
        dims=delta_sigma.dims,
        coords=delta_sigma.coords,
    )


def scale_to_snow_depth(
    snow_index: xr.DataArray,
    a: float,
    b: float,
    c: float,
) -> xr.DataArray:
    """Convert snow index to snow depth using empirical coefficients.

    SD = A * SI + B * SI^2 + C

    Negative values are clipped to zero.
    """
    sd = a * snow_index + b * snow_index**2 + c
    return sd.clip(min=0.0)


def generate_quality_flags(
    ds: xr.Dataset,
    snow_depth: xr.DataArray,
    fcf_threshold: float = 0.5,
) -> xr.DataArray:
    """Generate per-pixel quality flags.

    Returns DataArray with QualityFlag integer values.
    """
    # Start with all valid
    flags = xr.full_like(snow_depth, QualityFlag.VALID, dtype=np.uint8)

    # Flag wet snow (where snow_cover mask indicates no snow)
    if "snow_cover" in ds:
        flags = flags.where(ds["snow_cover"] != 0, QualityFlag.WET_SNOW)

    # Flag high forest cover
    if "forest_cover_fraction" in ds:
        flags = flags.where(ds["forest_cover_fraction"] <= fcf_threshold, QualityFlag.HIGH_FOREST)

    # Flag unreasonable snow depth (> 20m or < 0)
    flags = flags.where((snow_depth >= 0) & (snow_depth <= 20.0), QualityFlag.OUTSIDE_RANGE)

    return flags
