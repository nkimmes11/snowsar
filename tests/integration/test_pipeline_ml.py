"""End-to-end integration test for the ML algorithm pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import xarray as xr

from snowsar.algorithms.ml import MLAlgorithm
from snowsar.types import QualityFlag

pytestmark = pytest.mark.integration


class TestMLPipeline:
    def test_fallback_pipeline_with_placeholder_registry(
        self, integration_ml_dataset: xr.Dataset
    ) -> None:
        """With no published model, the pipeline returns a well-formed fallback Dataset."""
        algo = MLAlgorithm()
        result = algo.run(integration_ml_dataset)

        assert "snow_depth" in result
        assert "quality_flag" in result
        assert "uncertainty" in result
        assert result["snow_depth"].dtype == np.float32
        assert result["quality_flag"].dtype == np.uint8
        assert np.all(np.isnan(result["snow_depth"].values))

    def test_mocked_model_pipeline(self, integration_ml_dataset: xr.Dataset) -> None:
        """With a mocked model, the pipeline produces valid snow depth predictions."""
        mock_model = MagicMock()
        n = integration_ml_dataset["gamma0_vv"].size
        mock_model.predict.return_value = np.full(n, 0.9, dtype=np.float32)

        with patch("snowsar.algorithms.ml.load_model", return_value=mock_model):
            algo = MLAlgorithm()
            result = algo.run(integration_ml_dataset)

        assert result["snow_depth"].shape == integration_ml_dataset["gamma0_vv"].shape
        assert result.attrs["algorithm"] == "ml"

        # Quality flags should be within the enum range
        valid_values = {int(q) for q in QualityFlag}
        unique_flags = set(np.unique(result["quality_flag"].values).tolist())
        assert unique_flags.issubset(valid_values)
