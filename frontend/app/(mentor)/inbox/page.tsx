"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Inbox, Clock, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";
import type { MentorInboxItem } from "@/lib/types";

export default function MentorInboxPage() {
  const [items, setItems] = useState<MentorInboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<{ items: MentorInboxItem[] }>("/mentor/inbox")
      .then((data) => {
        if (active) setItems(data.items);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load consultation requests."
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
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

      {error ? (
        <div role="alert" className="rounded-2xl border-2 border-red-200 bg-red-50 p-5 text-sm text-red-800">
          {error}
        </div>
      ) : items.length === 0 ? (
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
          {items.map((item) => (
            <Link
              key={item.report_id}
              href={`/mentor/reports/${item.report_id}`}
              className="p-6 bg-white border-2 border-stone-200 hover:border-amber-400 rounded-2xl shadow-sm transition flex items-center justify-between group"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-stone-900 text-base group-hover:text-amber-800 transition">{item.farmer_name}</span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">{item.status}</span>
                </div>
                <span className="text-xs text-stone-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-stone-400" />
                  Shared: {new Date(item.created_at).toLocaleDateString()} · Expires: {new Date(item.expires_at).toLocaleDateString()}
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
