# SnowSAR

SAR-based snow depth retrieval system for Northern Hemisphere mountain environments.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

SnowSAR is an open-source web application that retrieves snow depth estimates from satellite SAR (Synthetic Aperture Radar) data. It supports four complementary retrieval algorithms — empirical change-detection, ML-enhanced, dual-polarimetric, and L-band InSAR — unified behind a common data-provider abstraction so algorithms consume standardized data regardless of whether it comes from Google Earth Engine or local ASF downloads.

## Features

- **Four retrieval algorithms** (implemented across phases):
  - Lievens empirical change-detection (Sentinel-1 C-band)
  - ML-enhanced (XGBoost with ERA5 + WorldCover features)
  - DpRSE dual-polarimetric (treeless areas)
  - L-band InSAR (NISAR; Phase 3)
- **Cloud-agnostic data layer** — same algorithms run against GEE or locally-downloaded ASF data
- **FastAPI backend** with Celery/Redis job orchestration
- **React + Leaflet frontend** for interactive AOI selection and result visualization
- **SNOTEL validation** built in — point-level retrieval vs. observation comparison
- Runs in Docker (`docker compose up`) or directly with `uv run snowsar serve`

## Quickstart

Requires **Python 3.12+** and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Run the test suite
uv run pytest

# Start the API server
uv run snowsar serve

# (In another shell) start the frontend dev server
cd frontend && npm install && npm run dev
```

The API runs at `http://localhost:8000` (OpenAPI docs at `/api/docs`) and the frontend at `http://localhost:5173`.

## Architecture

Three-tier design:

- **Frontend** — React + TypeScript SPA with Leaflet map, AOI drawing, and job controls
- **Backend** — FastAPI REST API, Celery workers, PostgreSQL/PostGIS metadata store, Redis broker
- **Data & compute layer** — `DataProvider` abstraction (GEE or local ASF) returning standardized `xarray.Dataset` objects that all algorithms consume

```
┌────────────┐    ┌──────────────┐    ┌────────────────────┐
│  Frontend  │ →  │  FastAPI     │ →  │  Celery workers    │
│  (React)   │    │  + Postgres  │    │  + DataProvider    │
└────────────┘    └──────────────┘    │  + Algorithms      │
                                      └────────────────────┘
```

## Directory Layout

```
snowsar/           # Main Python package
  algorithms/      # Retrieval algorithms (Lievens, DpRSE, ML, InSAR)
  api/             # FastAPI app and route handlers
  providers/       # DataProvider implementations (GEE, ASF)
  validation/      # SNOTEL/GHCN-D validation utilities
  utils/           # Geo, raster, temporal helpers
tests/             # Unit + integration tests (>80% coverage target)
frontend/          # React + Vite frontend
docker/            # Dockerfiles and compose configs
docs/              # MkDocs site
notebooks/         # Example Jupyter notebooks per algorithm
models/            # ML model registry metadata (weights on Zenodo)
```

## Development

```bash
uv run pytest                                # All tests
uv run pytest -m "not integration"           # Unit tests only
uv run pytest tests/test_types.py::TestFoo   # Single test
uv run ruff check . && uv run ruff format .  # Lint and format
uv run mypy .                                # Type check
```

See `CLAUDE.md` for workflow requirements and the implementation plan.

## Documentation

- Product Requirements: `.llm/snowsar_prd_v1.2.md`
- Full docs (MkDocs): `uv run --extra docs mkdocs serve`
- API reference: `http://localhost:8000/api/docs` (Swagger UI when running)

## License

Apache 2.0. See [LICENSE](LICENSE).
