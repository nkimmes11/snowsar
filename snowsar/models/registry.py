"""ML model registry — declare, download, and load pre-trained models.

Models are declared in ``models/registry.json`` at the repo root. At runtime,
``download_model()`` uses ``pooch`` to fetch the serialized model from its
hosted URL (typically Zenodo), verify the SHA256 checksum, and cache the
file in ``~/.snowsar/models/``.

**Note:** As of the initial Phase 2 release, no production model has been
published. Registry entries may have ``url`` set to ``null``, in which case
``download_model()`` raises :class:`ModelNotAvailableError`. Users can
train and register their own models via :mod:`snowsar.models.training`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pooch

from snowsar.exceptions import SnowSARError

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "models" / "registry.json"
DEFAULT_CACHE_DIR = Path.home() / ".snowsar" / "models"


class ModelNotAvailableError(SnowSARError):
    """Raised when a requested model is not published in the registry."""


class ModelNotFoundError(SnowSARError):
    """Raised when a requested model name/version is not registered."""


def load_registry(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the model registry JSON and return the list of model entries."""
    registry_path = path or DEFAULT_REGISTRY_PATH
    with registry_path.open() as f:
        data = json.load(f)
    models: list[dict[str, Any]] = data.get("models", [])
    return models


def list_models(path: Path | None = None) -> list[dict[str, Any]]:
    """Return metadata for all registered models."""
    return load_registry(path)


def get_model_metadata(
    name: str,
    version: str = "latest",
    path: Path | None = None,
) -> dict[str, Any]:
    """Look up a registry entry by name and version.

    If ``version`` is ``"latest"``, returns the first matching entry for
    ``name``. Raises :class:`ModelNotFoundError` if no match.
    """
    for entry in load_registry(path):
        if entry["name"] != name:
            continue
        if version == "latest" or entry["version"] == version:
            return entry
    msg = f"Model not found in registry: name={name!r}, version={version!r}"
    raise ModelNotFoundError(msg)


def download_model(
    name: str,
    version: str = "latest",
    cache_dir: Path | None = None,
    registry_path: Path | None = None,
) -> Path:
    """Download (or retrieve from cache) a registered model file.

    Returns the local filesystem path to the cached model file.

    Raises:
        ModelNotFoundError: If the name/version is not in the registry.
        ModelNotAvailableError: If the registry entry has no URL (e.g.,
            placeholder entries where no production model has been published).
    """
    meta = get_model_metadata(name, version, registry_path)
    url = meta.get("url")
    if not url:
        msg = (
            f"Model {name!r} (version {meta['version']!r}) has no published URL. "
            "This is likely a placeholder — no production model exists yet. "
            "See Phase 5 of the implementation plan."
        )
        raise ModelNotAvailableError(msg)

    cache = cache_dir or DEFAULT_CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)

    sha256 = meta.get("sha256")
    known_hash = f"sha256:{sha256}" if sha256 else None

    fname = f"{name}_{meta['version']}.joblib"
    cached: str = pooch.retrieve(
        url=url,
        known_hash=known_hash,
        fname=fname,
        path=str(cache),
    )
    return Path(cached)


def load_model(
    name: str,
    version: str = "latest",
    cache_dir: Path | None = None,
    registry_path: Path | None = None,
) -> Any:
    """Download (if needed) and deserialize a registered model.

    The returned object is whatever ``joblib.dump()`` produced — typically a
    fitted scikit-learn/xgboost estimator or a dict containing the estimator
    plus a scaler and feature names.
    """
    model_path = download_model(name, version, cache_dir, registry_path)
    return joblib.load(model_path)


def load_local_model(path: Path) -> Any:
    """Load a model from a local joblib file without consulting the registry.

    Useful for users running custom/retrained models.
    """
    return joblib.load(path)
