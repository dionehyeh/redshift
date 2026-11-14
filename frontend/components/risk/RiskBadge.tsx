import { cva } from "class-variance-authority";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
  {
    variants: {
      level: {
        green: "bg-good-bg text-good",
        amber: "bg-watch-bg text-watch",
        red: "bg-risk-bg text-risk",
      },
    },
    defaultVariants: {
      level: "green",
    },
  }
);

const ICONS = {
  green: CheckCircle2,
  amber: AlertTriangle,
  red: XCircle,
} as const;

export function RiskBadge({
  level,
  label,
  className,
}: {
  level: "green" | "amber" | "red";
  label: string;
  className?: string;
}) {
  const Icon = ICONS[level] || CheckCircle2;
  return (
    <span className={cn(badgeVariants({ level }), className)}>
      <Icon className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
