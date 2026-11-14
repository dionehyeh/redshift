"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NewSeasonPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const fieldId = params.id;

  const [crop, setCrop] = useState("paddy");
  const [startDate, setStartDate] = useState("2025-09-20");
  const [endDate, setEndDate] = useState("2026-01-15");
  const [outcome, setOutcome] = useState("poor");
  const [lossPercent, setLossPercent] = useState(50);
  const [suspectedCause, setSuspectedCause] = useState("water_shortage");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`/api/fields/${fieldId}/seasons`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          crop,
          start_date: startDate,
          end_date: endDate,
          outcome,
          loss_percent: outcome === "poor" || outcome === "failed" ? Number(lossPercent) : 0,
          suspected_cause: suspectedCause,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || "Failed to log season");
      }

      // Trigger background diagnostic analysis
      await fetch(`/api/seasons/${data.id}/analyze`, { method: "POST" });
      router.push(`/seasons/${data.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to log season");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <Link href={`/fields/${fieldId}`} className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to Plot
      </Link>

      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-slate-900">Log Completed Harvest Season</h1>
        <p className="text-sm text-slate-600">Provide harvest outcome to diagnose stress weeks against NASA 20-year normals.</p>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">Crop Cultivated</label>
          <select
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
            className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="paddy">Paddy (Rice)</option>
            <option value="green_gram">Green Gram</option>
            <option value="cowpea">Cowpea</option>
            <option value="sesame">Sesame</option>
            <option value="banana">Banana</option>
            <option value="tapioca">Tapioca</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Sowing Date</label>
            <input
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full h-11 px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Harvest Date</label>
            <input
              type="date"
              required
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full h-11 px-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Harvest Outcome</label>
          <div className="grid grid-cols-4 gap-2">
            {["good", "average", "poor", "failed"].map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setOutcome(opt)}
                className={`h-11 rounded-xl text-xs font-bold capitalize transition border ${
                  outcome === opt
                    ? "bg-emerald-700 text-white border-emerald-700"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        {(outcome === "poor" || outcome === "failed") && (
          <div className="space-y-3 pt-2">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Estimated Crop Loss: {lossPercent}%</label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={lossPercent}
                onChange={(e) => setLossPercent(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg accent-emerald-700 cursor-pointer"
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Suspected Reason (Optional)</label>
              <select
                value={suspectedCause}
                onChange={(e) => setSuspectedCause(e.target.value)}
                className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
              >
                <option value="water_shortage">Water Shortage / Dry Spell</option>
                <option value="excess_rain">Flooding / Waterlogging</option>
                <option value="pests">Pest or Fungal Attack</option>
                <option value="unsure">Not Sure / Unclear</option>
              </select>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full h-12 rounded-xl bg-emerald-700 text-white font-medium hover:bg-emerald-800 transition disabled:opacity-50"
        >
          {loading ? "Diagnosing NASA Weather History..." : "Save Season & Run Diagnostic"}
        </button>
      </form>
    </div>
  );
}
