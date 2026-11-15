import Link from "next/link";
import {
  Plus,
  MapPin,
  ArrowRight,
  Droplets,
  CalendarPlus,
  Compass,
  Sprout,
  Mountain,
  Wheat,
  TreePine,
  Waves,
} from "lucide-react";
import { serverApi } from "@/lib/server-api";
import type { FieldListItem, FieldListResponse } from "@/lib/field-types";
import { formatHectares } from "@/lib/format";
import { ErrorBanner } from "@/components/common/ErrorBanner";

/* ── Status badge ── */
function StatusPill({ status }: { status: string }) {
  const map: Record<string, { bg: string; dot: string; label: string }> = {
    ready: {
      bg: "bg-emerald-100 text-emerald-800",
      dot: "bg-emerald-500",
      label: "Profile Ready",
    },
    failed: {
      bg: "bg-red-100 text-red-800",
      dot: "bg-red-500",
      label: "Analysis Failed",
    },
    building: {
      bg: "bg-amber-100 text-amber-800",
      dot: "bg-amber-500",
      label: "Analyzing…",
    },
    pending: {
      bg: "bg-amber-100 text-amber-800",
      dot: "bg-amber-500",
      label: "Pending…",
    },
  };
  const cfg = map[status] || map.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full ${cfg.bg}`}
    >
      <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

/* ── Water source label ── */
function waterLabel(s: string) {
  if (s === "rainfed") return "🌧️ Rain-fed";
  if (s === "borewell") return "🔵 Borewell";
  if (s === "canal") return "🏞️ Canal";
  return "💧 Unknown";
}

/* ── Per-card accent configs ── */
const CARD_THEMES = [
  {
    gradient: "from-emerald-600 to-green-800",
    iconBg: "bg-emerald-700",
    border: "border-emerald-200 hover:border-emerald-400",
    Icon: Sprout,
    illustration: "🌾",
  },
  {
    gradient: "from-amber-600 to-yellow-800",
    iconBg: "bg-amber-700",
    border: "border-amber-200 hover:border-amber-400",
    Icon: Wheat,
    illustration: "🌻",
  },
  {
    gradient: "from-green-700 to-emerald-900",
    iconBg: "bg-green-800",
    border: "border-green-200 hover:border-green-400",
    Icon: TreePine,
    illustration: "🍃",
  },
  {
    gradient: "from-teal-600 to-cyan-800",
    iconBg: "bg-teal-700",
    border: "border-teal-200 hover:border-teal-400",
    Icon: Waves,
    illustration: "🌿",
  },
];

export default async function FieldsPage() {
  let fields: FieldListItem[] = [];
  let fetchError: { code: string; message: string } | null = null;

  try {
    const data = await serverApi<FieldListResponse | { items: FieldListItem[] }>("/fields");
    fields = data.items || [];
  } catch (err) {
    fetchError = {
      code: "DATA_UNAVAILABLE",
      message:
        err instanceof Error
          ? err.message
          : "Unable to connect to the backend. Make sure the server is running.",
    };
  }

  return (
    <div className="flex flex-col items-center">
      {/* ═══════════════════════════════════════
           PAGE HERO — centered
         ═══════════════════════════════════════ */}
      <div className="text-center max-w-2xl mx-auto mb-10 space-y-4">
        {/* NASA badge */}
        <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-900 text-emerald-300 text-xs font-bold uppercase tracking-widest shadow">
          <Sprout className="w-4 h-4" />
          Powered by NASA Earth Data
        </span>

        <h1 className="text-4xl sm:text-5xl font-black text-stone-900 tracking-tight leading-[1.1]">
          Your Agricultural{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-700 to-emerald-600">
            Plots
          </span>
        </h1>

        <p className="text-stone-500 text-base sm:text-lg max-w-md mx-auto">
          Select a plot to explore 20+ years of satellite data, soil health
          reports, and climate-resilient crop plans.
        </p>

        {/* Add Plot CTA */}
        <div className="pt-2">
          <Link
            href="/fields/new"
            className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-2xl bg-gradient-to-r from-green-700 to-emerald-700 text-white font-bold text-base shadow-lg shadow-green-700/25 hover:shadow-xl hover:shadow-green-700/30 hover:-translate-y-0.5 active:translate-y-0 transition-all"
          >
            <Plus className="w-5 h-5" />
            Add New Plot
          </Link>
        </div>
      </div>

      {/* ═══════════════════════════════════════
           ERROR BANNER
         ═══════════════════════════════════════ */}
      {fetchError && (
        <div className="w-full max-w-md mb-8">
          <ErrorBanner code={fetchError.code} message={fetchError.message} />
        </div>
      )}

      {/* ═══════════════════════════════════════
           EMPTY STATE
         ═══════════════════════════════════════ */}
      {!fetchError && fields.length === 0 && (
        <div className="w-full max-w-md bg-white rounded-3xl border-2 border-dashed border-stone-300 p-12 text-center space-y-5 shadow-sm">
          <div className="text-6xl">🗺️</div>
          <h2 className="text-2xl font-extrabold text-stone-800">
            No plots added yet
          </h2>
          <p className="text-stone-500 text-sm leading-relaxed">
            Drop a pin on your field to extract 20+ years of NASA POWER
            radiation, IMD rainfall, SRTM elevation, and identify feasible
            rotation crops.
          </p>
          <Link
            href="/fields/new"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-green-700 to-emerald-700 text-white font-bold shadow-lg shadow-green-700/25 hover:shadow-xl transition-all"
          >
            <Plus className="w-5 h-5" />
            Add Your First Plot
          </Link>
        </div>
      )}

      {/* ═══════════════════════════════════════
           FIELD CARDS GRID — centered square cards
         ═══════════════════════════════════════ */}
      {fields.length > 0 && (
        <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-7 justify-items-center">
          {fields.map((field, i) => {
            const theme = CARD_THEMES[i % CARD_THEMES.length];
            const FieldIcon = theme.Icon;

            return (
              <div
                key={field.id}
                className={`group relative w-full max-w-[340px] aspect-square bg-white rounded-3xl border-2 ${theme.border} shadow-md hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col`}
              >
                {/* ── Colored header band ── */}
                <div
                  className={`relative bg-gradient-to-r ${theme.gradient} px-6 pt-5 pb-14`}
                >
                  {/* Decorative large emoji */}
                  <span className="absolute right-4 top-3 text-4xl opacity-20 select-none">
                    {theme.illustration}
                  </span>

                  {/* Icon + Name */}
                  <div className="relative z-10 flex items-start gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center flex-shrink-0 shadow-inner">
                      <FieldIcon className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h2 className="text-white font-extrabold text-lg leading-snug line-clamp-2 drop-shadow-sm">
                        {field.name}
                      </h2>
                    </div>
                  </div>
                </div>

                {/* ── Card body ── */}
                <div className="flex-1 px-6 -mt-8 relative z-10 flex flex-col">
                  {/* Status badge floating on the color/white boundary */}
                  <div className="mb-4">
                    <StatusPill status={field.profile_status} />
                  </div>

                  {/* Info rows */}
                  <div className="space-y-2.5 text-sm text-stone-600 flex-1">
                    {/* Coordinates */}
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-4 h-4 text-stone-500" />
                      </div>
                      <span className="font-mono text-xs text-stone-500">
                        {Math.abs(field.lat).toFixed(4)}°{" "}
                        {field.lat >= 0 ? "N" : "S"},{" "}
                        {Math.abs(field.lon).toFixed(4)}°{" "}
                        {field.lon >= 0 ? "E" : "W"}
                      </span>
                    </div>

                    {/* Water */}
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                        <Droplets className="w-4 h-4 text-blue-500" />
                      </div>
                      <span className="font-semibold text-stone-700">
                        {waterLabel(field.water_source)}
                      </span>
                      {field.water_quality &&
                        field.water_quality !== "unknown" && (
                          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-bold uppercase">
                            {field.water_quality}
                          </span>
                        )}
                    </div>

                    {/* Area */}
                    {field.area_ha != null && field.area_ha > 0 && (
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
                          <Mountain className="w-4 h-4 text-amber-600" />
                        </div>
                        <span className="font-semibold text-stone-700">
                          {formatHectares(field.area_ha)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* ── Action buttons ── */}
                  <div className="pt-4 pb-5 flex items-center gap-2">
                    <Link
                      href={`/fields/${field.id}`}
                      className={`flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-gradient-to-r ${theme.gradient} text-white text-sm font-bold shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all`}
                    >
                      View Profile
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                    <Link
                      href={`/fields/${field.id}/plan/new`}
                      title="Plan Crop Rotation"
                      className="w-10 h-10 rounded-xl bg-stone-100 hover:bg-emerald-100 text-stone-500 hover:text-emerald-700 flex items-center justify-center transition-all"
                    >
                      <Compass className="w-5 h-5" />
                    </Link>
                    <Link
                      href={`/fields/${field.id}/seasons/new`}
                      title="Log Past Season"
                      className="w-10 h-10 rounded-xl bg-stone-100 hover:bg-amber-100 text-stone-500 hover:text-amber-700 flex items-center justify-center transition-all"
                    >
                      <CalendarPlus className="w-5 h-5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
