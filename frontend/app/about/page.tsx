import Link from "next/link";
import { ArrowLeft, ExternalLink, ShieldAlert } from "lucide-react";

export default function AboutPage() {
  const sources = [
    {
      name: "NASA POWER",
      purpose: "20-year climatological normals, thermal limits, solar radiation",
      res: "~50 km (0.5 deg)",
      latency: "Near Real-Time (~2 days)",
    },
    {
      name: "GPM IMERG",
      purpose: "Precipitation estimates, dry spell tracking, waterlogging risk",
      res: "~10 km (0.1 deg)",
      latency: "Late run ~14 hours; Final run ~3.5 months",
    },
    {
      name: "MODIS (MOD13Q1)",
      purpose: "Vegetation health (NDVI) curve, crop greenness dips, fallow windows",
      res: "250 m (16-day)",
      latency: "1–2 weeks",
    },
    {
      name: "SRTM GL1",
      purpose: "Topography, slope gradient, flood-prone low-lying basin flag",
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
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to Home
      </Link>

      <div className="space-y-2">
        <h1 className="text-3xl font-extrabold text-slate-900">About Field Shift Analysis</h1>
        <p className="text-slate-600">
          Transparency into Earth observation sources, spatial resolutions, analytical latency, and mathematical limits.
        </p>
      </div>

      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-amber-900 space-y-1">
          <p className="font-semibold">Estimates, Not Guarantees</p>
          <p>
            Field Shift provides decision-support insights derived from satellite observations and regional agronomic rules.
            Satellite data can miss local convective showers, and cloud cover creates gaps during monsoon periods.
            Always consult your local Krishi Bhavan extension officer before purchasing seeds or applying fertilizers.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Earth Observation Data Catalog</h2>
        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-100 text-slate-900 font-semibold border-b border-slate-200">
              <tr>
                <th className="p-3">Dataset</th>
                <th className="p-3">Pipeline Purpose</th>
                <th className="p-3">Resolution</th>
                <th className="p-3">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sources.map((s) => (
                <tr key={s.name} className="hover:bg-slate-50">
                  <td className="p-3 font-medium text-slate-900">{s.name}</td>
                  <td className="p-3">{s.purpose}</td>
                  <td className="p-3 font-mono text-xs">{s.res}</td>
                  <td className="p-3 text-xs">{s.latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
