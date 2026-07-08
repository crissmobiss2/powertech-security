"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, severityColor, cn } from "@/lib/utils";
import type { Alert } from "@/types";
import { Radio, Filter, RefreshCw } from "lucide-react";

const SEVERITY_OPTIONS = ["", "critical", "high", "medium", "low", "info"];
const STATUS_OPTIONS = ["", "draft", "sending", "sent", "partial_failure", "failed"];

function alertStatusColor(status: string): string {
  const map: Record<string, string> = {
    draft: "text-gray-400 bg-surface-3",
    sending: "text-blue-400 bg-blue-950",
    sent: "text-green-400 bg-green-950",
    partial_failure: "text-yellow-400 bg-yellow-950",
    failed: "text-red-400 bg-red-950",
  };
  return map[status] ?? "text-gray-400 bg-surface-3";
}

function DeliveryBar({ sent, failed, total }: { sent: number; failed: number; total: number }) {
  if (total === 0) return <span className="text-xs text-gray-600">No recipients</span>;
  const pctSent = (sent / total) * 100;
  const pctFailed = (failed / total) * 100;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden max-w-[80px]">
        <div className="h-full flex">
          <div className="bg-green-500 h-full" style={{ width: `${pctSent}%` }} />
          <div className="bg-red-500 h-full" style={{ width: `${pctFailed}%` }} />
        </div>
      </div>
      <span className="text-xs text-gray-500 font-variant-numeric tabular-nums">
        {sent}/{total}
      </span>
    </div>
  );
}

export default function AlertsPage() {
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["alerts", { severity, status, page }],
    queryFn: () =>
      api.alerts.list({
        ...(severity && { severity }),
        ...(status && { status }),
        page,
        limit: 20,
      }),
  });

  const alerts: Alert[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Alerts" />
      <main className="flex-1 p-6">
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <select value={severity} onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All severities</option>
              {SEVERITY_OPTIONS.filter(Boolean).map((s) => (<option key={s} value={s}>{s}</option>))}
            </select>
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (<option key={s} value={s}>{s.replace("_", " ")}</option>))}
            </select>
            <button onClick={() => refetch()}
              className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.04]">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Alert</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">Severity</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Delivery</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Channels</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">Sent</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-5 py-4"><div className="h-4 bg-surface-3 rounded w-56" /></td>
                    <td className="px-4 py-4 hidden md:table-cell"><div className="h-5 bg-surface-3 rounded w-16" /></td>
                    <td className="px-4 py-4"><div className="h-5 bg-surface-3 rounded w-16" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded w-20" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded w-20" /></td>
                    <td className="px-4 py-4 hidden sm:table-cell"><div className="h-4 bg-surface-3 rounded w-24" /></td>
                  </tr>
                ))
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center">
                    <Radio className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">No alerts found</p>
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-white line-clamp-1">{alert.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{alert.message}</p>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border", severityColor(alert.severity))}>
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", alertStatusColor(alert.status))}>
                        {alert.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <DeliveryBar sent={alert.sent_count} failed={alert.failed_count} total={alert.total_recipients} />
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <div className="flex gap-1">
                        {alert.channels.map((ch) => (
                          <span key={ch} className="text-[10px] px-1.5 py-0.5 bg-surface-3 text-gray-400 rounded uppercase">{ch}</span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-gray-500">{alert.sent_at ? timeAgo(alert.sent_at) : "Pending"}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {data && data.pages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.04]">
              <p className="text-xs text-gray-500">
                Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, data.total)} of {data.total}
              </p>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="text-xs px-3 py-1.5 bg-surface-2 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-surface-3 transition-colors">Previous</button>
                <button onClick={() => setPage((p) => Math.min(data.pages, p + 1))} disabled={page === data.pages}
                  className="text-xs px-3 py-1.5 bg-surface-2 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-surface-3 transition-colors">Next</button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
