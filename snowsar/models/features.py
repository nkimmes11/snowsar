"""Feature vector assembly for the ML retrieval algorithm.

Converts standardized DataProvider xarray.Datasets into 2D feature matrices
suitable for scikit-learn / XGBoost regressors, and converts predictions
back into spatial/temporal DataArrays.

Derived features (e.g., ``cross_pol_ratio`` = VH - VV) are computed here
rather than required from the DataProvider.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from snowsar.exceptions import AlgorithmError

# Static (non-time-varying) variables get broadcast across the time dimension
STATIC_VARIABLES = frozenset(
    {
        "elevation",
        "slope",
        "aspect",
        "forest_cover_fraction",
        "land_cover_class",
    }
)

# Derived features computed from other variables
DERIVED_FEATURES = frozenset(
    {
        "cross_pol_ratio",
    }
)


def _compute_derived(name: str, ds: xr.Dataset) -> xr.DataArray:
    """Compute a derived feature not present directly in the Dataset."""
    if name == "cross_pol_ratio":
        return ds["gamma0_vh"] - ds["gamma0_vv"]
    msg = f"Unknown derived feature: {name!r}"
    raise AlgorithmError(msg)


def _broadcast_to_time(da: xr.DataArray, ds: xr.Dataset) -> xr.DataArray:
    """Broadcast a static (y, x) array across the time dimension."""
    if "time" in da.dims:
        return da
    broadcast, _ = xr.broadcast(da, ds["gamma0_vv"])
    return broadcast


def assemble_features(ds: xr.Dataset, feature_names: list[str]) -> np.ndarray:
    """Build a 2D feature matrix from a Dataset.

    Args:
        ds: Input Dataset conforming to the DataProvider contract.
        feature_names: Ordered list of feature names. Each name must either
            be a data variable in ``ds`` or a member of
            :data:`DERIVED_FEATURES`.

    Returns:
        A ``float32`` array of shape ``(n_samples, n_features)`` where
        ``n_samples = n_time * n_y * n_x``. Pixel ordering is
        C-contiguous with time as the slowest axis.

    Raises:
        AlgorithmError: If a requested feature is not available.
    """
    columns: list[np.ndarray] = []
    target_dims = ds["gamma0_vv"].dims  # (time, y, x)

    for name in feature_names:
        if name in ds.data_vars:
            da = ds[name]
        elif name in DERIVED_FEATURES:
            da = _compute_derived(name, ds)
        else:
            msg = f"Feature {name!r} not found in Dataset and is not a known derived feature"
            raise AlgorithmError(msg)

        if name in STATIC_VARIABLES or "time" not in da.dims:
            da = _broadcast_to_time(da, ds)

        da = da.transpose(*target_dims)
        columns.append(da.values.astype(np.float32).reshape(-1))

    matrix = np.stack(columns, axis=1)
    return matrix


def reshape_predictions(y_pred: np.ndarray, ds: xr.Dataset) -> xr.DataArray:
    """Reshape a 1D prediction array back into the input Dataset's grid.

    Args:
        y_pred: 1D array of length ``n_time * n_y * n_x``.
        ds: The Dataset whose shape ``y_pred`` was generated from.

    Returns:
        A DataArray with the same dims and coords as ``ds.gamma0_vv``.
    """
    template = ds["gamma0_vv"]
    reshaped = y_pred.astype(np.float32).reshape(template.shape)
    return xr.DataArray(
        reshaped,
        dims=template.dims,
        coords=template.coords,
    )
