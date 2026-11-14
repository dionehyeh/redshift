import { ShieldAlert } from "lucide-react";

export function EstimatesNote() {
  return (
    <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-start gap-2.5 text-xs text-slate-600">
      <ShieldAlert className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
      <p>
        <strong>Estimates, not guarantees.</strong> Derived from NASA satellite observations and regional agronomic rules.
        Local review with an agricultural extension officer is advised before purchasing seeds or applying inputs.
      </p>
    </div>
  );
}
