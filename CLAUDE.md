# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⛔ WORKFLOW GATES — READ FIRST

These gates apply throughout the entire session, including after `/compact`, after context resets, and during long multi-step implementations. Do not drift past them because you are "in the middle of something."

### Gate 1 — Step description + approval
Before beginning any implementation step from the active plan file, post a brief description of what will be created/changed and end with an explicit question like "Proceed?". Wait for user confirmation. **Do not start writing or editing files until the user replies yes.**

### Gate 2 — Test description + approval
Before running any `pytest` command — including `uv run pytest`, scoped runs like `uv run pytest tests/output`, marker runs like `-m integration`, re-runs after fixing a failure, and the final full-suite check before commit — post a brief description that:
- Names each test file or class being exercised
- Summarizes what each test validates (inputs, expected outputs, what property it verifies)
- Ends with "Proceed?" and waits for user confirmation

**Common failure mode:** during multi-step implementation, running `pytest` can feel like "just checking my work" rather than a gated action. It is still gated. Every `pytest` invocation requires a description and approval, no exceptions.

Lint, format, type-check, and git commands (`ruff`, `mypy`, `git`) do NOT require approval — run them freely.

### Gate 3 — Plan completeness verification (pre-commit)

Before declaring any step complete and before committing, explicitly cross-check every file AND every sub-feature listed in the plan text for that step. "Tests pass" does NOT mean the step is done — tests only verify what was implemented, not what was omitted.

For each item in the plan:
- ✅ delivered → note briefly
- ❌ not delivered → it MUST appear in the step-complete message as an explicit omission with either (a) a justification and user approval to defer, or (b) immediate fill-in before commit. Silent omission is a workflow violation.

A step-complete message that lists only what was built and not what was skipped is a Gate 3 failure. Adding `TODO` comments in place of implementation without surfacing the TODO to the user is also a Gate 3 failure.

When you finish a step, post a short "Plan completeness check" section that enumerates each bullet from the plan text (files and sub-features both) and marks each ✅ or ❌. If any ❌ entries exist, do not declare the step done — ask the user how to proceed.

---

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

- **Follow the implementation plan in order:** The implementation plan (in the active plan file) must be followed sequentially. Any deviations from the plan — including skipping steps, reordering steps, or changing scope — require explicit user approval before proceeding.
- **No silent partial delivery:** If a step's plan enumerates specific files, modules, or features (e.g., "Celery tasks → worker → DB persistence"), you must either deliver all of them, or explicitly flag the gaps and get user approval before declaring the step complete. Stubbed `TODO` comments without user acknowledgement are a workflow violation. See Gate 3 above.
- **Keep the as-built record honest:** The memory file `memory/project_status.md` is the authoritative as-built record of what has and has not been delivered. It must be updated at the end of every step to reflect reality — including any deferred scope, known gaps, or step numbering changes (e.g. inserted `1.5b`). A step is not complete until this file is accurate.
- **Commit after every step:** Push a git commit to the GitHub repository after completing each implementation step.
- **Verify CI passes:** After every push, check that all GitHub Actions CI runs (lint, typecheck, test) have passed. If any fail, fix the issues before proceeding to the next step.
- **Run locally before pushing:** Always run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` locally before committing.

## Branch Strategy

`main` (stable releases), `develop` (integration), `feature/*` (individual features). All merges to main require passing CI and review.