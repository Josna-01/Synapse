"use client";

import dynamic from "next/dynamic";
import { DistrictData } from "./ChoroplethMapInner";

// Dynamically import the inner Leaflet map component with SSR disabled.
// This prevents Next.js from throwing "window is not defined" errors during server-side rendering,
// because Leaflet internally requires the browser 'window' object immediately upon import.
const LeafletChoroplethMap = dynamic(() => import("./ChoroplethMapInner"), { ssr: false });

interface ChoroplethMapProps {
  districtData: DistrictData[];
  geojson: any; // Using `any` for FeatureCollection so we don't need to import GeoJSON types globally just for props
  center?: [number, number];
  zoom?: number;
  onDistrictClick?: (district: DistrictData) => void;
}

/**
 * Shell component for the ChoroplethMap.
 * Use this component in your pages/dashboards. It safely loads the Leaflet logic client-side only.
 */
export default function ChoroplethMap(props: ChoroplethMapProps) {
  return <LeafletChoroplethMap {...props} />;
}
