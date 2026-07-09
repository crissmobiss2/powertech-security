"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, cn } from "@/lib/utils";
import type { CameraFeed, Client, PaginatedResponse } from "@/types";
import {
  Camera, Wifi, WifiOff, ScanFace, Shield, Activity,
  Search, Trash2, ChevronLeft, ChevronRight,
  AlertCircle, Zap, Plus, X, Loader2,
} from "lucide-react";

function cameraStatusColor(status: string) {
  const map: Record<string, string> = {
    active: "bg-green-500",
    processing: "bg-blue-500 animate-pulse",
    inactive: "bg-gray-600",
    error: "bg-red-500",
  };
  return map[status] || "bg-gray-600";
}

function AddCameraModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const { data: clientsData } = useQuery<PaginatedResponse<Client>>({
    queryKey: ["clients-all"],
    queryFn: () => api.clients.list({ limit: 100 }),
  });
  const clients = clientsData?.data ?? [];

  const [form, setForm] = useState({
    client_id: "",
    name: "",
    stream_url: "",
    stream_type: "rtsp",
    location_description: "",
    floor: "",
    zone: "",
    ai_enabled: true,
    face_recognition_enabled: true,
    threat_detection_enabled: true,
    person_tracking_enabled: true,
    processing_fps: "5",
    detection_confidence_threshold: "0.7",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    if (clients.length > 0 && !form.client_id) {
      setForm((f) => ({ ...f, client_id: clients[0].id }));
    }
  }, [clients]); // eslint-disable-line react-hooks/exhaustive-deps

  const createMutation = useMutation({
    mutationFn: (data: typeof form) =>
      api.vision.cameras.create({
        ...data,
        client_id: data.client_id || clients[0]?.id,
        processing_fps: parseInt(data.processing_fps, 10),
        detection_confidence_threshold: parseFloat(data.detection_confidence_threshold),
      }),
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to create camera");
    },
  });

  function set(field: string, value: string | boolean) {
    setForm((f) => ({ ...f, [field]: value }));
    setError("");
  }

  const Toggle = ({ field, label }: { field: string; label: string }) => (
    <label className="flex items-center justify-between cursor-pointer">
      <span className="text-xs text-gray-400">{label}</span>
      <button
        type="button"
        onClick={() => set(field, !(form as Record<string, unknown>)[field])}
        className={cn(
          "w-9 h-5 rounded-full transition-colors relative",
          (form as Record<string, unknown>)[field] ? "bg-brand-500" : "bg-surface-3"
        )}
      >
        <span className={cn(
          "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform",
          (form as Record<string, unknown>)[field] ? "translate-x-4" : "translate-x-0.5"
        )} />
      </button>
    </label>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass-card rounded-2xl w-full max-w-lg mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] sticky top-0 bg-surface-1 z-10">
          <h2 className="text-base font-semibold text-white">Add camera feed</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
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
            <label className="block text-xs text-gray-400 mb-1.5">Camera name *</label>
            <input value={form.name} onChange={(e) => set("name", e.target.value)}
              className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
              placeholder="Lobby Entrance CAM-01" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Stream URL *</label>
            <input value={form.stream_url} onChange={(e) => set("stream_url", e.target.value)}
              className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500 font-mono"
              placeholder="rtsp://192.168.1.100:554/stream1" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Protocol</label>
              <select value={form.stream_type} onChange={(e) => set("stream_type", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
                <option value="rtsp">RTSP</option>
                <option value="http">HTTP</option>
                <option value="hls">HLS</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Floor</label>
              <input value={form.floor} onChange={(e) => set("floor", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
                placeholder="G/F" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Zone</label>
              <input value={form.zone} onChange={(e) => set("zone", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
                placeholder="Lobby" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Location description</label>
            <input value={form.location_description} onChange={(e) => set("location_description", e.target.value)}
              className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
              placeholder="Main entrance, facing south" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Processing FPS (1–30)</label>
              <input type="number" min="1" max="30" value={form.processing_fps} onChange={(e) => set("processing_fps", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Confidence threshold</label>
              <input type="number" min="0.1" max="1.0" step="0.05" value={form.detection_confidence_threshold}
                onChange={(e) => set("detection_confidence_threshold", e.target.value)}
                className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
            </div>
          </div>
          <div className="space-y-3 pt-2 border-t border-white/[0.06]">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">AI capabilities</p>
            <Toggle field="ai_enabled" label="AI Processing" />
            <Toggle field="face_recognition_enabled" label="Face Recognition" />
            <Toggle field="threat_detection_enabled" label="Threat Detection" />
            <Toggle field="person_tracking_enabled" label="Person Tracking" />
          </div>
          {error && <p className="text-xs text-red-400 bg-red-950/50 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06] sticky bottom-0 bg-surface-1">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button
            onClick={() => createMutation.mutate(form)}
            disabled={createMutation.isPending || !form.name || !form.stream_url}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Add camera
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CamerasPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const qc = useQueryClient();

  const params: Record<string, string | number> = { page, limit: 20 };
  if (statusFilter) params.status = statusFilter;

  const { data, isLoading } = useQuery<PaginatedResponse<CameraFeed>>({
    queryKey: ["vision-cameras-page", params],
    queryFn: () => api.vision.cameras.list(params),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.vision.cameras.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vision-cameras-page"] }),
  });

  const toggleAI = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.vision.cameras.update(id, { ai_enabled: enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vision-cameras-page"] }),
  });

  let cameras = data?.data ?? [];
  if (search) {
    const q = search.toLowerCase();
    cameras = cameras.filter(
      (c) => c.name.toLowerCase().includes(q) || c.location_description?.toLowerCase().includes(q)
    );
  }
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const activeCount = cameras.filter((c) => c.status === "active" || c.status === "processing").length;
  const errorCount = cameras.filter((c) => c.status === "error").length;

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      {showAdd && (
        <AddCameraModal
          onClose={() => setShowAdd(false)}
          onSuccess={() => qc.invalidateQueries({ queryKey: ["vision-cameras-page"] })}
        />
      )}
      <Header title="Camera Management" subtitle="CCTV feed management" />
      <main className="flex-1 p-6 space-y-6">
        {/* Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="glass-card rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-surface-3"><Camera className="w-4 h-4 text-blue-400" /></div>
            <div>
              <p className="text-xs text-gray-500">Total</p>
              <p className="text-lg font-bold text-white">{total}</p>
            </div>
          </div>
          <div className="glass-card rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-surface-3"><Wifi className="w-4 h-4 text-green-400" /></div>
            <div>
              <p className="text-xs text-gray-500">Online</p>
              <p className="text-lg font-bold text-green-400">{activeCount}</p>
            </div>
          </div>
          <div className="glass-card rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-surface-3"><AlertCircle className="w-4 h-4 text-red-400" /></div>
            <div>
              <p className="text-xs text-gray-500">Errors</p>
              <p className="text-lg font-bold text-red-400">{errorCount}</p>
            </div>
          </div>
          <div className="glass-card rounded-2xl p-4 flex items-center gap-3">
            <div className="p-2 rounded-lg bg-surface-3"><Zap className="w-4 h-4 text-purple-400" /></div>
            <div>
              <p className="text-xs text-gray-500">AI Enabled</p>
              <p className="text-lg font-bold text-purple-400">{cameras.filter((c) => c.ai_enabled).length}</p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search cameras..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-surface-1 border border-white/[0.04] rounded-lg text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-surface-1 border border-white/[0.04] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="processing">Processing</option>
            <option value="inactive">Inactive</option>
            <option value="error">Error</option>
          </select>
          <button
            onClick={() => setShowAdd(true)}
            className="ml-auto flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all"
          >
            <Plus className="w-4 h-4" />
            Add Camera
          </button>
        </div>

        {/* Camera Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {cameras.map((cam) => (
            <div key={cam.id} className="glass-card rounded-2xl overflow-hidden hover:border-white/[0.06] transition-colors">
              {/* Preview placeholder */}
              <div className="aspect-video bg-surface-3 relative flex items-center justify-center">
                <Camera className="w-12 h-12 text-gray-700" />
                <div className="absolute top-3 left-3 flex items-center gap-1.5">
                  <div className={cn("w-2.5 h-2.5 rounded-full", cameraStatusColor(cam.status))} />
                  <span className="text-xs font-medium text-gray-300 uppercase">{cam.status}</span>
                </div>
                {cam.ai_enabled && (
                  <div className="absolute top-3 right-3">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-blue-900/70 text-blue-300 font-semibold">AI ON</span>
                  </div>
                )}
                {cam.error_message && (
                  <div className="absolute bottom-0 inset-x-0 bg-red-950/90 px-3 py-1.5">
                    <p className="text-[10px] text-red-400 truncate">{cam.error_message}</p>
                  </div>
                )}
              </div>

              <div className="p-4 space-y-3">
                <div>
                  <h3 className="text-sm font-semibold text-white">{cam.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{cam.location_description || cam.zone || cam.stream_type.toUpperCase()}</p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1" title="Face Recognition">
                    <ScanFace className={cn("w-3.5 h-3.5", cam.face_recognition_enabled ? "text-blue-400" : "text-gray-700")} />
                    <span className={cn("text-[10px]", cam.face_recognition_enabled ? "text-blue-400" : "text-gray-700")}>Face</span>
                  </div>
                  <div className="flex items-center gap-1" title="Threat Detection">
                    <Shield className={cn("w-3.5 h-3.5", cam.threat_detection_enabled ? "text-red-400" : "text-gray-700")} />
                    <span className={cn("text-[10px]", cam.threat_detection_enabled ? "text-red-400" : "text-gray-700")}>Threat</span>
                  </div>
                  <div className="flex items-center gap-1" title="Person Tracking">
                    <Activity className={cn("w-3.5 h-3.5", cam.person_tracking_enabled ? "text-purple-400" : "text-gray-700")} />
                    <span className={cn("text-[10px]", cam.person_tracking_enabled ? "text-purple-400" : "text-gray-700")}>Track</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-gray-500 pt-2 border-t border-white/[0.04]">
                  <span>{cam.processing_fps} FPS · {(cam.detection_confidence_threshold * 100).toFixed(0)}% threshold</span>
                  <span>{cam.last_frame_at ? `Last frame ${timeAgo(cam.last_frame_at)}` : "No frames yet"}</span>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => toggleAI.mutate({ id: cam.id, enabled: !cam.ai_enabled })}
                    className={cn(
                      "flex-1 text-xs px-3 py-1.5 rounded-lg font-medium transition-colors",
                      cam.ai_enabled
                        ? "bg-surface-3 text-gray-300 hover:bg-white/[0.04] border border-white/[0.06]"
                        : "bg-gradient-to-r from-brand-600 to-brand-500 text-white hover:from-brand-500 hover:to-brand-400"
                    )}
                  >
                    {cam.ai_enabled ? "Disable AI" : "Enable AI"}
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete camera "${cam.name}"?`)) deleteMutation.mutate(cam.id);
                    }}
                    className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                    title="Delete camera"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {cameras.length === 0 && !isLoading && (
            <div className="col-span-full text-center py-12 text-gray-500 text-sm">
              No cameras found
            </div>
          )}
        </div>

        {pages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">{total} camera{total !== 1 ? "s" : ""}</p>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                className="p-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs text-gray-400">{page} / {pages}</span>
              <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}
                className="p-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
