"use client";

import type { FieldTimeline as FieldTimelineData } from "@/lib/field-types";

const LABELS: Record<string, string> = {
  rain_mm: "Rainfall",
  tmean: "Mean temperature",
  tmax: "Maximum temperature",
  ndvi: "Vegetation index (NDVI)",
};

function points(values: (number | null)[], weeks: number[]) {
  const valid = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (valid.length < 2) return "";
  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const spread = max - min || 1;
  return values
    .map((value, index) => {
      if (value === null || !Number.isFinite(value)) return null;
      const x = ((weeks[index] - 1) / 51) * 1000;
      const y = 180 - ((value - min) / spread) * 160 - 10;
      return `${x},${y}`;
    })
    .filter((point): point is string => point !== null)
    .join(" ");
}

export function FieldTimeline({ timeline }: { timeline: FieldTimelineData }) {
  const metrics = Object.entries(timeline.series);

  return (
    <section className="p-6 bg-white border border-slate-200 rounded-2xl space-y-5">
      <div>
        <h2 className="text-xl font-bold text-slate-900">52-week climate profile</h2>
        <p className="mt-1 text-xs text-slate-500">{timeline.source_note}</p>
      </div>

      {metrics.length === 0 ? (
        <p className="text-sm text-slate-500">Climate data is not available for this field yet.</p>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {metrics.map(([key, series]) => {
            const label = LABELS[key] || key;
            const normal = timeline.normals[key] || [];
            const observedPath = points(series.values, timeline.weeks);
            const normalPath = points(normal, timeline.weeks);

            return (
              <article key={key} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-800">{label}</h3>
                    <p className="text-xs text-slate-500">{series.source}</p>
                  </div>
                  {series.resolution && (
                    <span className="shrink-0 text-[11px] text-slate-500">{series.resolution}</span>
                  )}
                </div>
                <svg
                  viewBox="0 0 1000 200"
                  role="img"
                  aria-label={`${label} across 52 weeks`}
                  className="mt-3 h-32 w-full overflow-visible"
                  preserveAspectRatio="none"
                >
                  <line x1="0" y1="190" x2="1000" y2="190" stroke="#cbd5e1" />
                  {!series.is_normal && normalPath && (
                    <polyline
                      points={normalPath}
                      fill="none"
                      stroke="#94a3b8"
                      strokeWidth="3"
                      strokeDasharray="8 8"
                    />
                  )}
                  {observedPath && (
                    <polyline
                      points={observedPath}
                      fill="none"
                      stroke="#047857"
                      strokeWidth="4"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  )}
                </svg>
                <div className="flex justify-between text-[11px] text-slate-500">
                  <span>Week 1</span>
                  <span>Week 52</span>
                </div>
                <p className="mt-2 text-[11px] text-slate-500">
                  {series.is_normal
                    ? "Solid line: weekly climatological normal; historical observations are unavailable."
                    : "Dashed line: climatological normal; solid line: weekly observations."}
                </p>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
