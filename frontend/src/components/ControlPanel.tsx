import { useEffect, useState } from "react";
import { listAlgorithms } from "../api/client";
import type {
  AlgorithmInfo,
  AlgorithmParamsMap,
  BBox,
  JobCreateRequest,
  JobResponse,
} from "../types";
import { AlgorithmParams } from "./AlgorithmParams";
import { JobStatus } from "./JobStatus";

interface ControlPanelProps {
  bbox: BBox | null;
  onSubmit: (req: JobCreateRequest) => void;
  submitting: boolean;
  job: JobResponse | null;
  error: string | null;
}

const DEFAULT_ALGOS: AlgorithmInfo[] = [
  { id: "lievens", name: "Lievens", description: "" },
  { id: "dprse", name: "DpRSE", description: "" },
  { id: "ml", name: "ML (experimental)", description: "" },
];

export function ControlPanel({ bbox, onSubmit, submitting, job, error }: ControlPanelProps) {
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-01-31");
  const [selected, setSelected] = useState<Set<string>>(new Set(["lievens"]));
  const [backend, setBackend] = useState<"gee" | "local" | "fixture">("fixture");
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[]>(DEFAULT_ALGOS);
  const [params, setParams] = useState<AlgorithmParamsMap>({});

  useEffect(() => {
    listAlgorithms()
      .then((list) => {
        if (list.length > 0) setAlgorithms(list);
      })
      .catch(() => {
        // keep defaults
      });
  }, []);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bbox || selected.size === 0) return;
    const selectedIds = [...selected];
    const activeParams: AlgorithmParamsMap = {};
    for (const id of selectedIds) {
      if (id === "lievens" && params.lievens) activeParams.lievens = params.lievens;
      if (id === "dprse" && params.dprse) activeParams.dprse = params.dprse;
      if (id === "ml" && params.ml) activeParams.ml = params.ml;
    }
    onSubmit({
      bbox,
      start_date: startDate,
      end_date: endDate,
      algorithms: selectedIds,
      backend,
      ...(Object.keys(activeParams).length > 0 ? { algorithm_params: activeParams } : {}),
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
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
            <div style={{ fontSize: 13, color: "#9ca3af" }}>
              Shift+drag on the map to draw
            </div>
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

        <fieldset style={{ border: "1px solid #e5e7eb", borderRadius: 4, padding: 10 }}>
          <legend style={{ fontSize: 13, fontWeight: 600 }}>Algorithms</legend>
          {algorithms.map((a) => (
            <label
              key={a.id}
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
            >
              <input
                type="checkbox"
                checked={selected.has(a.id)}
                onChange={() => toggle(a.id)}
              />
              {a.name}
            </label>
          ))}
          {[...selected].map((id) => (
            <AlgorithmParams
              key={id}
              algorithmId={id}
              params={params}
              onChange={setParams}
            />
          ))}
        </fieldset>

        <label style={{ fontSize: 13 }}>
          Backend
          <select
            value={backend}
            onChange={(e) => setBackend(e.target.value as "gee" | "local" | "fixture")}
            style={{ display: "block", width: "100%", marginTop: 2 }}
          >
            <option value="gee">Google Earth Engine</option>
            <option value="local">Local (ASF)</option>
            <option value="fixture">Fixture (synthetic, dev only)</option>
          </select>
        </label>

        <button
          type="submit"
          disabled={!bbox || selected.size === 0 || submitting}
          style={{
            padding: "8px 16px",
            background:
              !bbox || selected.size === 0 || submitting ? "#9ca3af" : "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor:
              !bbox || selected.size === 0 || submitting ? "not-allowed" : "pointer",
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
