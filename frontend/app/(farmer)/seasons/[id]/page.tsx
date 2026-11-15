"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  CircleAlert,
  Loader2,
  Pencil,
  RefreshCw,
  Save,
  ShieldAlert,
  Sprout,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  CropListResponse,
  FindingReviewResponse,
  SeasonAnalysis,
  SeasonOutcome,
  SeasonPatchRequest,
  SeasonRecord,
  SeasonFinding,
} from "@/lib/season-types";

const CAUSES = [
  { value: "water_stress", label: "Water stress" },
  { value: "heat_stress", label: "Heat stress" },
  { value: "excess_rain", label: "Excess rain / waterlogging" },
  { value: "pest_attack", label: "Pest or disease" },
  { value: "unknown_vegetation_stress", label: "Other vegetation stress" },
  { value: "other", label: "Other cause" },
];

const IN_PROGRESS = new Set(["queued", "running"]);
const TERMINAL = new Set(["done", "done_with_gaps", "failed"]);

function readable(value: string) {
  return value.replace(/_/g, " ");
}

function statusLabel(status: SeasonAnalysis["analysis_status"]) {
  return status.replace(/_/g, " ");
}

function findingTitle(kind: string) {
  const labels: Record<string, string> = {
    rain_deficit: "Rainfall deficit",
    heat: "Heat stress",
    ndvi_dip: "Low satellite greenness",
    cloud_gap: "Satellite image gap",
    bare_field: "Low vegetation cover",
  };
  return labels[kind] ?? readable(kind);
}

