import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ControlPanel } from "../ControlPanel";
import type { BBox } from "../../types";

vi.mock("../../api/client", () => ({
  listAlgorithms: vi.fn().mockResolvedValue([
    { id: "lievens", name: "Lievens", description: "" },
    { id: "dprse", name: "DpRSE", description: "" },
  ]),
}));

const BBOX: BBox = { west: -120.5, south: 37.5, east: -120.0, north: 38.0 };

describe("ControlPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("disables submit when no bbox is drawn", async () => {
    render(
      <ControlPanel
        bbox={null}
        onSubmit={vi.fn()}
        submitting={false}
        job={null}
        error={null}
      />,
    );
    const button = await screen.findByRole("button", { name: /run retrieval/i });
    expect(button).toBeDisabled();
  });

  it("disables submit when no algorithms are selected", async () => {
    const user = userEvent.setup();
    render(
      <ControlPanel
        bbox={BBOX}
        onSubmit={vi.fn()}
        submitting={false}
        job={null}
        error={null}
      />,
    );
    const lievens = await screen.findByRole("checkbox", { name: /lievens/i });
    await user.click(lievens);
    const button = screen.getByRole("button", { name: /run retrieval/i });
    expect(button).toBeDisabled();
  });

  it("calls onSubmit with the current form values", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <ControlPanel
        bbox={BBOX}
        onSubmit={onSubmit}
        submitting={false}
        job={null}
        error={null}
      />,
    );
    const button = await screen.findByRole("button", { name: /run retrieval/i });
    await user.click(button);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        bbox: BBOX,
        algorithms: ["lievens"],
        backend: "fixture",
        start_date: expect.any(String),
        end_date: expect.any(String),
      }),
    );
  });
});
