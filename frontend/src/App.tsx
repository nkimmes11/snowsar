import { useState } from "react";
import { ControlPanel } from "./components/ControlPanel";
import { MapView } from "./components/MapView";
import { useJob } from "./hooks/useJob";
import type { BBox } from "./types";

export function App() {
  const [bbox, setBBox] = useState<BBox | null>(null);
  const { job, error, submitting, submit } = useJob();

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <ControlPanel
        bbox={bbox}
        onSubmit={submit}
        submitting={submitting}
        job={job}
        error={error}
      />
      <MapView bbox={bbox} onBBoxChange={setBBox} job={job} />
    </div>
  );
}
