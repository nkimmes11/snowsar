import type { AlgorithmInfo, JobCreateRequest, JobResponse } from "../types";

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function createJob(body: JobCreateRequest): Promise<JobResponse> {
  return request<JobResponse>("/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getJob(jobId: string): Promise<JobResponse> {
  return request<JobResponse>(`/jobs/${jobId}`);
}

export function listAlgorithms(): Promise<AlgorithmInfo[]> {
  return request<AlgorithmInfo[]>("/algorithms");
}
