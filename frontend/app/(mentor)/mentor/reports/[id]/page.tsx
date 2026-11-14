"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Send, ShieldCheck, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export default function MentorReportDetailPage({ params }: { params: { id: string } }) {
  const reportId = params.id;
  const [report, setReport] = useState<any>(null);
  const [commentText, setCommentText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api<any>(`/reports/${reportId}`)
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
      await api(`/reports/${reportId}/comments`, {
        method: "POST",
        body: JSON.stringify({ text: commentText }),
      });
      setCommentText("");
      setMsg("Advisory comment posted successfully.");
      const updated = await api<any>(`/reports/${reportId}`);
      setReport(updated);
    } catch (err: any) {
      setMsg("Failed to post comment.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="p-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-stone-200 border-t-amber-700 rounded-full animate-spin mx-auto" />
        <p className="text-stone-600 font-semibold text-sm">Loading scrubbed consultation snapshot...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Left Navigation */}
      <div>
        <Link
          href="/inbox"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-700 hover:text-amber-800 hover:border-amber-300 font-semibold text-sm shadow-sm transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-amber-700" /> Back to Shared Requests
        </Link>
      </div>

      <div className="space-y-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-bold uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5" /> Privacy-Preserving Farmer Snapshot
        </span>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Consultation Report #{reportId}
        </h1>
        <p className="text-stone-600 text-sm">
          Submitted by: <strong className="text-stone-800 font-bold">{report?.farmer_name || "Kerala Demo Farmer"}</strong>
        </p>
      </div>

      {msg && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-sm font-semibold">
          {msg}
        </div>
      )}

      {/* Advisory Feedback Section */}
      <div className="p-8 bg-white border-2 border-stone-200 rounded-3xl shadow-sm space-y-6">
        <h2 className="text-xl font-extrabold text-stone-900">Advisor Notes & Extension Recommendations</h2>

        <div className="space-y-3">
          {report?.comments?.length === 0 ? (
            <p className="text-stone-500 text-sm italic">No extension notes added yet.</p>
          ) : (
            report?.comments?.map((c: any) => (
              <div key={c.id} className="p-5 bg-stone-50 border border-stone-200 rounded-2xl space-y-1">
                <span className="text-xs font-bold text-amber-900 block">{c.author || "Extension Mentor"}</span>
                <p className="text-sm text-stone-800 font-medium">{c.text}</p>
              </div>
            ))
          )}
        </div>

        <form onSubmit={handleAddComment} className="space-y-3 pt-4 border-t border-stone-100">
          <label className="text-sm font-bold text-stone-800 block">Add Extension Guidance</label>
          <textarea
            required
            rows={3}
            placeholder="Type your recommendations on sowing date adjustments, certified seed varieties, or biofertilizer practices..."
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            className="w-full p-4 border-2 border-stone-200 rounded-2xl focus:border-amber-600 focus:ring-2 focus:ring-amber-600/20 focus:outline-none text-sm text-stone-900 font-medium"
          />
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-amber-700 to-yellow-800 text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-60"
          >
            <Send className="w-4 h-4" />
            {submitting ? "Posting..." : "Post Advisory Note"}
          </button>
        </form>
      </div>
    </div>
  );
}
