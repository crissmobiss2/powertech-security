"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, cn } from "@/lib/utils";
import type { Client, RiskTier } from "@/types";
import { Users, Filter, RefreshCw, Plus, Building2, Trash2 } from "lucide-react";

const STATUS_OPTIONS = ["", "active", "inactive", "suspended", "prospect"];
const RISK_OPTIONS: RiskTier[] = ["critical", "high", "medium", "low"];

function riskColor(risk: string): string {
  const map: Record<string, string> = {
    critical: "text-red-400 bg-red-950 border-red-800",
    high: "text-orange-400 bg-orange-950 border-orange-800",
    medium: "text-yellow-400 bg-yellow-950 border-yellow-800",
    low: "text-green-400 bg-green-950 border-green-800",
  };
  return map[risk] ?? "text-gray-400 bg-surface-3 border-white/[0.06]";
}

function clientStatusColor(status: string): string {
  const map: Record<string, string> = {
    active: "text-green-400 bg-green-950",
    inactive: "text-gray-400 bg-surface-3",
    suspended: "text-red-400 bg-red-950",
    prospect: "text-blue-400 bg-blue-950",
  };
  return map[status] ?? "text-gray-400 bg-surface-3";
}

export default function ClientsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [riskTier, setRiskTier] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["clients", { status: statusFilter, risk_tier: riskTier, search, page }],
    queryFn: () =>
      api.clients.list({
        ...(statusFilter && { status: statusFilter }),
        ...(riskTier && { risk_tier: riskTier }),
        ...(search && { search }),
        page,
        limit: 20,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.clients.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });

  const clients: Client[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Clients" subtitle="Client account management" />
      <main className="flex-1 p-6">
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <input type="text" placeholder="Search clients..." value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500 w-48" />
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (<option key={s} value={s}>{s}</option>))}
            </select>
            <select value={riskTier} onChange={(e) => { setRiskTier(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All risk tiers</option>
              {RISK_OPTIONS.map((r) => (<option key={r} value={r}>{r}</option>))}
            </select>
            <button onClick={() => refetch()} className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors">
            <Plus className="w-4 h-4" />
            Add Client
          </button>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.04]">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">Code</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Risk Tier</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Industry</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-5 py-4"><div className="h-4 bg-surface-3 rounded-lg w-48" /></td>
                    <td className="px-4 py-4 hidden md:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-16" /></td>
                    <td className="px-4 py-4"><div className="h-5 bg-surface-3 rounded-lg w-16" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-5 bg-surface-3 rounded-lg w-16" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-24" /></td>
                    <td className="px-4 py-4 hidden sm:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-24" /></td>
                    <td className="px-4 py-4" />
                  </tr>
                ))
              ) : clients.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center">
                    <Building2 className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">No clients found</p>
                  </td>
                </tr>
              ) : (
                clients.map((client) => (
                  <tr key={client.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-surface-3 flex items-center justify-center shrink-0">
                          <Building2 className="w-4 h-4 text-gray-400" />
                        </div>
                        <div>
                          <p className="font-medium text-white">{client.name}</p>
                          {client.billing_email && <p className="text-xs text-gray-500">{client.billing_email}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <span className="text-xs text-gray-400 font-mono">{client.code}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize", clientStatusColor(client.status))}>
                        {client.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border capitalize", riskColor(client.risk_tier))}>
                        {client.risk_tier}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className="text-xs text-gray-400">{client.industry ?? "—"}</span>
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-gray-500">{timeAgo(client.created_at)}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <button onClick={() => { if (confirm("Delete this client?")) deleteMutation.mutate(client.id); }}
                        className="p-1.5 text-gray-600 hover:text-red-400 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
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
                  className="text-xs px-3 py-1.5 bg-surface-3 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-white/[0.04] transition-colors">Previous</button>
                <button onClick={() => setPage((p) => Math.min(data.pages, p + 1))} disabled={page === data.pages}
                  className="text-xs px-3 py-1.5 bg-surface-3 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-white/[0.04] transition-colors">Next</button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
