import Link from "next/link";
import { ArrowLeft, Compass, Calendar, AlertCircle, Plus } from "lucide-react";
import { serverApi } from "@/lib/server-api";

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
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-800">Field record not found</h2>
        <Link href="/fields" className="text-emerald-700 underline text-sm">
          Return to plots list
        </Link>
      </div>
    );
  }

  const p = field.profile || {};

  return (
    <div className="space-y-6">
      <Link href="/fields" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to My Fields
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">{field.name}</h1>
          <p className="text-sm text-slate-500 font-mono">
            {field.lat?.toFixed(3)}°N, {field.lon?.toFixed(3)}°E · Cell {field.climate_cell_id}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/fields/${fieldId}/seasons/new`}
            className="h-11 px-4 rounded-xl border border-slate-300 bg-white text-slate-800 text-sm font-semibold flex items-center gap-1.5 hover:bg-slate-50 transition"
          >
            <Calendar className="w-4 h-4" /> Log Season
          </Link>
          <Link
            href={`/fields/${fieldId}/plan/new`}
            className="h-11 px-5 rounded-xl bg-emerald-700 text-white text-sm font-semibold flex items-center gap-1.5 hover:bg-emerald-800 transition"
          >
            <Compass className="w-4 h-4" /> Plan Rotations
          </Link>
        </div>
      </div>

      {/* Profile Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 bg-white border border-slate-200 rounded-2xl">
          <span className="text-xs text-slate-500 block">Elevation</span>
          <span className="text-lg font-bold text-slate-900">{p.elevation_m?.value} m</span>
          <span className="text-[10px] text-slate-400 block mt-1">{p.elevation_m?.source}</span>
        </div>
        <div className="p-4 bg-white border border-slate-200 rounded-2xl">
          <span className="text-xs text-slate-500 block">Drainage & Basin</span>
          <span className="text-lg font-bold text-slate-900 capitalize">{p.drainage?.value}</span>
          <span className="text-[10px] text-slate-400 block mt-1">
            {p.flood_prone?.value ? "Flood-prone basin" : "Normal run-off"}
          </span>
        </div>
        <div className="p-4 bg-white border border-slate-200 rounded-2xl">
          <span className="text-xs text-slate-500 block">Soil pH</span>
          <span className="text-lg font-bold text-slate-900">{p.soil_ph?.value}</span>
          <span className="text-[10px] text-slate-400 block mt-1">{p.soil_ph?.source}</span>
        </div>
        <div className="p-4 bg-white border border-slate-200 rounded-2xl">
          <span className="text-xs text-slate-500 block">Water Source</span>
          <span className="text-lg font-bold text-slate-900 capitalize">{field.water_source}</span>
          <span className="text-[10px] text-slate-400 block mt-1">Quality: {field.water_quality}</span>
        </div>
      </div>

      {/* Feasible Crops Section */}
      <div className="p-6 bg-white border border-slate-200 rounded-2xl space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Regional Feasible Crops</h2>
        <div className="divide-y divide-slate-100">
          {feasible.map((fc: any) => (
            <div key={fc.crop} className="py-3 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-900 capitalize">{fc.crop.replace("_", " ")}</span>
                <p className="text-xs text-slate-500">{fc.reason}</p>
              </div>
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-semibold capitalize ${
                  fc.class === "suitable"
                    ? "bg-emerald-100 text-emerald-800"
                    : fc.class === "marginal"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {fc.class}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Cropping History */}
      <div className="p-6 bg-white border border-slate-200 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Recorded Seasons</h2>
          <Link
            href={`/fields/${fieldId}/seasons/new`}
            className="text-xs text-emerald-700 font-semibold hover:underline flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> Log Past Season
          </Link>
        </div>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500 italic">No past seasons logged yet for this field.</p>
        ) : (
          <div className="space-y-3">
            {history.map((s: any) => (
              <div
                key={s.id}
                className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between"
              >
                <div>
                  <span className="font-bold text-slate-800 capitalize">
                    {s.crop_name || "Paddy"} ({s.status})
                  </span>
                  <p className="text-xs text-slate-500">
                    {s.start_date} to {s.end_date || "Ongoing"} · Outcome: {s.outcome || "N/A"}
                  </p>
                  {s.approved_cause && (
                    <span className="inline-block mt-1 text-[11px] bg-amber-100 text-amber-900 px-2 py-0.5 rounded-full font-medium">
                      Verified Cause: {s.approved_cause}
                    </span>
                  )}
                </div>
                {s.status === "completed" && (
                  <Link
                    href={`/seasons/${s.id}`}
                    className="text-xs font-semibold text-emerald-700 hover:underline"
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
