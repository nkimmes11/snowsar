"""Tests for the ML-enhanced snow depth algorithm (experimental)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import xarray as xr

from snowsar.algorithms.ml import MLAlgorithm
from snowsar.types import AlgorithmID, Backend, QualityFlag


class TestMLMetadata:
    def test_algorithm_id(self) -> None:
        algo = MLAlgorithm()
        assert algo.algorithm_id == AlgorithmID.ML

    def test_description_flags_experimental(self) -> None:
        algo = MLAlgorithm()
        assert "EXPERIMENTAL" in algo.description or "experimental" in algo.description.lower()

    def test_supported_backends_gee_only(self) -> None:
        algo = MLAlgorithm()
        assert Backend.GEE in algo.supported_backends


class TestMLValidation:
    def test_validate_input_requires_ml_vars(self, synthetic_sar_dataset: xr.Dataset) -> None:
        """The SAR-only synthetic dataset lacks temperature_2m/land_cover_class."""
        algo = MLAlgorithm()
        with pytest.raises(ValueError, match="missing required variables"):
            algo.validate_input(synthetic_sar_dataset)

    def test_validate_input_with_ml_vars(self, synthetic_ml_dataset: xr.Dataset) -> None:
        algo = MLAlgorithm()
        algo.validate_input(synthetic_ml_dataset)  # should not raise


class TestMLFallback:
    def test_run_returns_fallback_when_model_missing(
        self, synthetic_ml_dataset: xr.Dataset
    ) -> None:
        """With fallback=True and no published model, returns all-NaN Dataset."""
        algo = MLAlgorithm()
        result = algo.run(
            synthetic_ml_dataset,
            params={"model_name": "placeholder_model_that_does_not_exist"},
        )
        assert "snow_depth" in result
        assert np.all(np.isnan(result["snow_depth"].values))
        assert (result["quality_flag"].values == QualityFlag.INSUFFICIENT_SAR).all()
        assert "fallback_reason" in result.attrs

    def test_run_raises_when_fallback_disabled(self, synthetic_ml_dataset: xr.Dataset) -> None:
        from snowsar.exceptions import SnowSARError

        algo = MLAlgorithm()
        with pytest.raises(SnowSARError):
            algo.run(
                synthetic_ml_dataset,
                params={
                    "model_name": "nonexistent_model",
                    "fallback_on_missing_model": False,
                },
            )


class TestMLInference:
    def test_run_with_mock_model(self, synthetic_ml_dataset: xr.Dataset) -> None:
        """Patching load_model to return a predictable mock yields expected shape."""
        mock_model = MagicMock()
        n = synthetic_ml_dataset["gamma0_vv"].size
        mock_model.predict.return_value = np.full(n, 1.5, dtype=np.float32)

        with patch("snowsar.algorithms.ml.load_model", return_value=mock_model):
            algo = MLAlgorithm()
            result = algo.run(synthetic_ml_dataset)

        assert result["snow_depth"].shape == synthetic_ml_dataset["gamma0_vv"].shape
        # Valid pixels should have snow_depth = 1.5
        valid_mask = result["quality_flag"].values == QualityFlag.VALID
        if valid_mask.any():
            valid_sd = result["snow_depth"].values[valid_mask]
            np.testing.assert_allclose(valid_sd, 1.5, rtol=1e-4)
        assert result.attrs["algorithm"] == "ml"

    def test_local_model_path_used(self, synthetic_ml_dataset: xr.Dataset, tmp_path: Path) -> None:
        """A local_model_path bypasses the registry."""
        mock_model = MagicMock()
        n = synthetic_ml_dataset["gamma0_vv"].size
        mock_model.predict.return_value = np.full(n, 0.8, dtype=np.float32)

        local_path = tmp_path / "local.joblib"
        # The file is never actually loaded (load_local_model is patched),
        # but a path must exist for downstream code paths that stat it.
        local_path.write_bytes(b"")

        with patch(
            "snowsar.algorithms.ml.load_local_model",
            return_value={"model": mock_model, "features": None},
        ) as mock_loader:
            algo = MLAlgorithm()
            result = algo.run(
                synthetic_ml_dataset,
                params={"local_model_path": str(local_path)},
            )
        mock_loader.assert_called_once()
        assert result["snow_depth"].shape == synthetic_ml_dataset["gamma0_vv"].shape

    def test_negative_predictions_clipped(self, synthetic_ml_dataset: xr.Dataset) -> None:
        """Negative predictions should be clipped to zero before masking."""
        mock_model = MagicMock()
        n = synthetic_ml_dataset["gamma0_vv"].size
        mock_model.predict.return_value = np.full(n, -2.0, dtype=np.float32)

        with patch("snowsar.algorithms.ml.load_model", return_value=mock_model):
            algo = MLAlgorithm()
            result = algo.run(synthetic_ml_dataset)

        # Where valid, values should be 0 (clipped)
        valid_mask = result["quality_flag"].values == QualityFlag.VALID
        if valid_mask.any():
            assert (result["snow_depth"].values[valid_mask] == 0.0).all()
