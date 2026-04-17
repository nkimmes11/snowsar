"""Base protocol for snow depth retrieval algorithms."""

from __future__ import annotations

from typing import Any, Protocol

import xarray as xr

from snowsar.types import AlgorithmID, Backend


class SnowDepthAlgorithm(Protocol):
    """Protocol that all retrieval algorithms must satisfy.

    Each algorithm takes a standardized xarray.Dataset (from a DataProvider)
    and returns a Dataset with snow_depth, quality_flag, and uncertainty.
    """

    @property
    def algorithm_id(self) -> AlgorithmID: ...

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def supported_backends(self) -> list[Backend]: ...

    def validate_input(self, ds: xr.Dataset) -> None:
        """Check that the input Dataset has the required variables.

        Raises ValueError if validation fails.
        """
        ...

    def run(self, ds: xr.Dataset, params: dict[str, Any] | None = None) -> xr.Dataset:
        """Execute the retrieval algorithm.

        Args:
            ds: Standardized input Dataset from a DataProvider.
            params: Algorithm-specific parameters (optional overrides).

        Returns:
            Dataset with at minimum:
                - snow_depth: float32, meters
                - quality_flag: uint8 (QualityFlag values)
                - uncertainty: float32, meters (NaN where unavailable)
            Plus all input coordinates and CRS metadata.
        """
        ...
