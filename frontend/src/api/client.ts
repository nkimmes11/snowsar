import type {
  AlgorithmInfo,
  CompareRequest,
  ComparisonResponse,
  JobCreateRequest,
  JobResponse,
  PointSample,
  StationValidationRequest,
  TimeSeriesPoint,
  ValidationResponse,
} from "../types";

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

export interface TimeSeriesOptions {
  variable?: string;
  method?: "mean" | "median" | "max" | "min";
  valid_only?: boolean;
}

export function getTimeSeries(
  jobId: string,
  opts: TimeSeriesOptions = {},
): Promise<TimeSeriesPoint[]> {
  const params = new URLSearchParams();
  if (opts.variable) params.set("variable", opts.variable);
  if (opts.method) params.set("method", opts.method);
  if (opts.valid_only !== undefined) params.set("valid_only", String(opts.valid_only));
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<TimeSeriesPoint[]>(`/jobs/${jobId}/results/timeseries${suffix}`);
}

export function queryPoints(
  jobId: string,
  points: { lon: number; lat: number; id?: string }[],
  method: "nearest" | "linear" = "nearest",
): Promise<PointSample[]> {
  return request<PointSample[]>(`/jobs/${jobId}/results/points`, {
    method: "POST",
    body: JSON.stringify({ points, method }),
  });
}

export function validateSnotel(
  jobId: string,
  body: StationValidationRequest,
): Promise<ValidationResponse> {
  return request<ValidationResponse>(`/jobs/${jobId}/validation/snotel`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function validateGhcnd(
  jobId: string,
  body: StationValidationRequest,
): Promise<ValidationResponse> {
  return request<ValidationResponse>(`/jobs/${jobId}/validation/ghcnd`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function validateUpload(
  jobId: string,
  file: File,
  format: "csv" | "geojson",
  options: { max_distance_deg?: number; tolerance_days?: number } = {},
): Promise<ValidationResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("format", format);
  if (options.max_distance_deg !== undefined) {
    form.append("max_distance_deg", String(options.max_distance_deg));
  }
  if (options.tolerance_days !== undefined) {
    form.append("tolerance_days", String(options.tolerance_days));
  }
  const res = await fetch(`${BASE}/jobs/${jobId}/validation/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return (await res.json()) as ValidationResponse;
}

export function compareJobs(
  jobIdA: string,
  jobIdB: string,
  body: CompareRequest = {},
): Promise<ComparisonResponse> {
  return request<ComparisonResponse>(`/jobs/${jobIdA}/compare/${jobIdB}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function geotiffUrl(jobId: string, variable = "snow_depth"): string {
  return `${BASE}/jobs/${jobId}/results/geotiff?variable=${encodeURIComponent(variable)}`;
}

export function netcdfUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/results/netcdf`;
}
