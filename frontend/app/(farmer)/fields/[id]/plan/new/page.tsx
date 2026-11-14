"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Compass, Sparkles, Sprout } from "lucide-react";
import { api } from "@/lib/api";

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
      const data = await api<{ plan_id?: number; id?: number }>(`/fields/${fieldId}/plans`, {
        method: "POST",
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

      const targetPlanId = data.plan_id || data.id || 1;
      router.push(`/plans/${targetPlanId}`);
    } catch (err: any) {
      setError(err.message || "Failed to generate strategy cards");
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
          <Sprout className="w-3.5 h-3.5" /> Climate-Resilient Rotation
        </span>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Plan Next Crop Cycle
        </h1>
        <p className="text-stone-600 text-sm">
          Generate 3 comparative strategy cards (customary + 2 climate-resilient alternatives) scored by NASA agro-meteorological metrics.
        </p>
      </div>

      {error && (
        <div className="p-4 text-sm text-red-800 bg-red-50 border border-red-200 rounded-xl font-medium">
          {error}
        </div>
      )}

      <form
        onSubmit={handleCreatePlan}
        className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-6"
      >
        {/* Mode Selector */}
        <div className="space-y-2">
          <label className="text-sm font-bold text-stone-800">Planning Mode</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setMode("suggest")}
              className={`p-4 rounded-2xl border-2 text-left transition-all ${
                mode === "suggest"
                  ? "bg-green-50/70 border-green-700 text-green-950 font-bold shadow-sm"
                  : "bg-white border-stone-200 text-stone-700 hover:border-stone-300"
              }`}
            >
              <span className="block text-sm font-extrabold">Suggest Rotations</span>
              <span className="text-xs text-stone-500 font-normal mt-0.5 block">
                Customary + 2 resilient rotation crops
              </span>
            </button>
            <button
              type="button"
              onClick={() => setMode("farmer_led")}
              className={`p-4 rounded-2xl border-2 text-left transition-all ${
                mode === "farmer_led"
                  ? "bg-green-50/70 border-green-700 text-green-950 font-bold shadow-sm"
                  : "bg-white border-stone-200 text-stone-700 hover:border-stone-300"
              }`}
            >
              <span className="block text-sm font-extrabold">I Have a Crop in Mind</span>
              <span className="text-xs text-stone-500 font-normal mt-0.5 block">
                Evaluate your personal crop choice
              </span>
            </button>
          </div>
        </div>

        {/* Season Selector */}
        <div className="space-y-1.5">
          <label className="text-sm font-bold text-stone-800">Target Season Window</label>
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
          >
            <option value="puncha">Puncha / Summer Season (Week 2 to 16)</option>
            <option value="virippu">Virippu / Autumn Monsoon (Week 18 to 38)</option>
            <option value="mundakan">Mundakan / Winter Season (Week 38 to 3)</option>
          </select>
        </div>

        {/* Stored Soil Moisture */}
        <div className="space-y-1.5">
          <label className="text-sm font-bold text-stone-800">Current Soil Moisture Condition</label>
          <select
            value={storedWater}
            onChange={(e) => setStoredWater(e.target.value)}
            className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
          >
            <option value="moist">Moist (Holds soil ball shape when squeezed)</option>
            <option value="wet">Wet / Standing Water (Saturated bunds)</option>
            <option value="dry">Dry (Crumbly surface crust)</option>
          </select>
        </div>

        {/* Farmer-Led Specific Inputs */}
        {mode === "farmer_led" && (
          <div className="p-5 bg-stone-50 border-2 border-stone-200 rounded-2xl space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-bold text-stone-800">Your Target Crop</label>
              <select
                value={crop}
                onChange={(e) => setCrop(e.target.value)}
                className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
              >
                <option value="green_gram">Green Gram (Cherupayar)</option>
                <option value="cowpea">Cowpea (Vanpayar)</option>
                <option value="sesame">Sesame (Ellu)</option>
                <option value="groundnut">Groundnut</option>
                <option value="okra">Okra (Bhindi)</option>
                <option value="corn">Sweet Corn</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-bold text-stone-800">Primary Motivation</label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full h-12 px-4 border-2 border-stone-200 rounded-xl bg-white focus:border-green-600 focus:ring-2 focus:ring-green-600/20 focus:outline-none font-medium text-stone-800 text-sm transition"
              >
                <option value="market">High Market Demand / Premium Local Price</option>
                <option value="finance">Lower Seed / Fertilizer Cost</option>
                <option value="other">Personal Experience / Customary Practice</option>
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
          {loading ? "Computing 6-Factor Scores..." : "Generate 3 Strategy Cards"}
        </button>
      </form>
    </div>
  );
}
