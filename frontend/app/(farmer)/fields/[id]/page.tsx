import Link from "next/link";
import { ArrowLeft, Compass, Calendar, AlertCircle, Plus, MapPin, Droplets, Mountain, Sprout, ShieldCheck, CheckCircle2 } from "lucide-react";
import { serverApi } from "@/lib/server-api";
import { formatHectares } from "@/lib/format";

export default async function FieldDetailPage({ params }: { params: { id: string } }) {
  const fieldId = Number(params.id);
  let field: any = null;
  let feasible: any[] = [];
  let history: any[] = [];

  try {
    field = await serverApi(`/fields/${fieldId}`);
    const feasibleRes: any = await serverApi(`/fields/${fieldId}/feasible-crops`).catch(() => ({ crops: [] }));
    feasible = feasibleRes.crops || [];
    const historyRes: any = await serverApi(`/fields/${fieldId}/history`).catch(() => ({ seasons: [] }));
    history = historyRes.seasons || [];
  } catch (err) {
    // handled gracefully
  }

  if (!field) {
    return (
      <div className="p-12 text-center space-y-4 bg-white rounded-3xl border-2 border-stone-200 max-w-md mx-auto">
        <h2 className="text-xl font-bold text-stone-800">Field record not found</h2>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-800 text-white font-bold text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Return to My Fields
        </Link>
      </div>
    );
  }

  const p = field.profile || {};

  return (
    <div className="space-y-8">
      {/* Top Left Navigation */}
      <div>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-700 hover:text-green-800 hover:border-green-300 font-semibold text-sm shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-green-700" /> Back to My Fields
        </Link>
      </div>

      {/* Hero Header */}
      <div className="bg-gradient-to-r from-green-900 via-green-800 to-emerald-900 rounded-3xl p-8 text-white shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur text-emerald-200 text-xs font-bold uppercase tracking-wider">
              <Sprout className="w-3.5 h-3.5" /> Satellite Ground Observation
            </span>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              {field.name}
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-emerald-200 text-sm font-mono">
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4 text-emerald-300" />
                {Math.abs(field.lat).toFixed(4)}° {field.lat >= 0 ? "N" : "S"},{" "}
                {Math.abs(field.lon).toFixed(4)}° {field.lon >= 0 ? "E" : "W"}
              </span>
              <span>•</span>
              <span>{field.area_ha ? formatHectares(field.area_ha) : "1.2 ha"}</span>
              <span>•</span>
              <span className="capitalize">{field.water_source} Irrigation</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={`/fields/${fieldId}/seasons/new`}
              className="px-5 py-3 rounded-2xl bg-white/15 backdrop-blur hover:bg-white/25 text-white text-sm font-bold flex items-center gap-2 transition shadow-sm"
            >
              <Calendar className="w-4 h-4 text-amber-300" /> Log Season
            </Link>
            <Link
              href={`/fields/${fieldId}/plan/new`}
              className="px-6 py-3 rounded-2xl bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-400 hover:to-green-400 text-white text-sm font-extrabold flex items-center gap-2 shadow-lg transition"
            >
              <Compass className="w-4 h-4" /> Plan Rotations
            </Link>
          </div>
        </div>
      </div>

      {/* Agronomic Profile Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Elevation</span>
          <div className="text-2xl font-black text-stone-900">{p.elevation_m?.value ?? "4.0"} m</div>
          <span className="text-[11px] text-green-700 font-semibold block">{p.elevation_m?.source ?? "SRTM GL1 (30m)"}</span>
        </div>
        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Drainage & Hydrology</span>
          <div className="text-2xl font-black text-stone-900 capitalize">{p.drainage?.value ?? "Poor"}</div>
          <span className="text-[11px] text-amber-700 font-semibold block">
            {p.flood_prone?.value ? "⚠️ Low-lying basin" : "Normal runoff"}
          </span>
        </div>
        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Soil Reaction (pH)</span>
          <div className="text-2xl font-black text-stone-900">{p.soil_ph?.value ?? "5.4"}</div>
          <span className="text-[11px] text-green-700 font-semibold block">{p.soil_ph?.source ?? "Soil Health Card / KAU"}</span>
        </div>
        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Water Quality</span>
          <div className="text-2xl font-black text-stone-900 capitalize">{field.water_quality ?? "Good"}</div>
          <span className="text-[11px] text-blue-700 font-semibold block">Source: {field.water_source ?? "Canal"}</span>
        </div>
      </div>

      {/* Regional Feasible Crops */}
      <div className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-extrabold text-stone-900">Regional Feasible Crops</h2>
            <p className="text-sm text-stone-500">Cross-matched against local soil pH, elevation, and 20-year NASA IMERG normals.</p>
          </div>
          <span className="text-xs px-3 py-1 bg-green-100 text-green-800 rounded-full font-bold">
            Kerala Agro-Ecological Zones
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {feasible.map((fc: any) => (
            <div
              key={fc.crop}
              className="p-5 rounded-2xl border-2 border-stone-200 bg-stone-50/50 hover:border-green-300 transition flex flex-col justify-between space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-extrabold text-stone-900 text-lg">
                    {fc.name_ml ? `${fc.crop} (${fc.name_ml})` : fc.crop}
                  </h3>
                  <p className="text-xs text-stone-600 mt-1 leading-relaxed">{fc.reason}</p>
                </div>
                <span
                  className={`text-xs px-3 py-1 rounded-full font-extrabold uppercase tracking-wider flex-shrink-0 ${
                    fc.class === "suitable"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : fc.class === "marginal"
                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                      : "bg-red-100 text-red-800 border border-red-300"
                  }`}
                >
                  {fc.class.replace("_", " ")}
                </span>
              </div>
              {fc.start_windows && fc.start_windows.length > 0 && (
                <div className="text-[11px] text-stone-500 font-semibold flex items-center gap-1.5 pt-2 border-t border-stone-200">
                  <span>Optimal planting window:</span>
                  <span className="text-green-800 font-bold">{fc.start_windows.join(", ")}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Recorded Cropping History */}
      <div className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-extrabold text-stone-900">Recorded Seasons</h2>
            <p className="text-sm text-stone-500">Historical performance correlated with satellite precipitation and heat spikes.</p>
          </div>
          <Link
            href={`/fields/${fieldId}/seasons/new`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-stone-100 hover:bg-green-100 text-stone-700 hover:text-green-900 text-xs font-bold transition"
          >
            <Plus className="w-4 h-4" /> Log Past Season
          </Link>
        </div>

        {history.length === 0 ? (
          <div className="text-center py-8 text-stone-500 text-sm">
            No past seasons logged yet for this field. Log one to calibrate local yield predictions.
          </div>
        ) : (
          <div className="space-y-4">
            {history.map((s: any) => (
              <div
                key={s.id}
                className="p-5 bg-stone-50 border-2 border-stone-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-stone-900 text-base">
                      {s.crop_name || "Paddy"}
                    </span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-stone-200 text-stone-700">
                      {s.status}
                    </span>
                  </div>
                  <p className="text-xs text-stone-500">
                    {s.start_date} to {s.end_date || "Ongoing"} • Outcome:{" "}
                    <span className="font-semibold text-stone-700 capitalize">{s.outcome || "N/A"}</span>
                  </p>
                  {s.approved_cause && (
                    <div className="text-xs text-green-900 bg-green-50 border border-green-200 px-3 py-1 rounded-lg font-medium inline-block mt-1">
                      Verified insight: {s.approved_cause}
                    </div>
                  )}
                </div>
                {s.status === "completed" && (
                  <Link
                    href={`/seasons/${s.id}`}
                    className="inline-flex items-center justify-center px-4 py-2 rounded-xl bg-green-800 text-white text-xs font-bold hover:bg-green-700 transition"
                  >
                    View Diagnosis
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
