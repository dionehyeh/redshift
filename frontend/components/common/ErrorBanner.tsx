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
    <div className="p-5 bg-red-50 border-2 border-red-200 rounded-2xl flex items-start justify-between gap-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-5 h-5 text-red-600" />
        </div>
        <div>
          <span className="font-bold text-sm text-red-900 block">
            Connection Issue
          </span>
          <p className="text-xs text-red-700 mt-0.5 leading-relaxed">
            {displayMsg}
          </p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-100 text-red-800 text-xs font-bold hover:bg-red-200 transition"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Retry
        </button>
      )}
    </div>
  );
}
