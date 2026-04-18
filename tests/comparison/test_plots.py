"""Tests for comparison plotting helpers (figure factories)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import xarray as xr

from snowsar.comparison.plots import difference_map_plot, taylor_diagram


class TestDifferenceMapPlot:
    def test_returns_figure(self, ds_a: xr.Dataset, ds_b: xr.Dataset) -> None:
        fig = difference_map_plot(ds_a, ds_b)
        assert fig is not None
        plt.close(fig)

    def test_accepts_time_index(self, ds_a: xr.Dataset, ds_b: xr.Dataset) -> None:
        fig = difference_map_plot(ds_a, ds_b, time_index=0)
        assert fig is not None
        plt.close(fig)


class TestTaylorDiagram:
    def test_returns_figure(
        self, ds_a: xr.Dataset, ds_b: xr.Dataset, ds_identical_to_a: xr.Dataset
    ) -> None:
        fig = taylor_diagram(ds_a, {"A_again": ds_identical_to_a, "B": ds_b})
        assert fig is not None
        plt.close(fig)
