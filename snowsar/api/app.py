"""FastAPI application factory."""

from fastapi import FastAPI

from snowsar import __version__


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SnowSAR API",
        description="SAR-based snow depth retrieval system",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    from snowsar.api.routes import algorithms, health, jobs, results, timeseries

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(algorithms.router, prefix="/api/v1", tags=["algorithms"])
    app.include_router(results.router, prefix="/api/v1", tags=["results"])
    app.include_router(timeseries.router, prefix="/api/v1", tags=["results"])

    return app
