"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, AlertTriangle, X, ShieldAlert, Sparkles, Sprout } from "lucide-react";
import { api } from "@/lib/api";

export default function SeasonDiagnosisPage({ params }: { params: { id: string } }) {
  const seasonId = params.id;
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewMsg, setReviewMsg] = useState("");

  useEffect(() => {
    api<any>(`/seasons/${seasonId}`)
      .then((data) => {
        setAnalysis(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [seasonId]);

  async function handleReview(findingId: number, action: "confirm" | "correct" | "reject") {
    try {
      await api(`/findings/${findingId}/review`, {
        method: "POST",
        body: JSON.stringify({ action, new_cause: action === "correct" ? "pest_attack" : null }),
      });
      setReviewMsg(`Finding ${action}ed successfully.`);
      const refreshed = await api<any>(`/seasons/${seasonId}`);
      setAnalysis(refreshed);
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (loading) {
    return (
      <div className="p-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-stone-200 border-t-green-700 rounded-full animate-spin mx-auto" />
        <p className="text-stone-600 font-semibold text-sm">Extracting NASA Earthdata & computing 20-year normals...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Top Left Navigation */}
      <div>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-700 hover:text-green-800 hover:border-green-300 font-semibold text-sm shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-green-700" /> Back to My Fields
        </Link>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
            <Sprout className="w-3.5 h-3.5" /> Satellite Ground Diagnostic
          </span>
          <span className="text-xs px-3 py-1 bg-amber-100 text-amber-900 border border-amber-300 rounded-full font-bold">
            Status: {analysis?.approval_status || "Pending Extension Review"}
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Season Likely-Causes Diagnosis
        </h1>
        <p className="text-sm text-stone-600">
          Correlating observed crop stress against 20-year NASA IMERG precipitation and NASA POWER thermal baselines.
        </p>
      </div>

      {reviewMsg && (
        <div className="p-4 text-sm font-semibold text-emerald-900 bg-emerald-50 border border-emerald-300 rounded-2xl">
          ✅ {reviewMsg}
        </div>
      )}

      {/* Diagnosed Findings List */}
      <div className="space-y-4">
        <h2 className="text-xl font-extrabold text-stone-900">Detected Environmental Stress Events</h2>

        {analysis?.findings?.length === 0 ? (
          <div className="p-8 bg-white border-2 border-stone-200 rounded-3xl text-center text-stone-500">
            No extreme climate anomalies detected for this season window.
          </div>
        ) : (
          analysis?.findings?.map((f: any) => (
            <div key={f.id} className="p-6 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="font-extrabold text-stone-900 text-lg">
                  {f.metric || f.kind || "Environmental Anomaly"}
                </span>
                <span className="text-xs px-3 py-1 rounded-full font-bold bg-amber-100 text-amber-900 border border-amber-300 w-fit">
                  {f.severity || "Warning"}
                </span>
              </div>

              <p className="text-sm text-stone-700 font-medium leading-relaxed">{f.finding || f.text}</p>

              <div className="flex flex-wrap items-center justify-between pt-3 border-t border-stone-100 text-xs text-stone-500 gap-3">
                <span className="font-medium">Confidence: High (Satellite IMERG 0.1° / POWER 0.5°)</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleReview(f.id, "confirm")}
                    className="px-3.5 py-1.5 rounded-xl bg-emerald-100 text-emerald-900 font-bold hover:bg-emerald-200 flex items-center gap-1.5 transition"
                  >
                    <Check className="w-4 h-4" /> Confirm
                  </button>
                  <button
                    onClick={() => handleReview(f.id, "reject")}
                    className="px-3.5 py-1.5 rounded-xl bg-stone-100 text-stone-700 font-bold hover:bg-stone-200 flex items-center gap-1.5 transition"
                  >
                    <X className="w-4 h-4" /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Recommendations */}
      {analysis?.recommendations && (
        <div className="p-6 bg-emerald-50/70 border-2 border-emerald-200 rounded-3xl space-y-2">
          <h3 className="text-sm font-extrabold text-emerald-950 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-700" /> Agronomic Adaptation Advice
          </h3>
          <p className="text-xs text-emerald-900 leading-relaxed font-medium">
            {analysis.recommendations[0]}
          </p>
        </div>
      )}

      {/* Transparent Data Gaps */}
      <div className="p-6 bg-stone-100 border border-stone-200 rounded-3xl space-y-2">
        <h3 className="text-sm font-bold text-stone-800 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-stone-600" /> Analytical Boundaries & Ground Gaps
        </h3>
        <p className="text-xs text-stone-600 leading-relaxed">
          Satellite precipitation estimates may smooth localized cloudbursts. Ground validation with your local Krishi Bhavan officer is recommended for insurance or relief filings.
        </p>
      </div>

      <div className="pt-2">
        <Link
          href="/fields"
          className="inline-flex items-center justify-center h-12 px-8 rounded-xl bg-gradient-to-r from-green-700 to-emerald-700 text-white font-bold text-sm hover:from-green-800 hover:to-emerald-800 shadow-md transition-all"
        >
          Return to My Fields
        </Link>
      </div>
    </div>
  );
}
