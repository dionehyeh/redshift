"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, AlertTriangle, X, ShieldAlert, Sparkles } from "lucide-react";

export default function SeasonDiagnosisPage({ params }: { params: { id: string } }) {
  const seasonId = params.id;
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewMsg, setReviewMsg] = useState("");

  useEffect(() => {
    fetch(`/api/seasons/${seasonId}/analysis`)
      .then((res) => res.json())
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
      const res = await fetch(`/api/findings/${findingId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, new_cause: action === "correct" ? "pest_attack" : null }),
      });
      if (res.ok) {
        setReviewMsg(`Finding ${action}ed successfully.`);
        // Refresh findings
        const refreshed = await (await fetch(`/api/seasons/${seasonId}/analysis`)).json();
        setAnalysis(refreshed);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Extracting NASA Earthdata & computing 20-year normals...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link href="/fields" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to Plots
      </Link>

      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-extrabold text-slate-900">Season Likely-Causes Diagnosis</h1>
          <span className="text-xs px-2.5 py-1 bg-amber-100 text-amber-900 rounded-full font-semibold">
            Status: {analysis?.approval_status || "Pending Review"}
          </span>
        </div>
        <p className="text-sm text-slate-600">
          Comparing observed weather against {analysis?.comparison_years || "20-year climatology"}.
        </p>
      </div>

      {reviewMsg && (
        <div className="p-3 text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl">
          {reviewMsg}
        </div>
      )}

      {/* Diagnosed Findings List */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Detected Environmental Stress Events</h2>

        {analysis?.findings?.length === 0 ? (
          <div className="p-6 bg-white border border-slate-200 rounded-2xl text-center text-slate-500">
            No extreme climate anomalies detected for this season.
          </div>
        ) : (
          analysis?.findings?.map((f: any) => (
            <div key={f.id} className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 capitalize text-base">
                  {f.kind.replace("_", " ")} ({f.crop_stage} Stage)
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-red-100 text-red-800">
                  {f.deviation} ({f.source})
                </span>
              </div>

              <p className="text-sm text-slate-700">{f.text}</p>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
                <span>Weeks {f.weeks[0]} to {f.weeks[1]} after planting · Confidence: {f.confidence}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleReview(f.id, "confirm")}
                    className="px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-800 font-semibold hover:bg-emerald-200 flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" /> Confirm
                  </button>
                  <button
                    onClick={() => handleReview(f.id, "reject")}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 font-semibold hover:bg-slate-200 flex items-center gap-1"
                  >
                    <X className="w-3.5 h-3.5" /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Transparent Data Gaps */}
      <div className="p-5 bg-slate-50 border border-slate-200 rounded-2xl space-y-2">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
          <ShieldAlert className="w-4 h-4 text-slate-600" /> Analytical Boundaries & In-Situ Gaps
        </h3>
        <ul className="list-disc pl-5 text-xs text-slate-600 space-y-1">
          {analysis?.gaps?.map((g: string, i: number) => (
            <li key={i}>{g}</li>
          ))}
        </ul>
      </div>

      <div className="pt-2">
        <Link
          href={`/fields`}
          className="inline-flex items-center justify-center h-12 px-6 rounded-xl bg-emerald-700 text-white font-medium hover:bg-emerald-800 transition"
        >
          Return to My Fields
        </Link>
      </div>
    </div>
  );
}
