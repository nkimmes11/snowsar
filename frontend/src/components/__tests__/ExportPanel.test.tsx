import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ExportPanel } from "../ExportPanel";
import type { JobResponse } from "../../types";

const COMPLETED: JobResponse = {
  job_id: "job-xyz",
  status: "completed",
  algorithms: ["lievens"],
  backend: "gee",
  created_at: "2024-01-01T00:00:00Z",
};

describe("ExportPanel", () => {
  it("shows a waiting message when no job is present", () => {
    render(<ExportPanel job={null} timeSeries={null} validationPairs={null} />);
    expect(
      screen.getByText(/export available after the job completes/i),
    ).toBeInTheDocument();
  });

  it("disables the CSV export button when there is no time-series data", () => {
    render(<ExportPanel job={COMPLETED} timeSeries={null} validationPairs={null} />);
    const csvButton = screen.getByRole("button", { name: /export time-series csv/i });
    expect(csvButton).toBeDisabled();
  });

  it("renders a GeoTIFF download link when the job is completed", () => {
    render(<ExportPanel job={COMPLETED} timeSeries={null} validationPairs={null} />);
    const link = screen.getByRole("link", { name: /download geotiff/i });
    expect(link).toHaveAttribute("href", expect.stringContaining("/api/v1/jobs/job-xyz/results/geotiff"));
    expect(link).toHaveAttribute("download");
  });
});
