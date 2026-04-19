import { useCallback, useEffect, useState } from "react";
import { getTimeSeries } from "../api/client";
import type { TimeSeriesPoint } from "../types";

export function useTimeSeries(jobId: string | null) {
  const [data, setData] = useState<TimeSeriesPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getTimeSeries(jobId, { variable: "snow_depth", method: "mean" });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch time-series");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (jobId) {
      void fetchData();
    } else {
      setData(null);
      setError(null);
    }
  }, [jobId, fetchData]);

  return { data, error, loading, refresh: fetchData };
}
