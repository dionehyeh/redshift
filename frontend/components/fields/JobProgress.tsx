"use client";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useJob } from "@/lib/hooks";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

const STEP_LABELS: Record<string, string> = {
  terrain: "Extracting terrain & elevation data",
  soil: "Loading soil composition from SoilGrids",
  climate_normals: "Fetching 52-week climate normals",
  feasibility: "Scoring crop feasibility",
};

interface JobProgressProps {
  jobId: string;
  onDone?: (fieldId?: number) => void;
  onError?: (message: string) => void;
}

export function JobProgress({ jobId, onDone, onError }: JobProgressProps) {
  const router = useRouter();
  const { status, step, progress, error } = useJob(jobId);
  const completed = status === "done" || status === "done_with_gaps";
  const notifiedRef = useRef(false);

  useEffect(() => {
    if (notifiedRef.current) return;
    if (completed) {
      notifiedRef.current = true;
      if (onDone) onDone();
      else router.refresh();
    } else if (status === "failed" && error) {
      notifiedRef.current = true;
      onError?.(error);
    }
  }, [completed, status, error, onDone, onError, router]);

  const steps = ["terrain", "soil", "climate_normals", "feasibility"];
  const currentIdx = steps.indexOf(step);

  return (
    <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
      <div className="flex items-center gap-3">
        {completed ? (
          <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
        ) : status === "failed" ? (
          <XCircle className="w-6 h-6 text-red-500 shrink-0" />
        ) : status === "unavailable" ? (
          <XCircle className="w-6 h-6 text-red-500 shrink-0" />
        ) : (
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin shrink-0" />
        )}
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {completed
              ? status === "done_with_gaps"
                ? "Field profile ready with data gaps"
                : "Field profile ready"
              : status === "failed"
              ? "Setup failed"
              : status === "unavailable"
              ? "Unable to check setup status"
              : "Setting up your field profile…"}
          </p>
          <p className="text-xs text-slate-500">
            {completed
              ? "All data sources loaded"
              : status === "failed"
              ? error || "Unknown error"
              : status === "unavailable"
              ? error || "Job status is unavailable"
              : STEP_LABELS[step] || "Initializing…"}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-2 rounded-full bg-emerald-600 transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>

      {/* Step list */}
      <ul className="space-y-2">
        {steps.map((s, i) => {
          const done = i < currentIdx || completed;
          const active = s === step && !completed && status !== "failed" && status !== "unavailable";
          return (
            <li key={s} className="flex items-center gap-2 text-sm">
              {done ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              ) : active ? (
                <Loader2 className="w-4 h-4 text-emerald-600 animate-spin shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-slate-200 shrink-0" />
              )}
              <span
                className={
                  done
                    ? "text-slate-500 line-through"
                    : active
                    ? "text-slate-900 font-medium"
                    : "text-slate-400"
                }
              >
                {STEP_LABELS[s]}
              </span>
            </li>
          );
        })}
      </ul>

      {/* Disclaimer */}
      <p className="text-[11px] text-slate-400 italic">
        These are estimates derived from satellite data, not on-site measurements.
      </p>
    </div>
  );
}
