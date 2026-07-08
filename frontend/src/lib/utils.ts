import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function timeAgo(date: string | null): string {
  if (!date) return "—";
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function formatDate(date: string | null, fmt = "MMM d, yyyy HH:mm"): string {
  if (!date) return "—";
  return format(new Date(date), fmt);
}

export function severityColor(severity: string): string {
  const map: Record<string, string> = {
    critical: "text-red-400 bg-red-950 border-red-800",
    high: "text-orange-400 bg-orange-950 border-orange-800",
    medium: "text-yellow-400 bg-yellow-950 border-yellow-800",
    low: "text-green-400 bg-green-950 border-green-800",
    info: "text-blue-400 bg-blue-950 border-blue-800",
  };
  return map[severity] ?? "text-gray-400 bg-surface-3 border-white/[0.06]";
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    new: "text-red-400 bg-red-950",
    acknowledged: "text-orange-400 bg-orange-950",
    investigating: "text-yellow-400 bg-yellow-950",
    in_progress: "text-blue-400 bg-blue-950",
    resolved: "text-green-400 bg-green-950",
    closed: "text-gray-400 bg-surface-3",
    false_positive: "text-gray-400 bg-surface-3",
    open: "text-red-400 bg-red-950",
    assigned: "text-orange-400 bg-orange-950",
    on_hold: "text-yellow-400 bg-yellow-950",
    cancelled: "text-gray-400 bg-surface-3",
  };
  return map[status] ?? "text-gray-400 bg-surface-3";
}

export function assetStatusColor(status: string): string {
  const map: Record<string, string> = {
    online: "text-green-400",
    offline: "text-red-400",
    degraded: "text-yellow-400",
    maintenance: "text-blue-400",
    decommissioned: "text-gray-500",
    unknown: "text-gray-400",
  };
  return map[status] ?? "text-gray-400";
}
