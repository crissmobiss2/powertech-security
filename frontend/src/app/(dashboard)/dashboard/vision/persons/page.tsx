"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import type { AuthorizedPerson, PaginatedResponse } from "@/types";
import {
  Users, Plus, Search, ScanFace, Shield, UserCheck,
  UserX, Trash2, Edit3, ChevronLeft, ChevronRight, Eye,
} from "lucide-react";

function personTypeBadge(type: string) {
  const map: Record<string, string> = {
    employee: "bg-blue-950 text-blue-400 border-blue-800",
    contractor: "bg-purple-950 text-purple-400 border-purple-800",
    visitor: "bg-surface-3 text-gray-300 border-white/[0.06]",
    vip: "bg-amber-950 text-amber-400 border-amber-800",
    banned: "bg-red-950 text-red-400 border-red-800",
  };
  return map[type] || "bg-surface-3 text-gray-400 border-white/[0.06]";
}

function accessBadge(level: string) {
  const map: Record<string, string> = {
    restricted: "text-red-400",
    standard: "text-gray-400",
    elevated: "text-yellow-400",
    full: "text-green-400",
  };
  return map[level] || "text-gray-400";
}

export default function PersonsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const qc = useQueryClient();

  const params: Record<string, string | number> = { page, limit: 20 };
  if (search) params.search = search;
  if (typeFilter) params.person_type = typeFilter;
  if (statusFilter) params.status = statusFilter;

  const { data, isLoading } = useQuery<PaginatedResponse<AuthorizedPerson>>({
    queryKey: ["vision-persons", params],
    queryFn: () => api.vision.persons.list(params),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.vision.persons.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vision-persons"] }),
  });

  const persons = data?.data ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Authorized Persons" subtitle="Authorized personnel registry" />
      <main className="flex-1 p-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {["employee", "contractor", "visitor", "banned"].map((type) => {
            const count = persons.filter((p) => p.person_type === type).length;
            const icons: Record<string, React.ElementType> = {
              employee: UserCheck, contractor: Users, visitor: Eye, banned: UserX,
            };
            const Icon = icons[type] || Users;
            return (
              <div key={type} className="glass-card rounded-2xl p-4 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3">
                  <Icon className={cn("w-4 h-4", type === "banned" ? "text-red-400" : "text-blue-400")} />
                </div>
                <div>
                  <p className="text-xs text-gray-500 capitalize">{type === "banned" ? "Banned" : `${type}s`}</p>
                  <p className="text-lg font-bold text-white">{count}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 bg-surface-1 border border-white/[0.04] rounded-lg text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="bg-surface-1 border border-white/[0.04] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Types</option>
            <option value="employee">Employee</option>
            <option value="contractor">Contractor</option>
            <option value="visitor">Visitor</option>
            <option value="vip">VIP</option>
            <option value="banned">Banned</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-surface-1 border border-white/[0.04] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="banned">Banned</option>
            <option value="expired">Expired</option>
          </select>
        </div>

        {/* Table */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-white/[0.04]">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Employee ID</th>
                  <th className="px-5 py-3 font-medium">Department</th>
                  <th className="px-5 py-3 font-medium">Access</th>
                  <th className="px-5 py-3 font-medium">Face Data</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Added</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {persons.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-surface-3 flex items-center justify-center shrink-0">
                          <span className="text-xs font-bold text-gray-400">
                            {p.first_name?.[0] ?? "?"}{p.last_name?.[0] ?? ""}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{p.first_name} {p.last_name}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium capitalize", personTypeBadge(p.person_type))}>
                        {p.person_type}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-400 font-mono text-xs">{p.employee_id || "—"}</td>
                    <td className="px-5 py-3 text-gray-400">{p.department || "—"}</td>
                    <td className="px-5 py-3">
                      <span className={cn("text-xs font-medium uppercase", accessBadge(p.access_level))}>
                        {p.access_level}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1.5">
                        <ScanFace className={cn("w-4 h-4", p.face_encoding_count > 0 ? "text-green-400" : "text-gray-600")} />
                        <span className="text-xs text-gray-400">{p.face_encoding_count} encoding{p.face_encoding_count !== 1 ? "s" : ""}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={cn(
                        "text-xs px-2 py-0.5 rounded-full border font-medium",
                        p.status === "active" ? "bg-green-950 text-green-400 border-green-800" :
                        p.status === "banned" ? "bg-red-950 text-red-400 border-red-800" :
                        "bg-surface-3 text-gray-400 border-white/[0.06]"
                      )}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-xs text-gray-500 whitespace-nowrap">{formatDate(p.created_at)}</td>
                    <td className="px-5 py-3">
                      <div className="flex gap-1">
                        <button
                          onClick={() => {
                            if (confirm(`Delete ${p.first_name} ${p.last_name}? This removes all face data.`)) {
                              deleteMutation.mutate(p.id);
                            }
                          }}
                          className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {persons.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={9} className="px-5 py-8 text-center text-gray-500 text-sm">
                      No authorized persons found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.04]">
              <p className="text-xs text-gray-500">{total} person{total !== 1 ? "s" : ""}</p>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="p-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs text-gray-400">
                  {page} / {pages}
                </span>
                <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}
                  className="p-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
