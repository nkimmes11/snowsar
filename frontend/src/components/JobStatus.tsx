import type { JobResponse } from "../types";

interface JobStatusProps {
  job: JobResponse | null;
  error: string | null;
}

const STATUS_STYLES: Record<string, { color: string; label: string }> = {
  pending: { color: "#f59e0b", label: "Pending" },
  running: { color: "#3b82f6", label: "Running..." },
  completed: { color: "#10b981", label: "Completed" },
  failed: { color: "#ef4444", label: "Failed" },
};

export function JobStatus({ job, error }: JobStatusProps) {
  if (error) {
    return (
      <div style={{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 4 }}>
        <strong>Error:</strong> {error}
      </div>
    );
  }

  if (!job) return null;

  const style = STATUS_STYLES[job.status] ?? STATUS_STYLES.pending;

  return (
    <div style={{ padding: "8px 12px", background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 4 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: style.color,
            display: "inline-block",
          }}
        />
        <strong>{style.label}</strong>
      </div>
      <div style={{ fontSize: 13, color: "#6b7280" }}>
        Job: {job.job_id}
        <br />
        Algorithms: {job.algorithms.join(", ")}
        {job.message && (
          <>
            <br />
            {job.message}
          </>
        )}
      </div>
      {job.error_message && (
        <pre
          style={{
            marginTop: 6,
            padding: "6px 8px",
            fontSize: 11,
            fontFamily: "monospace",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 4,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            maxHeight: 180,
            overflowY: "auto",
            color: "#7f1d1d",
          }}
        >
          {job.error_message}
        </pre>
      )}
    </div>
  );
}
