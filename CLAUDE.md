# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SnowSAR is an open-source (Apache 2.0) Python web application that retrieves snow depth estimates from satellite SAR data. It targets Northern Hemisphere mountain environments and implements four retrieval algorithms: empirical (Lievens), ML-enhanced (XGBoost), dual-polarimetric (DpRSE), and L-band InSAR (NISAR). The PRD lives at `.llm/snowsar_prd_v1.2.md`.

## Build and Development

This project uses **uv** for Python package management (Python 3.12+, see `.python-version`).

```bash
uv sync                  # Install dependencies
uv run pytest            # Run all tests
uv run pytest tests/test_foo.py::test_bar  # Run a single test
uv run ruff check .      # Lint
uv run ruff format .     # Format
uv run mypy .            # Type check
```

## Architecture

Three-tier design: browser frontend (React or Vue + Leaflet), Python backend (FastAPI + Celery/Redis), and a cloud-agnostic data/compute layer.

**Key architectural pattern:** A `DataProvider` abstraction decouples algorithm code from data sources. Algorithms consume standardized `xarray.Dataset` objects regardless of whether data comes from Google Earth Engine or local ASF downloads.

**Planned package layout:**
- `snowsar/` — main package (algorithms, data providers, API, utilities)
- `tests/` — pytest suite (unit + integration, >80% coverage target)
- `frontend/` — web UI
- `models/` — ML model registry metadata (actual models hosted on Zenodo, fetched via `pooch`)
- `docker/` — containerization configs
- `notebooks/` — example Jupyter notebooks per algorithm

## Algorithm Implementations

1. **Lievens empirical change-detection** (Phase 1) — adapts the `spicy-snow` package; uses Sentinel-1 C-band cross-polarization ratio with forest cover fraction weighting
2. **ML-enhanced retrieval** (Phase 2) — XGBoost default; pre-trained models stored on Zenodo, downloaded/cached via `pooch` to `~/.snowsar/models/`
3. **DpRSE dual-polarimetric** (Phase 2) — reference code from Figshare; treeless areas only
4. **L-band InSAR** (Phase 3) — NISAR data via `isce3`/`mintpy` (optional deps); local/ASF backend only (no GEE support); includes Sturm et al. density model for SWE-to-depth conversion

## CI/CD

GitHub Actions: ruff (lint) + mypy (types) + pytest (tests) on every push/PR. Integration tests, Docker builds, and docs on merge to main. PyPI publish on tagged releases.

## Workflow Requirements

- **Commit after every step:** Push a git commit to the GitHub repository after completing each implementation step.
- **Verify CI passes:** After every push, check that all GitHub Actions CI runs (lint, typecheck, test) have passed. If any fail, fix the issues before proceeding to the next step.
- **Run locally before pushing:** Always run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` locally before committing.

## Branch Strategy

`main` (stable releases), `develop` (integration), `feature/*` (individual features). All merges to main require passing CI and review.

## Conversations with User
1. Ensure that a brief description of each step is provided prior to performing the step. Ask for user input to proceed.
2. Ensure that a brief description of the tests, and what they are testing, is provided prior to running the tests. Ask for user input to proceed prior to performing the tests.