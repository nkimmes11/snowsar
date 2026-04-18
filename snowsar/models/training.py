"""Utilities for training ML snow depth models.

These helpers are **not used in the runtime retrieval pipeline**. They
exist for users who want to train a regional model against their own
labeled data. Full training workflow is outlined in Phase 5 of the
implementation plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass
class TrainingResult:
    """Summary metrics from a training run."""

    mae: float
    rmse: float
    r2: float
    n_samples: int


def train_xgboost(
    x_train: np.ndarray,
    y_train: np.ndarray,
    params: dict[str, Any] | None = None,
) -> Any:
    """Fit an XGBoost regressor with sensible defaults.

    Args:
        x_train: Feature matrix of shape (n_samples, n_features).
        y_train: Target snow depths in meters.
        params: Optional hyperparameter overrides.

    Returns:
        The fitted XGBoost regressor.
    """
    import xgboost as xgb

    defaults = {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "objective": "reg:squarederror",
        "random_state": 42,
    }
    if params:
        defaults.update(params)

    model = xgb.XGBRegressor(**defaults)
    model.fit(x_train, y_train)
    return model


def evaluate(model: Any, x_val: np.ndarray, y_val: np.ndarray) -> TrainingResult:
    """Compute validation metrics for a fitted model."""
    y_pred = model.predict(x_val)
    mae = float(mean_absolute_error(y_val, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))
    r2 = float(r2_score(y_val, y_pred))
    return TrainingResult(mae=mae, rmse=rmse, r2=r2, n_samples=len(y_val))


def save_model(model: Any, path: Path, feature_names: list[str] | None = None) -> None:
    """Serialize a fitted model (optionally with its feature list) to disk.

    If ``feature_names`` is provided, the saved bundle is a dict containing
    both the model and the feature names, which is the expected format for
    registry entries loaded by :func:`snowsar.models.registry.load_model`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle: Any = model if feature_names is None else {"model": model, "features": feature_names}
    joblib.dump(bundle, path)
