"use client";

import { useEffect, useState } from "react";
import { HelpCircle, X } from "lucide-react";

export function ExplainerSheet({
  explainerKey,
  label = "What does this mean?",
}: {
  explainerKey: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [card, setCard] = useState<{ title: string; body: string } | null>(null);

  useEffect(() => {
    if (open && !card) {
      fetch(`/api/explainers/${explainerKey}`)
        .then((res) => res.json())
        .then((data) => setCard(data))
        .catch(() =>
          setCard({
            title: "Science Explainer",
            body: "Satellite observations are compared against historical multi-year baselines.",
          })
        );
    }
  }, [open, explainerKey, card]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900 font-semibold underline"
      >
        <HelpCircle className="w-3.5 h-3.5" />
        {label}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 bg-white rounded-2xl shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg text-slate-900">
                {card?.title || "Loading Explainer..."}
              </h3>
              <button
                onClick={() => setOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-slate-700 leading-relaxed">
              {card?.body || "Fetching explainer content..."}
            </p>
            <div className="pt-2 text-right">
              <button
                onClick={() => setOpen(false)}
                className="h-10 px-5 rounded-xl bg-slate-100 text-slate-800 text-xs font-semibold hover:bg-slate-200"
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
