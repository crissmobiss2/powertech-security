"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, severityColor, statusColor, cn } from "@/lib/utils";
import type { Incident } from "@/types";
import { AlertTriangle, Plus, Filter, RefreshCw } from "lucide-react";

const SEVERITY_OPTIONS = ["", "critical", "high", "medium", "low", "info"];
const STATUS_OPTIONS = [
  "", "new", "acknowledged", "investigating", "in_progress", "resolved", "closed",
];

export default function IncidentsPage() {
  const qc = useQueryClient();
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["incidents", { severity, status, page }],
    queryFn: () =>
      api.incidents.list({
        ...(severity && { severity }),
        ...(status && { status }),
        page,
        limit: 20,
      }),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => api.incidents.acknowledge(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  const incidents: Incident[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Incidents" subtitle="Security incident management" />

      <main className="flex-1 p-6">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-600" />
            <select
              value={severity}
              onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-brand-500/50"
            >
              <option value="">All severities</option>
              {SEVERITY_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s} className="capitalize">{s}</option>
              ))}
            </select>
            <select
              value={status}
              onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-brand-500/50"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s} className="capitalize">{s.replace("_", " ")}</option>
              ))}
            </select>
            <button
              onClick={() => refetch()}
              className="p-2 text-gray-500 hover:text-gray-300 hover:bg-white/[0.04] rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20">
            <Plus className="w-4 h-4" />
            New Incident
          </button>
        </div>

        {/* Table */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.04]">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Incident
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">
                  Severity
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">
                  SLA Due
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">
                  Created
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-shimmer">
                    <td className="px-5 py-4">
                      <div className="h-4 bg-surface-3 rounded-lg w-64" />
                    </td>
                    <td className="px-4 py-4 hidden md:table-cell">
                      <div className="h-5 bg-surface-3 rounded-lg w-16" />
                    </td>
                    <td className="px-4 py-4">
                      <div className="h-5 bg-surface-3 rounded-lg w-20" />
                    </td>
                    <td className="px-4 py-4 hidden lg:table-cell">
                      <div className="h-4 bg-surface-3 rounded-lg w-24" />
                    </td>
                    <td className="px-4 py-4 hidden sm:table-cell">
                      <div className="h-4 bg-surface-3 rounded-lg w-24" />
                    </td>
                    <td className="px-4 py-4" />
                  </tr>
                ))
              ) : incidents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center">
                    <AlertTriangle className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">No incidents found</p>
                  </td>
                </tr>
              ) : (
                incidents.map((incident) => (
                  <tr key={incident.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-5 py-3.5">
                      <div>
                        <p className="font-medium text-white line-clamp-1">{incident.title}</p>
                        {incident.description && (
                          <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{incident.description}</p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <span className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border",
                        severityColor(incident.severity)
                      )}>
                        {incident.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                        statusColor(incident.status)
                      )}>
                        {incident.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className={cn(
                        "text-xs",
                        incident.sla_due_at && new Date(incident.sla_due_at) < new Date()
                          ? "text-red-400 font-medium"
                          : "text-gray-500"
                      )}>
                        {incident.sla_due_at ? timeAgo(incident.sla_due_at) : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-gray-500">{timeAgo(incident.created_at)}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      {incident.status === "new" && (
                        <button
                          onClick={() => acknowledgeMutation.mutate(incident.id)}
                          disabled={acknowledgeMutation.isPending}
                          className="text-xs px-2.5 py-1 bg-surface-2 hover:bg-blue-900/50 text-gray-300 hover:text-blue-300 rounded-lg border border-white/[0.06] hover:border-blue-700 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          Acknowledge
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.04]">
              <p className="text-xs text-gray-500">
                Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, data.total)} of {data.total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="text-xs px-3 py-1.5 bg-surface-2 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-surface-3 transition-colors"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                  disabled={page === data.pages}
                  className="text-xs px-3 py-1.5 bg-surface-2 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-surface-3 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
