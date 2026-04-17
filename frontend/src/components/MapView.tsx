import { useCallback, useRef } from "react";
import { MapContainer, TileLayer, FeatureGroup, Rectangle, useMapEvents } from "react-leaflet";
import L from "leaflet";
import type { BBox, JobResponse } from "../types";
import { ResultLayer } from "./ResultLayer";

interface MapViewProps {
  bbox: BBox | null;
  onBBoxChange: (bbox: BBox | null) => void;
  job: JobResponse | null;
}

/** Handles map click-drag to draw an AOI rectangle. */
function DrawHandler({ onBBoxChange }: { onBBoxChange: (bbox: BBox | null) => void }) {
  const startRef = useRef<L.LatLng | null>(null);

  useMapEvents({
    mousedown(e) {
      if (!e.originalEvent.shiftKey) return;
      startRef.current = e.latlng;
      e.originalEvent.preventDefault();
    },
    mousemove() {
      // Drawing feedback could be added here
    },
    mouseup(e) {
      if (!startRef.current) return;
      const start = startRef.current;
      const end = e.latlng;
      startRef.current = null;

      const west = Math.min(start.lng, end.lng);
      const east = Math.max(start.lng, end.lng);
      const south = Math.min(start.lat, end.lat);
      const north = Math.max(start.lat, end.lat);

      if (Math.abs(east - west) > 0.001 && Math.abs(north - south) > 0.001) {
        onBBoxChange({ west, south, east, north });
      }
    },
  });

  return null;
}

export function MapView({ bbox, onBBoxChange, job }: MapViewProps) {
  const handleBBoxChange = useCallback(
    (newBBox: BBox | null) => {
      onBBoxChange(newBBox);
    },
    [onBBoxChange],
  );

  return (
    <MapContainer
      center={[45, -110]}
      zoom={5}
      style={{ flex: 1, height: "100%" }}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <DrawHandler onBBoxChange={handleBBoxChange} />
      {bbox && (
        <FeatureGroup>
          <Rectangle
            bounds={[
              [bbox.south, bbox.west],
              [bbox.north, bbox.east],
            ]}
            pathOptions={{ color: "#2563eb", weight: 2, fillOpacity: 0.1 }}
          />
        </FeatureGroup>
      )}
      <ResultLayer job={job} />
    </MapContainer>
  );
}
