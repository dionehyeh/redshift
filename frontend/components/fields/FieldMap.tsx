"use client";

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";

export default function FieldMap({
  lat,
  lon,
  onChange,
  readOnly = false,
}: {
  lat: number;
  lon: number;
  onChange?: (lat: number, lon: number) => void;
  readOnly?: boolean;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="h-64 w-full bg-slate-100 animate-pulse rounded-2xl flex items-center justify-center text-xs text-slate-400">Loading Map...</div>;
  }

  return (
    <div className="relative h-64 w-full bg-emerald-50/50 border border-slate-200 rounded-2xl overflow-hidden flex flex-col items-center justify-center text-center p-4 space-y-2">
      <div className="p-3 bg-emerald-100 text-emerald-800 rounded-full">
        <MapPin className="w-6 h-6 animate-bounce" />
      </div>
      <div>
        <span className="font-bold text-sm text-slate-900 block">Plot Geographic Coordinate</span>
        <span className="font-mono text-xs text-slate-600 block mt-0.5">
          {lat.toFixed(4)}°N, {lon.toFixed(4)}°E
        </span>
      </div>
      <p className="text-[11px] text-slate-400 max-w-xs">
        {readOnly ? "Interactive Leaflet satellite overlay" : "Drag the pin or use device GPS to position your plot."}
      </p>
    </div>
  );
}
