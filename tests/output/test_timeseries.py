"""Tests for the time-series aggregation helper."""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from snowsar.exceptions import AlgorithmError
from snowsar.output.timeseries import extract_timeseries


class TestExtractTimeseries:
    def test_one_row_per_timestep(self, synthetic_result_dataset: xr.Dataset) -> None:
        df = extract_timeseries(synthetic_result_dataset)
        assert len(df) == synthetic_result_dataset.sizes["time"]
        assert list(df.columns) == ["value", "std", "n_valid", "n_total"]

    def test_valid_only_excludes_flagged_pixels(self, synthetic_result_dataset: xr.Dataset) -> None:
        df_valid = extract_timeseries(synthetic_result_dataset, valid_only=True)
        df_all = extract_timeseries(synthetic_result_dataset, valid_only=False)
        # First timestep has 1 flagged pixel (INSUFFICIENT_SAR at [0,0,0]) — also NaN
        # Second timestep has 1 WET_SNOW at [1,2,2]
        assert int(df_valid.iloc[1]["n_valid"]) < int(df_all.iloc[1]["n_valid"])

    def test_mean_matches_numpy_over_valid_pixels(
        self, synthetic_result_dataset: xr.Dataset
    ) -> None:
        df = extract_timeseries(synthetic_result_dataset, valid_only=False)
        for i in range(synthetic_result_dataset.sizes["time"]):
            expected = float(np.nanmean(synthetic_result_dataset["snow_depth"].isel(time=i).values))
            assert df.iloc[i]["value"] == pytest.approx(expected, rel=1e-5)

    def test_median_method(self, synthetic_result_dataset: xr.Dataset) -> None:
        df = extract_timeseries(synthetic_result_dataset, method="median")
        assert len(df) == synthetic_result_dataset.sizes["time"]
        assert "value" in df.columns

    def test_max_min_methods(self, synthetic_result_dataset: xr.Dataset) -> None:
        df_max = extract_timeseries(synthetic_result_dataset, method="max")
        df_min = extract_timeseries(synthetic_result_dataset, method="min")
        assert (df_max["value"].values >= df_min["value"].values).all()

    def test_missing_variable_raises(self, synthetic_result_dataset: xr.Dataset) -> None:
        with pytest.raises(AlgorithmError, match="not found"):
            extract_timeseries(synthetic_result_dataset, variable="nope")

    def test_no_time_dim_raises(self, synthetic_result_dataset: xr.Dataset) -> None:
        ds = synthetic_result_dataset.isel(time=0, drop=True)
        with pytest.raises(AlgorithmError, match="no time dimension"):
            extract_timeseries(ds)

    def test_n_total_equals_grid_size(self, synthetic_result_dataset: xr.Dataset) -> None:
        ny = synthetic_result_dataset.sizes["y"]
        nx = synthetic_result_dataset.sizes["x"]
        df = extract_timeseries(synthetic_result_dataset)
        assert (df["n_total"] == ny * nx).all()
