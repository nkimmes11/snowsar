"""Tests for validation metrics."""

from __future__ import annotations

import numpy as np
import pytest

from snowsar.validation.metrics import ValidationMetrics, compute_metrics, scatter_plot


class TestComputeMetrics:
    def test_perfect_predictions(self) -> None:
        pred = np.array([1.0, 2.0, 3.0])
        obs = np.array([1.0, 2.0, 3.0])
        m = compute_metrics(pred, obs)
        assert m.bias == pytest.approx(0.0)
        assert m.rmse == pytest.approx(0.0)
        assert m.mae == pytest.approx(0.0)
        assert m.pearson_r == pytest.approx(1.0)
        assert m.count == 3

    def test_constant_bias(self) -> None:
        pred = np.array([2.0, 3.0, 4.0])
        obs = np.array([1.0, 2.0, 3.0])
        m = compute_metrics(pred, obs)
        assert m.bias == pytest.approx(1.0)
        assert m.rmse == pytest.approx(1.0)
        assert m.mae == pytest.approx(1.0)
        assert m.pearson_r == pytest.approx(1.0)

    def test_nan_handling(self) -> None:
        pred = np.array([1.0, np.nan, 3.0])
        obs = np.array([1.0, 2.0, 3.0])
        m = compute_metrics(pred, obs)
        assert m.count == 2

    def test_empty_after_nan_removal(self) -> None:
        pred = np.array([np.nan, np.nan])
        obs = np.array([1.0, 2.0])
        m = compute_metrics(pred, obs)
        assert m.count == 0
        assert np.isnan(m.bias)

    def test_to_dict(self) -> None:
        m = ValidationMetrics(bias=0.1, rmse=0.5, mae=0.3, pearson_r=0.9, count=10)
        d = m.to_dict()
        assert d["bias"] == 0.1
        assert d["count"] == 10


class TestScatterPlot:
    def test_creates_figure(self) -> None:
        pred = np.array([1.0, 2.0, 3.0, 4.0])
        obs = np.array([1.1, 2.2, 2.8, 4.1])
        fig = scatter_plot(pred, obs, title="Test")
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)
