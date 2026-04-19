"""Synchronous pipeline runner: provider -> algorithm(s) -> results store.

Invoked by FastAPI BackgroundTasks (default) or by a Celery task when
execution_mode == "celery". Runs in-process and updates the job store
+ api.results_store so downstream endpoints have something to serve.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

import xarray as xr

from snowsar.algorithms.registry import get_algorithm
from snowsar.api import results_store
from snowsar.api.schemas import JobCreateRequest, JobStatus
from snowsar.exceptions import JobError, SnowSARError
from snowsar.jobs import store as job_store
from snowsar.providers.registry import get_provider
from snowsar.types import AOI, AlgorithmID, Backend, TemporalRange

log = logging.getLogger(__name__)


def _coerce_backend(value: str) -> Backend:
    try:
        return Backend[value.upper()]
    except KeyError as exc:
        msg = f"Unknown backend: {value}"
        raise JobError(msg) from exc


def _coerce_algorithm(value: str) -> AlgorithmID:
    try:
        return AlgorithmID(value)
    except ValueError as exc:
        msg = f"Unknown algorithm: {value}"
        raise JobError(msg) from exc


def _merge_outputs(outputs: dict[str, xr.Dataset]) -> xr.Dataset:
    """Combine per-algorithm output Datasets into a single result Dataset.

    When only one algorithm ran, its output is returned verbatim. When
    multiple algorithms ran, their snow_depth / quality_flag / uncertainty
    variables are suffixed with the algorithm id (e.g. snow_depth_lievens).
    The first algorithm's outputs also remain under the unsuffixed names
    so existing single-variable endpoints keep working.
    """
    if not outputs:
        msg = "No algorithm outputs to merge"
        raise JobError(msg)

    ids = list(outputs.keys())
    primary_id = ids[0]
    merged = outputs[primary_id].copy()

    for algo_id, ds in outputs.items():
        for var in ("snow_depth", "quality_flag", "uncertainty"):
            if var in ds:
                merged[f"{var}_{algo_id}"] = ds[var]

    merged.attrs["algorithms"] = ",".join(ids)
    merged.attrs["primary_algorithm"] = primary_id
    return merged


def run_job(job_id: str, request: JobCreateRequest) -> None:
    """Execute the full pipeline for a single job, updating status as it runs.

    Exceptions are caught and recorded on the job; nothing is re-raised
    because this runs inside a BackgroundTask / Celery worker.
    """
    job_store.update_status(job_id, JobStatus.RUNNING)
    log.info("job %s: starting (backend=%s algos=%s)", job_id, request.backend, request.algorithms)

    try:
        backend = _coerce_backend(request.backend)
        algorithms = [_coerce_algorithm(a) for a in request.algorithms]
        if not algorithms:
            msg = "At least one algorithm must be specified"
            raise JobError(msg)

        aoi = AOI.from_bbox(
            request.bbox.west, request.bbox.south, request.bbox.east, request.bbox.north
        )
        temporal_range = TemporalRange(start=request.start_date, end=request.end_date)

        provider = get_provider(backend)
        input_ds = provider.load_full(aoi, temporal_range)

        outputs: dict[str, xr.Dataset] = {}
        for aid in algorithms:
            algo = get_algorithm(aid)
            params: dict[str, Any] | None = (
                request.algorithm_params.get(aid.value)  # type: ignore[assignment]
                if isinstance(request.algorithm_params, dict)
                else None
            )
            outputs[aid.value] = algo.run(input_ds, params)

        merged = _merge_outputs(outputs)
        results_store.put(job_id, merged)
        job_store.update_status(job_id, JobStatus.COMPLETED)
        log.info("job %s: completed", job_id)

    except SnowSARError as exc:
        log.exception("job %s: failed (SnowSARError)", job_id)
        job_store.update_status(job_id, JobStatus.FAILED, error_message=str(exc))
    except Exception as exc:
        log.exception("job %s: failed (unexpected)", job_id)
        job_store.update_status(
            job_id,
            JobStatus.FAILED,
            error_message=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )
