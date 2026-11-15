"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type {
  CropListResponse,
  SeasonAnalysisStartResponse,
  SeasonCreateResponse,
  SeasonOutcome,
} from "@/lib/season-types";

const OUTCOMES: { value: SeasonOutcome; label: string; selected: string }[] = [
  { value: "good", label: "Good", selected: "bg-emerald-700 text-white border-emerald-700" },
  { value: "average", label: "Average", selected: "bg-blue-700 text-white border-blue-700" },
  { value: "poor", label: "Poor", selected: "bg-amber-600 text-white border-amber-600" },
  { value: "failed", label: "Failed", selected: "bg-red-700 text-white border-red-700" },
];

const INPUT_CLASS =
  "h-12 w-full rounded-xl border-2 border-stone-200 bg-white px-4 text-sm text-stone-800 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20";

export default function NewSeasonPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const fieldId = params.id;
  const [crops, setCrops] = useState<CropListResponse["items"]>([]);
  const [crop, setCrop] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [outcome, setOutcome] = useState<SeasonOutcome | "">("");
  const [lossPercent, setLossPercent] = useState("");
  const [suspectedCause, setSuspectedCause] = useState("unsure");
  const [investment, setInvestment] = useState("");
  const [revenue, setRevenue] = useState("");
  const [loadingCrops, setLoadingCrops] = useState(true);
  const [loading, setLoading] = useState(false);
  const [createdSeasonId, setCreatedSeasonId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<CropListResponse>("/crops")
      .then((response) => {
        if (!active) return;
        setCrops(response.items);
        setCrop(response.items[0]?.id ?? "");
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!outcome || !crop) {
      setError("Choose a crop and record the harvest outcome.");
      return;
    }

    setLoading(true);
    setError("");
    setCreatedSeasonId(null);
    try {
      const season = await api<SeasonCreateResponse>(`/fields/${fieldId}/seasons`, {
        method: "POST",
        body: JSON.stringify({
          crop,
          start_date: startDate,
          end_date: endDate,
          outcome,
          loss_percent:
            outcome === "poor" || outcome === "failed"
              ? Number(lossPercent)
              : undefined,
          suspected_cause:
            outcome === "poor" || outcome === "failed"
              ? suspectedCause
              : undefined,
          investment: investment === "" ? undefined : Number(investment),
          revenue: revenue === "" ? undefined : Number(revenue),
        }),
      });

      setCreatedSeasonId(season.id);
      try {
        await api<SeasonAnalysisStartResponse>(`/seasons/${season.id}/analyze`, {
          method: "POST",
        });
        router.push(`/seasons/${season.id}`);
      } catch (analysisError) {
        setError(
          `Season saved, but diagnosis could not be started: ${
            analysisError instanceof Error
              ? analysisError.message
              : "The analysis request failed."
          }`
        );
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to save the season."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        href={`/fields/${fieldId}`}
        className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 hover:border-green-300 hover:text-green-800"
      >
        <ArrowLeft className="h-4 w-4 text-green-700" /> Back to Plot
      </Link>

      <header className="space-y-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-emerald-800">
          <Calendar className="h-3.5 w-3.5" /> Historical Harvest Record
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-stone-900">
          Log Completed Harvest Season
        </h1>
        <p className="text-sm text-stone-600">
          Record the season details. The diagnostic uses the available climate
          observations and reports any data gaps.
        </p>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800">
          {error}
          {createdSeasonId && (
            <Link
              href={`/seasons/${createdSeasonId}`}
              className="ml-2 font-bold underline"
            >
              Open saved season
            </Link>
          )}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-3xl border-2 border-stone-200 bg-white p-8 shadow-sm"
      >
        <div className="space-y-1.5">
          <label htmlFor="season-crop" className="text-sm font-bold text-stone-800">
            Crop Cultivated
          </label>
          <select
            id="season-crop"
            required
            value={crop}
            onChange={(event) => setCrop(event.target.value)}
            disabled={loadingCrops || crops.length === 0}
            className={INPUT_CLASS}
          >
            {loadingCrops && <option value="">Loading crop catalog…</option>}
            {!loadingCrops && crops.length === 0 && (
              <option value="">No crops are available</option>
            )}
            {crops.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name.en}
                {item.name.ml ? ` (${item.name.ml})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor="season-start" className="text-sm font-bold text-stone-800">
              Sowing / Planting Date
            </label>
            <input
              id="season-start"
              type="date"
              required
              value={startDate}
              max={endDate || undefined}
              onChange={(event) => setStartDate(event.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="season-end" className="text-sm font-bold text-stone-800">
              Harvest Date
            </label>
            <input
              id="season-end"
              type="date"
              required
              value={endDate}
              min={startDate || undefined}
              onChange={(event) => setEndDate(event.target.value)}
              className={INPUT_CLASS}
            />
          </div>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-bold text-stone-800">
            Observed Harvest Outcome
          </legend>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            {OUTCOMES.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={outcome === option.value}
                onClick={() => setOutcome(option.value)}
                className={`h-12 rounded-xl border-2 text-xs font-extrabold transition ${
                  outcome === option.value
                    ? `${option.selected} shadow-md`
                    : "border-stone-200 bg-stone-50 text-stone-700 hover:bg-stone-100"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>

        {(outcome === "poor" || outcome === "failed") && (
          <div className="space-y-4 rounded-2xl border-2 border-stone-200 bg-stone-50 p-5">
            <div className="space-y-1.5">
              <label htmlFor="season-loss" className="flex justify-between text-sm font-bold text-stone-800">
                <span>Estimated Crop Loss</span>
                <span className="font-extrabold text-red-700">{lossPercent || 0}%</span>
              </label>
              <input
                id="season-loss"
                type="range"
                min={0}
                max={100}
                step={1}
                value={lossPercent || 0}
                onChange={(event) => setLossPercent(event.target.value)}
                className="h-2 w-full cursor-pointer rounded-lg bg-stone-200 accent-green-700"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="suspected-cause" className="text-sm font-bold text-stone-800">
                Suspected Primary Cause
              </label>
              <select
                id="suspected-cause"
                value={suspectedCause}
                onChange={(event) => setSuspectedCause(event.target.value)}
                className={INPUT_CLASS}
              >
                <option value="water_shortage">Water shortage / dry spell</option>
                <option value="excess_rain">Excess rain / waterlogging</option>
                <option value="pests">Pests or disease</option>
                <option value="unsure">Not sure</option>
              </select>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor="season-investment" className="text-sm font-bold text-stone-800">
              Investment (optional)
            </label>
            <input
              id="season-investment"
              type="number"
              min="0"
              step="0.01"
              value={investment}
              onChange={(event) => setInvestment(event.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="season-revenue" className="text-sm font-bold text-stone-800">
              Revenue (optional)
            </label>
            <input
              id="season-revenue"
              type="number"
              min="0"
              step="0.01"
              value={revenue}
              onChange={(event) => setRevenue(event.target.value)}
              className={INPUT_CLASS}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || loadingCrops || crops.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-green-700 to-emerald-700 py-3.5 text-base font-bold text-white shadow-md transition hover:from-green-800 hover:to-emerald-800 disabled:opacity-60"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Sparkles className="h-5 w-5 text-emerald-200" />
          )}
          {loading ? "Saving season and starting diagnosis…" : "Save Season & Run Diagnostic"}
        </button>
      </form>
    </div>
  );
}
