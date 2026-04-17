"""Algorithm registry — discover and instantiate retrieval algorithms."""

from __future__ import annotations

from snowsar.algorithms.base import SnowDepthAlgorithm
from snowsar.exceptions import SnowSARError
from snowsar.types import AlgorithmID


def get_algorithm(algorithm_id: AlgorithmID) -> SnowDepthAlgorithm:
    """Create an algorithm instance by ID.

    Raises:
        SnowSARError: If the algorithm ID is not recognized.
    """
    if algorithm_id == AlgorithmID.LIEVENS:
        from snowsar.algorithms.lievens import LievensAlgorithm

        return LievensAlgorithm()

    # Phase 2+ algorithms will be added here:
    # if algorithm_id == AlgorithmID.ML: ...
    # if algorithm_id == AlgorithmID.DPRSE: ...
    # if algorithm_id == AlgorithmID.INSAR: ...

    msg = f"Algorithm not yet implemented: {algorithm_id}"
    raise SnowSARError(msg)


def list_algorithms() -> list[dict[str, str]]:
    """Return metadata for all available algorithms."""
    available = []
    for aid in AlgorithmID:
        try:
            algo = get_algorithm(aid)
            available.append(
                {
                    "id": aid.value,
                    "name": algo.name,
                    "description": algo.description,
                }
            )
        except SnowSARError:
            continue
    return available
