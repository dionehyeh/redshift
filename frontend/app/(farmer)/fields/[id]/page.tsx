import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Compass,
  Pencil,
  Plus,
  MapPin,
  Sprout,
  Droplets,
  Mountain,
} from "lucide-react";
import { serverApi } from "@/lib/server-api";
import { ApiError } from "@/lib/api";
import { formatHectares } from "@/lib/format";
import type {
  FeasibleCropsResponse,
  FieldHistoryResponse,
  FieldMapData,
  FieldProfile,
  FieldTimeline,
} from "@/lib/field-types";
import { FieldProfileEditor } from "@/components/fields/FieldProfileEditor";
import { FieldTimeline as FieldTimelineView } from "@/components/fields/FieldTimeline";
import { JobProgress } from "@/components/fields/JobProgress";
import FieldMap from "@/components/fields/FieldMap";

function location(lat: number, lon: number) {
  return `${Math.abs(lat).toFixed(4)}°${lat < 0 ? "S" : "N"}, ${Math.abs(lon).toFixed(4)}°${lon < 0 ? "W" : "E"}`;
}

export default async function FieldDetailPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams?: { job_id?: string };
}) {
  const fieldId = Number(params.id);
  if (!Number.isSafeInteger(fieldId) || fieldId <= 0) {
    return (
      <div className="p-12 text-center space-y-4 bg-white rounded-3xl border-2 border-stone-200 max-w-md mx-auto">
        <h2 className="text-xl font-bold text-stone-800">Invalid field identifier</h2>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-800 text-white font-bold text-sm shadow-md"
        >
          <ArrowLeft className="w-4 h-4" /> Return to My Fields
        </Link>
      </div>
    );
  }

  let field: FieldProfile;
  try {
    field = await serverApi<FieldProfile>(`/fields/${fieldId}`);
  } catch (error) {
    return (
      <div className="space-y-4 rounded-3xl border-2 border-red-200 bg-red-50 p-8 text-center max-w-md mx-auto">
        <h2 className="text-xl font-bold text-red-900">Unable to load this field</h2>
        <p role="alert" className="text-sm text-red-800">
          {error instanceof Error ? error.message : "The field profile could not be retrieved."}
        </p>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-800 text-white font-bold text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Return to My Fields
        </Link>
      </div>
    );
  }

  const [feasibleResult, historyResult, mapResult, timelineResult] = await Promise.allSettled([
    serverApi<FeasibleCropsResponse | { crops: any[] }>(`/fields/${fieldId}/feasible-crops`),
    serverApi<FieldHistoryResponse | { seasons: any[] }>(`/fields/${fieldId}/history`),
    serverApi<FieldMapData>(`/fields/${fieldId}/map`),
    serverApi<FieldTimeline>(`/fields/${fieldId}/timeline`),
  ]);

  const feasible =
    feasibleResult.status === "fulfilled"
      ? "suitable" in feasibleResult.value
        ? [...feasibleResult.value.suitable, ...feasibleResult.value.marginal, ...feasibleResult.value.not_suitable]
        : (feasibleResult.value as any).crops || []
      : [];

  const history =
    historyResult.status === "fulfilled"
      ? (historyResult.value as any).seasons || []
      : [];

  const mapData = mapResult.status === "fulfilled" ? mapResult.value : null;
  const timeline = timelineResult.status === "fulfilled" ? timelineResult.value : null;

  const errors = [
    ...([feasibleResult, historyResult, mapResult, timelineResult].flatMap((result, index) => {
      if (result.status === "fulfilled") return [];
      const error = result.reason;
      if (index === 0 && error instanceof ApiError && error.code === "FIELD_NOT_READY") return [];
      const labels = ["Crop suitability", "Season history", "Field map", "Climate timeline"];
      return [`${labels[index]}: ${error instanceof Error ? error.message : "Request failed"}`];
    })),
  ];

  const profile = field.profile || {};
  const jobId = searchParams?.job_id;

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

      {jobId && field.profile_status !== "ready" && <JobProgress jobId={jobId} />}

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
                {location(field.lat, field.lon)}
              </span>
              <span>•</span>
              <span>{field.area_ha ? formatHectares(field.area_ha) : "Area not recorded"}</span>
              <span>•</span>
              <span className="capitalize">{field.water_source} water</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <a
              href="#edit-profile"
              className="px-4 py-3 rounded-2xl bg-white/15 backdrop-blur hover:bg-white/25 text-white text-sm font-bold flex items-center gap-1.5 transition shadow-sm"
            >
              <Pencil className="w-4 h-4 text-emerald-300" /> Edit Profile
            </a>
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

      {field.profile_status !== "ready" && (
        <div
          className={`rounded-2xl border-2 p-5 text-sm font-medium ${
            field.profile_status === "failed"
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-amber-200 bg-amber-50 text-amber-900"
          }`}
        >
          {field.profile_status === "failed"
            ? "Field setup could not retrieve the elevation or required climate data. Unavailable measurements are not replaced with regional defaults."
            : "Field data is being prepared from remote-sensing and soil sources. Missing provider data will be shown rather than estimated with regional defaults."}
        </div>
      )}

      {field.gaps.length > 0 && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-950">
          <p className="font-bold">Some field data is unavailable:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {field.gaps.map((gap) => <li key={gap}>{gap}</li>)}
          </ul>
        </div>
      )}

      {errors.length > 0 && (
        <div role="alert" className="space-y-1 rounded-2xl border-2 border-red-200 bg-red-50 p-5 text-sm text-red-800 font-medium">
          {errors.map((error) => (
            <p key={error}>{error}</p>
          ))}
        </div>
      )}

      {/* Agronomic Profile Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Elevation</span>
          <div className="text-2xl font-black text-stone-900">
            {profile.elevation_m?.value ?? "Unavailable"} {profile.elevation_m?.value != null ? "m" : ""}
          </div>
          <span className="text-[11px] text-green-700 font-semibold block">
            {profile.elevation_m?.source || "Source unavailable"}
          </span>
        </div>

        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Drainage & Hydrology</span>
          <div className="text-2xl font-black text-stone-900 capitalize">
            {String(profile.drainage?.value ?? "Unavailable")}
          </div>
          <span className="text-[11px] text-amber-700 font-semibold block">
            {profile.flood_prone?.value === true
              ? "Potential local low point (low confidence)"
              : profile.flood_prone?.value === false
              ? "No local low-point signal"
              : "Flood status unavailable; not a flood map"}
          </span>
        </div>

        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Soil Reaction (pH)</span>
          <div className="text-2xl font-black text-stone-900">{profile.soil_ph?.value ?? "Unavailable"}</div>
          <span className="text-[11px] text-green-700 font-semibold block">
            {profile.soil_ph?.source || "Source unavailable"}
          </span>
        </div>

        <div className="p-5 bg-white border-2 border-stone-200 rounded-2xl shadow-sm space-y-1">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Water Quality</span>
          <div className="text-2xl font-black text-stone-900 capitalize">{field.water_quality ?? "Unknown"}</div>
          <span className="text-[11px] text-blue-700 font-semibold block">Source: {field.water_source ?? "Unknown"}</span>
        </div>
      </div>

      {/* Field Map Section */}
      {mapData && (
        <section className="rounded-3xl border-2 border-stone-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-extrabold text-stone-900">Field Map</h2>
              <p className="text-xs text-stone-500 font-mono">
                {location(field.lat, field.lon)} · {field.area_ha ? formatHectares(field.area_ha) : "Area not recorded"}
              </p>
            </div>
            <div className="text-right text-xs text-stone-600">
              <p>Elevation: {profile.elevation_m?.value ?? "Unavailable"}{profile.elevation_m?.value != null ? " m" : ""}</p>
              <p>Flood status: {profile.flood_prone?.value === true ? "Potential low point" : profile.flood_prone?.value === false ? "No low-point signal" : "Unavailable"}</p>
            </div>
          </div>
          <FieldMap data={mapData} lat={field.lat} lon={field.lon} />
        </section>
      )}

      {/* Field Timeline Section */}
      {timeline && <FieldTimelineView timeline={timeline} />}

      {/* Regional Feasible Crops */}
      <div className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-extrabold text-stone-900">Regional Feasible Crops</h2>
            <p className="text-sm text-stone-500">Cross-matched against available soil, terrain, and 20-year NASA POWER climate data.</p>
          </div>
          <span className="text-xs px-3 py-1 bg-green-100 text-green-800 rounded-full font-bold">
            Kerala Agro-Ecological Zones
          </span>
        </div>

        {feasible.length === 0 ? (
          <p className="text-sm text-stone-500 italic">
            {field.profile_status === "ready"
              ? "No crop suitability results are available."
              : "Suitability will appear after field setup finishes."}
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {feasible.map((fc: any) => {
              const cropName = fc.crop_name || fc.crop || "Crop";
              const malayalam = fc.name_ml ? ` (${fc.name_ml})` : "";
              return (
                <div
                  key={fc.crop_id || fc.crop || cropName}
                  className="p-5 rounded-2xl border-2 border-stone-200 bg-stone-50/50 hover:border-green-300 transition flex flex-col justify-between space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-extrabold text-stone-900 text-lg">
                        {cropName.replace(/_/g, " ")}{malayalam}
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
                      {fc.class?.replace(/_/g, " ")}
                    </span>
                  </div>
                  {fc.start_windows && fc.start_windows.length > 0 && (
                    <div className="text-[11px] text-stone-500 font-semibold flex items-center gap-1.5 pt-2 border-t border-stone-200">
                      <span>Optimal planting window:</span>
                      <span className="text-green-800 font-bold">{fc.start_windows.join(", ")}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
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
                      {s.status || "completed"}
                    </span>
                  </div>
                  <p className="text-xs text-stone-500">
                    {s.start_date || "N/A"} to {s.end_date || "Ongoing"} • Outcome:{" "}
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

      {/* Field Profile Editor Section */}
      <div id="edit-profile">
        <FieldProfileEditor field={field} />
      </div>
    </div>
  );
}
