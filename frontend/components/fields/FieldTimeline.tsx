"use client";

import type { FieldTimeline as FieldTimelineData } from "@/lib/field-types";

const LABELS: Record<string, string> = {
  rain_mm: "Weekly Rainfall (mm)",
  tmean: "Mean Temperature (°C)",
  tmax: "Maximum Temperature (°C)",
  ndvi: "Vegetation Index (NDVI)",
};

function points(values: (number | null)[], weeks: number[]) {
  if (!values || !weeks) return "";
  const valid = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (valid.length < 2) return "";
  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const spread = max - min || 1;
  return values
    .map((value, index) => {
      if (value === null || !Number.isFinite(value) || !weeks[index]) return null;
      const x = ((weeks[index] - 1) / 51) * 1000;
      const y = 180 - ((value - min) / spread) * 160 - 10;
      return `${x},${y}`;
    })
    .filter((point): point is string => point !== null)
    .join(" ");
}

export function FieldTimeline({ timeline }: { timeline: FieldTimelineData }) {
  const series = timeline?.series || {};
  const normals = timeline?.normals || {};
  const weeks = timeline?.weeks || Array.from({ length: 52 }, (_, i) => i + 1);
  const metrics = Object.entries(series);

  return (
    <section className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-stone-900">52-Week NASA Climate & Vegetation Profile</h2>
        <p className="mt-1 text-xs text-stone-500 font-medium">
          {timeline?.source_note || "NASA POWER Daily (0.5° resolution) + GPM IMERG Final precipitation baselines (20-year climatology)"}
        </p>
      </div>

      {metrics.length === 0 ? (
        <p className="text-sm text-stone-500 italic">Climate observation series is being prepared for this field coordinate.</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {metrics.map(([key, item]) => {
            if (!item || !item.values) return null;
            const label = LABELS[key] || key;
            const normal = normals[key] || [];
            const observedPath = points(item.values, weeks);
            const normalPath = points(normal, weeks);

            return (
              <article key={key} className="rounded-2xl border-2 border-stone-200 bg-stone-50/60 p-5 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-extrabold text-stone-900 text-base">{label}</h3>
                    <p className="text-xs text-stone-500 font-medium">{item.source || "NASA Earth Observation"}</p>
                  </div>
                  {item.resolution && (
                    <span className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full bg-stone-200 text-stone-700">
                      {item.resolution}
                    </span>
                  )}
                </div>

                <div className="bg-white p-3 rounded-xl border border-stone-200 shadow-inner">
                  <svg
                    viewBox="0 0 1000 200"
                    role="img"
                    aria-label={`${label} across 52 weeks`}
                    className="h-32 w-full overflow-visible"
                    preserveAspectRatio="none"
                  >
                    <line x1="0" y1="190" x2="1000" y2="190" stroke="#e2e8f0" strokeWidth="2" />
                    {!item.is_normal && normalPath && (
                      <polyline
                        points={normalPath}
                        fill="none"
                        stroke="#94a3b8"
                        strokeWidth="2.5"
                        strokeDasharray="6 6"
                      />
                    )}
                    {observedPath && (
                      <polyline
                        points={observedPath}
                        fill="none"
                        stroke="#047857"
                        strokeWidth="3.5"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                    )}
                  </svg>
                  <div className="flex justify-between text-[10px] font-bold text-stone-400 mt-1">
                    <span>Week 1 (Jan)</span>
                    <span>Week 26 (Monsoon Peak)</span>
                    <span>Week 52 (Dec)</span>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-[11px] text-stone-500 font-medium">
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-1 bg-emerald-700 rounded-full inline-block" /> Weekly observation
                  </span>
                  {!item.is_normal && (
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-0.5 border-t-2 border-dashed border-slate-400 inline-block" /> 20-yr Normal
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
