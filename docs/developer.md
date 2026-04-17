# Developer Guide

## Setup

```bash
uv sync
uv run pre-commit install  # optional — runs lint/format/typecheck on commit
```

## Running Tests

```bash
uv run pytest                           # all tests
uv run pytest -m "not integration"      # unit tests only
uv run pytest -m "integration"          # integration tests only
uv run pytest --cov=snowsar             # with coverage
```

## Code Quality

The CI pipeline enforces three gates on every push:

1. `uv run ruff check .` — lint
2. `uv run ruff format --check .` — formatting
3. `uv run mypy .` — strict type checking
4. `uv run pytest` — full test suite

Run these locally before pushing.

## Adding a New Algorithm

1. Create `snowsar/algorithms/<name>.py` implementing the `SnowDepthAlgorithm`
   protocol (see `snowsar/algorithms/base.py`)
2. Register in `snowsar/algorithms/registry.py`
3. Add `AlgorithmID.<NAME>` to `snowsar/types.py`
4. Add unit tests in `tests/algorithms/test_<name>.py`
5. Add integration test under `tests/integration/`
6. Add doc page under `docs/algorithms/<name>.md` and register in `mkdocs.yml`

## Architecture

See `README.md` and `CLAUDE.md` for high-level architecture. The PRD at
`.llm/snowsar_prd_v1.2.md` is the source of truth for requirements.

---

*Full developer guide coming in Phase 3.*
