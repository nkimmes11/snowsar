"""Matplotlib figure factories for cross-algorithm comparison."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import xarray as xr

from snowsar.comparison.stats import compute_pairwise_stats, difference_map

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def difference_map_plot(
    ds_a: xr.Dataset,
    ds_b: xr.Dataset,
    *,
    variable: str = "snow_depth",
    time_index: int | None = None,
    valid_only: bool = True,
    title: str | None = None,
) -> Figure:
    """Plot a 2-D map of ``ds_a[variable] - ds_b[variable]`` at a single timestep."""
    import matplotlib.pyplot as plt

    diff = difference_map(ds_a, ds_b, variable=variable, valid_only=valid_only)

    if "time" in diff.dims:
        if time_index is None:
            diff2d = diff.mean(dim="time", skipna=True)
        else:
            diff2d = diff.isel(time=time_index)
    else:
        diff2d = diff

    vals = diff2d.values
    vmax = float(np.nanmax(np.abs(vals))) if np.isfinite(vals).any() else 1.0
    vmax = vmax if vmax > 0 else 1.0

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(
        vals,
        origin="lower",
        cmap="RdBu_r",
        vmin=-vmax,
        vmax=vmax,
        aspect="auto",
    )
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title or f"{variable} difference (A - B)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(f"{variable} (A - B)")
    fig.tight_layout()
    return fig


def taylor_diagram(
    ds_ref: xr.Dataset,
    others: dict[str, xr.Dataset],
    *,
    variable: str = "snow_depth",
    valid_only: bool = True,
    title: str = "Taylor diagram",
) -> Figure:
    """Render a Taylor diagram comparing several Datasets to a reference.

    Each candidate in ``others`` is plotted at polar coordinates
    (theta = arccos(pearson_r), r = std_candidate / std_reference).
    """
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(7, 6))
    # Polar axes expose set_theta_*/set_rlim which aren't on the generic Axes stub.
    ax: Any = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(-1)
    ax.set_thetalim(0, np.pi / 2)
    ax.set_rlim(0, 2.0)
    ax.set_title(title)

    ax.plot(0, 1.0, marker="o", color="black", label="reference")

    for name, ds in others.items():
        stats = compute_pairwise_stats(ds, ds_ref, variable=variable, valid_only=valid_only)
        if not np.isfinite(stats.pearson_r) or not np.isfinite(stats.std_ratio):
            continue
        r_clamped = float(np.clip(stats.pearson_r, -1.0, 1.0))
        theta = float(np.arccos(r_clamped))
        radius = float(stats.std_ratio)
        ax.plot(theta, radius, marker="o", linestyle="", label=name)

    ax.set_xlabel("correlation (cos theta)")
    ax.set_ylabel("std candidate / std reference")
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    fig.tight_layout()
    return fig
