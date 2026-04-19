import { useState } from "react";
import { useComparison } from "../hooks/useComparison";
import type { JobResponse } from "../types";

interface Props {
  job: JobResponse | null;
  showDiffOverlay: boolean;
  onToggleDiffOverlay: (value: boolean) => void;
}

export function ComparisonPanel({ job, showDiffOverlay, onToggleDiffOverlay }: Props) {
  const [otherJobId, setOtherJobId] = useState("");
  const [returnMap, setReturnMap] = useState(false);
  const [validOnly, setValidOnly] = useState(true);
  const [tolerance, setTolerance] = useState(0.1);
  const { result, error, loading, run } = useComparison();

  const jobReady = job?.status === "completed";

  const handleRun = () => {
    if (!jobReady || !job || !otherJobId) return;
    void run(job.job_id, otherJobId, {
      valid_only: validOnly,
      agreement_tolerance_m: tolerance,
      return_difference_map: returnMap,
    });
  };

  if (!job) return <div style={{ color: "#6b7280", fontSize: 13 }}>Run a job first.</div>;
  if (!jobReady) {
    return (
      <div style={{ color: "#6b7280", fontSize: 13 }}>
        Comparison available after the job completes.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <label style={{ fontSize: 13 }}>
        Other job ID
        <input
          type="text"
          value={otherJobId}
          onChange={(e) => setOtherJobId(e.target.value)}
          placeholder="job-id to compare against"
          style={{ display: "block", width: "100%", marginTop: 2 }}
        />
      </label>
      <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
        <input
          type="checkbox"
          checked={validOnly}
          onChange={(e) => setValidOnly(e.target.checked)}
        />
        VALID pixels only
      </label>
      <label style={{ fontSize: 13 }}>
        Agreement tolerance (m)
        <input
          type="number"
          step="0.01"
          min={0}
          value={tolerance}
          onChange={(e) => setTolerance(Number(e.target.value))}
          style={{ display: "block", width: "100%", marginTop: 2 }}
        />
      </label>
      <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
        <input
          type="checkbox"
          checked={returnMap}
          onChange={(e) => setReturnMap(e.target.checked)}
        />
        Return difference map
      </label>

      <button
        type="button"
        onClick={handleRun}
        disabled={loading || !otherJobId}
        style={{
          padding: "6px 12px",
          background: loading || !otherJobId ? "#9ca3af" : "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: loading || !otherJobId ? "not-allowed" : "pointer",
          fontWeight: 600,
          fontSize: 13,
        }}
      >
        {loading ? "Comparing…" : "Compare"}
      </button>

      {error && <div style={{ color: "#b91c1c", fontSize: 13 }}>{error}</div>}

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            {result.job_a} vs {result.job_b} · variable: {result.variable}
          </div>
          <table style={{ fontSize: 12, borderCollapse: "collapse" }}>
            <tbody>
              {Object.entries(result.stats).map(([k, v]) => (
                <tr key={k}>
                  <td style={{ padding: "2px 8px 2px 0", color: "#6b7280" }}>{k}</td>
                  <td style={{ fontFamily: "monospace" }}>
                    {typeof v === "number" && Number.isFinite(v) ? v.toFixed(4) : String(v)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.difference_map && (
            <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={showDiffOverlay}
                onChange={(e) => onToggleDiffOverlay(e.target.checked)}
              />
              Show difference-map overlay (shape: {result.difference_map.shape.join("×")})
            </label>
          )}
        </div>
      )}
    </div>
  );
}
