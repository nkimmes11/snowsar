import { useCallback, useState } from "react";
import { compareJobs } from "../api/client";
import type { CompareRequest, ComparisonResponse } from "../types";

export function useComparison() {
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(
    async (jobA: string, jobB: string, body: CompareRequest = {}) => {
      setLoading(true);
      setError(null);
      try {
        const res = await compareJobs(jobA, jobB, body);
        setResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Comparison failed");
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, error, loading, run, clear };
}
