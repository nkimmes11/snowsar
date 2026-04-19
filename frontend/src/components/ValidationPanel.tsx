import { useMemo, useState } from "react";
import type {
  BBox,
  JobResponse,
  ValidationResponse,
  ValidationSource,
} from "../types";
import type { RunStationArgs, RunUploadArgs } from "../hooks/useValidation";
import { Plot } from "./PlotlyChart";

interface Props {
  job: JobResponse | null;
  bbox: BBox | null;
  start: string;
  end: string;
  result: ValidationResponse | null;
  ranSource: ValidationSource | null;
  error: string | null;
  loading: boolean;
  onRunStation: (args: RunStationArgs) => void;
  onRunUpload: (args: RunUploadArgs) => void;
}

export function ValidationPanel({
  job,
  bbox,
  start,
  end,
  result,
  ranSource,
  error,
  loading,
  onRunStation,
  onRunUpload,
}: Props) {
  const [source, setSource] = useState<ValidationSource>("snotel");
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState<"csv" | "geojson">("csv");

  const jobReady = job?.status === "completed";

  const handleRun = () => {
    if (!jobReady || !job) return;
    if (source === "upload") {
      if (!file) return;
      onRunUpload({ jobId: job.job_id, file, format });
    } else {
      if (!bbox) return;
      onRunStation({ source, jobId: job.job_id, bbox, start, end });
    }
  };

  const scatter = useMemo(() => {
    if (!result?.pairs) return null;
    const obs = result.pairs.map((p) => p.observed_m);
    const pred = result.pairs.map((p) => p.predicted_m);
    const maxVal = Math.max(1, ...obs, ...pred);
    return { obs, pred, maxVal };
  }, [result]);

  if (!job) return <div style={{ color: "#6b7280", fontSize: 13 }}>Run a job first.</div>;
  if (!jobReady) {
    return (
      <div style={{ color: "#6b7280", fontSize: 13 }}>
        Validation available after the job completes.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <label style={{ fontSize: 13 }}>
        Source
        <select
          value={source}
          onChange={(e) => setSource(e.target.value as ValidationSource)}
          style={{ display: "block", width: "100%", marginTop: 2 }}
        >
          <option value="snotel">SNOTEL</option>
          <option value="ghcnd">GHCN-D</option>
          <option value="upload">User upload</option>
        </select>
      </label>

      {source === "upload" ? (
        <>
          <label style={{ fontSize: 13 }}>
            Format
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value as "csv" | "geojson")}
              style={{ display: "block", width: "100%", marginTop: 2 }}
            >
              <option value="csv">CSV</option>
              <option value="geojson">GeoJSON</option>
            </select>
          </label>
          <label style={{ fontSize: 13 }}>
            File
            <input
              type="file"
              accept={format === "csv" ? ".csv,text/csv" : ".geojson,.json,application/geo+json"}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              style={{ display: "block", width: "100%", marginTop: 2 }}
            />
          </label>
        </>
      ) : (
        <div style={{ fontSize: 12, color: "#6b7280" }}>
          Uses the AOI and date range from the retrieval job.
        </div>
      )}

      <button
        type="button"
        onClick={handleRun}
        disabled={loading || (source !== "upload" && !bbox) || (source === "upload" && !file)}
        style={{
          padding: "6px 12px",
          background: loading ? "#9ca3af" : "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: loading ? "wait" : "pointer",
          fontWeight: 600,
          fontSize: 13,
        }}
      >
        {loading ? "Running…" : "Run validation"}
      </button>

      {error && <div style={{ color: "#b91c1c", fontSize: 13 }}>{error}</div>}

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            Source: {ranSource} · stations: {result.stations_found} · obs: {result.observations_found} · matched: {result.matched_count}
          </div>
          <table style={{ fontSize: 12, borderCollapse: "collapse" }}>
            <tbody>
              {Object.entries(result.metrics).map(([k, v]) => (
                <tr key={k}>
                  <td style={{ padding: "2px 8px 2px 0", color: "#6b7280" }}>{k}</td>
                  <td style={{ fontFamily: "monospace" }}>
                    {typeof v === "number" && Number.isFinite(v) ? v.toFixed(4) : String(v)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {scatter && scatter.obs.length > 0 && (
            <Plot
              data={[
                {
                  type: "scatter",
                  mode: "markers",
                  x: scatter.obs,
                  y: scatter.pred,
                  marker: { color: "#2563eb", size: 6 },
                  name: "pairs",
                },
                {
                  type: "scatter",
                  mode: "lines",
                  x: [0, scatter.maxVal],
                  y: [0, scatter.maxVal],
                  line: { color: "#9ca3af", dash: "dash" },
                  name: "1:1",
                },
              ]}
              layout={{
                autosize: true,
                height: 300,
                margin: { l: 50, r: 10, t: 10, b: 40 },
                xaxis: { title: { text: "observed (m)" } },
                yaxis: { title: { text: "predicted (m)" } },
                showlegend: false,
              }}
              config={{ responsive: true, displaylogo: false }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          )}
        </div>
      )}
    </div>
  );
}
