"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, assetStatusColor, cn } from "@/lib/utils";
import type { Asset, AssetType, AssetStatus } from "@/types";
import { Cpu, Filter, RefreshCw, Plus, Wifi, WifiOff, Circle } from "lucide-react";

const TYPE_OPTIONS: AssetType[] = [
  "camera", "nvr", "dvr", "access_panel", "door_controller", "biometric",
  "server", "workstation", "laptop", "network_switch", "router", "firewall",
  "ups", "sensor", "iot_device", "other",
];

const STATUS_OPTIONS: AssetStatus[] = [
  "online", "offline", "degraded", "maintenance", "decommissioned", "unknown",
];

function StatusDot({ status }: { status: AssetStatus }) {
  const colorMap: Record<string, string> = {
    online: "bg-green-500",
    offline: "bg-red-500",
    degraded: "bg-yellow-500",
    maintenance: "bg-blue-500",
    decommissioned: "bg-gray-600",
    unknown: "bg-gray-500",
  };
  return <span className={cn("w-2 h-2 rounded-full shrink-0", colorMap[status] ?? "bg-gray-500")} />;
}

export default function AssetsPage() {
  const qc = useQueryClient();
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["assets", { type, status, search, page }],
    queryFn: () =>
      api.assets.list({
        ...(type && { type }),
        ...(status && { status }),
        ...(search && { search }),
        page,
        limit: 20,
      }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: string }) =>
      api.assets.updateStatus(id, newStatus),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });

  const assets: Asset[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Asset Registry" subtitle="Infrastructure & device management" />
      <main className="flex-1 p-6">
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <input
              type="text" placeholder="Search assets..." value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500 w-48"
            />
            <select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All types</option>
              {TYPE_OPTIONS.map((t) => (<option key={t} value={t}>{t.replace("_", " ")}</option>))}
            </select>
            <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((s) => (<option key={s} value={s}>{s}</option>))}
            </select>
            <button onClick={() => refetch()} className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors">
            <Plus className="w-4 h-4" />
            Add Asset
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {(["online", "offline", "degraded", "maintenance"] as const).map((s) => {
            const count = assets.filter((a) => a.status === s).length;
            return (
              <div key={s} className="bg-surface-1 border border-white/[0.04] rounded-xl px-4 py-3 flex items-center gap-3">
                <StatusDot status={s} />
                <div>
                  <p className="text-lg font-bold text-white font-variant-numeric tabular-nums">{data ? (status === s ? data.total : count) : "—"}</p>
                  <p className="text-xs text-gray-500 capitalize">{s}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="glass-card rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.04]">
                <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">Type</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">IP Address</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Location</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">Last Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-5 py-4"><div className="h-4 bg-surface-3 rounded-lg w-48" /></td>
                    <td className="px-4 py-4 hidden md:table-cell"><div className="h-5 bg-surface-3 rounded-lg w-20" /></td>
                    <td className="px-4 py-4"><div className="h-5 bg-surface-3 rounded-lg w-16" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-28" /></td>
                    <td className="px-4 py-4 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-24" /></td>
                    <td className="px-4 py-4 hidden sm:table-cell"><div className="h-4 bg-surface-3 rounded-lg w-24" /></td>
                  </tr>
                ))
              ) : assets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center">
                    <Cpu className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">No assets found</p>
                  </td>
                </tr>
              ) : (
                assets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <StatusDot status={asset.status} />
                        <div>
                          <p className="font-medium text-white">{asset.name}</p>
                          {asset.code && <p className="text-xs text-gray-500 font-mono">{asset.code}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <span className="text-xs px-2 py-0.5 bg-surface-3 text-gray-400 rounded capitalize">
                        {asset.type.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={cn("text-xs font-medium capitalize", assetStatusColor(asset.status))}>
                        {asset.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className="text-xs text-gray-400 font-mono">{asset.ip_address ?? "—"}</span>
                    </td>
                    <td className="px-4 py-3.5 hidden lg:table-cell">
                      <span className="text-xs text-gray-500">{asset.location_detail ?? asset.floor ?? "—"}</span>
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-gray-500">{timeAgo(asset.last_seen_at)}</span>
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
