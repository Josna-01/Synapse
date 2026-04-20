/**
 * apps/web/src/app/components/map/LeafletMapInner.tsx
 *
 * SYNAPSE — Leaflet map implementation (client-only)
 * OpenStreetMap tiles, urgency-coloured markers, real-time Firestore updates.
 *
 * Replaces: Google Maps JavaScript API + @react-google-maps/api
 * New deps:  leaflet, react-leaflet, @types/leaflet
 *
 * Visual design preserved:
 *   critical  (≥80)  → red    #EF4444
 *   high      (60-79) → orange #F97316
 *   moderate  (40-59) → amber  #EAB308
 *   low       (<40)   → green  #22C55E
 */

"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { NeedMarker } from "./MapComponent";

// Fix Leaflet default marker icon path (common Next.js issue)
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "/leaflet/marker-icon-2x.png",
  iconUrl: "/leaflet/marker-icon.png",
  shadowUrl: "/leaflet/marker-shadow.png",
});

// ── Urgency colour mapping (same palette as Google Maps version) ──────────────

function urgencyColour(score: number): string {
  if (score >= 80) return "#EF4444";  // red     — critical
  if (score >= 60) return "#F97316";  // orange  — high
  if (score >= 40) return "#EAB308";  // amber   — moderate
  return "#22C55E";                   // green   — low
}

function urgencyLabel(score: number): string {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 40) return "Moderate";
  return "Low";
}

function markerRadius(score: number): number {
  // Larger radius for more urgent needs — matches heatmap blob effect
  if (score >= 80) return 18;
  if (score >= 60) return 14;
  if (score >= 40) return 10;
  return 8;
}

// ── Auto-fit bounds when markers change ──────────────────────────────────────

function BoundsUpdater({ needs }: { needs: NeedMarker[] }) {
  const map = useMap();
  useEffect(() => {
    if (needs.length === 0) return;
    const bounds = L.latLngBounds(needs.map((n) => [n.lat, n.lng]));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [needs, map]);
  return null;
}

// ── Main Leaflet map ──────────────────────────────────────────────────────────

interface LeafletMapInnerProps {
  needs: NeedMarker[];
  center: [number, number];
  zoom: number;
  onMarkerClick?: (need: NeedMarker) => void;
}

export default function LeafletMapInner({
  needs,
  center,
  zoom,
  onMarkerClick,
}: LeafletMapInnerProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      style={{ height: "100%", width: "100%", borderRadius: "0.75rem" }}
      zoomControl={true}
    >
      {/* OpenStreetMap tiles — free, no API key required */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />

      {/* Auto-fit bounds to visible markers */}
      {needs.length > 0 && <BoundsUpdater needs={needs} />}

      {/* Urgency-coloured circle markers — same visual design as Google Maps version */}
      {needs.map((need) => {
        const colour = urgencyColour(need.urgency_score);
        return (
          <CircleMarker
            key={need.id}
            center={[need.lat, need.lng]}
            radius={markerRadius(need.urgency_score)}
            pathOptions={{
              fillColor: colour,
              fillOpacity: 0.75,
              color: colour,
              weight: 2,
              opacity: 1,
            }}
            eventHandlers={{
              click: () => onMarkerClick?.(need),
            }}
          >
            <Popup className="synapse-popup">
              <div className="min-w-[180px]">
                <div
                  className="text-xs font-semibold uppercase tracking-wide mb-1"
                  style={{ color: colour }}
                >
                  {urgencyLabel(need.urgency_score)} · {need.urgency_score}/100
                </div>
                <div className="font-medium text-sm text-gray-900 mb-1">
                  {need.title}
                </div>
                <div className="text-xs text-gray-500 capitalize mb-2">
                  {need.category.replace(/_/g, " ")}
                </div>
                <div className="text-xs text-gray-600">
                  {need.affected_count.toLocaleString()} people affected
                </div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
