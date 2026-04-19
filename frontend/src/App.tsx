import { useState } from "react";
import { ComparisonPanel } from "./components/ComparisonPanel";
import { ControlPanel } from "./components/ControlPanel";
import { ExportPanel } from "./components/ExportPanel";
import { MapView } from "./components/MapView";
import { Tabs, type TabDef } from "./components/Tabs";
import { TimeSeriesChart } from "./components/TimeSeriesChart";
import { ValidationPanel } from "./components/ValidationPanel";
import { useJob } from "./hooks/useJob";
import { useTimeSeries } from "./hooks/useTimeSeries";
import { useValidation } from "./hooks/useValidation";
import type { BBox, JobCreateRequest } from "./types";

export function App() {
  const [bbox, setBBox] = useState<BBox | null>(null);
  const [queryPoint, setQueryPoint] = useState<{ lat: number; lon: number } | null>(null);
  const [activeTab, setActiveTab] = useState<string>("config");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-01-31");
  const [showDiffOverlay, setShowDiffOverlay] = useState(false);

  const { job, error, submitting, submit } = useJob();

  const completedJobId = job?.status === "completed" ? job.job_id : null;
  const timeSeries = useTimeSeries(completedJobId);
  const validation = useValidation();

  const handleSubmit = (req: JobCreateRequest) => {
    setStartDate(req.start_date);
    setEndDate(req.end_date);
    submit(req);
  };

  const tabs: TabDef[] = [
    {
      id: "config",
      label: "Config",
      content: (
        <ControlPanel
          bbox={bbox}
          onSubmit={handleSubmit}
          submitting={submitting}
          job={job}
          error={error}
        />
      ),
    },
    {
      id: "timeseries",
      label: "Time-Series",
      content: (
        <TimeSeriesChart
          job={job}
          queryPoint={queryPoint}
          data={timeSeries.data}
          loading={timeSeries.loading}
          error={timeSeries.error}
        />
      ),
    },
    {
      id: "validation",
      label: "Validation",
      content: (
        <ValidationPanel
          job={job}
          bbox={bbox}
          start={startDate}
          end={endDate}
          result={validation.result}
          ranSource={validation.source}
          error={validation.error}
          loading={validation.loading}
          onRunStation={validation.runStation}
          onRunUpload={validation.runUpload}
        />
      ),
    },
    {
      id: "comparison",
      label: "Comparison",
      content: (
        <ComparisonPanel
          job={job}
          showDiffOverlay={showDiffOverlay}
          onToggleDiffOverlay={setShowDiffOverlay}
        />
      ),
    },
    {
      id: "export",
      label: "Export",
      content: (
        <ExportPanel
          job={job}
          timeSeries={timeSeries.data}
          validationPairs={validation.result?.pairs ?? null}
        />
      ),
    },
  ];

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <div
        style={{
          width: 360,
          background: "#fff",
          borderRight: "1px solid #e5e7eb",
          display: "flex",
          flexDirection: "column",
          minHeight: 0,
        }}
      >
        <div style={{ padding: "10px 12px", borderBottom: "1px solid #e5e7eb" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>SnowSAR</h2>
        </div>
        <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
      </div>
      <MapView
        bbox={bbox}
        onBBoxChange={setBBox}
        job={job}
        queryPoint={queryPoint}
        onQueryPoint={setQueryPoint}
        showDiffOverlay={showDiffOverlay}
      />
    </div>
  );
}
