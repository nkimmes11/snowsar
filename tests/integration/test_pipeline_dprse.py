"""End-to-end integration test for the DpRSE algorithm pipeline."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.algorithms.dprse import DpRSEAlgorithm
from snowsar.types import QualityFlag

pytestmark = pytest.mark.integration


class TestDpRSEPipeline:
    def test_full_pipeline_produces_valid_output(self, integration_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(integration_sar_dataset)

        assert "snow_depth" in result
        assert "quality_flag" in result
        assert "uncertainty" in result

        assert result["snow_depth"].dtype == np.float32
        assert result["quality_flag"].dtype == np.uint8
        assert result["uncertainty"].dtype == np.float32

    def test_quality_flags_within_enum_range(self, integration_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(integration_sar_dataset)

        valid_values = {int(q) for q in QualityFlag}
        unique_flags = set(np.unique(result["quality_flag"].values).tolist())
        assert unique_flags.issubset(valid_values)

    def test_preserves_coords_and_crs(self, integration_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result = algo.run(integration_sar_dataset)

        assert "time" in result.coords
        assert result.attrs["crs"] == integration_sar_dataset.attrs["crs"]
        assert result.attrs["algorithm"] == "dprse"

    def test_custom_regression_changes_output(self, integration_sar_dataset: xr.Dataset) -> None:
        algo = DpRSEAlgorithm()
        result_default = algo.run(integration_sar_dataset)
        result_custom = algo.run(
            integration_sar_dataset,
            params={"regression_slope": 10.0, "regression_intercept": 0.0},
        )

        default_mean = np.nanmean(result_default["snow_depth"].values)
        custom_mean = np.nanmean(result_custom["snow_depth"].values)
        assert default_mean != custom_mean
