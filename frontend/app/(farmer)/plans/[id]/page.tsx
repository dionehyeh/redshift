"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, AlertTriangle, XCircle, RotateCcw, Share2, Check, Sparkles } from "lucide-react";

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
    fetch(`/api/plans/${planId}`)
      .then((res) => res.json())
      .then((data) => {
        setPlan(data);
        setCards(data.cards || []);
        setChosenCardId(data.chosen_card_id);
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
        const res = await fetch(`/api/plans/${planId}/rescore`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario: { rain: Number(rainSlider), temp: Number(tempSlider) },
          }),
        });
        const data = await res.json();
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
      const res = await fetch(`/api/plans/${planId}/choose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId }),
      });
      if (res.ok) {
        setChosenCardId(cardId);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Evaluating rotation scores against multi-scenario weather...</div>;
  }

  const getVerdictBadge = (verdict: string) => {
    if (verdict === "Feasible") {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
          <CheckCircle2 className="w-3.5 h-3.5" /> Feasible
        </span>
      );
    }
    if (verdict === "Possible with risk") {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900">
          <AlertTriangle className="w-3.5 h-3.5" /> Possible with Risk
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800">
        <XCircle className="w-3.5 h-3.5" /> Not Suited This Season
      </span>
    );
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Link href="/fields" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to Plots
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">Season Rotation Strategies</h1>
          <p className="text-sm text-slate-600">
            5–8 Month Outlook: <strong className="text-slate-800 capitalize">{plan?.outlook?.label || "Near Normal"}</strong> (IMD Monsoon Bulletin)
          </p>
        </div>
        {rescoring && (
          <span className="text-xs px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 animate-pulse font-medium">
            Recalculating factor scores...
          </span>
        )}
      </div>

      {/* Sticky Interactive What-If Controls */}
      <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">What-If Weather Scenarios</h2>
          <button
            onClick={() => {
              setRainSlider(1.0);
              setTempSlider(0.0);
            }}
            className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset to Expected
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>Rainfall Shift</span>
              <span className="font-mono font-bold text-emerald-800">
                {rainSlider === 1.0 ? "Expected Normal" : `${Math.round((rainSlider - 1) * 100)}%`}
              </span>
            </div>
            <input
              type="range"
              min={0.7}
              max={1.2}
              step={0.05}
              value={rainSlider}
              onChange={(e) => setRainSlider(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg accent-emerald-700 cursor-pointer"
            />
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>Temperature Offset</span>
              <span className="font-mono font-bold text-emerald-800">
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
              className="w-full h-2 bg-slate-200 rounded-lg accent-emerald-700 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Strategy Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {cards.map((c: any) => (
          <div
            key={c.id || c.crop}
            className={`p-6 bg-white border rounded-2xl shadow-sm flex flex-col justify-between space-y-4 ${
              chosenCardId === c.position ? "border-emerald-600 ring-2 ring-emerald-500" : "border-slate-200"
            }`}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  {c.is_existing_rotation ? "Card 1: Customary" : `Card ${c.position}: Alternative`}
                </span>
                {c.robustness?.holds_up_best && (
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-900">
                    Holds Up Best
                  </span>
                )}
              </div>

              <div>
                <h3 className="text-2xl font-extrabold text-slate-900 capitalize">
                  {c.crop.replace("_", " ")}
                </h3>
                <div className="mt-1 flex items-center justify-between">
                  {getVerdictBadge(c.verdict)}
                  <span className="text-xs text-slate-500 font-mono">Score: {c.total || "N/A"}/100</span>
                </div>
              </div>

              {/* 6-Factor Risk Badges */}
              <div className="grid grid-cols-3 gap-1.5 pt-2">
                {["water", "rotation", "temp", "soil", "market", "timing"].map((f) => {
                  const color = c.colors?.[f] || "amber";
                  const score = c.factors?.[f];
                  return (
                    <div
                      key={f}
                      className={`p-1.5 rounded-lg text-center text-[10px] font-bold capitalize ${
                        color === "green"
                          ? "bg-emerald-50 text-emerald-800"
                          : color === "amber"
                          ? "bg-amber-50 text-amber-900"
                          : "bg-red-50 text-red-800"
                      }`}
                    >
                      <span className="block truncate">{f}</span>
                      <span className="font-mono">{score ?? "-"}</span>
                    </div>
                  );
                })}
              </div>

              <div className="text-xs text-slate-700 space-y-2 pt-2 border-t border-slate-100">
                <p><strong>Why:</strong> {c.text?.why}</p>
                <p><strong>Risks:</strong> {c.text?.risks}</p>
                <p><strong>Watch for:</strong> {c.text?.watch_for}</p>
                <p><strong>After this:</strong> {c.text?.after_this}</p>
              </div>

              {/* Items for local review */}
              {c.needs_local_review?.length > 0 && (
                <div className="pt-2 text-xs text-slate-500">
                  <span className="font-semibold block text-slate-700">Check locally:</span>
                  <ul className="list-disc pl-4 mt-0.5 space-y-0.5">
                    {c.needs_local_review.map((item: string, idx: number) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-100 space-y-2">
              <button
                onClick={() => handleChoose(c.position)}
                className={`w-full h-11 rounded-xl text-sm font-semibold flex items-center justify-center gap-1.5 transition ${
                  chosenCardId === c.position
                    ? "bg-emerald-800 text-white"
                    : "bg-emerald-700 text-white hover:bg-emerald-800"
                }`}
              >
                {chosenCardId === c.position ? (
                  <>
                    <Check className="w-4 h-4" /> Selected as Plan
                  </>
                ) : (
                  "Go With This Plan"
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
