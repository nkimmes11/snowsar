/** Bounding box in lon/lat (EPSG:4326). */
export interface BBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface LievensParams {
  coefficient_a: number;
  coefficient_b: number;
  coefficient_c: number;
  use_fcf_weighting: boolean;
  temporal_window_days: number;
}

export interface DpRSEParams {
  use_land_cover_mask: boolean;
  mask_forest: boolean;
}

export interface MLParams {
  model_id: string;
}

export type AlgorithmParamsMap = Partial<{
  lievens: LievensParams;
  dprse: DpRSEParams;
  ml: MLParams;
}>;

/** Request body for POST /api/v1/jobs. */
export interface JobCreateRequest {
  bbox: BBox;
  start_date: string;
  end_date: string;
  algorithms: string[];
  backend: "gee" | "local" | "fixture";
  resolution_m?: number;
  algorithm_params?: AlgorithmParamsMap;
}

/** Response from GET /api/v1/jobs/{id}. */
export interface JobResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  algorithms: string[];
  backend: string;
  created_at: string;
  updated_at?: string | null;
  error_message?: string | null;
  message?: string;
}

/** Algorithm metadata from GET /api/v1/algorithms. */
export interface AlgorithmInfo {
  id: string;
  name: string;
  description: string;
}

/** Row returned by GET /jobs/{id}/results/timeseries.
 *
 * Produced by extract_timeseries() which aggregates the requested variable
 * over the spatial dims and reports: value (mean/median/max/min), std,
 * n_valid (non-NaN pixel count), n_total (grid-cell count).
 */
export interface TimeSeriesPoint {
  time: string;
  value: number | null;
  std: number | null;
  n_valid: number | null;
  n_total: number | null;
}

/** Single point of a point-query (POST /jobs/{id}/results/points). */
export interface PointSample {
  id?: string | null;
  lon: number;
  lat: number;
  [variable: string]: string | number | null | undefined;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface StationValidationRequest {
  bbox: BBox;
  date_range: DateRange;
  max_distance_deg?: number;
  tolerance_days?: number;
}

export interface ValidationMetrics {
  count: number;
  bias: number;
  mae: number;
  rmse: number;
  pearson_r: number;
}

export interface ValidationPair {
  station_id: string;
  obs_date: string | null;
  observed_m: number;
  predicted_m: number;
}

export interface ValidationResponse {
  metrics: ValidationMetrics;
  matched_count: number;
  stations_found: number;
  observations_found: number;
  pairs?: ValidationPair[];
}

export type ValidationSource = "snotel" | "ghcnd" | "upload";

export interface CompareRequest {
  variable?: string;
  valid_only?: boolean;
  agreement_tolerance_m?: number;
  return_difference_map?: boolean;
}

export interface ComparisonStats {
  count: number;
  bias: number;
  rmse: number;
  mae: number;
  pearson_r: number;
  std_ratio: number;
  agreement_rate: number;
}

export interface DifferenceMap {
  shape: number[];
  dims: string[];
  values: number[] | number[][] | number[][][];
}

export interface ComparisonResponse {
  job_a: string;
  job_b: string;
  variable: string;
  stats: ComparisonStats;
  difference_map?: DifferenceMap;
}
