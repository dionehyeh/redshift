"use client";

import dynamic from "next/dynamic";
import type { FieldMapData } from "@/lib/field-types";

const FieldMapView = dynamic(() => import("./FieldMapView"), {
  ssr: false,
  loading: () => (
    <div className="h-72 w-full animate-pulse rounded-2xl bg-stone-100" aria-label="Loading field map" />
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
  return (
    <div className="relative z-0 isolate overflow-hidden rounded-2xl border border-stone-200">
      <FieldMapView data={data} lat={lat} lon={lon} />
    </div>
  );
}
