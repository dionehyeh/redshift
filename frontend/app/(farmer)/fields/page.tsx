import Link from "next/link";
import { Plus, MapPin, ArrowRight } from "lucide-react";
import { serverApi } from "@/lib/server-api";

export default async function FieldsPage() {
  let fields: any[] = [];
  try {
    const data = await serverApi<{ items: any[] }>("/fields");
    fields = data.items || [];
  } catch (err) {
    fields = [];
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Your Agricultural Plots</h1>
          <p className="text-sm text-slate-600">Select a plot to view soil profile, diagnose past seasons, or plan rotations.</p>
        </div>
        <Link
          href="/fields/new"
          className="inline-flex items-center gap-1.5 h-11 px-4 rounded-xl bg-emerald-700 text-white font-medium hover:bg-emerald-800 transition"
        >
          <Plus className="w-4 h-4" /> Add Field
        </Link>
      </div>

      {fields.length === 0 ? (
        <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl space-y-4">
          <MapPin className="w-12 h-12 text-slate-400 mx-auto" />
          <h3 className="font-bold text-slate-800">No plots added yet</h3>
          <p className="text-sm text-slate-600 max-w-sm mx-auto">
            Drop a pin on your field to extract 20+ years of NASA Earth observations, terrain elevation, and feasible crops.
          </p>
          <Link
            href="/fields/new"
            className="inline-flex items-center gap-1.5 h-11 px-5 rounded-xl bg-emerald-700 text-white text-sm font-medium"
          >
            <Plus className="w-4 h-4" /> Add Your First Plot
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {fields.map((f) => (
            <Link
              key={f.id}
              href={`/fields/${f.id}`}
              className="p-5 bg-white border border-slate-200 rounded-2xl hover:border-emerald-500 hover:shadow-sm transition flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-lg text-slate-900">{f.name}</h3>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                      f.profile_status === "ready"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {f.profile_status === "ready" ? "Profile Ready" : "Analyzing Data..."}
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-mono">
                  {f.lat.toFixed(3)}°N, {f.lon.toFixed(3)}°E · {f.water_source}
                </p>
              </div>

              <div className="pt-4 flex items-center justify-between text-sm font-semibold text-emerald-700">
                <span>View Field Details</span>
                <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
