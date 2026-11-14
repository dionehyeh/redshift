"use client";

import dynamic from "next/dynamic";
import type { FieldMapData } from "@/lib/field-types";

const FieldMapView = dynamic(() => import("./FieldMapView"), {
  ssr: false,
  loading: () => (
    <div className="h-72 w-full animate-pulse rounded-xl bg-slate-100" aria-label="Loading field map" />
  ),
});

export default function FieldMap({
  data,
  lat,
  lon,
}: {
  data: FieldMapData;
  lat: number;
  lon: number;
}) {
  return <FieldMapView data={data} lat={lat} lon={lon} />;
}
