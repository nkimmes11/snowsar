"""Tests for the provider registry."""

from __future__ import annotations

import pytest

from snowsar.exceptions import SnowSARError
from snowsar.providers.registry import get_provider
from snowsar.types import Backend


class TestProviderRegistry:
    def test_gee_provider_import_error_message(self) -> None:
        """GEE provider should give a clear error if ee isn't authenticated."""
        # This will either succeed (if ee is installed + authed) or raise
        # DataProviderError with a helpful message
        try:
            provider = get_provider(Backend.GEE)
            assert provider is not None
        except Exception as exc:
            assert "Earth Engine" in str(exc) or "earthengine" in str(exc)

    def test_local_provider_creates(self, tmp_path: object) -> None:
        """LOCAL provider should instantiate without external services."""
        from snowsar.providers.asf import ASFProvider

        provider = ASFProvider(data_dir=tmp_path)  # type: ignore[arg-type]
        assert provider is not None

    def test_invalid_backend_raises(self) -> None:
        """Non-existent backend should raise."""
        with pytest.raises(SnowSARError):
            get_provider("not_a_backend")  # type: ignore[arg-type]
