"""Integration test for algorithm registry — schema conformance across algorithms."""

from __future__ import annotations

import pytest
import xarray as xr

from snowsar.algorithms.registry import get_algorithm, list_algorithms
from snowsar.exceptions import SnowSARError
from snowsar.types import AlgorithmID

pytestmark = pytest.mark.integration


class TestAlgorithmRegistry:
    def test_all_registered_algorithms_have_conformant_output(
        self, integration_sar_dataset: xr.Dataset
    ) -> None:
        """Every registered algorithm must produce the same output schema."""
        required_vars = {"snow_depth", "quality_flag", "uncertainty"}

        for aid in AlgorithmID:
            try:
                algo = get_algorithm(aid)
            except SnowSARError:
                # Skip algorithms not yet implemented
                continue

            result = algo.run(integration_sar_dataset)
            missing = required_vars - set(result.data_vars)
            assert not missing, f"{aid.value} missing variables: {missing}"
            assert result.attrs.get("algorithm") is not None

    def test_list_algorithms_matches_implemented(self) -> None:
        """list_algorithms() should include every algorithm that can be instantiated."""
        listed = list_algorithms()
        listed_ids = {a["id"] for a in listed}

        for aid in AlgorithmID:
            try:
                get_algorithm(aid)
                assert aid.value in listed_ids, f"{aid.value} instantiable but not listed"
            except SnowSARError:
                continue
