import { useMemo } from "react";
import type { JobResponse, TimeSeriesPoint } from "../types";
import { Plot } from "./PlotlyChart";

interface Props {
  job: JobResponse | null;
  queryPoint: { lat: number; lon: number } | null;
  data: TimeSeriesPoint[] | null;
  loading: boolean;
  error: string | null;
}

function extractSeries(points: TimeSeriesPoint[]): {
  x: string[];
  y: number[];
  nValid: number[];
} {
  // The /results/timeseries endpoint returns aggregated statistics
  // with columns {time, value, std, n_valid, n_total} — "value" is the
  // spatial aggregate of the requested variable (snow_depth by default).
  const x: string[] = [];
  const y: number[] = [];
  const nValid: number[] = [];
  for (const row of points) {
    const value = row.value;
    if (typeof value === "number" && Number.isFinite(value)) {
      x.push(String(row.time));
      y.push(value);
      const nv = row.n_valid;
      nValid.push(typeof nv === "number" ? nv : 0);
    }
  }
  return { x, y, nValid };
}

export function TimeSeriesChart({ job, queryPoint, data, loading, error }: Props) {
  const traces = useMemo(() => {
    if (!data) return [];
    const { x, y } = extractSeries(data);
    return [
      {
        type: "scatter" as const,
        mode: "lines+markers" as const,
        x,
        y,
        name: "snow depth (AOI aggregate)",
        line: { color: "#2563eb" },
      },
    ];
  }, [data]);

  if (!job) {
    return <div style={{ color: "#6b7280", fontSize: 13 }}>Run a job first.</div>;
  }
  if (job.status !== "completed") {
    return (
      <div style={{ color: "#6b7280", fontSize: 13 }}>
        Time-series available after the job completes.
      </div>
    );
  }
  if (loading) return <div style={{ fontSize: 13 }}>Loading time-series…</div>;
  if (error) return <div style={{ color: "#b91c1c", fontSize: 13 }}>{error}</div>;
  if (!data || data.length === 0) {
    return <div style={{ color: "#6b7280", fontSize: 13 }}>No data.</div>;
  }

  return (
    <div>
      {queryPoint && (
        <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 6 }}>
          Query point: {queryPoint.lat.toFixed(4)}, {queryPoint.lon.toFixed(4)}
          {" — "}
          showing AOI-mean series (per-pixel query uses /results/points).
        </div>
      )}
      <Plot
        data={traces}
        layout={{
          autosize: true,
          height: 320,
          margin: { l: 40, r: 10, t: 10, b: 40 },
          xaxis: { title: { text: "time" } },
          yaxis: { title: { text: "snow depth (m)" } },
          showlegend: false,
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
