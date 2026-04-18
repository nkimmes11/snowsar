"""Tests for the ML model registry."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import joblib
import pytest

from snowsar.models.registry import (
    ModelNotAvailableError,
    ModelNotFoundError,
    download_model,
    get_model_metadata,
    list_models,
    load_local_model,
    load_model,
    load_registry,
)


@pytest.fixture
def placeholder_registry(tmp_path: Path) -> Path:
    """A registry file with both a placeholder and a publishable entry."""
    data = {
        "models": [
            {
                "name": "placeholder_model",
                "version": "0.0.0-placeholder",
                "description": "No URL",
                "url": None,
                "sha256": None,
                "algorithm_family": "xgboost",
                "features": ["gamma0_vv", "gamma0_vh"],
                "experimental": True,
            },
            {
                "name": "test_model",
                "version": "1.0",
                "description": "Fake published model",
                "url": "https://example.com/fake.joblib",
                "sha256": "deadbeef",
                "algorithm_family": "xgboost",
                "features": ["gamma0_vv", "gamma0_vh"],
            },
        ]
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(data))
    return path


class TestLoadRegistry:
    def test_production_registry_loads(self) -> None:
        """The committed registry.json must be parseable."""
        models = list_models()
        assert isinstance(models, list)
        assert len(models) >= 1
        for m in models:
            assert "name" in m
            assert "version" in m

    def test_custom_registry_loads(self, placeholder_registry: Path) -> None:
        models = load_registry(placeholder_registry)
        assert len(models) == 2


class TestGetMetadata:
    def test_latest_returns_first_match(self, placeholder_registry: Path) -> None:
        meta = get_model_metadata("test_model", "latest", placeholder_registry)
        assert meta["version"] == "1.0"

    def test_specific_version(self, placeholder_registry: Path) -> None:
        meta = get_model_metadata("test_model", "1.0", placeholder_registry)
        assert meta["name"] == "test_model"

    def test_unknown_name_raises(self, placeholder_registry: Path) -> None:
        with pytest.raises(ModelNotFoundError):
            get_model_metadata("nonexistent", "latest", placeholder_registry)

    def test_unknown_version_raises(self, placeholder_registry: Path) -> None:
        with pytest.raises(ModelNotFoundError):
            get_model_metadata("test_model", "9.9.9", placeholder_registry)


class TestDownloadModel:
    def test_placeholder_raises_not_available(self, placeholder_registry: Path) -> None:
        with pytest.raises(ModelNotAvailableError):
            download_model("placeholder_model", "latest", registry_path=placeholder_registry)

    def test_published_invokes_pooch(self, placeholder_registry: Path, tmp_path: Path) -> None:
        """With a published URL, download_model should call pooch.retrieve."""
        fake_path = tmp_path / "fake.joblib"
        fake_path.write_bytes(b"placeholder")

        with patch("snowsar.models.registry.pooch.retrieve", return_value=str(fake_path)) as mock:
            result = download_model(
                "test_model",
                "1.0",
                cache_dir=tmp_path,
                registry_path=placeholder_registry,
            )
        assert result == fake_path
        mock.assert_called_once()


class TestLoadModel:
    def test_load_bundled_model(self, tmp_path: Path, placeholder_registry: Path) -> None:
        """load_model should download then joblib-load the file."""
        fake_path = tmp_path / "fake.joblib"
        joblib.dump({"model": "fake_estimator", "features": ["a", "b"]}, fake_path)

        with patch("snowsar.models.registry.pooch.retrieve", return_value=str(fake_path)):
            bundle = load_model(
                "test_model",
                "1.0",
                cache_dir=tmp_path,
                registry_path=placeholder_registry,
            )
        assert bundle["model"] == "fake_estimator"
        assert bundle["features"] == ["a", "b"]

    def test_load_local_model(self, tmp_path: Path) -> None:
        path = tmp_path / "local.joblib"
        joblib.dump({"k": "v"}, path)
        assert load_local_model(path) == {"k": "v"}
