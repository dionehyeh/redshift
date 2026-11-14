"use client";

import { useJob } from "@/lib/hooks";
import { Loader2, CheckCircle2, AlertTriangle } from "lucide-react";

export function JobProgress({
  jobId,
  onComplete,
}: {
  jobId: string;
  onComplete?: () => void;
}) {
  const { data: job, isLoading } = useJob(jobId);

  if (isLoading || !job) {
    return (
      <div className="p-4 bg-white border border-slate-200 rounded-xl flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-emerald-700" />
        <span className="text-sm font-medium text-slate-700">Connecting to background task runner...</span>
      </div>
    );
  }

  const isFailed = job.status === "failed";
  const isDone = job.status === "done" || job.status === "done_with_gaps";

  return (
    <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-slate-800">
          Step: <span className="capitalize">{job.step.replace("_", " ")}</span>
        </span>
        <span className="font-mono text-xs text-slate-500">{job.progress}%</span>
      </div>

      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            isFailed ? "bg-red-600" : isDone ? "bg-emerald-600" : "bg-emerald-500"
          }`}
          style={{ width: `${job.progress}%` }}
        />
      </div>

      {isDone && (
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800">
          <CheckCircle2 className="w-4 h-4" /> Processing completed successfully.
        </div>
      )}

      {isFailed && (
        <div className="flex items-center gap-2 text-xs font-semibold text-red-700">
          <AlertTriangle className="w-4 h-4" /> Error: {job.error || "Background task failed."}
        </div>
      )}
    </div>
  );
}
