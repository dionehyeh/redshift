import Link from "next/link";
import {
  Plus,
  MapPin,
  ArrowRight,
  Droplets,
  CalendarPlus,
  Compass,
} from "lucide-react";
import { serverApi } from "@/lib/server-api";
import type { FieldListItem, FieldListResponse } from "@/lib/field-types";
import { formatHectares } from "@/lib/format";
import { RiskBadge } from "@/components/risk/RiskBadge";
import { ErrorBanner } from "@/components/common/ErrorBanner";

function getStatusBadgeConfig(status: FieldListItem["profile_status"]) {
  switch (status) {
    case "ready":
      return { level: "green" as const, label: "Profile Ready" };
    case "failed":
      return { level: "red" as const, label: "Analysis Failed" };
    case "building":
    case "pending":
    default:
      return { level: "amber" as const, label: "Analyzing Data..." };
  }
}

function formatWaterSource(source: string): string {
  switch (source?.toLowerCase()) {
    case "rainfed":
      return "Rain-fed";
    case "borewell":
      return "Borewell";
    case "canal":
      return "Canal";
    default:
      return "Water source unset";
  }
}

export default async function FieldsPage() {
  let fields: FieldListItem[] = [];
  let fetchError: { code: string; message: string } | null = null;

  try {
    const data = await serverApi<FieldListResponse>("/fields");
    fields = data.items || [];
  } catch (err) {
    fetchError = {
      code: "DATA_UNAVAILABLE",
      message:
        err instanceof Error
          ? err.message
          : "Unable to connect to the backend service. Please ensure the backend is running.",
    };
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Your Agricultural Plots
          </h1>
          <p className="text-base text-slate-600 mt-1">
            Select a plot to view 20+ years of NASA Earth observations, assess soil health, or plan climate-resilient rotations.
          </p>
        </div>

        <Link
          href="/fields/new"
          className="inline-flex items-center justify-center gap-2 h-12 px-6 rounded-xl bg-emerald-700 text-white font-semibold hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2 transition shadow-sm"
        >
          <Plus className="w-5 h-5" />
          <span>Add New Plot</span>
        </Link>
      </div>

      {/* Error state if backend unreachable */}
      {fetchError && (
        <ErrorBanner
          code={fetchError.code}
          message={fetchError.message}
        />
      )}

      {/* Empty State */}
      {!fetchError && fields.length === 0 && (
        <div className="p-8 sm:p-12 text-center bg-white border border-slate-200 rounded-3xl shadow-sm space-y-5">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
            <MapPin className="w-8 h-8" />
          </div>

          <div className="space-y-2 max-w-md mx-auto">
            <h2 className="text-2xl font-bold text-slate-900">No plots added yet</h2>
            <p className="text-base text-slate-600">
              Drop a pin on your field to extract 20+ years of NASA Earth observations (POWER radiation, IMD rainfall normals, SRTM elevation) and identify feasible rotation crops.
            </p>
          </div>

          <div className="pt-2">
            <Link
              href="/fields/new"
              className="inline-flex items-center justify-center gap-2 h-12 px-8 rounded-xl bg-emerald-700 text-white text-base font-semibold hover:bg-emerald-800 transition shadow-sm"
            >
              <Plus className="w-5 h-5" />
              <span>Add Your First Plot</span>
            </Link>
          </div>
        </div>
      )}

      {/* Fields Grid */}
      {fields.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {fields.map((field) => {
            const statusConfig = getStatusBadgeConfig(field.profile_status);

            return (
              <div
                key={field.id}
                className="group bg-white border border-slate-200 rounded-3xl p-6 hover:border-emerald-500 hover:shadow-md transition-all duration-200 flex flex-col justify-between space-y-5"
              >
                <div className="space-y-3">
                  {/* Header: Field Name & Multi-Sensory Status Badge */}
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-2xl font-bold text-slate-900 group-hover:text-emerald-800 transition line-clamp-1">
                      {field.name}
                    </h2>
                    <RiskBadge
                      level={statusConfig.level}
                      label={statusConfig.label}
                    />
                  </div>

                  {/* Geolocation Coordinates */}
                  <div className="flex items-center gap-2 text-sm text-slate-600 font-mono">
                    <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span>
                      {Math.abs(field.lat).toFixed(4)}° {field.lat >= 0 ? "N" : "S"},{" "}
                      {Math.abs(field.lon).toFixed(4)}° {field.lon >= 0 ? "E" : "W"}
                    </span>
                  </div>

                  {/* Physical & Agronomic Attributes */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-700">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 font-medium">
                      <Droplets className="w-3.5 h-3.5 text-blue-600" />
                      {formatWaterSource(field.water_source)}
                    </span>

                    {field.area_ha != null && field.area_ha > 0 && (
                      <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-100 font-medium">
                        {formatHectares(field.area_ha)}
                      </span>
                    )}

                  </div>
                </div>

                {/* Card Actions & Navigation */}
                <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-2">
                  <Link
                    href={`/fields/${field.id}`}
                    className="inline-flex items-center gap-2 text-sm font-bold text-emerald-700 hover:text-emerald-900 transition h-11 px-2 -ml-2 rounded-lg"
                  >
                    <span>View Field Profile</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </Link>

                  <div className="flex items-center gap-2">
                    <Link
                      href={`/fields/${field.id}/plan/new`}
                      title="Plan Crop Rotation"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-800 transition h-11 px-3.5 rounded-xl"
                    >
                      <Compass className="w-4 h-4 text-emerald-600" />
                      <span>Plan</span>
                    </Link>

                    <Link
                      href={`/fields/${field.id}/seasons/new`}
                      title="Log Past Season"
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-blue-50 hover:text-blue-800 transition h-11 px-3.5 rounded-xl"
                    >
                      <CalendarPlus className="w-4 h-4 text-blue-600" />
                      <span>History</span>
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
