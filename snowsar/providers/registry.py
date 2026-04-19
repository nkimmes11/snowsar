"""Provider registry — factory for creating DataProvider instances."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from snowsar.exceptions import SnowSARError
from snowsar.types import Backend

if TYPE_CHECKING:
    from snowsar.providers.base import DataProvider


def get_provider(backend: Backend, **kwargs: Any) -> DataProvider:
    """Create a DataProvider instance for the given backend.

    Args:
        backend: Which processing backend to use.
        **kwargs: Backend-specific configuration passed to the provider constructor.

    Returns:
        A DataProvider implementation.

    Raises:
        SnowSARError: If the backend is not supported or cannot be initialized.
    """
    if backend == Backend.GEE:
        from snowsar.providers.gee import GEEProvider

        return GEEProvider(**kwargs)
    if backend == Backend.LOCAL:
        from snowsar.providers.asf import ASFProvider

        return ASFProvider(**kwargs)
    if backend == Backend.FIXTURE:
        from snowsar.providers.fixture import FixtureProvider

        return FixtureProvider()
    msg = f"Unsupported backend: {backend}"
    raise SnowSARError(msg)
