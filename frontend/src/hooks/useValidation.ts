import { useCallback, useState } from "react";
import {
  validateGhcnd,
  validateSnotel,
  validateUpload,
} from "../api/client";
import type {
  BBox,
  StationValidationRequest,
  ValidationResponse,
  ValidationSource,
} from "../types";

export interface RunStationArgs {
  source: "snotel" | "ghcnd";
  jobId: string;
  bbox: BBox;
  start: string;
  end: string;
}

export interface RunUploadArgs {
  jobId: string;
  file: File;
  format: "csv" | "geojson";
}

export function useValidation() {
  const [result, setResult] = useState<ValidationResponse | null>(null);
  const [source, setSource] = useState<ValidationSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const runStation = useCallback(async (args: RunStationArgs) => {
    setLoading(true);
    setError(null);
    try {
      const body: StationValidationRequest = {
        bbox: args.bbox,
        date_range: { start: args.start, end: args.end },
      };
      const res =
        args.source === "snotel"
          ? await validateSnotel(args.jobId, body)
          : await validateGhcnd(args.jobId, body);
      setResult(res);
      setSource(args.source);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const runUpload = useCallback(async (args: RunUploadArgs) => {
    setLoading(true);
    setError(null);
    try {
      const res = await validateUpload(args.jobId, args.file, args.format);
      setResult(res);
      setSource("upload");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, source, error, loading, runStation, runUpload };
}
