import { AlertCircle, RotateCcw } from "lucide-react";
import { getErrorMessage } from "@/lib/errors";

export function ErrorBanner({
  code,
  message,
  onRetry,
}: {
  code: string;
  message?: string;
  onRetry?: () => void;
}) {
  const displayMsg = message || getErrorMessage(code);

  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded-2xl flex items-start justify-between gap-3 text-red-900">
      <div className="flex items-start gap-2.5">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-sm block">Action Failed</span>
          <p className="text-xs text-red-800 mt-0.5">{displayMsg}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-semibold text-red-800 underline hover:text-red-950 flex items-center gap-1"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Retry
        </button>
      )}
    </div>
  );
}
