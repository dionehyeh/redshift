"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "./api";
import type { Job, RescoreResponse, Scenario, Plan } from "./types";

export function useJob(jobId?: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api<Job>(`/jobs/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "done_with_gaps" || status === "failed" ? false : 2000;
    },
  });
}

export function useRescore(planId: number, initialScenario: Scenario = { rain: 1.0, temp: 0.0 }) {
  const [scenario, setScenario] = useState<Scenario>(initialScenario);
  const [debouncedScenario, setDebouncedScenario] = useState<Scenario>(scenario);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedScenario(scenario);
    }, 300);
    return () => clearTimeout(timer);
  }, [scenario]);

  const query = useQuery({
    queryKey: ["rescore", planId, debouncedScenario],
    queryFn: () =>
      api<RescoreResponse>(`/plans/${planId}/rescore`, {
        method: "POST",
        body: JSON.stringify({ scenario: debouncedScenario }),
      }),
    placeholderData: (previousData) => previousData,
  });

  return {
    scenario,
    setScenario,
    reset: () => setScenario({ rain: 1.0, temp: 0.0 }),
    ...query,
  };
}
