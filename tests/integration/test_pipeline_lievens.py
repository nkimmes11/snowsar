"""End-to-end integration test for the Lievens algorithm pipeline."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.algorithms.lievens import LievensAlgorithm
from snowsar.types import QualityFlag

pytestmark = pytest.mark.integration


class TestLievensPipeline:
    def test_full_pipeline_produces_valid_output(self, integration_sar_dataset: xr.Dataset) -> None:
        """Run Lievens end-to-end and verify output schema."""
        algo = LievensAlgorithm()
        result = algo.run(integration_sar_dataset)

        # Required output variables
        assert "snow_depth" in result
        assert "quality_flag" in result
        assert "uncertainty" in result

        # Correct dtypes (critical for GeoTIFF writing)
        assert result["snow_depth"].dtype == np.float32
        assert result["quality_flag"].dtype == np.uint8
        assert result["uncertainty"].dtype == np.float32

    def test_quality_flags_within_enum_range(self, integration_sar_dataset: xr.Dataset) -> None:
        """All quality_flag values must be valid QualityFlag members."""
        algo = LievensAlgorithm()
        result = algo.run(integration_sar_dataset)

        valid_values = {int(q) for q in QualityFlag}
        unique_flags = set(np.unique(result["quality_flag"].values).tolist())
        assert unique_flags.issubset(valid_values)

    def test_preserves_coords_and_crs(self, integration_sar_dataset: xr.Dataset) -> None:
        """Output Dataset must preserve coordinates and CRS attribute."""
        algo = LievensAlgorithm()
        result = algo.run(integration_sar_dataset)

        assert "time" in result.coords
        assert "x" in result.coords
        assert "y" in result.coords
        assert result.attrs["crs"] == integration_sar_dataset.attrs["crs"]
        assert result.attrs["algorithm"] == "lievens"

    def test_custom_parameters_propagate(self, integration_sar_dataset: xr.Dataset) -> None:
        """Custom regression coefficients should change output magnitude."""
        algo = LievensAlgorithm()
        result_default = algo.run(integration_sar_dataset)
        result_custom = algo.run(
            integration_sar_dataset, params={"coeff_a": 4.0, "coeff_b": 1.0, "coeff_c": 0.0}
        )

        # Results should differ when coefficients differ
        default_mean = np.nanmean(result_default["snow_depth"].values)
        custom_mean = np.nanmean(result_custom["snow_depth"].values)
        assert default_mean != custom_mean
