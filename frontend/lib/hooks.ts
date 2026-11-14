"use client";
import { useState, useEffect, useRef } from "react";
import { api } from "./api";

type JobStatus = "queued" | "running" | "done" | "done_with_gaps" | "failed";

// Poll a background job until done or failed
export function useJob(jobId: string | null) {
  const [status, setStatus] = useState<JobStatus | "unavailable" | null>(null);
  const [step, setStep] = useState<string>("");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const data = await api<{
          status: JobStatus;
          step: string | null;
          progress: number;
          error: string | null;
        }>(`/jobs/${jobId}`);
        setStatus(data.status);
        setStep(data.step || "");
        setProgress(data.progress || 0);
        if (data.status === "done" || data.status === "done_with_gaps" || data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          if (data.status === "failed") setError(data.error || "Job failed");
        }
      } catch (e: any) {
        setStatus("unavailable");
        setError(e instanceof Error ? e.message : "Unable to retrieve job status");
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId]);

  return { status, step, progress, error };
}
