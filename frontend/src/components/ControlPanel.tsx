import { useEffect, useState } from "react";
import { listAlgorithms } from "../api/client";
import type { AlgorithmInfo, BBox, JobCreateRequest } from "../types";
import { JobStatus } from "./JobStatus";

interface ControlPanelProps {
  bbox: BBox | null;
  onSubmit: (req: JobCreateRequest) => void;
  submitting: boolean;
  job: import("../types").JobResponse | null;
  error: string | null;
}

export function ControlPanel({ bbox, onSubmit, submitting, job, error }: ControlPanelProps) {
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-01-31");
  const [algorithm, setAlgorithm] = useState("lievens");
  const [backend, setBackend] = useState<"gee" | "local">("gee");
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[]>([]);

  useEffect(() => {
    listAlgorithms()
      .then(setAlgorithms)
      .catch(() => {
        setAlgorithms([
          { id: "lievens", name: "Lievens", description: "" },
          { id: "dprse", name: "DpRSE", description: "" },
        ]);
      });
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bbox) return;
    onSubmit({
      bbox,
      start_date: startDate,
      end_date: endDate,
      algorithms: [algorithm],
      backend,
    });
  };

  return (
    <div
      style={{
        width: 320,
        padding: 16,
        background: "#fff",
        borderRight: "1px solid #e5e7eb",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        overflowY: "auto",
      }}
    >
      <h2 style={{ margin: 0, fontSize: 18 }}>SnowSAR</h2>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <fieldset style={{ border: "1px solid #e5e7eb", borderRadius: 4, padding: 10 }}>
          <legend style={{ fontSize: 13, fontWeight: 600 }}>Area of Interest</legend>
          {bbox ? (
            <div style={{ fontSize: 12, fontFamily: "monospace" }}>
              W: {bbox.west.toFixed(4)}, S: {bbox.south.toFixed(4)}
              <br />
              E: {bbox.east.toFixed(4)}, N: {bbox.north.toFixed(4)}
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "#9ca3af" }}>Draw a rectangle on the map</div>
          )}
        </fieldset>

        <label style={{ fontSize: 13 }}>
          Start Date
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 2 }}
          />
        </label>

        <label style={{ fontSize: 13 }}>
          End Date
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 2 }}
          />
        </label>

        <label style={{ fontSize: 13 }}>
          Algorithm
          <select
            value={algorithm}
            onChange={(e) => setAlgorithm(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 2 }}
          >
            {algorithms.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>

        <label style={{ fontSize: 13 }}>
          Backend
          <select
            value={backend}
            onChange={(e) => setBackend(e.target.value as "gee" | "local")}
            style={{ display: "block", width: "100%", marginTop: 2 }}
          >
            <option value="gee">Google Earth Engine</option>
            <option value="local">Local (ASF)</option>
          </select>
        </label>

        <button
          type="submit"
          disabled={!bbox || submitting}
          style={{
            padding: "8px 16px",
            background: !bbox || submitting ? "#9ca3af" : "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: !bbox || submitting ? "not-allowed" : "pointer",
            fontWeight: 600,
          }}
        >
          {submitting ? "Submitting..." : "Run Retrieval"}
        </button>
      </form>

      <JobStatus job={job} error={error} />
    </div>
  );
}
