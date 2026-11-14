"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin, Droplets, Mountain, Sprout, Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { FieldCreateResponse } from "@/lib/field-types";

export default function NewFieldPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [lat, setLat] = useState(9.5833);
  const [lon, setLon] = useState(76.5167);
  const [areaHa, setAreaHa] = useState("1.2");
  const [waterSource, setWaterSource] = useState("canal");
  const [waterQuality, setWaterQuality] = useState("good");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await api<FieldCreateResponse>("/fields", {
        method: "POST",
        body: JSON.stringify({
          name,
          lat: Number(lat),
          lon: Number(lon),
          area_ha: areaHa ? Number(areaHa) : null,
          water_source: waterSource,
          water_quality: waterQuality,
        }),
      });

      const targetId = data.field_id || 1;
      const jobQuery = data.job_id ? `?job_id=${encodeURIComponent(data.job_id)}` : "";
      router.push(`/fields/${targetId}${jobQuery}`);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : "Failed to create field plot");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Top Left Navigation */}
      <div>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-700 hover:text-green-800 hover:border-green-300 font-semibold text-sm shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-green-700" /> Back to My Fields
        </Link>
      </div>

      {/* Header */}
      <div className="space-y-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
          <Sprout className="w-3.5 h-3.5" /> New Observation Point
        </span>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Add Agricultural Plot
        </h1>
        <p className="text-stone-600 text-sm">
          Set coordinates to extract 20+ years of NASA Earth observations (POWER radiation, IMD rainfall, SRTM topography) for this location.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-800 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Form Card */}
      <form
        onSubmit={handleSubmit}
        className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-5"
      >
        <div className="space-y-1.5">
          <label className="text-sm font-bold text-stone-800">Plot Name</label>
          <input
            type="text"
            required
            placeholder="e.g. Kuttanad Demonstration Plot"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-900 transition"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-stone-800 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-green-700" /> Latitude (°N)
            </label>
            <input
              type="number"
              step="0.0001"
              required
              value={lat}
              onChange={(e) => setLat(Number(e.target.value))}
              className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-mono text-stone-900 text-sm transition"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-stone-800 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-green-700" /> Longitude (°E)
            </label>
            <input
              type="number"
              step="0.0001"
              required
              value={lon}
              onChange={(e) => setLon(Number(e.target.value))}
              className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-mono text-stone-900 text-sm transition"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-bold text-stone-800 flex items-center gap-1.5">
            <Mountain className="w-4 h-4 text-amber-700" /> Plot Area (Hectares, optional)
          </label>
          <input
            type="number"
            min="0.01"
            step="0.1"
            value={areaHa}
            onChange={(e) => setAreaHa(e.target.value)}
            className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-900 transition"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-stone-800 flex items-center gap-1.5">
              <Droplets className="w-4 h-4 text-blue-600" /> Water Source
            </label>
            <select
              value={waterSource}
              onChange={(e) => setWaterSource(e.target.value)}
              className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
            >
              <option value="canal">Canal Irrigation</option>
              <option value="rainfed">Rain-fed</option>
              <option value="borewell">Borewell</option>
              <option value="unknown">Not Specified</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-stone-800">Water Quality</label>
            <select
              value={waterQuality}
              onChange={(e) => setWaterQuality(e.target.value)}
              className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
            >
              <option value="good">Good Fresh Water</option>
              <option value="saline">Saline / Brackish</option>
              <option value="unknown">Not Tested</option>
            </select>
          </div>
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full h-13 py-3.5 rounded-xl bg-gradient-to-r from-green-700 to-emerald-700 text-white font-bold text-base shadow-md hover:shadow-lg hover:from-green-800 hover:to-emerald-800 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <Plus className="w-5 h-5" />
            {loading ? "Extracting NASA Data..." : "Create Plot & Extract NASA Data"}
          </button>
        </div>
      </form>
    </div>
  );
}
