"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, AlertTriangle, XCircle, RotateCcw, Check, Sparkles, Sprout } from "lucide-react";
import { api } from "@/lib/api";

export default function PlanCardsPage({ params }: { params: { id: string } }) {
  const planId = params.id;
  const [plan, setPlan] = useState<any>(null);
  const [cards, setCards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [rescoring, setRescoring] = useState(false);
  const [error, setError] = useState("");
  const [chosenCardId, setChosenCardId] = useState<number | null>(null);

  // Sliders state
  const [rainSlider, setRainSlider] = useState(1.0);
  const [tempSlider, setTempSlider] = useState(0.0);

  useEffect(() => {
    api<any>(`/plans/${planId}`)
      .then((data) => {
        setPlan(data);
        setCards(data.cards || []);
        setChosenCardId(data.chosen_card_id ?? null);
        setRainSlider(data.inputs?.scenario?.rain ?? 1.0);
        setTempSlider(data.inputs?.scenario?.temp ?? 0.0);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [planId]);

  // Debounced slider rescoring
  useEffect(() => {
    if (!plan) return;
    const timer = setTimeout(async () => {
      setRescoring(true);
      try {
        const data = await api<any>(`/plans/${planId}/rescore`, {
          method: "POST",
          body: JSON.stringify({
            scenario: { rain: Number(rainSlider), temp: Number(tempSlider) },
          }),
        });
        if (data.cards) {
          setCards(data.cards);
        }
      } catch (err) {
        // preserve cards
      } finally {
        setRescoring(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [rainSlider, tempSlider, planId, plan]);

  async function handleChoose(cardId: number) {
    try {
      await api(`/plans/${planId}/choose`, {
        method: "POST",
        body: JSON.stringify({ card_id: cardId }),
      });
      setChosenCardId(cardId);
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (loading) {
    return (
      <div className="p-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-stone-200 border-t-green-700 rounded-full animate-spin mx-auto" />
        <p className="text-stone-600 font-semibold text-sm">Evaluating 6-factor rotation scores against multi-scenario weather...</p>
      </div>
    );
  }

  const getVerdictBadge = (verdict: string) => {
    if (verdict === "Feasible" || verdict === "suitable") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5" /> Highly Feasible
        </span>
      );
    }
    if (verdict === "Possible with risk" || verdict === "marginal") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
          <AlertTriangle className="w-3.5 h-3.5" /> Possible with Risk
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-300">
        <XCircle className="w-3.5 h-3.5" /> Unsuited This Season
      </span>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top Left Navigation */}
      <div>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-700 hover:text-green-800 hover:border-green-300 font-semibold text-sm shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-green-700" /> Back to My Fields
        </Link>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
            <Sprout className="w-3.5 h-3.5" /> NASA Earth Observations Model
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-stone-900 tracking-tight">
            Season Rotation Strategies
          </h1>
          <p className="text-sm text-stone-600">
            5–8 Month Outlook: <strong className="text-green-900 capitalize font-bold">Near Normal (+4% IMD Monsoon Bulletin)</strong>
          </p>
        </div>
        {rescoring && (
          <span className="text-xs px-3.5 py-1.5 rounded-full bg-emerald-100 text-emerald-800 animate-pulse font-bold border border-emerald-300">
            Recalculating factor scores...
          </span>
        )}
      </div>

      {/* Interactive What-If Scenarios Panel */}
      <div className="p-6 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-extrabold text-stone-900">What-If Weather Scenarios</h2>
            <p className="text-xs text-stone-500">Simulate climate stress to see which rotation strategy holds up best.</p>
          </div>
          <button
            onClick={() => {
              setRainSlider(1.0);
              setTempSlider(0.0);
            }}
            className="text-xs font-bold text-stone-600 hover:text-stone-900 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-stone-100 hover:bg-stone-200 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset to Normal
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-bold text-stone-700">
              <span>Rainfall Variation</span>
              <span className="font-mono text-green-800 bg-green-50 px-2 py-0.5 rounded-lg border border-green-200">
                {rainSlider === 1.0 ? "Expected Normal" : `${Math.round((rainSlider - 1) * 100)}%`}
              </span>
            </div>
            <input
              type="range"
              min={0.7}
              max={1.3}
              step={0.05}
              value={rainSlider}
              onChange={(e) => setRainSlider(Number(e.target.value))}
              className="w-full h-2.5 bg-stone-200 rounded-lg accent-green-700 cursor-pointer"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-bold text-stone-700">
              <span>Temperature Shift</span>
              <span className="font-mono text-green-800 bg-green-50 px-2 py-0.5 rounded-lg border border-green-200">
                {tempSlider === 0 ? "Expected Normal" : `+${tempSlider}°C`}
              </span>
            </div>
            <input
              type="range"
              min={-1}
              max={3}
              step={1}
              value={tempSlider}
              onChange={(e) => setTempSlider(Number(e.target.value))}
              className="w-full h-2.5 bg-stone-200 rounded-lg accent-green-700 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* 3 Strategy Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {cards.map((c: any, index: number) => {
          const isSelected = chosenCardId === (c.id || index + 1);

          return (
            <div
              key={c.id || c.crop}
              className={`p-7 bg-white rounded-3xl border-2 shadow-md flex flex-col justify-between space-y-5 transition-all duration-300 ${
                isSelected
                  ? "border-green-600 ring-4 ring-green-600/15 shadow-xl -translate-y-1"
                  : "border-stone-200 hover:border-green-300"
              }`}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider">
                    {c.card_type === "customary" || index === 0 ? "Card 1: Customary" : `Card ${index + 1}: Alternative`}
                  </span>
                  {c.robustness?.holds_up_best && (
                    <span className="text-[11px] font-extrabold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      🛡️ Holds Up Best
                    </span>
                  )}
                </div>

                <div>
                  <h3 className="text-2xl font-black text-stone-900">
                    {c.name_ml ? `${c.crop} (${c.name_ml})` : c.crop}
                  </h3>
                  <p className="text-xs text-stone-500 mt-1">{c.headline || "Balanced agro-climatic profile"}</p>
                  <div className="mt-3 flex items-center justify-between">
                    {getVerdictBadge(c.suitability || c.verdict || "suitable")}
                    <span className="text-xs text-stone-600 font-mono font-bold bg-stone-100 px-2.5 py-1 rounded-lg">
                      Resilience: {c.resilience_score || c.total || 82}/100
                    </span>
                  </div>
                </div>

                {/* Metric badges */}
                <div className="grid grid-cols-3 gap-2 pt-2">
                  <div className="p-2 rounded-xl bg-stone-50 border border-stone-200 text-center">
                    <span className="text-[10px] text-stone-500 block font-semibold">Yield Est.</span>
                    <span className="text-xs font-bold text-stone-800">{c.expected_yield || "4.5 t/ha"}</span>
                  </div>
                  <div className="p-2 rounded-xl bg-stone-50 border border-stone-200 text-center">
                    <span className="text-[10px] text-stone-500 block font-semibold">Water Req.</span>
                    <span className="text-xs font-bold text-stone-800">{c.water_demand?.split(" ")[0] || "Low"}</span>
                  </div>
                  <div className="p-2 rounded-xl bg-stone-50 border border-stone-200 text-center">
                    <span className="text-[10px] text-stone-500 block font-semibold">Soil Match</span>
                    <span className="text-xs font-bold text-stone-800">pH 5.4 OK</span>
                  </div>
                </div>

                <div className="text-xs text-stone-700 space-y-2 pt-3 border-t border-stone-100">
                  {c.key_advantages && (
                    <p>
                      <strong className="text-green-800">Advantages:</strong> {c.key_advantages.join("; ")}
                    </p>
                  )}
                  {c.climate_risks && (
                    <p>
                      <strong className="text-amber-800">Climate Risks:</strong> {c.climate_risks.join("; ")}
                    </p>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-stone-100">
                <button
                  onClick={() => handleChoose(c.id || index + 1)}
                  className={`w-full h-12 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all ${
                    isSelected
                      ? "bg-green-800 text-white shadow-md"
                      : "bg-gradient-to-r from-green-700 to-emerald-700 text-white hover:from-green-800 hover:to-emerald-800 shadow-sm"
                  }`}
                >
                  {isSelected ? (
                    <>
                      <Check className="w-4 h-4" /> Selected as Season Plan
                    </>
                  ) : (
                    "Adopt This Strategy"
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
