import { useCallback, useEffect, useRef, useState } from "react";
import { createJob, getJob } from "../api/client";
import type { JobCreateRequest, JobResponse } from "../types";

const POLL_INTERVAL_MS = 3000;

export function useJob() {
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(
    (jobId: string) => {
      stopPolling();
      timerRef.current = setInterval(async () => {
        try {
          const updated = await getJob(jobId);
          setJob(updated);
          if (updated.status === "completed" || updated.status === "failed") {
            stopPolling();
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "Polling failed");
          stopPolling();
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling],
  );

  const submit = useCallback(
    async (req: JobCreateRequest) => {
      setError(null);
      setSubmitting(true);
      try {
        const created = await createJob(req);
        setJob(created);
        if (created.status === "pending" || created.status === "running") {
          poll(created.job_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Submission failed");
      } finally {
        setSubmitting(false);
      }
    },
    [poll],
  );

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return { job, error, submitting, submit };
}
