"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ShieldCheck, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";

export default function FarmerReportStatusPage({ params }: { params: { id: string } }) {
  const reportId = params.id;
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [revoked, setRevoked] = useState(false);

  useEffect(() => {
    api<any>(`/reports/${reportId}`)
      .then((data) => {
        setReport(data);
        setRevoked(Boolean(data.revoked_at));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [reportId]);

  async function handleRevoke() {
    try {
      await api(`/reports/${reportId}/revoke`, { method: "POST" });
      setRevoked(true);
    } catch {
      // handle error
    }
  }

  if (loading) {
    return (
      <div className="p-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-stone-200 border-t-green-700 rounded-full animate-spin mx-auto" />
        <p className="text-stone-600 font-semibold text-sm">Loading consultation record...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
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
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5" /> Consent & Privacy Control
        </span>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Extension Advisory Status
        </h1>
        <p className="text-sm text-stone-600">
          Review mentor guidance and manage your real-time data revocation controls.
        </p>
      </div>

      <div className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-5">
        <div className="flex items-center justify-between">
          <span className="text-base font-extrabold text-stone-800">Snapshot Status</span>
          <span
            className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${
              revoked
                ? "bg-stone-200 text-stone-700"
                : "bg-emerald-100 text-emerald-800 border border-emerald-300"
            }`}
          >
            {revoked ? "Access Revoked" : "Active Consultation"}
          </span>
        </div>

        <div className="text-xs text-stone-500 space-y-1 bg-stone-50 p-4 rounded-xl border border-stone-200">
          <p>Shared Sections: <span className="font-semibold text-stone-700">Crop Rotation, Soil pH, 20-Year Climate Normals</span></p>
          <p>Consent: <span className="font-semibold text-stone-700">Expiring in 30 days (Auto-purge)</span></p>
        </div>

        {/* Advisor Comments */}
        <div className="pt-4 border-t border-stone-100 space-y-3">
          <h3 className="text-base font-extrabold text-stone-900 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-green-700" /> Extension Officer Feedback
          </h3>
          {report?.comments?.length === 0 ? (
            <p className="text-xs text-stone-500 italic">No feedback submitted yet. Your local Krishi Bhavan mentor is reviewing the snapshot.</p>
          ) : (
            report?.comments?.map((c: any) => (
              <div key={c.id} className="p-5 bg-emerald-50/60 border border-emerald-200 rounded-2xl space-y-1">
                <span className="text-xs font-bold text-green-950 block">{c.author || "Krishi Bhavan Officer"}</span>
                <p className="text-sm text-stone-800 font-medium">{c.text || c.body}</p>
              </div>
            ))
          )}
        </div>

        {!revoked && (
          <div className="pt-4 border-t border-stone-100 flex justify-end">
            <button
              onClick={handleRevoke}
              className="text-xs font-bold text-red-700 hover:text-red-900 px-4 py-2 rounded-xl bg-red-50 hover:bg-red-100 transition"
            >
              Stop Sharing / Revoke Access
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
