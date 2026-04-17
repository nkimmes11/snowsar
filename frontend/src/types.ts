/** Bounding box in lon/lat (EPSG:4326). */
export interface BBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

/** Request body for POST /api/v1/jobs. */
export interface JobCreateRequest {
  bbox: BBox;
  start_date: string;
  end_date: string;
  algorithms: string[];
  backend: "gee" | "local";
  resolution_m?: number;
}

/** Response from GET /api/v1/jobs/{id}. */
export interface JobResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  algorithms: string[];
  backend: string;
  created_at: string;
  message?: string;
}

/** Algorithm metadata from GET /api/v1/algorithms. */
export interface AlgorithmInfo {
  id: string;
  name: string;
  description: string;
}
