import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ValidationPanel } from "../ValidationPanel";
import type { BBox, JobResponse } from "../../types";

// Plotly imports a heavy browser runtime that jsdom doesn't love; stub it.
vi.mock("../PlotlyChart", () => ({
  Plot: () => null,
}));

const BBOX: BBox = { west: -120.5, south: 37.5, east: -120.0, north: 38.0 };
const JOB: JobResponse = {
  job_id: "job-xyz",
  status: "completed",
  algorithms: ["lievens"],
  backend: "gee",
  created_at: "2024-01-01T00:00:00Z",
};

function renderPanel(overrides: Partial<Parameters<typeof ValidationPanel>[0]> = {}) {
  const props: Parameters<typeof ValidationPanel>[0] = {
    job: JOB,
    bbox: BBOX,
    start: "2024-01-01",
    end: "2024-01-31",
    result: null,
    ranSource: null,
    error: null,
    loading: false,
    onRunStation: vi.fn(),
    onRunUpload: vi.fn(),
    ...overrides,
  };
  return { props, utils: render(<ValidationPanel {...props} />) };
}

describe("ValidationPanel", () => {
  it("reveals upload controls when source=upload", async () => {
    const user = userEvent.setup();
    renderPanel();
    const sourceSelect = screen.getByLabelText(/source/i);
    await user.selectOptions(sourceSelect, "upload");
    expect(screen.getByLabelText(/format/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^file$/i)).toBeInTheDocument();
  });

  it("disables run when bbox is missing for station sources", () => {
    renderPanel({ bbox: null });
    const button = screen.getByRole("button", { name: /run validation/i });
    expect(button).toBeDisabled();
  });

  it("calls onRunStation with the expected payload when clicked", async () => {
    const user = userEvent.setup();
    const onRunStation = vi.fn();
    renderPanel({ onRunStation });
    const button = screen.getByRole("button", { name: /run validation/i });
    await user.click(button);
    expect(onRunStation).toHaveBeenCalledTimes(1);
    expect(onRunStation).toHaveBeenCalledWith({
      source: "snotel",
      jobId: "job-xyz",
      bbox: BBOX,
      start: "2024-01-01",
      end: "2024-01-31",
    });
  });
});
