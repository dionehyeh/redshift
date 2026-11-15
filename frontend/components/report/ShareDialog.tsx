"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, X, Send, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Helper, HelperType } from "@/lib/types";

export function ShareDialog({
  planId,
  open,
  onClose,
  onSuccess,
}: {
  planId: number;
  open: boolean;
  onClose: () => void;
  onSuccess?: (reportId: number) => void;
}) {
  const [helpers, setHelpers] = useState<Helper[]>([]);
  const [helperType, setHelperType] = useState<HelperType | "all">("all");
  const [mentorId, setMentorId] = useState<number | null>(null);
  const [shareFields, setShareFields] = useState<string[]>(["cards", "findings"]);
  const [expiresDays, setExpiresDays] = useState<number>(14);
  const [loadingHelpers, setLoadingHelpers] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;

    let active = true;
    setLoadingHelpers(true);
    setError("");
    setHelpers([]);
    setMentorId(null);
    const filter = helperType === "all" ? "" : `?type=${helperType}`;
    api<{ items: Helper[] }>(`/helpers${filter}`)
      .then(({ items }) => {
        if (!active) return;
        setHelpers(items);
        setMentorId((selectedId) =>
          items.some((helper) => helper.id === selectedId)
            ? selectedId
            : (items[0]?.id ?? null)
        );
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Could not load available advisors."
          );
        }
      })
      .finally(() => {
        if (active) setLoadingHelpers(false);
      });

    return () => {
      active = false;
    };
  }, [open, helperType]);

  if (!open) return null;

  function toggleField(f: string) {
    setShareFields((prev) =>
      prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (mentorId === null || shareFields.length === 0) {
      setError("Choose an advisor and at least one section to share.");
      return;
    }
    setLoading(true);
    setError("");

    try {
      const data = await api<{ id: number }>("/reports", {
        method: "POST",
        body: JSON.stringify({
          plan_id: planId,
          mentor_id: mentorId,
          share: shareFields,
          expires_days: expiresDays,
        }),
      });

      onSuccess?.(data.id);
      onClose();
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to share report."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="w-full max-w-lg p-6 bg-white rounded-2xl shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-700" />
            <h2 className="font-bold text-lg text-slate-900">Selective Advisor Consultation</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-600">
          Select which sections of your plot and strategy you consent to share with an advisor.
        </p>

        {error && (
          <div className="p-2.5 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <div className="space-y-1">
            <label htmlFor="advisor-type" className="text-xs font-semibold text-slate-700">Advisor type</label>
            <select
              id="advisor-type"
              value={helperType}
              onChange={(e) => setHelperType(e.target.value as HelperType | "all")}
              className="w-full h-10 px-3 border border-slate-300 rounded-xl text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="all">All advisors</option>
              <option value="student">Student mentors</option>
              <option value="volunteer">Volunteers</option>
              <option value="college">College mentors</option>
              <option value="officer">Officers</option>
            </select>
          </div>
          <div className="space-y-1">
            <label htmlFor="advisor" className="text-xs font-semibold text-slate-700">Select Advisor</label>
            <select
              id="advisor"
              value={mentorId ?? ""}
              onChange={(e) => setMentorId(Number(e.target.value))}
              disabled={loadingHelpers || helpers.length === 0}
              className="w-full h-10 px-3 border border-slate-300 rounded-xl text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-100"
            >
              {loadingHelpers && <option value="">Loading advisors…</option>}
              {!loadingHelpers && helpers.length === 0 && (
                <option value="">No advisors available</option>
              )}
              {helpers.map((helper) => (
                <option key={helper.id} value={helper.id}>{helper.label}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700">Consented Data Sections</label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {[
                { id: "cards", label: "Strategy Cards & Scores" },
                { id: "findings", label: "Past Stress Diagnoses" },
                { id: "field_profile", label: "Terrain & Soil pH" },
                { id: "history", label: "Historical Harvest Yields" },
              ].map((item) => (
                <label
                  key={item.id}
                  className="p-2.5 border rounded-xl flex items-center gap-2 cursor-pointer border-slate-200 hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={shareFields.includes(item.id)}
                    onChange={() => toggleField(item.id)}
                    className="rounded text-emerald-700 focus:ring-emerald-500"
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Access Lifetime</label>
            <select
              value={expiresDays}
              onChange={(e) => setExpiresDays(Number(e.target.value))}
              className="w-full h-10 px-3 border border-slate-300 rounded-xl text-xs bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value={7}>7 Days</option>
              <option value={14}>14 Days (Recommended)</option>
              <option value={30}>30 Days</option>
            </select>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 h-11 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || loadingHelpers || helpers.length === 0 || shareFields.length === 0}
              className="flex-1 h-11 rounded-xl bg-emerald-700 text-white text-xs font-semibold hover:bg-emerald-800 flex items-center justify-center gap-1.5"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              {loading ? "Creating Snapshot..." : "Share Scrubbed Snapshot"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
