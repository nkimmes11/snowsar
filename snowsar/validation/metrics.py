"""Statistical metrics for validation of snow depth retrievals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure


@dataclass
class ValidationMetrics:
    """Summary statistics comparing predicted vs. observed snow depth."""

    bias: float
    rmse: float
    mae: float
    pearson_r: float
    count: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "bias": self.bias,
            "rmse": self.rmse,
            "mae": self.mae,
            "pearson_r": self.pearson_r,
            "count": self.count,
        }


def compute_metrics(predicted: np.ndarray, observed: np.ndarray) -> ValidationMetrics:
    """Compute validation statistics between predicted and observed arrays.

    Both arrays must be the same length. NaN values are excluded.

    Args:
        predicted: Model-predicted snow depth values (meters).
        observed: In-situ observed snow depth values (meters).

    Returns:
        ValidationMetrics with bias, RMSE, MAE, Pearson R, and sample count.
    """
    pred = np.asarray(predicted, dtype=np.float64)
    obs = np.asarray(observed, dtype=np.float64)

    # Remove NaN pairs
    valid = ~(np.isnan(pred) | np.isnan(obs))
    pred = pred[valid]
    obs = obs[valid]

    count = len(pred)
    if count == 0:
        return ValidationMetrics(bias=np.nan, rmse=np.nan, mae=np.nan, pearson_r=np.nan, count=0)

    diff = pred - obs
    bias = float(np.mean(diff))
    rmse = float(np.sqrt(np.mean(diff**2)))
    mae = float(np.mean(np.abs(diff)))

    if count < 2 or np.std(pred) == 0 or np.std(obs) == 0:
        pearson_r = np.nan
    else:
        pearson_r = float(np.corrcoef(pred, obs)[0, 1])

    return ValidationMetrics(bias=bias, rmse=rmse, mae=mae, pearson_r=pearson_r, count=count)


def scatter_plot(
    predicted: np.ndarray,
    observed: np.ndarray,
    title: str = "Validation Scatter Plot",
) -> Figure:
    """Create a scatter plot of predicted vs. observed snow depth.

    Returns a matplotlib Figure.
    """
    import matplotlib.pyplot as plt

    pred = np.asarray(predicted, dtype=np.float64)
    obs = np.asarray(observed, dtype=np.float64)
    valid = ~(np.isnan(pred) | np.isnan(obs))
    pred = pred[valid]
    obs = obs[valid]

    metrics = compute_metrics(pred, obs)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(obs, pred, alpha=0.5, s=10, edgecolors="none")

    # 1:1 line
    lim_max = max(obs.max(), pred.max()) * 1.1 if len(obs) > 0 else 1.0
    ax.plot([0, lim_max], [0, lim_max], "k--", linewidth=0.8, label="1:1")

    ax.set_xlabel("Observed Snow Depth (m)")
    ax.set_ylabel("Predicted Snow Depth (m)")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.set_xlim(0, lim_max)
    ax.set_ylim(0, lim_max)

    stats_text = (
        f"N = {metrics.count}\n"
        f"Bias = {metrics.bias:.3f} m\n"
        f"RMSE = {metrics.rmse:.3f} m\n"
        f"MAE = {metrics.mae:.3f} m\n"
        f"R = {metrics.pearson_r:.3f}"
    )
    ax.text(
        0.05,
        0.95,
        stats_text,
        transform=ax.transAxes,
        verticalalignment="top",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )

    plt.tight_layout()
    return fig
