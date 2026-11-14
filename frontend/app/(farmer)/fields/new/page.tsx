"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin } from "lucide-react";

export default function NewFieldPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [lat, setLat] = useState(9.50);
  const [lon, setLon] = useState(76.40);
  const [areaHa, setAreaHa] = useState("1.0");
  const [waterSource, setWaterSource] = useState("rainfed");
  const [waterQuality, setWaterQuality] = useState("unknown");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/fields", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          lat: Number(lat),
          lon: Number(lon),
          area_ha: Number(areaHa),
          water_source: waterSource,
          water_quality: waterQuality,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || "Failed to create field");
      }

      router.push(`/fields/${data.field_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create field");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <Link href="/fields" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to My Fields
      </Link>

      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-slate-900">Add New Agricultural Plot</h1>
        <p className="text-sm text-slate-600">Enter coordinates or drop a pin to extract NASA elevation & weather series.</p>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">Plot Name</label>
          <input
            type="text"
            required
            placeholder="e.g. West Canal Plot"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-11 px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Latitude</label>
            <input
              type="number"
              step="0.0001"
              required
              value={lat}
              onChange={(e) => setLat(Number(e.target.value))}
              className="w-full h-11 px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Longitude</label>
            <input
              type="number"
              step="0.0001"
              required
              value={lon}
              onChange={(e) => setLon(Number(e.target.value))}
              className="w-full h-11 px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none font-mono text-sm"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">Area (Hectares)</label>
          <input
            type="number"
            step="0.1"
            value={areaHa}
            onChange={(e) => setAreaHa(e.target.value)}
            className="w-full h-11 px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Primary Water Source</label>
            <select
              value={waterSource}
              onChange={(e) => setWaterSource(e.target.value)}
              className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
            >
              <option value="rainfed">Rain-fed</option>
              <option value="borewell">Borewell</option>
              <option value="canal">Canal Irrigation</option>
              <option value="unknown">Not Sure</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Water Quality</label>
            <select
              value={waterQuality}
              onChange={(e) => setWaterQuality(e.target.value)}
              className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
            >
              <option value="good">Good Fresh Water</option>
              <option value="saline">Saline / Brackish</option>
              <option value="unknown">Not Tested</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full h-12 rounded-xl bg-emerald-700 text-white font-medium hover:bg-emerald-800 transition disabled:opacity-50"
        >
          {loading ? "Initializing Field Profile..." : "Create Plot & Extract NASA Data"}
        </button>
      </form>
    </div>
  );
}
