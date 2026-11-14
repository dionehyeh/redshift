import { WifiOff } from "lucide-react";

export function OfflineBanner() {
  return (
    <div className="bg-slate-800 text-slate-100 px-4 py-2 text-xs flex items-center justify-center gap-2">
      <WifiOff className="w-3.5 h-3.5 text-amber-400" />
      <span>Offline Mode active: Displaying saved field profiles and cached 20-year NASA normals.</span>
    </div>
  );
}