export default function SeasonDiagnosisPage({
  params,
}: {
  params: { id: string };
}) {
  const seasonId = params.id;
  const [season, setSeason] = useState<SeasonRecord | null>(null);
  const [analysis, setAnalysis] = useState<SeasonAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savingSeason, setSavingSeason] = useState(false);
  const [editingSeason, setEditingSeason] = useState(false);
  const [reviewingFinding, setReviewingFinding] = useState<number | null>(null);
  const [correctionCauses, setCorrectionCauses] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refreshAnalysis = useCallback(async () => {
    const result = await api<SeasonAnalysis>(`/seasons/${seasonId}/analysis`);
    setAnalysis(result);
    return result;
  }, [seasonId]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      api<SeasonRecord>(`/seasons/${seasonId}`),
      api<SeasonAnalysis>(`/seasons/${seasonId}/analysis`),
    ])
      .then(([seasonResult, analysisResult]) => {
        if (!active) return;
        setSeason(seasonResult);
        setAnalysis(analysisResult);
        setError("");
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Could not load the season diagnosis."
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [seasonId]);

  useEffect(() => {
    if (!analysis || !IN_PROGRESS.has(analysis.analysis_status)) return;
    let active = true;
    const timer = window.setInterval(() => {
      api<SeasonAnalysis>(`/seasons/${seasonId}/analysis`)
        .then((result) => {
          if (active) setAnalysis(result);
        })
        .catch((requestError: unknown) => {
          if (!active) return;
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Could not refresh the diagnosis status."
          );
        });
    }, 2000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [analysis?.analysis_status, seasonId]);

  async function startAnalysis() {
    setRefreshing(true);
    setError("");
    setMessage("");
    try {
      const result = await api<{ season_id: number; job_id: string; status: "queued" }>(
        `/seasons/${seasonId}/analyze`,
        { method: "POST" }
      );
      setAnalysis((current) => ({
        season_id: result.season_id,
        approval_status: current?.approval_status ?? season?.approval_status ?? "pending_review",
        analysis_status: "queued",
        job_id: result.job_id,
        comparison_years: null,
        findings: [],
        gaps: [],
        likely_causes: null,
        followup_question: null,
        analysis_error: null,
      }));
      setMessage("Diagnosis started. This page will update when results are ready.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not start the season diagnosis."
      );
    } finally {
      setRefreshing(false);
    }
  }

  async function saveSeason(updates: SeasonPatchRequest) {
    setSavingSeason(true);
    setError("");
    setMessage("");
    try {
      await api(`/seasons/${seasonId}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      });
      const updatedSeason = await api<SeasonRecord>(`/seasons/${seasonId}`);
      setSeason(updatedSeason);
      setEditingSeason(false);
      setMessage("Season updated. Starting a fresh diagnosis with the updated details.");
      await startAnalysis();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not update the season."
      );
    } finally {
      setSavingSeason(false);
    }
  }

  async function reviewFinding(
    finding: SeasonFinding,
    action: "confirm" | "correct" | "reject"
  ) {
    setReviewingFinding(finding.id);
    setError("");
    setMessage("");
    try {
      const body: { action: typeof action; new_cause?: string } = { action };
      if (action === "correct") {
        const cause = correctionCauses[finding.id];
        if (!cause) {
          setError("Choose the corrected cause before submitting.");
          return;
        }
        body.new_cause = cause;
      }

      const result = await api<FindingReviewResponse>(
        `/findings/${finding.id}/review`,
        { method: "POST", body: JSON.stringify(body) }
      );
      const [updatedSeason] = await Promise.all([
        api<SeasonRecord>(`/seasons/${seasonId}`),
        refreshAnalysis(),
      ]);
      setSeason(updatedSeason);
      setMessage(
        result.review_status === "rejected"
          ? "Finding rejected."
          : `Finding ${result.review_status}.`
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not save your finding review."
      );
    } finally {
      setReviewingFinding(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 p-16 text-center">
        <Loader2 className="mx-auto h-10 w-10 animate-spin text-green-700" />
        <p className="text-sm font-semibold text-stone-600">Loading recorded season and diagnosis…</p>
      </div>
    );
  }

  if (error && !season) {
    return (
      <div className="mx-auto max-w-xl space-y-4 rounded-3xl border-2 border-red-200 bg-red-50 p-8 text-center">
        <p role="alert" className="text-sm font-medium text-red-800">{error}</p>
        <Link
          href="/fields"
          className="inline-flex items-center gap-2 rounded-xl bg-green-800 px-5 py-2.5 text-sm font-bold text-white"
        >
          <ArrowLeft className="h-4 w-4" /> Back to My Fields
        </Link>
      </div>
    );
  }

  const analysisStatus = analysis?.analysis_status ?? "not_started";
  const isComplete = analysisStatus === "done" || analysisStatus === "done_with_gaps";
  const canStart = !analysis || analysisStatus === "not_started" || analysisStatus === "failed" || TERMINAL.has(analysisStatus);

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <Link
        href={season ? `/fields/${season.field_id}` : "/fields"}
        className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 hover:border-green-300 hover:text-green-800"
      >
        <ArrowLeft className="h-4 w-4 text-green-700" /> Back to Field
      </Link>

      {error && (
        <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}
      {message && (
        <div role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-900">
          {message}
        </div>
      )}

      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-800">
                <Sprout className="h-3.5 w-3.5" /> Season diagnosis
              </span>
              <span className="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-xs font-bold capitalize text-stone-700">
                Review: {readable(season?.approval_status ?? "pending_review")}
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-stone-900">
              {season?.crop ?? "Season"} diagnosis
            </h1>
            <p className="text-sm text-stone-600">
              {season?.start_date ?? "Date not recorded"} to {season?.end_date ?? "Date not recorded"}
              {" · "}Outcome: {season?.outcome ?? "Not recorded"}
              {season?.loss_percent !== null && season?.loss_percent !== undefined
                ? ` · Estimated loss: ${season.loss_percent}%`
                : ""}
            </p>
            {(season?.investment !== null && season?.investment !== undefined) ||
            (season?.revenue !== null && season?.revenue !== undefined) ? (
              <p className="text-sm text-stone-600">
                {season.investment !== null && season.investment !== undefined
                  ? `Investment: ${season.investment}`
                  : ""}
                {season.investment !== null && season.investment !== undefined &&
                season.revenue !== null && season.revenue !== undefined
                  ? " · "
                  : ""}
                {season.revenue !== null && season.revenue !== undefined
                  ? `Revenue: ${season.revenue}`
                  : ""}
              </p>
            ) : null}
          </div>
          {season && !editingSeason && (
            <button
              type="button"
              onClick={() => setEditingSeason(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-sm font-bold text-stone-700 hover:border-green-400 hover:text-green-800"
            >
              <Pencil className="h-4 w-4" /> Edit season
            </button>
          )}
        </div>
      </header>

      {editingSeason && season && (
        <SeasonEditor
          season={season}
          saving={savingSeason}
          onCancel={() => setEditingSeason(false)}
          onSave={saveSeason}
        />
      )}

      <section className="space-y-4 rounded-3xl border-2 border-stone-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-extrabold text-stone-900">Analysis status</h2>
            <p className="mt-1 text-sm capitalize text-stone-600">
              {statusLabel(analysisStatus)}
              {analysis?.job_id ? ` · Job ${analysis.job_id}` : ""}
            </p>
          </div>
          {canStart && (
            <button
              type="button"
              onClick={startAnalysis}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-xl bg-green-800 px-4 py-2.5 text-sm font-bold text-white hover:bg-green-700 disabled:opacity-60"
            >
              {refreshing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {analysisStatus === "not_started" ? "Run diagnosis" : "Run again"}
            </button>
          )}
        </div>

        {IN_PROGRESS.has(analysisStatus) && (
          <div className="flex items-center gap-3 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">
            <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
            <span>Diagnosis is running. This page checks for updates automatically.</span>
          </div>
        )}
        {analysisStatus === "failed" && (
          <div className="flex items-start gap-3 rounded-xl bg-red-50 p-4 text-sm text-red-800">
            <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-bold">Analysis failed</p>
              <p>{analysis?.analysis_error || "The backend could not complete this diagnosis."}</p>
            </div>
          </div>
        )}
        {analysisStatus === "not_started" && (
          <p className="text-sm text-stone-600">
            No analysis has been run for this season yet.
          </p>
        )}
        {analysis?.comparison_years && (
          <p className="text-sm text-stone-600">
            Historical comparison: <span className="font-semibold">{analysis.comparison_years}</span>
          </p>
        )}
      </section>

      {isComplete && analysis && (
        <>
          {analysis.likely_causes && (
            <section className="space-y-4 rounded-3xl border-2 border-emerald-200 bg-emerald-50/70 p-6">
              <h2 className="text-xl font-extrabold text-emerald-950">Likely causes</h2>
              {analysis.likely_causes.suspected.length > 0 ? (
                <ul className="space-y-3">
                  {analysis.likely_causes.suspected.map((cause, index) => (
                    <li key={`${cause.cause}-${index}`} className="rounded-xl border border-emerald-200 bg-white p-4">
                      <p className="font-bold capitalize text-stone-900">{readable(cause.cause)}</p>
                      {cause.from_finding && (
                        <p className="mt-1 text-sm text-stone-600">
                          Based on {findingTitle(cause.from_finding)}
                          {cause.weeks
                            ? `, weeks ${cause.weeks[0]}–${cause.weeks[1]}`
                            : ""}
                          {cause.stage ? ` · ${readable(cause.stage)} stage` : ""}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-stone-700">No likely causes were identified from the available findings.</p>
              )}
              {analysis.likely_causes.farmer_cause && (
                <p className="text-sm text-stone-700">
                  Farmer-reported cause: {readable(analysis.likely_causes.farmer_cause)}
                </p>
              )}
              {analysis.likely_causes.not_assessable.length > 0 && (
                <p className="text-sm text-stone-600">
                  Not assessed by satellite data: {analysis.likely_causes.not_assessable.join(", ")}.
                </p>
              )}
            </section>
          )}

          <section className="space-y-4">
            <h2 className="text-xl font-extrabold text-stone-900">
              Detected environmental stress events
            </h2>
            {analysis.findings.length === 0 ? (
              <div className="rounded-3xl border-2 border-stone-200 bg-white p-8 text-center text-sm text-stone-600">
                Analysis completed with no stress findings in the available data.
              </div>
            ) : (
              analysis.findings.map((finding) => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  correctionCause={correctionCauses[finding.id] ?? ""}
                  disabled={reviewingFinding === finding.id}
                  onCorrectionCauseChange={(cause) =>
                    setCorrectionCauses((previous) => ({
                      ...previous,
                      [finding.id]: cause,
                    }))
                  }
                  onReview={(action) => reviewFinding(finding, action)}
                />
              ))
            )}
          </section>

          {analysis.gaps.length > 0 && (
            <section className="space-y-2 rounded-3xl border border-amber-200 bg-amber-50 p-6">
              <h2 className="flex items-center gap-2 font-bold text-amber-950">
                <ShieldAlert className="h-5 w-5" /> Data gaps and limitations
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
                {analysis.gaps.map((gap, index) => <li key={`${gap}-${index}`}>{gap}</li>)}
              </ul>
            </section>
          )}

          {analysis.followup_question && (
            <section className="rounded-2xl border border-stone-200 bg-stone-50 p-5">
              <h2 className="font-bold text-stone-900">Ground-truth follow-up</h2>
              <p className="mt-1 text-sm text-stone-700">{analysis.followup_question}</p>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function FindingCard({
  finding,
  correctionCause,
  disabled,
  onCorrectionCauseChange,
  onReview,
}: {
  finding: SeasonFinding;
  correctionCause: string;
  disabled: boolean;
  onCorrectionCauseChange: (cause: string) => void;
  onReview: (action: "confirm" | "correct" | "reject") => void;
}) {
  const pending = finding.review_status === "pending";
  return (
    <article className="space-y-4 rounded-3xl border-2 border-stone-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-extrabold capitalize text-stone-900">
            {findingTitle(finding.kind)}
          </h3>
          <p className="mt-1 text-sm leading-relaxed text-stone-700">{finding.text}</p>
        </div>
        <span className="rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-xs font-bold capitalize text-amber-900">
          Severity {finding.severity}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-3 border-t border-stone-100 pt-4 text-sm sm:grid-cols-3">
        <div><dt className="text-xs text-stone-500">Weeks</dt><dd className="font-semibold text-stone-800">{finding.weeks[0]}–{finding.weeks[1]}</dd></div>
        <div><dt className="text-xs text-stone-500">Crop stage</dt><dd className="capitalize text-stone-800">{readable(finding.crop_stage)}</dd></div>
        <div><dt className="text-xs text-stone-500">Deviation</dt><dd className="text-stone-800">{finding.deviation || "Not available"}</dd></div>
        <div><dt className="text-xs text-stone-500">Confidence</dt><dd className="capitalize text-stone-800">{finding.confidence}</dd></div>
        <div><dt className="text-xs text-stone-500">Source</dt><dd className="text-stone-800">{finding.source}</dd></div>
        <div><dt className="text-xs text-stone-500">Resolution</dt><dd className="text-stone-800">{finding.resolution}</dd></div>
      </dl>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-100 pt-4">
        <span className="text-xs font-semibold capitalize text-stone-600">
          Review: {readable(finding.review_status)}
        </span>
        {pending && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={disabled}
              onClick={() => onReview("confirm")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-100 px-3 py-2 text-xs font-bold text-emerald-900 hover:bg-emerald-200 disabled:opacity-50"
            >
              <Check className="h-4 w-4" /> Confirm
            </button>
            <select
              aria-label={`Corrected cause for ${findingTitle(finding.kind)}`}
              value={correctionCause}
              disabled={disabled}
              onChange={(event) => onCorrectionCauseChange(event.target.value)}
              className="h-9 rounded-lg border border-stone-300 bg-white px-2 text-xs text-stone-800"
            >
              <option value="">Select cause…</option>
              {CAUSES.map((cause) => (
                <option key={cause.value} value={cause.value}>{cause.label}</option>
              ))}
            </select>
            <button
              type="button"
              disabled={disabled || !correctionCause}
              onClick={() => onReview("correct")}
              className="rounded-lg bg-blue-100 px-3 py-2 text-xs font-bold text-blue-900 hover:bg-blue-200 disabled:opacity-50"
            >
              Correct
            </button>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onReview("reject")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-stone-100 px-3 py-2 text-xs font-bold text-stone-700 hover:bg-stone-200 disabled:opacity-50"
            >
              <X className="h-4 w-4" /> Reject
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

function SeasonEditor({
  season,
  saving,
  onCancel,
  onSave,
}: {
  season: SeasonRecord;
  saving: boolean;
  onCancel: () => void;
  onSave: (updates: SeasonPatchRequest) => Promise<void>;
}) {
  const [crops, setCrops] = useState<CropListResponse["items"]>([]);
  const [crop, setCrop] = useState(season.crop ?? "");
  const [startDate, setStartDate] = useState(season.start_date ?? "");
  const [endDate, setEndDate] = useState(season.end_date ?? "");
  const [outcome, setOutcome] = useState<SeasonOutcome | "">(season.outcome ?? "");
  const [lossPercent, setLossPercent] = useState(
    season.loss_percent === null ? "" : String(season.loss_percent)
  );
  const [suspectedCause, setSuspectedCause] = useState(season.suspected_cause ?? "");
  const [investment, setInvestment] = useState(
    season.investment === null ? "" : String(season.investment)
  );
  const [revenue, setRevenue] = useState(
    season.revenue === null ? "" : String(season.revenue)
  );
  const [loadingCrops, setLoadingCrops] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<CropListResponse>("/crops")
      .then((response) => {
        if (!active) return;
        setCrops(response.items);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Could not load the crop catalog."
          );
        }
      })
      .finally(() => {
        if (active) setLoadingCrops(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!crop || !outcome) {
      setError("Choose a crop and outcome.");
      return;
    }
    if (endDate < startDate) {
      setError("Harvest date must be on or after the planting date.");
      return;
    }
    setError("");
    await onSave({
      crop,
      start_date: startDate,
      end_date: endDate,
      outcome,
      loss_percent: lossPercent === "" ? null : Number(lossPercent),
      suspected_cause: suspectedCause || null,
      investment: investment === "" ? null : Number(investment),
      revenue: revenue === "" ? null : Number(revenue),
    });
  }

  const inputClass =
    "h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm text-stone-800 focus:border-green-600 focus:outline-none";

  return (
    <form
      onSubmit={submit}
      className="space-y-4 rounded-3xl border-2 border-green-200 bg-white p-6 shadow-sm"
    >
      <h2 className="text-lg font-extrabold text-stone-900">Update season record</h2>
      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Crop
          <select
            required
            value={crop ?? ""}
            disabled={loadingCrops || crops.length === 0}
            onChange={(event) => setCrop(event.target.value)}
            className={inputClass}
          >
            {crops.map((item) => (
              <option key={item.id} value={item.id}>{item.name.en}</option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Outcome
          <select
            required
            value={outcome}
            onChange={(event) => setOutcome(event.target.value as SeasonOutcome)}
            className={inputClass}
          >
            <option value="">Select outcome…</option>
            <option value="good">Good</option>
            <option value="average">Average</option>
            <option value="poor">Poor</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Planting date
          <input
            required
            type="date"
            value={startDate}
            max={endDate || undefined}
            onChange={(event) => setStartDate(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Harvest date
          <input
            required
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(event) => setEndDate(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Loss percent
          <input
            type="number"
            min="0"
            max="100"
            value={lossPercent}
            onChange={(event) => setLossPercent(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Suspected cause
          <select
            value={suspectedCause}
            onChange={(event) => setSuspectedCause(event.target.value)}
            className={inputClass}
          >
            <option value="">Not provided</option>
            <option value="water_shortage">Water shortage</option>
            <option value="excess_rain">Excess rain / waterlogging</option>
            <option value="pests">Pests or disease</option>
            <option value="unsure">Not sure</option>
          </select>
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Investment
          <input
            type="number"
            min="0"
            step="0.01"
            value={investment}
            onChange={(event) => setInvestment(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="space-y-1 text-sm font-semibold text-stone-700">
          Revenue
          <input
            type="number"
            min="0"
            step="0.01"
            value={revenue}
            onChange={(event) => setRevenue(event.target.value)}
            className={inputClass}
          />
        </label>
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 px-4 py-2 text-sm font-bold text-stone-700 disabled:opacity-50"
        >
          <X className="h-4 w-4" /> Cancel
        </button>
        <button
          type="submit"
          disabled={saving || loadingCrops || crops.length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg bg-green-800 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save and re-analyze
        </button>
      </div>
    </form>
  );
}
