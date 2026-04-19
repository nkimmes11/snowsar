import { geotiffUrl, netcdfUrl } from "../api/client";
import type { JobResponse, TimeSeriesPoint, ValidationPair } from "../types";

interface Props {
  job: JobResponse | null;
  timeSeries: TimeSeriesPoint[] | null;
  validationPairs: ValidationPair[] | null;
}

function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const keys = Array.from(
    rows.reduce<Set<string>>((acc, row) => {
      for (const k of Object.keys(row)) acc.add(k);
      return acc;
    }, new Set<string>()),
  );
  const escape = (value: unknown): string => {
    if (value === null || value === undefined) return "";
    const s = String(value);
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const header = keys.join(",");
  const body = rows.map((r) => keys.map((k) => escape(r[k])).join(",")).join("\n");
  return `${header}\n${body}\n`;
}

function downloadBlob(content: string, filename: string, mime = "text/csv") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const buttonStyle = (disabled: boolean): React.CSSProperties => ({
  padding: "6px 12px",
  background: disabled ? "#e5e7eb" : "#2563eb",
  color: disabled ? "#6b7280" : "#fff",
  border: "none",
  borderRadius: 4,
  cursor: disabled ? "not-allowed" : "pointer",
  fontSize: 13,
  fontWeight: 600,
  textDecoration: "none",
  display: "inline-block",
  textAlign: "center",
});

export function ExportPanel({ job, timeSeries, validationPairs }: Props) {
  const jobReady = job?.status === "completed";
  if (!jobReady || !job) {
    return (
      <div style={{ color: "#6b7280", fontSize: 13 }}>
        Export available after the job completes.
      </div>
    );
  }

  const handleTimeSeriesExport = () => {
    if (!timeSeries || timeSeries.length === 0) return;
    downloadBlob(
      toCsv(timeSeries as unknown as Record<string, unknown>[]),
      `${job.job_id}_timeseries.csv`,
    );
  };

  const handlePairsExport = () => {
    if (!validationPairs || validationPairs.length === 0) return;
    downloadBlob(
      toCsv(validationPairs as unknown as Record<string, unknown>[]),
      `${job.job_id}_validation.csv`,
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <a
        href={geotiffUrl(job.job_id)}
        style={buttonStyle(false)}
        download
      >
        Download GeoTIFF
      </a>
      <a
        href={netcdfUrl(job.job_id)}
        style={buttonStyle(false)}
        download
      >
        Download NetCDF
      </a>
      <button
        type="button"
        onClick={handleTimeSeriesExport}
        disabled={!timeSeries || timeSeries.length === 0}
        style={buttonStyle(!timeSeries || timeSeries.length === 0)}
      >
        Export time-series CSV
      </button>
      <button
        type="button"
        onClick={handlePairsExport}
        disabled={!validationPairs || validationPairs.length === 0}
        style={buttonStyle(!validationPairs || validationPairs.length === 0)}
      >
        Export validation pairs CSV
      </button>
    </div>
  );
}
