"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, severityColor, statusColor, cn } from "@/lib/utils";
import type { Ticket } from "@/types";
import { Ticket as TicketIcon, Filter, RefreshCw, Plus, MapPin, Clock } from "lucide-react";

const STATUS_OPTIONS = ["", "open", "assigned", "in_progress", "on_hold", "resolved", "closed", "cancelled"];
const PRIORITY_OPTIONS = ["", "critical", "high", "medium", "low"];
const TYPE_OPTIONS = ["", "installation", "maintenance", "support", "investigation", "emergency", "inspection"];

export default function TicketsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["tickets", { status, priority, type, page }],
    queryFn: () =>
      api.tickets.list({
        ...(status && { status }),
        ...(priority && { priority }),
        ...(type && { type }),
        page,
        limit: 20,
      }),
  });

  const checkinMutation = useMutation({
    mutationFn: (id: string) => api.tickets.checkin(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tickets"] }),
  });

  const tickets: Ticket[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Tickets & Work Orders" subtitle="Service dispatch & field operations" />
      <main className="flex-1 p-6">
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (<option key={s} value={s}>{s.replace("_", " ")}</option>))}
            </select>
            <select value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All priorities</option>
              {PRIORITY_OPTIONS.filter(Boolean).map((p) => (<option key={p} value={p}>{p}</option>))}
            </select>
            <select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All types</option>
              {TYPE_OPTIONS.filter(Boolean).map((t) => (<option key={t} value={t}>{t}</option>))}
            </select>
            <button onClick={() => refetch()} className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors">
            <Plus className="w-4 h-4" />
            New Ticket
          </button>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.04]">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Ticket</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">Priority</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Type</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">SLA Due</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-5 py-4"><div className="h-4 bg-surface-3 rounded-lg w-56" /></td>
                    <td className="px-4 py-4 hidden md:table-cell"><div className="h-5 bg-surface-3 rounded-lg w-16" /></td>
                    <td className="px-4 py-4"><div className="h-5 bg-surface-3 rounded-lg w-20" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-20" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-24" /></td>
                    <td className="px-4 py-4 hidden sm:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-24" /></td>
                    <td className="px-4 py-4" />
                  </tr>
                ))
              ) : tickets.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center">
                    <TicketIcon className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">No tickets found</p>
                  </td>
                </tr>
              ) : (
                tickets.map((ticket) => (
                  <tr key={ticket.id} onClick={() => router.push(`/tickets/${ticket.id}`)}
                    className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-white line-clamp-1">{ticket.title}</p>
                      {ticket.description && <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{ticket.description}</p>}
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border", severityColor(ticket.priority))}>
                        {ticket.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", statusColor(ticket.status))}>
                        {ticket.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className="text-xs text-gray-400 capitalize">{ticket.type}</span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className={cn("text-xs", ticket.sla_due_at && new Date(ticket.sla_due_at) < new Date() ? "text-red-400 font-medium" : "text-gray-500")}>
                        {ticket.sla_due_at ? timeAgo(ticket.sla_due_at) : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-gray-500">{timeAgo(ticket.created_at)}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      {(ticket.status === "assigned" || ticket.status === "open") && !ticket.checkin_at && (
                        <button onClick={(e) => { e.stopPropagation(); checkinMutation.mutate(ticket.id); }} disabled={checkinMutation.isPending}
                          className="text-xs px-2.5 py-1 bg-surface-3 hover:bg-green-900 text-gray-300 hover:text-green-300 rounded-lg border border-white/[0.06] hover:border-green-700 transition-colors opacity-0 group-hover:opacity-100">
                          <MapPin className="w-3 h-3 inline mr-1" />Check in
                        </button>
                      )}
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
