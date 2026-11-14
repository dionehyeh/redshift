"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Compass, Sparkles } from "lucide-react";

export default function NewPlanPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const fieldId = params.id;

  const [mode, setMode] = useState<"suggest" | "farmer_led">("suggest");
  const [season, setSeason] = useState("puncha");
  const [toggle, setToggle] = useState<string | null>(null);
  const [crop, setCrop] = useState("green_gram");
  const [reason, setReason] = useState("market");
  const [storedWater, setStoredWater] = useState<string>("moist");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreatePlan(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`/api/fields/${fieldId}/plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          season,
          start_week: season === "puncha" ? 2 : season === "virippu" ? 18 : 38,
          toggle,
          crop: mode === "farmer_led" ? crop : null,
          reason: mode === "farmer_led" ? reason : null,
          stored_water_answer: storedWater,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || "Failed to generate strategy cards");
      }

      router.push(`/plans/${data.plan_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to generate strategy cards");
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
        <h1 className="text-2xl font-extrabold text-slate-900">Plan Next Crop Cycle</h1>
        <p className="text-sm text-slate-600">Choose between automated resilient rotation suggestions or test your own crop choice.</p>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl">
          {error}
        </div>
      )}

      <form onSubmit={handleCreatePlan} className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
        {/* Mode Selector */}
        <div className="space-y-2">
          <label className="text-sm font-semibold text-slate-900">Planning Mode</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setMode("suggest")}
              className={`p-4 rounded-xl border text-left transition ${
                mode === "suggest"
                  ? "bg-emerald-50 border-emerald-600 text-emerald-950 font-bold"
                  : "bg-white border-slate-200 text-slate-700"
              }`}
            >
              <span className="block text-sm">Suggest Rotations</span>
              <span className="text-xs font-normal text-slate-500">Customary + 2 resilient crops</span>
            </button>
            <button
              type="button"
              onClick={() => setMode("farmer_led")}
              className={`p-4 rounded-xl border text-left transition ${
                mode === "farmer_led"
                  ? "bg-emerald-50 border-emerald-600 text-emerald-950 font-bold"
                  : "bg-white border-slate-200 text-slate-700"
              }`}
            >
              <span className="block text-sm">I Have a Crop in Mind</span>
              <span className="text-xs font-normal text-slate-500">Evaluate your target crop</span>
            </button>
          </div>
        </div>

        {/* Season Selector */}
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">Target Season Window</label>
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
          >
            <option value="puncha">Puncha / Summer (Week 2 to 16)</option>
            <option value="virippu">Virippu / Autumn (Week 18 to 38)</option>
            <option value="mundakan">Mundakan / Winter (Week 38 to 3)</option>
          </select>
        </div>

        {/* Stored Soil Moisture */}
        <div className="space-y-1">
          <label className="text-sm font-medium text-slate-700">How wet is the soil right now?</label>
          <select
            value={storedWater}
            onChange={(e) => setStoredWater(e.target.value)}
            className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
          >
            <option value="moist">Moist (Holds shape when squeezed)</option>
            <option value="wet">Wet / Standing Water (Saturated)</option>
            <option value="dry">Dry (Crumbly surface)</option>
          </select>
        </div>

        {/* Farmer-Led Specific Inputs */}
        {mode === "farmer_led" && (
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Your Target Crop</label>
              <select
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
              >
                <option value="green_gram">Green Gram (Cherupayar)</option>
                <option value="cowpea">Cowpea (Vanpayar)</option>
                <option value="sesame">Sesame (Ellu)</option>
                <option value="groundnut">Groundnut</option>
                <option value="okra">Okra (Bhindi)</option>
                <option value="corn">Sweet Corn (Not cataloged)</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Primary Motivation</label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full h-11 px-3 border border-slate-300 rounded-xl bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none text-sm"
              >
                <option value="market">High Market Demand / Price</option>
                <option value="finance">Lower Seed / Fertilizer Cost</option>
                <option value="other">Personal Experience / Customary</option>
              </select>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full h-12 rounded-xl bg-emerald-700 text-white font-medium hover:bg-emerald-800 transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {loading ? "Computing 6-Factor Scores..." : "Generate 3 Strategy Cards"}
        </button>
      </form>
    </div>
  );
}
