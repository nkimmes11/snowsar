"""Pairwise statistics and difference maps between two retrieval Datasets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import xarray as xr

from snowsar.exceptions import AlgorithmError
from snowsar.types import QualityFlag


@dataclass(frozen=True)
class ComparisonStats:
    """Summary of agreement between two retrieval Datasets."""

    bias: float
    rmse: float
    mae: float
    pearson_r: float
    std_ratio: float
    agreement_rate: float
    count: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "bias": self.bias,
            "rmse": self.rmse,
            "mae": self.mae,
            "pearson_r": self.pearson_r,
            "std_ratio": self.std_ratio,
            "agreement_rate": self.agreement_rate,
            "count": self.count,
        }


def _align(
    ds_a: xr.Dataset,
    ds_b: xr.Dataset,
    variable: str,
) -> tuple[xr.DataArray, xr.DataArray]:
    if variable not in ds_a or variable not in ds_b:
        msg = f"variable {variable!r} missing from one or both Datasets"
        raise AlgorithmError(msg)
    a, b = xr.align(ds_a[variable], ds_b[variable], join="inner")
    if a.size == 0 or b.size == 0:
        msg = "no overlapping coordinates between the two Datasets"
        raise AlgorithmError(msg)
    return a, b


def _valid_mask(
    ds_a: xr.Dataset,
    ds_b: xr.Dataset,
    a_vals: np.ndarray,
    b_vals: np.ndarray,
    valid_only: bool,
) -> np.ndarray:
    mask = ~(np.isnan(a_vals) | np.isnan(b_vals))
    if valid_only and "quality_flag" in ds_a and "quality_flag" in ds_b:
        qa, qb = xr.align(ds_a["quality_flag"], ds_b["quality_flag"], join="inner")
        qa_valid = qa.values == int(QualityFlag.VALID)
        qb_valid = qb.values == int(QualityFlag.VALID)
        mask &= qa_valid & qb_valid
    return np.asarray(mask, dtype=bool)


def compute_pairwise_stats(
    ds_a: xr.Dataset,
    ds_b: xr.Dataset,
    *,
    variable: str = "snow_depth",
    valid_only: bool = True,
    agreement_tolerance_m: float = 0.1,
) -> ComparisonStats:
    """Compute pairwise statistics between two retrieval Datasets.

    Both Datasets must share the same coordinate grid (any non-overlap is dropped).
    When ``valid_only`` is True and both Datasets carry a ``quality_flag`` variable,
    only pixels flagged VALID in both are included.

    Args:
        ds_a: First retrieval Dataset.
        ds_b: Second retrieval Dataset.
        variable: Variable to compare (default ``snow_depth``).
        valid_only: Restrict to pixels flagged VALID in both Datasets.
        agreement_tolerance_m: Threshold for the ``agreement_rate`` metric
            (fraction of paired pixels within ``|a - b| <= tolerance``).
    """
    a, b = _align(ds_a, ds_b, variable)
    a_vals = a.values.astype(np.float64)
    b_vals = b.values.astype(np.float64)

    mask = _valid_mask(ds_a, ds_b, a_vals, b_vals, valid_only)
    a_vals = a_vals[mask]
    b_vals = b_vals[mask]

    count = int(a_vals.size)
    if count == 0:
        return ComparisonStats(
            bias=float("nan"),
            rmse=float("nan"),
            mae=float("nan"),
            pearson_r=float("nan"),
            std_ratio=float("nan"),
            agreement_rate=float("nan"),
            count=0,
        )

    diff = a_vals - b_vals
    bias = float(np.mean(diff))
    rmse = float(np.sqrt(np.mean(diff**2)))
    mae = float(np.mean(np.abs(diff)))

    std_a = float(np.std(a_vals))
    std_b = float(np.std(b_vals))
    if count < 2 or std_a == 0 or std_b == 0:
        pearson_r = float("nan")
        std_ratio = float("nan") if std_b == 0 else float(std_a / std_b)
    else:
        pearson_r = float(np.corrcoef(a_vals, b_vals)[0, 1])
        std_ratio = float(std_a / std_b)

    agreement_rate = float(np.mean(np.abs(diff) <= agreement_tolerance_m))

    return ComparisonStats(
        bias=bias,
        rmse=rmse,
        mae=mae,
        pearson_r=pearson_r,
        std_ratio=std_ratio,
        agreement_rate=agreement_rate,
        count=count,
    )


def difference_map(
    ds_a: xr.Dataset,
    ds_b: xr.Dataset,
    *,
    variable: str = "snow_depth",
    valid_only: bool = True,
) -> xr.DataArray:
    """Return the pixel-wise difference ``ds_a[variable] - ds_b[variable]``.

    Non-VALID pixels (in either Dataset) are set to NaN when ``valid_only`` is True.
    """
    a, b = _align(ds_a, ds_b, variable)
    diff = (a.astype(np.float64) - b.astype(np.float64)).astype(np.float32)
    if valid_only and "quality_flag" in ds_a and "quality_flag" in ds_b:
        qa, qb = xr.align(ds_a["quality_flag"], ds_b["quality_flag"], join="inner")
        both_valid = (qa.values == int(QualityFlag.VALID)) & (qb.values == int(QualityFlag.VALID))
        diff = diff.where(both_valid)
    diff.name = f"{variable}_diff"
    diff.attrs.update(
        {
            "long_name": f"Difference in {variable} (a - b)",
            "description": "Pairwise difference between two retrieval Datasets",
        }
    )
    return diff
