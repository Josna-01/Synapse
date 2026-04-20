/**
 * apps/web/src/app/components/map/MapComponent.tsx
 *
 * SYNAPSE — Live urgency heatmap and volunteer task map
 * Uses Leaflet + OpenStreetMap (replaces Google Maps JavaScript API)
 *
 * npm install leaflet react-leaflet @types/leaflet
 */

"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef } from "react";

// react-leaflet must be imported client-side only (uses window)
// Next.js 14: use dynamic import with ssr: false
const LeafletMap = dynamic(() => import("./LeafletMapInner"), { ssr: false });

export interface NeedMarker {
  id: string;
  lat: number;
  lng: number;
  urgency_score: number;   // 0–100
  category: string;
  title: string;
  affected_count: number;
}

interface MapComponentProps {
  needs: NeedMarker[];
  center?: [number, number];    // [lat, lng]
  zoom?: number;
  onMarkerClick?: (need: NeedMarker) => void;
}

/**
 * Shell component — delegates to LeafletMapInner (client-only).
 * This pattern is required in Next.js 14 App Router because Leaflet
 * uses browser APIs that are unavailable during SSR.
 */
export default function MapComponent({
  needs,
  center = [12.9716, 77.5946],  // Default: Bengaluru
  zoom = 12,
  onMarkerClick,
}: MapComponentProps) {
  return (
    <LeafletMap
      needs={needs}
      center={center}
      zoom={zoom}
      onMarkerClick={onMarkerClick}
    />
  );
}
