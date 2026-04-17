import { useMap } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import type { JobResponse } from "../types";

interface ResultLayerProps {
  job: JobResponse | null;
}

/**
 * Placeholder result layer component.
 *
 * When a job completes, this displays a visual indicator on the map.
 * Full GeoTIFF raster overlay rendering will be added in Phase 2
 * (Step 2.5) using georaster-layer-for-leaflet once the backend
 * produces downloadable GeoTIFF results.
 */
export function ResultLayer({ job }: ResultLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!job || job.status !== "completed") return;

    const popup = L.popup()
      .setLatLng(map.getCenter())
      .setContent(
        `<div style="text-align:center">
          <strong>Job Complete</strong><br/>
          ${job.algorithms.join(", ")}<br/>
          <em>GeoTIFF overlay coming in Phase 2</em>
        </div>`,
      )
      .openOn(map);

    return () => {
      popup.remove();
    };
  }, [job, map]);

  return null;
}
