"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Send, ShieldCheck, CheckCircle2 } from "lucide-react";

export default function MentorReportDetailPage({ params }: { params: { id: string } }) {
  const reportId = params.id;
  const [report, setReport] = useState<any>(null);
  const [commentText, setCommentText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    fetch(`/api/reports/${reportId}`)
      .then((res) => res.json())
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [reportId]);

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setMsg("");

    try {
      const res = await fetch(`/api/reports/${reportId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: commentText }),
      });
      if (res.ok) {
        setCommentText("");
        setMsg("Advisory comment posted successfully.");
        const updated = await (await fetch(`/api/reports/${reportId}`)).json();
        setReport(updated);
      }
    } catch (err: any) {
      setMsg("Failed to post comment.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading scrubbed consultation snapshot...</div>;
  }

  const snapshot = report?.snapshot || {};

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link href="/inbox" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft className="w-4 h-4" /> Back to Queue
      </Link>

      <div className="space-y-1">
        <h1 className="text-2xl font-extrabold text-slate-900">Consultation Review (Snapshot)</h1>
        <p className="text-xs text-slate-500">
          Viewing farmer-consented snapshot. Confidential contact information has been scrubbed.
        </p>
      </div>

      {msg && (
        <div className="p-3 text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl">
          {msg}
        </div>
      )}

      {/* Snapshot Cards */}
      {snapshot.cards && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-900">Generated Strategy Cards</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {snapshot.cards.map((c: any, i: number) => (
              <div key={i} className="p-4 bg-white border border-slate-200 rounded-xl space-y-2">
                <span className="text-[10px] uppercase font-bold text-slate-500">Card {c.position}</span>
                <h3 className="font-bold text-base text-slate-900 capitalize">{c.crop_id || "Crop"}</h3>
                <span className="inline-block text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-800">
                  {c.verdict}
                </span>
                <span className="block text-xs font-mono text-slate-500">Score: {c.total || "N/A"}/100</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Field Conditions */}
      {snapshot.field && (
        <div className="p-5 bg-white border border-slate-200 rounded-2xl space-y-2">
          <h3 className="font-bold text-slate-900 text-sm">Consented Plot Conditions</h3>
          <p className="text-xs text-slate-600">
            Elevation: {snapshot.field.elevation_m} m · Drainage: {snapshot.field.drainage} · Soil pH: {snapshot.field.soil_ph} · Basin: {snapshot.field.flood_prone ? "Flood-prone" : "Normal"}
          </p>
        </div>
      )}

      {/* Existing Comments */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900">Advisory Comments Thread</h3>
        {report?.comments?.map((c: any) => (
          <div key={c.id} className="p-4 bg-white border border-slate-200 rounded-xl space-y-1">
            <span className="text-xs font-semibold text-blue-900 block">{c.author_label}</span>
            <p className="text-sm text-slate-800">{c.body}</p>
          </div>
        ))}
      </div>

      {/* Submit Comment */}
      <form onSubmit={handleAddComment} className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
        <label className="text-sm font-semibold text-slate-900 block">
          Add Advisory Note to Farmer
        </label>
        <textarea
          required
          rows={3}
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          placeholder="e.g. Ensure pre-sowing seed treatment with Rhizobium culture and check channel bunds..."
          className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
        />
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-slate-500 italic">
            Your note will be labeled: "Student mentor, not a certified advisor".
          </span>
          <button
            type="submit"
            disabled={submitting}
            className="h-10 px-5 rounded-xl bg-blue-700 text-white text-xs font-semibold hover:bg-blue-800 transition flex items-center gap-1.5"
          >
            <Send className="w-3.5 h-3.5" /> Post Advice
          </button>
        </div>
      </form>
    </div>
  );
}
