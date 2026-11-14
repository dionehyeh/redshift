import Link from "next/link";
import { ArrowLeft, ShieldAlert } from "lucide-react";

export default function AboutPage() {
  const sources = [
    {
      name: "NASA POWER",
      purpose:
        "20-year climatological normals, thermal limits, solar radiation",
      res: "~50 km (0.5 deg)",
      latency: "Near Real-Time (~2 days)",
    },
    {
      name: "GPM IMERG",
      purpose:
        "Precipitation estimates, dry spell tracking, waterlogging risk",
      res: "~10 km (0.1 deg)",
      latency: "Late run ~14 hours; Final run ~3.5 months",
    },
    {
      name: "MODIS (MOD13Q1)",
      purpose:
        "Vegetation health (NDVI) curve, crop greenness dips, fallow windows",
      res: "250 m (16-day)",
      latency: "1–2 weeks",
    },
    {
      name: "SRTM GL1",
      purpose:
        "Topography, slope gradient, flood-prone low-lying basin flag",
      res: "30 m (1 arc-sec)",
      latency: "Static DEM",
    },
    {
      name: "ISRIC SoilGrids",
      purpose: "Baseline soil pH, texture, and organic carbon estimate",
      res: "250 m",
      latency: "Static ML model",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 via-stone-100 to-amber-50">
      {/* ── Top bar ── */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-green-900 via-green-800 to-emerald-900 shadow-lg">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-5 h-14">
          <Link
            href="/fields"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/15 text-white text-sm font-semibold hover:bg-white/25 transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            My Fields
          </Link>
          <span className="text-emerald-200/70 text-xs font-bold tracking-widest uppercase">
            Field Shift
          </span>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="max-w-4xl mx-auto px-5 py-10 space-y-8">
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold text-stone-900">
            About Field Shift Analysis
          </h1>
          <p className="text-stone-500">
            Transparency into Earth observation sources, spatial resolutions,
            analytical latency, and mathematical limits.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-amber-50 border-2 border-amber-200 flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
            <ShieldAlert className="w-5 h-5 text-amber-700" />
          </div>
          <div className="text-sm text-amber-900 space-y-1">
            <p className="font-bold">Estimates, Not Guarantees</p>
            <p>
              Field Shift provides decision-support insights derived from
              satellite observations and regional agronomic rules. Satellite
              data can miss local convective showers, and cloud cover creates
              gaps during monsoon periods. Always consult your local Krishi
              Bhavan extension officer before purchasing seeds or applying
              fertilizers.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-extrabold text-stone-900">
            🛰️ Earth Observation Data Catalog
          </h2>
          <div className="overflow-x-auto rounded-2xl border-2 border-stone-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="bg-gradient-to-r from-green-900 to-emerald-900 text-white">
                  <th className="p-4 font-bold">Dataset</th>
                  <th className="p-4 font-bold">Pipeline Purpose</th>
                  <th className="p-4 font-bold">Resolution</th>
                  <th className="p-4 font-bold">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {sources.map((s, i) => (
                  <tr
                    key={s.name}
                    className={`${
                      i % 2 === 0 ? "bg-white" : "bg-stone-50"
                    } hover:bg-emerald-50 transition-colors`}
                  >
                    <td className="p-4 font-bold text-stone-900">{s.name}</td>
                    <td className="p-4 text-stone-600">{s.purpose}</td>
                    <td className="p-4 font-mono text-xs text-stone-500">
                      {s.res}
                    </td>
                    <td className="p-4 text-xs text-stone-500">{s.latency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
