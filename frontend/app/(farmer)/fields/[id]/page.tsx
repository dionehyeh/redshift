import Link from "next/link";
import { ArrowLeft, Calendar, Compass, Pencil, Plus } from "lucide-react";
import { serverApi } from "@/lib/server-api";
import { ApiError } from "@/lib/api";
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
      <div className="p-8 text-center space-y-4">
        <h2 className="text-xl font-bold text-slate-800">Invalid field identifier</h2>
        <Link href="/fields" className="text-emerald-700 underline text-sm">Return to fields</Link>
      </div>
    );
  }

  let field: FieldProfile;
  try {
    field = await serverApi<FieldProfile>(`/fields/${fieldId}`);
  } catch (error) {
    return (
      <div className="space-y-4 rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
        <h2 className="text-xl font-bold text-red-900">Unable to load this field</h2>
        <p role="alert" className="text-sm text-red-800">
          {error instanceof Error ? error.message : "The field profile could not be retrieved."}
        </p>
        <Link href="/fields" className="text-emerald-700 underline text-sm">Return to fields</Link>
      </div>
    );
  }

  const [feasibleResult, historyResult, mapResult, timelineResult] = await Promise.allSettled([
    serverApi<FeasibleCropsResponse>(`/fields/${fieldId}/feasible-crops`),
    serverApi<FieldHistoryResponse>(`/fields/${fieldId}/history`),
    serverApi<FieldMapData>(`/fields/${fieldId}/map`),
    serverApi<FieldTimeline>(`/fields/${fieldId}/timeline`),
  ]);
  const feasible =
    feasibleResult.status === "fulfilled"
      ? [...feasibleResult.value.suitable, ...feasibleResult.value.marginal, ...feasibleResult.value.not_suitable]
      : [];
  const history = historyResult.status === "fulfilled" ? historyResult.value.seasons : [];
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
    <div className="space-y-6">
      <Link href="/fields" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Back to My Fields
      </Link>

      {jobId && field.profile_status !== "ready" && <JobProgress jobId={jobId} />}

      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">{field.name}</h1>
          <p className="font-mono text-sm text-slate-500">
            {location(field.lat, field.lon)} · {field.climate_cell_id ? `Cell ${field.climate_cell_id}` : "Climate cell pending"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a href="#edit-profile" className="flex h-11 items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50">
            <Pencil className="h-4 w-4" /> Edit Profile
          </a>
          <Link href={`/fields/${fieldId}/seasons/new`} className="flex h-11 items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50">
            <Calendar className="h-4 w-4" /> Log Season
          </Link>
          <Link href={`/fields/${fieldId}/plan/new`} className="flex h-11 items-center gap-1.5 rounded-xl bg-emerald-700 px-5 text-sm font-semibold text-white hover:bg-emerald-800">
            <Compass className="h-4 w-4" /> Plan Rotations
          </Link>
        </div>
      </div>

      {field.profile_status !== "ready" && (
        <div className={`rounded-xl border p-4 text-sm ${
          field.profile_status === "failed"
            ? "border-red-200 bg-red-50 text-red-800"
            : "border-amber-200 bg-amber-50 text-amber-900"
        }`}>
          {field.profile_status === "failed"
            ? "Field setup failed. The field record is saved, but profile and crop suitability data need attention."
            : "Field data is still being prepared. Profile values and crop suitability may be incomplete."}
        </div>
      )}

      {errors.length > 0 && (
        <div role="alert" className="space-y-1 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {errors.map((error) => <p key={error}>{error}</p>)}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <span className="block text-xs text-slate-500">Elevation</span>
          <span className="text-lg font-bold text-slate-900">{profile.elevation_m?.value ?? "—"}{profile.elevation_m?.value != null ? " m" : ""}</span>
          <span className="mt-1 block text-[10px] text-slate-400">{profile.elevation_m?.source || "Not available"}</span>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <span className="block text-xs text-slate-500">Drainage & basin</span>
          <span className="text-lg font-bold capitalize text-slate-900">{String(profile.drainage?.value ?? "—")}</span>
          <span className="mt-1 block text-[10px] text-slate-400">
            {profile.flood_prone?.value === true ? "Flood-prone estimate" : profile.flood_prone?.value === false ? "No flood flag" : "Flood status unavailable"}
          </span>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <span className="block text-xs text-slate-500">Soil pH</span>
          <span className="text-lg font-bold text-slate-900">{profile.soil_ph?.value ?? "—"}</span>
          <span className="mt-1 block text-[10px] text-slate-400">{profile.soil_ph?.source || "Not available"}</span>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <span className="block text-xs text-slate-500">Water source</span>
          <span className="text-lg font-bold capitalize text-slate-900">{field.water_source}</span>
          <span className="mt-1 block text-[10px] text-slate-400">Quality: {field.water_quality}</span>
        </div>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Field map</h2>
            <p className="text-xs text-slate-500">{location(field.lat, field.lon)} · {field.area_ha ?? "Area not set"} hectares</p>
          </div>
          <div className="text-right text-xs text-slate-600">
            <p>Elevation: {profile.elevation_m?.value ?? "Unavailable"}{profile.elevation_m?.value != null ? " m" : ""}</p>
            <p>Flood flag: {profile.flood_prone?.value == null ? "Unavailable" : profile.flood_prone.value ? "Prone" : "Not flagged"}</p>
          </div>
        </div>
        {mapData ? (
          <FieldMap data={mapData} lat={field.lat} lon={field.lon} />
        ) : (
          <p className="rounded-lg bg-amber-50 p-4 text-sm text-amber-900">The map could not be loaded.</p>
        )}
        <p className="text-[11px] text-slate-500">If no surveyed boundary is stored, the map marks only the recorded coordinate; it does not estimate a field outline.</p>
      </section>

      {timeline && <FieldTimelineView timeline={timeline} />}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Regional feasible crops</h2>
          <p className="text-xs text-slate-500">Suitability reflects the stored field profile and seasonal assumptions.</p>
        </div>
        {feasible.length === 0 ? (
          <p className="text-sm text-slate-500">
            {field.profile_status === "ready" ? "No crop suitability results are available." : "Suitability will appear after field setup finishes."}
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {feasible.map((crop) => (
              <div key={crop.crop_id} className="flex items-center justify-between gap-4 py-3">
                <div>
                  <span className="font-semibold capitalize text-slate-900">{crop.crop_name.replace(/_/g, " ")}</span>
                  <p className="text-xs text-slate-500">{crop.reason}</p>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${
                  crop.class === "suitable" ? "bg-emerald-100 text-emerald-800" :
                  crop.class === "marginal" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"
                }`}>{crop.class.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Recorded seasons</h2>
          <Link href={`/fields/${fieldId}/seasons/new`} className="flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:underline">
            <Plus className="h-3.5 w-3.5" /> Log past season
          </Link>
        </div>
        {history.length === 0 ? (
          <p className="text-sm italic text-slate-500">No past seasons logged for this field.</p>
        ) : (
          <div className="space-y-3">
            {history.map((season) => (
              <div key={season.id} className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div>
                  <span className="font-bold capitalize text-slate-800">{season.crop_name || "Crop not specified"} ({season.status || "unknown"})</span>
                  <p className="text-xs text-slate-500">{season.start_date || "Date not recorded"} to {season.end_date || "Ongoing"} · Outcome: {season.outcome || "Not recorded"}</p>
                  {season.approved_cause && <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-900">Verified cause: {season.approved_cause}</span>}
                </div>
                {season.status === "completed" && (
                  <Link href={`/seasons/${season.id}`} className="shrink-0 text-xs font-semibold text-emerald-700 hover:underline">View diagnosis</Link>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <div id="edit-profile">
        <FieldProfileEditor field={field} />
      </div>
    </div>
  );
}
