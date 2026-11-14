"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Inbox, Clock } from "lucide-react";

export default function MentorInboxPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/mentor/inbox")
      .then((res) => res.json())
      .then((data) => {
        setItems(data.items || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Loading consultation queue...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">Farmer Consultation Queue</h1>
        <p className="text-sm text-slate-600">Review shared strategy cards and submit advisory feedback.</p>
      </div>

      {items.length === 0 ? (
        <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl space-y-3">
          <Inbox className="w-12 h-12 text-slate-400 mx-auto" />
          <h3 className="font-bold text-slate-800">Inbox is Clear</h3>
          <p className="text-xs text-slate-500">No farmers have shared consultation reports with your account recently.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Link
              key={item.report_id}
              href={`/mentor/reports/${item.report_id}`}
              className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm hover:border-blue-500 transition flex items-center justify-between"
            >
              <div className="space-y-1">
                <span className="font-bold text-slate-900 block">{item.farmer_name}</span>
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> Shared: {new Date(item.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-900 uppercase">
                  {item.status}
                </span>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
