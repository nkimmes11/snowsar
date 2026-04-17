"""Tests for the algorithm registry."""

from __future__ import annotations

import pytest

from snowsar.algorithms.registry import get_algorithm, list_algorithms
from snowsar.exceptions import SnowSARError
from snowsar.types import AlgorithmID


class TestAlgorithmRegistry:
    def test_get_lievens(self) -> None:
        algo = get_algorithm(AlgorithmID.LIEVENS)
        assert algo.algorithm_id == AlgorithmID.LIEVENS

    def test_get_unimplemented_raises(self) -> None:
        with pytest.raises(SnowSARError, match="not yet implemented"):
            get_algorithm(AlgorithmID.ML)

    def test_list_algorithms(self) -> None:
        available = list_algorithms()
        assert len(available) >= 1
        ids = [a["id"] for a in available]
        assert "lievens" in ids
