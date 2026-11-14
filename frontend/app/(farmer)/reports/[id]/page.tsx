"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ShieldCheck, UserCheck, MessageSquare, AlertCircle } from "lucide-react";

export default function FarmerReportStatusPage({ params }: { params: { id: string } }) {
  const reportId = params.id;
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [revoked, setRevoked] = useState(false);

  useEffect(() => {
    fetch(`/api/reports/${reportId}`)
      .then((res) => res.json())
      .then((data) => {
        setReport(data);
        setRevoked(Boolean(data.revoked_at));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [reportId]);

  async function handleRevoke() {
    try {
      const res = await fetch(`/api/reports/${reportId}/revoke`, { method: "POST" });
      if (res.ok) {
        setRevoked(true);
      }
    } catch (err) {
      // handle error
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading consultation record...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href="/fields" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to Plots
      </Link>

      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-slate-900">Mentor Consultation Status</h1>
        <p className="text-sm text-slate-600">Review advisor feedback and manage your shared data consent.</p>
      </div>

      <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-700">Consultation Status</span>
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase ${
              revoked
                ? "bg-slate-100 text-slate-600"
                : report?.status === "commented"
                ? "bg-emerald-100 text-emerald-800"
                : "bg-blue-100 text-blue-800"
            }`}
          >
            {revoked ? "Revoked" : report?.status || "Sent"}
          </span>
        </div>

        <div className="text-xs text-slate-500 space-y-1">
          <p>Shared Sections: {report?.shared_fields?.join(", ") || "N/A"}</p>
          <p>Expires On: {report?.expires_at ? new Date(report.expires_at).toLocaleDateString() : "N/A"}</p>
        </div>

        {/* Advisor Comments */}
        <div className="pt-4 border-t border-slate-100 space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <MessageSquare className="w-4 h-4 text-emerald-700" /> Advisor Comments
          </h3>
          {report?.comments?.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No feedback submitted by your mentor yet.</p>
          ) : (
            report?.comments?.map((c: any) => (
              <div key={c.id} className="p-4 bg-emerald-50/50 border border-emerald-100 rounded-xl space-y-1">
                <span className="text-xs font-semibold text-emerald-900 block">{c.author_label}</span>
                <p className="text-sm text-slate-800">{c.body}</p>
              </div>
            ))
          )}
        </div>

        {!revoked && (
          <div className="pt-4 border-t border-slate-100 flex justify-end">
            <button
              onClick={handleRevoke}
              className="text-xs font-semibold text-red-600 hover:text-red-800"
            >
              Stop Sharing / Revoke Access
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
