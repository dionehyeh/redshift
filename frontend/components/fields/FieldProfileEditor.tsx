"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { FieldPatchResponse, FieldProfile } from "@/lib/field-types";
import { JobProgress } from "@/components/fields/JobProgress";

export function FieldProfileEditor({ field }: { field: FieldProfile }) {
  const router = useRouter();
  const [name, setName] = useState(field.name);
  const [latitude, setLatitude] = useState(String(field.lat));
  const [longitude, setLongitude] = useState(String(field.lon));
  const [area, setArea] = useState(field.area_ha?.toString() || "");
  const [waterSource, setWaterSource] = useState(field.water_source);
  const [waterQuality, setWaterQuality] = useState(field.water_quality);
  const [soilPh, setSoilPh] = useState("");
  const [soilOc, setSoilOc] = useState("");
  const [soilTexture, setSoilTexture] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const finishRebuild = useCallback(() => {
    setJobId(null);
    router.refresh();
  }, [router]);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const corrections: Array<{ key: string; value: string | number }> = [];
    if (soilPh.trim()) corrections.push({ key: "soil_ph", value: Number(soilPh) });
    if (soilOc.trim()) corrections.push({ key: "soil_oc", value: Number(soilOc) });
    if (soilTexture.trim()) corrections.push({ key: "soil_texture", value: soilTexture.trim() });

    try {
      const result = await api<FieldPatchResponse>(`/fields/${field.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          lat: Number(latitude),
          lon: Number(longitude),
          area_ha: area.trim() ? Number(area) : undefined,
          water_source: waterSource,
          water_quality: waterQuality,
          ...(corrections.length > 0 ? { corrections } : {}),
        }),
      });
      if (result.job_id) setJobId(result.job_id);
      else {
        setSoilPh("");
        setSoilOc("");
        setSoilTexture("");
        router.refresh();
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to update this field");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
      <h2 className="text-lg font-bold text-slate-900">Edit field profile</h2>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-sm text-slate-700">
          Field name
          <input required minLength={2} maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" />
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Area (hectares)
          <input type="number" min="0.01" step="any" value={area} onChange={(event) => setArea(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" />
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Latitude
          <input required type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" />
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Longitude
          <input required type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" />
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Water source
          <select value={waterSource} onChange={(event) => setWaterSource(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3">
            <option value="rainfed">Rain-fed</option>
            <option value="borewell">Borewell</option>
            <option value="canal">Canal irrigation</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Water quality
          <select value={waterQuality} onChange={(event) => setWaterQuality(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3">
            <option value="good">Good</option>
            <option value="saline">Saline</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Soil pH correction (0–14)
          <input type="number" min="0" max="14" step="any" value={soilPh} onChange={(event) => setSoilPh(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" placeholder={String(field.profile.soil_ph?.value ?? "")} />
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          Soil organic carbon correction
          <input type="number" min="0" max="100" step="any" value={soilOc} onChange={(event) => setSoilOc(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" placeholder={String(field.profile.soil_oc?.value ?? "")} />
        </label>
        <label className="space-y-1 text-sm text-slate-700 sm:col-span-2">
          Soil texture correction
          <input value={soilTexture} onChange={(event) => setSoilTexture(event.target.value)} className="h-10 w-full rounded-lg border border-slate-300 px-3" placeholder={String(field.profile.soil_texture?.value ?? "")} />
        </label>
      </div>

      <p className="text-xs text-slate-500">Only enter soil values you want to correct; submitted corrections are recorded for audit.</p>
      <button type="submit" disabled={saving} className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
        {saving ? "Saving…" : "Save field"}
      </button>
      {jobId && <JobProgress jobId={jobId} onDone={finishRebuild} />}
    </form>
  );
}
