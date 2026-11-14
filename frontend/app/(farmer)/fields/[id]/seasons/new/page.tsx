"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Calendar, Sparkles, Sprout } from "lucide-react";
import { api } from "@/lib/api";

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
      const data = await api<{ id?: number; season_id?: number }>(`/fields/${fieldId}/seasons`, {
        method: "POST",
        body: JSON.stringify({
          crop,
          start_date: startDate,
          end_date: endDate,
          outcome,
          loss_percent: outcome === "poor" || outcome === "failed" ? Number(lossPercent) : 0,
          suspected_cause: suspectedCause,
        }),
      });

      const targetSeasonId = data.id || data.season_id || 1;
      // Trigger background diagnostic analysis if available
      try {
        await api(`/seasons/${targetSeasonId}/analyze`, { method: "POST" });
      } catch {
        // silent fallback
      }
      router.push(`/seasons/${targetSeasonId}`);
    } catch (err: any) {
      setError(err.message || "Failed to log season");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Top Left Navigation */}
      <div>
        <Link
          href={`/fields/${fieldId}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-700 hover:text-green-800 hover:border-green-300 font-semibold text-sm shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-green-700" /> Back to Plot
        </Link>
      </div>

      <div className="space-y-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
          <Calendar className="w-3.5 h-3.5" /> Historical Harvest Calibration
        </span>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Log Completed Harvest Season
        </h1>
        <p className="text-stone-600 text-sm">
          Provide your observed harvest outcome to diagnose stress weeks against NASA 20-year precipitation and temperature normals.
        </p>
      </div>

      {error && (
        <div className="p-4 text-sm text-red-800 bg-red-50 border border-red-200 rounded-xl font-medium">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-5"
      >
        <div className="space-y-1.5">
          <label className="text-sm font-bold text-stone-800">Crop Cultivated</label>
          <select
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
            className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
          >
            <option value="paddy">Paddy (Rice / നെല്ല്)</option>
            <option value="green_gram">Green Gram (ചെറുപയർ)</option>
            <option value="cowpea">Cowpea (വൻപയർ)</option>
            <option value="sesame">Sesame (എള്ള്)</option>
            <option value="banana">Banana (വാഴ)</option>
            <option value="tapioca">Tapioca (കപ്പ)</option>
          </select>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-stone-800">Sowing / Planting Date</label>
            <input
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-mono text-stone-900 text-sm transition"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-stone-800">Harvest Date</label>
            <input
              type="date"
              required
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-mono text-stone-900 text-sm transition"
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-bold text-stone-800">Observed Harvest Outcome</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[
              { val: "good", label: "Good", color: "bg-emerald-700 text-white border-emerald-700" },
              { val: "average", label: "Average", color: "bg-blue-700 text-white border-blue-700" },
              { val: "poor", label: "Poor", color: "bg-amber-600 text-white border-amber-600" },
              { val: "failed", label: "Failed", color: "bg-red-700 text-white border-red-700" },
            ].map((opt) => (
              <button
                key={opt.val}
                type="button"
                onClick={() => setOutcome(opt.val)}
                className={`h-12 rounded-xl text-xs font-extrabold capitalize transition-all border-2 ${
                  outcome === opt.val
                    ? opt.color + " shadow-md"
                    : "bg-stone-50 text-stone-700 border-stone-200 hover:bg-stone-100"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {(outcome === "poor" || outcome === "failed") && (
          <div className="p-5 bg-stone-50 border-2 border-stone-200 rounded-2xl space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-bold text-stone-800 flex justify-between">
                <span>Estimated Crop Loss</span>
                <span className="text-red-700 font-extrabold">{lossPercent}%</span>
              </label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={lossPercent}
                onChange={(e) => setLossPercent(Number(e.target.value))}
                className="w-full h-2 bg-stone-200 rounded-lg accent-green-700 cursor-pointer"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-bold text-stone-800">Suspected Primary Cause</label>
              <select
                value={suspectedCause}
                onChange={(e) => setSuspectedCause(e.target.value)}
                className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
              >
                <option value="water_shortage">Water Shortage / Dry Spell at Critical Growth Stage</option>
                <option value="excess_rain">Flooding / Waterlogging / Cloudburst</option>
                <option value="pests">Pest Infestation or Fungal Blast</option>
                <option value="unsure">Not Sure / Requires Satellite Analysis</option>
              </select>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full h-13 py-3.5 rounded-xl bg-gradient-to-r from-green-700 to-emerald-700 text-white font-bold text-base shadow-md hover:shadow-lg hover:from-green-800 hover:to-emerald-800 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
        >
          <Sparkles className="w-5 h-5 text-emerald-200" />
          {loading ? "Diagnosing NASA Weather History..." : "Save Season & Run Diagnostic"}
        </button>
      </form>
    </div>
  );
}
