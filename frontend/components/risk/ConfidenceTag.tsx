import { Info } from "lucide-react";

export function ConfidenceTag({
  level,
  reason,
}: {
  level: "high" | "medium" | "low" | string;
  reason?: string;
}) {
  const colors: Record<string, string> = {
    high: "bg-emerald-50 text-emerald-800 border-emerald-200",
    medium: "bg-blue-50 text-blue-800 border-blue-200",
    low: "bg-slate-100 text-slate-700 border-slate-200",
  };

  return (
    <span
      title={reason}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${
        colors[level.toLowerCase()] || colors.low
      }`}
    >
      <Info className="w-3 h-3" />
      Confidence: {level.toUpperCase()}
    </span>
  );
}
