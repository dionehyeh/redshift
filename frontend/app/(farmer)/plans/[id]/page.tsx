"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, AlertTriangle, XCircle, RotateCcw, Check, Sprout, Share2 } from "lucide-react";
import { api } from "@/lib/api";
import { ShareDialog } from "@/components/report/ShareDialog";
import type { Plan, PlanCardData, RescoreResponse } from "@/lib/types";

export default function PlanCardsPage({ params }: { params: { id: string } }) {
  const planId = params.id;
  const router = useRouter();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [cards, setCards] = useState<PlanCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [rescoring, setRescoring] = useState(false);
  const [error, setError] = useState("");
  const [chosenCardId, setChosenCardId] = useState<number | null>(null);
  const [shareOpen, setShareOpen] = useState(false);

  // Sliders state
  const [rainSlider, setRainSlider] = useState(1.0);
  const [tempSlider, setTempSlider] = useState(0.0);

  useEffect(() => {
    api<Plan>(`/plans/${planId}`)
      .then((data) => {
        setPlan(data);
        setCards(data.cards || []);
        setChosenCardId(data.chosen_card_id ?? null);
        setLoading(false);
      })
      .catch((requestError: unknown) => {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load this plan."
        );
        setLoading(false);
      });
  }, [planId]);

  // Debounced slider rescoring
  useEffect(() => {
    if (!plan) return;
    const timer = setTimeout(async () => {
      setRescoring(true);
      try {
        const data = await api<RescoreResponse>(`/plans/${planId}/rescore`, {
          method: "POST",
          body: JSON.stringify({
            scenario: { rain: Number(rainSlider), temp: Number(tempSlider) },
          }),
        });
        setCards(data.cards);
        setError("");
      } catch (requestError: unknown) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to update scenario scores."
        );
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
      setError("");
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to save the selected strategy."
      );
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

  if (!plan) {
    return (
      <div role="alert" className="mx-auto max-w-2xl rounded-2xl border-2 border-red-200 bg-red-50 p-6 text-sm text-red-800">
        {error || "This plan could not be loaded."}
      </div>
    );
  }

  const getVerdictBadge = (verdict: PlanCardData["verdict"]) => {
    if (verdict === "Feasible") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5" /> Highly Feasible
        </span>
      );
    }
    if (verdict === "Possible with risk") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
          <AlertTriangle className="w-3.5 h-3.5" /> Possible with Risk
        </span>
      );
    }
    if (verdict === "Not assessed") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-stone-100 text-stone-700 border border-stone-300">
          Not Assessed
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
            Seasonal outlook: <strong className="text-green-900 font-bold">{plan.outlook.label}</strong>
            {" "}({plan.outlook.confidence} confidence)
          </p>
        </div>
        <div className="flex items-center gap-3">
          {rescoring && (
            <span className="text-xs px-3.5 py-1.5 rounded-full bg-emerald-100 text-emerald-800 animate-pulse font-bold border border-emerald-300">
              Recalculating factor scores...
            </span>
          )}
          <button
            type="button"
            onClick={() => setShareOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-800 px-4 py-2.5 text-sm font-bold text-white hover:bg-emerald-900"
          >
            <Share2 className="h-4 w-4" /> Share with an advisor
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

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
        {cards.map((card, index) => {
          const isSelected = chosenCardId === card.id;

          return (
            <div
              key={card.id}
              className={`p-7 bg-white rounded-3xl border-2 shadow-md flex flex-col justify-between space-y-5 transition-all duration-300 ${
                isSelected
                  ? "border-green-600 ring-4 ring-green-600/15 shadow-xl -translate-y-1"
                  : "border-stone-200 hover:border-green-300"
              }`}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider">
                    {card.is_existing_rotation ? "Existing rotation" : `Strategy ${index + 1}`}
                  </span>
                  {card.robustness.holds_up_best && (
                    <span className="text-[11px] font-extrabold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      Holds up best
                    </span>
                  )}
                </div>

                <div>
                  <h3 className="text-2xl font-black text-stone-900">
                    {card.crop.replaceAll("_", " ")}
                  </h3>
                  <div className="mt-3 flex items-center justify-between">
                    {getVerdictBadge(card.verdict)}
                    <span className="text-xs text-stone-600 font-mono font-bold bg-stone-100 px-2.5 py-1 rounded-lg">
                      Score: {card.total ?? "Not scored"}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-stone-500">
                    {card.confidence.level} confidence · {card.confidence.reason}
                  </p>
                </div>

                <div className="space-y-2 border-t border-stone-100 pt-3">
                  {Object.entries(card.factors).map(([factor, score]) => (
                    <div key={factor} className="flex items-center justify-between text-xs">
                      <span className="capitalize text-stone-600">{factor}</span>
                      <span className="font-semibold text-stone-800">{score}</span>
                    </div>
                  ))}
                </div>

                <div className="space-y-2 border-t border-stone-100 pt-3 text-xs text-stone-700">
                  <p><strong className="text-green-800">Why:</strong> {card.text.why}</p>
                  <p><strong className="text-amber-800">Risks:</strong> {card.text.risks}</p>
                  <p><strong>Next step:</strong> {card.text.next_step}</p>
                  {card.notes.length > 0 && (
                    <ul className="list-disc space-y-1 pl-4 text-stone-600">
                      {card.notes.map((note) => <li key={note}>{note}</li>)}
                    </ul>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-stone-100">
                <button
                  onClick={() => handleChoose(card.id)}
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
      <ShareDialog
        planId={plan.plan_id}
        open={shareOpen}
        onClose={() => setShareOpen(false)}
        onSuccess={(reportId) => router.push(`/reports/${reportId}`)}
      />
    </div>
  );
}
