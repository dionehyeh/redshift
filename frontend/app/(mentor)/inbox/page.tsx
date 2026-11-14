"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Inbox, Clock, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";

export default function MentorInboxPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<{ items: any[] }>("/inbox")
      .then((data) => {
        setItems(data.items || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-16 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-stone-200 border-t-amber-700 rounded-full animate-spin mx-auto" />
        <p className="text-stone-600 font-semibold text-sm">Loading advisor consultation queue...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="space-y-1">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-bold uppercase tracking-wider">
          <GraduationCap className="w-3.5 h-3.5" /> Extension Consultation Queue
        </span>
        <h1 className="text-3xl font-extrabold text-stone-900 tracking-tight">
          Farmer Shared Requests
        </h1>
        <p className="text-stone-600 text-sm">
          Review shared rotation strategies, cross-examine satellite anomalies, and submit extension guidance.
        </p>
      </div>

      {items.length === 0 ? (
        <div className="p-12 text-center bg-white border-2 border-stone-200 rounded-3xl space-y-4 shadow-sm">
          <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center mx-auto">
            <Inbox className="w-8 h-8" />
          </div>
          <h3 className="font-extrabold text-stone-800 text-lg">Inbox is Clear</h3>
          <p className="text-xs text-stone-500 max-w-sm mx-auto">
            No farmers have shared consultation reports recently. When a farmer submits a strategy for advice, it will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item, idx) => (
            <Link
              key={item.id || item.report_id || idx}
              href={`/mentor/reports/${item.id || item.report_id || 1}`}
              className="p-6 bg-white border-2 border-stone-200 hover:border-amber-400 rounded-2xl shadow-sm transition flex items-center justify-between group"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-stone-900 text-base group-hover:text-amber-800 transition">
                    {item.farmer_name || "Kerala Demo Farmer"}
                  </span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    {item.field_name || "Plot Strategy"}
                  </span>
                </div>
                <span className="text-xs text-stone-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-stone-400" />
                  Shared: {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Today"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm font-bold text-amber-700 group-hover:translate-x-1 transition-transform">
                <span>Review Report</span>
                <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
