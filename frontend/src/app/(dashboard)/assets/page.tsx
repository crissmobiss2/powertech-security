"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, assetStatusColor, cn } from "@/lib/utils";
import type { Asset, AssetType, AssetStatus, Client, PaginatedResponse } from "@/types";
import { Cpu, Filter, RefreshCw, Plus, X, Loader2 } from "lucide-react";

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

function AddAssetModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const { data: clientsData } = useQuery<PaginatedResponse<Client>>({
    queryKey: ["clients-all"],
    queryFn: () => api.clients.list({ limit: 100 }),
  });
  const clients = clientsData?.data ?? [];

  const [form, setForm] = useState({
    client_id: "",
    name: "",
    type: "camera" as AssetType,
    code: "",
    ip_address: "",
    location_detail: "",
    floor: "",
    zone: "",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    if (clients.length > 0 && !form.client_id) {
      setForm((f) => ({ ...f, client_id: clients[0].id }));
    }
  }, [clients]); // eslint-disable-line react-hooks/exhaustive-deps

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => {
      const payload: Record<string, string> = {
        client_id: data.client_id || clients[0]?.id,
        name: data.name,
        type: data.type,
      };
      if (data.code) payload.code = data.code;
      if (data.ip_address) payload.ip_address = data.ip_address;
      if (data.location_detail) payload.location_detail = data.location_detail;
      if (data.floor) payload.floor = data.floor;
      if (data.zone) payload.zone = data.zone;
      return api.assets.create(payload);
    },
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to create asset");
    },
  });

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setError("");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass-card rounded-2xl w-full max-w-lg mx-4 shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] shrink-0">
          <h2 className="text-base font-semibold text-white">Register asset</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4 overflow-y-auto">
          {clients.length > 1 && (
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Client</label>
              <select value={form.client_id} onChange={(e) => set("client_id", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Asset Name *</label>
            <input value={form.name} onChange={(e) => set("name", e.target.value)}
              className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
              placeholder="Gate 1 Camera North" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Type *</label>
              <select value={form.type} onChange={(e) => set("type", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
                {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Asset Code</label>
              <input value={form.code} onChange={(e) => set("code", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
                placeholder="CAM-001" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">IP Address</label>
            <input value={form.ip_address} onChange={(e) => set("ip_address", e.target.value)}
              className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500 font-mono"
              placeholder="192.168.1.100" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Floor / Level</label>
              <input value={form.floor} onChange={(e) => set("floor", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
                placeholder="Ground Floor" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Zone</label>
              <input value={form.zone} onChange={(e) => set("zone", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
                placeholder="Zone A" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Location Detail</label>
            <input value={form.location_detail} onChange={(e) => set("location_detail", e.target.value)}
              className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
              placeholder="Main entrance lobby, facing north" />
          </div>
          {error && <p className="text-xs text-red-400 bg-red-950/50 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06] shrink-0">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button
            onClick={() => createMutation.mutate(form)}
            disabled={createMutation.isPending || !form.name}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Register asset
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AssetsPage() {
  const qc = useQueryClient();
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);

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

  void statusMutation;

  const assets: Asset[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      {showAdd && (
        <AddAssetModal
          onClose={() => setShowAdd(false)}
          onSuccess={() => qc.invalidateQueries({ queryKey: ["assets"] })}
        />
      )}
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
              {TYPE_OPTIONS.map((t) => (<option key={t} value={t}>{t.replace(/_/g, " ")}</option>))}
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
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors"
          >
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
                    <Cpu className="w-8 h-8 text-gray-700 mx-auto mb-3" />
                    <p className="text-gray-400 text-sm font-medium">No assets registered</p>
                    <p className="text-gray-600 text-xs mt-1">Register cameras, access panels, and other security hardware</p>
                    <button
                      onClick={() => setShowAdd(true)}
                      className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 hover:bg-surface-3 border border-white/[0.06] text-gray-300 text-xs rounded-lg transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Register first asset
                    </button>
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
                        {asset.type.replace(/_/g, " ")}
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
