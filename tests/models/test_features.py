"""Tests for the ML feature-vector assembly."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.exceptions import AlgorithmError
from snowsar.models.features import assemble_features, reshape_predictions


class TestAssembleFeatures:
    def test_shape(self, synthetic_ml_dataset: xr.Dataset) -> None:
        """Feature matrix has shape (n_time * n_y * n_x, n_features)."""
        features = ["gamma0_vv", "gamma0_vh", "elevation"]
        x = assemble_features(synthetic_ml_dataset, features)
        nt = synthetic_ml_dataset.sizes["time"]
        ny = synthetic_ml_dataset.sizes["y"]
        nx = synthetic_ml_dataset.sizes["x"]
        assert x.shape == (nt * ny * nx, 3)
        assert x.dtype == np.float32

    def test_static_broadcast_across_time(self, synthetic_ml_dataset: xr.Dataset) -> None:
        """A static variable's values should repeat for each time slice."""
        x = assemble_features(synthetic_ml_dataset, ["elevation"])
        nt = synthetic_ml_dataset.sizes["time"]
        ny = synthetic_ml_dataset.sizes["y"]
        nx = synthetic_ml_dataset.sizes["x"]
        reshaped = x.reshape(nt, ny, nx)
        # First time slice should equal subsequent slices
        np.testing.assert_allclose(reshaped[0], reshaped[1])

    def test_derived_cross_pol_ratio(self, synthetic_ml_dataset: xr.Dataset) -> None:
        """cross_pol_ratio = VH - VV should be computed automatically."""
        x = assemble_features(synthetic_ml_dataset, ["gamma0_vv", "gamma0_vh", "cross_pol_ratio"])
        vv_col = x[:, 0]
        vh_col = x[:, 1]
        cr_col = x[:, 2]
        np.testing.assert_allclose(cr_col, vh_col - vv_col, rtol=1e-5)

    def test_unknown_feature_raises(self, synthetic_ml_dataset: xr.Dataset) -> None:
        with pytest.raises(AlgorithmError, match="not found"):
            assemble_features(synthetic_ml_dataset, ["does_not_exist"])


class TestReshapePredictions:
    def test_shape_matches_input(self, synthetic_ml_dataset: xr.Dataset) -> None:
        template = synthetic_ml_dataset["gamma0_vv"]
        n = template.size
        y_pred = np.linspace(0, 5, n, dtype=np.float32)
        da = reshape_predictions(y_pred, synthetic_ml_dataset)
        assert da.shape == template.shape
        assert da.dims == template.dims

    def test_values_preserved(self, synthetic_ml_dataset: xr.Dataset) -> None:
        template = synthetic_ml_dataset["gamma0_vv"]
        n = template.size
        y_pred = np.arange(n, dtype=np.float32)
        da = reshape_predictions(y_pred, synthetic_ml_dataset)
        flat = da.values.reshape(-1)
        np.testing.assert_allclose(flat, y_pred)
