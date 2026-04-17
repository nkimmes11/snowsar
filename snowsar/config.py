"""Application configuration via environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """SnowSAR application settings.

    All values can be overridden via environment variables
    (prefix: SNOWSAR_).
    """

    model_config = {"env_prefix": "SNOWSAR_"}

    # Database
    database_url: str = "postgresql+psycopg://snowsar:snowsar@localhost:5432/snowsar"

    # Celery / Redis
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Data storage
    data_dir: Path = Path.home() / ".snowsar" / "data"
    results_dir: Path = Path.home() / ".snowsar" / "results"
    models_dir: Path = Path.home() / ".snowsar" / "models"

    # GEE
    gee_project: str | None = None

    # ASF / Earthdata
    earthdata_username: str | None = None
    earthdata_password: str | None = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    def ensure_dirs(self) -> None:
        """Create local storage directories if they don't exist."""
        for d in (self.data_dir, self.results_dir, self.models_dir):
            d.mkdir(parents=True, exist_ok=True)
