import { Database, Wifi } from "lucide-react";

export function DataBadge({
  isLive = false,
}: {
  isLive?: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
        isLive
          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
          : "bg-blue-50 text-blue-800 border-blue-200"
      }`}
    >
      {isLive ? <Wifi className="w-3 h-3 text-emerald-600" /> : <Database className="w-3 h-3 text-blue-600" />}
      <span>{isLive ? "NASA Live Data" : "Climatology Cached"}</span>
    </span>
  );
}
