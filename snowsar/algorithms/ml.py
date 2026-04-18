"""ML-enhanced snow depth retrieval (experimental).

Uses a pre-trained gradient-boosted regressor (XGBoost by default) to
predict snow depth from SAR backscatter plus topographic and
environmental features.

.. warning::
    **Experimental.** The retrieval framework here is complete, but no
    production-trained model has been published yet. Registry entries are
    placeholders. Until a production model is available, calls to
    :meth:`MLAlgorithm.run` will either use a user-supplied model or
    (with ``fallback_on_missing_model=True``) return an all-NaN
    Dataset with quality flags indicating the missing model.

    See Phase 5 of the implementation plan for the model training roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import xarray as xr

from snowsar.exceptions import AlgorithmError
from snowsar.models.features import assemble_features, reshape_predictions
from snowsar.models.registry import (
    ModelNotAvailableError,
    ModelNotFoundError,
    load_local_model,
    load_model,
)
from snowsar.types import AlgorithmID, Backend, QualityFlag
from snowsar.utils.raster import ML_REQUIRED_VARIABLES, validate_dataset

DEFAULT_FEATURES: list[str] = [
    "gamma0_vv",
    "gamma0_vh",
    "cross_pol_ratio",
    "incidence_angle",
    "elevation",
    "slope",
    "aspect",
    "forest_cover_fraction",
    "temperature_2m",
    "land_cover_class",
]


@dataclass
class MLParams:
    """Configuration parameters for the ML algorithm."""

    model_name: str = "lievens_ml_v1"
    model_version: str = "latest"

    # Path to a local model file; overrides the registry when set
    local_model_path: str | None = None

    # Feature list to override the model's declared features
    feature_overrides: list[str] | None = None

    # If the model can't be loaded, return NaN output with WET_SNOW flag instead of raising
    fallback_on_missing_model: bool = True

    # Hyperparameter overrides (only relevant when retraining)
    hyperparameter_overrides: dict[str, Any] = field(default_factory=dict)

    # Maximum valid snow depth (meters)
    max_snow_depth: float = 20.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MLParams:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class MLAlgorithm:
    """ML-enhanced snow depth retrieval (experimental).

    The algorithm loads a pre-trained regressor from the model registry
    (or a user-supplied local file), assembles a feature matrix from the
    input Dataset, predicts snow depth per-pixel, and returns a
    standardized output Dataset.
    """

    @property
    def algorithm_id(self) -> AlgorithmID:
        return AlgorithmID.ML

    @property
    def name(self) -> str:
        return "ML-Enhanced (Experimental)"

    @property
    def description(self) -> str:
        return (
            "Gradient-boosted regression (XGBoost) over SAR + ancillary features. "
            "EXPERIMENTAL: no production model published yet; see Phase 5 of the plan."
        )

    @property
    def supported_backends(self) -> list[Backend]:
        # GEE backend supports ERA5/WorldCover; local provider stubs raise
        # NotImplementedError for now (Phase 3 will add local ingestion).
        return [Backend.GEE]

    def validate_input(self, ds: xr.Dataset) -> None:
        """Verify the input Dataset has all SAR, ancillary, and ML variables."""
        validate_dataset(ds, required=ML_REQUIRED_VARIABLES)

    def run(self, ds: xr.Dataset, params: dict[str, Any] | None = None) -> xr.Dataset:
        """Execute the ML snow depth retrieval.

        Returns:
            Dataset with ``snow_depth``, ``quality_flag``, ``uncertainty``.
        """
        self.validate_input(ds)
        p = MLParams(**params) if params else MLParams()

        model, features = _load_model_and_features(p)
        if model is None:
            return _build_fallback_output(ds, reason="model unavailable")

        x = assemble_features(ds, features)

        try:
            y_pred = model.predict(x)
        except Exception as e:
            if p.fallback_on_missing_model:
                return _build_fallback_output(ds, reason=f"inference failed: {e}")
            msg = f"Model prediction failed: {e}"
            raise AlgorithmError(msg) from e

        snow_depth = reshape_predictions(np.asarray(y_pred), ds)
        snow_depth = snow_depth.clip(min=0.0)

        quality_flag = _generate_quality_flags(ds, snow_depth, p.max_snow_depth)
        snow_depth = snow_depth.where(quality_flag == QualityFlag.VALID)

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
                "algorithm": "ml",
                "algorithm_version": "1.0-experimental",
                "model_name": p.model_name,
                "model_version": p.model_version,
                "features": ",".join(features),
            },
        )
        return result


def _load_model_and_features(p: MLParams) -> tuple[Any | None, list[str]]:
    """Load the model from local file or registry; return (model, features)."""
    features = p.feature_overrides or list(DEFAULT_FEATURES)

    if p.local_model_path:
        bundle = load_local_model(__import__("pathlib").Path(p.local_model_path))
        model, bundle_features = _unpack_bundle(bundle)
        if bundle_features and not p.feature_overrides:
            features = bundle_features
        return model, features

    try:
        bundle = load_model(p.model_name, p.model_version)
    except (ModelNotAvailableError, ModelNotFoundError):
        if p.fallback_on_missing_model:
            return None, features
        raise

    model, bundle_features = _unpack_bundle(bundle)
    if bundle_features and not p.feature_overrides:
        features = bundle_features
    return model, features


def _unpack_bundle(bundle: Any) -> tuple[Any, list[str] | None]:
    """Unpack a joblib bundle that may be a bare model or a dict with metadata."""
    if isinstance(bundle, dict) and "model" in bundle:
        return bundle["model"], bundle.get("features")
    return bundle, None


def _build_fallback_output(ds: xr.Dataset, reason: str) -> xr.Dataset:
    """Return an all-NaN output Dataset when the model is unavailable."""
    template = ds["gamma0_vv"]
    nan_depth = xr.DataArray(
        np.full(template.shape, np.nan, dtype=np.float32),
        dims=template.dims,
        coords=template.coords,
    )
    flag = xr.DataArray(
        np.full(template.shape, QualityFlag.INSUFFICIENT_SAR, dtype=np.uint8),
        dims=template.dims,
        coords=template.coords,
    )
    return xr.Dataset(
        {
            "snow_depth": nan_depth,
            "quality_flag": flag,
            "uncertainty": (template.dims, np.full(template.shape, np.nan, dtype=np.float32)),
        },
        coords=ds.coords,
        attrs={
            **ds.attrs,
            "algorithm": "ml",
            "algorithm_version": "1.0-experimental",
            "fallback_reason": reason,
        },
    )


def _generate_quality_flags(
    ds: xr.Dataset,
    snow_depth: xr.DataArray,
    max_snow_depth: float,
) -> xr.DataArray:
    """Generate per-pixel quality flags for ML retrieval."""
    flags = xr.full_like(snow_depth, QualityFlag.VALID, dtype=np.uint8)

    if "snow_cover" in ds:
        flags = flags.where(ds["snow_cover"] != 0, QualityFlag.WET_SNOW)

    valid_range = (snow_depth >= 0) & (snow_depth <= max_snow_depth)
    flags = flags.where(valid_range, QualityFlag.OUTSIDE_RANGE)

    return flags
