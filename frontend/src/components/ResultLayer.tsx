import { useMap } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import type { JobResponse } from "../types";

interface ResultLayerProps {
  job: JobResponse | null;
  showDiffOverlay: boolean;
}

/**
 * Placeholder result layer.
 *
 * GeoTIFF raster overlay rendering (georaster-layer-for-leaflet) is
 * scheduled for a future phase once Celery workers write downloadable
 * GeoTIFFs to shared storage rather than in-process result stores.
 */
export function ResultLayer({ job, showDiffOverlay }: ResultLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!job || job.status !== "completed") return;

    const content = showDiffOverlay
      ? `<div style="text-align:center">
          <strong>Difference overlay</strong><br/>
          ${job.algorithms.join(", ")}<br/>
          <em>raster overlay coming soon</em>
        </div>`
      : `<div style="text-align:center">
          <strong>Job Complete</strong><br/>
          ${job.algorithms.join(", ")}<br/>
          <em>GeoTIFF overlay coming soon</em>
        </div>`;

    const popup = L.popup().setLatLng(map.getCenter()).setContent(content).openOn(map);

    return () => {
      popup.remove();
    };
  }, [job, showDiffOverlay, map]);

  return null;
}
