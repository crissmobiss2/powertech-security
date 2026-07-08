"use client";
import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, severityColor, cn } from "@/lib/utils";
import { useVisionSocket, type VisionEvent } from "@/hooks/useVisionSocket";
import { ThreatNotificationPanel } from "@/components/vision/ThreatNotificationPanel";
import { ZoneMap } from "@/components/vision/ZoneMap";
import { ThreatResponsePanel } from "@/components/vision/ThreatResponsePanel";
import type {
  VisionDashboardStats,
  ThreatDetection,
  FaceDetection,
  PersonTrack,
  CameraFeed,
} from "@/types";
import {
  Eye, Camera, Shield, Users, AlertTriangle, ScanFace,
  Crosshair, Activity, CheckCircle2, XCircle,
  Brain, Smile, Frown, Meh, AlertCircle, Zap,
  User, Shirt,
} from "lucide-react";

type TabKey = "overview" | "threats" | "detections" | "tracks";

function StatCard({
  label, value, icon: Icon, color, gradient, sub,
}: {
  label: string; value: number | string; icon: React.ElementType; color: string; gradient?: string; sub?: string;
}) {
  return (
    <div className="glass-card rounded-2xl p-5 group hover:border-white/[0.08] transition-all">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">{label}</p>
          <p className={`text-3xl font-bold mt-1.5 tabular-nums ${color}`}>{value}</p>
          {sub && <p className="text-[11px] text-gray-600 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${gradient ? `bg-gradient-to-br ${gradient} shadow-lg` : "bg-surface-3"}`}>
          <Icon className={`w-5 h-5 ${gradient ? "text-white" : color}`} />
        </div>
      </div>
    </div>
  );
}

function ThreatSeverityDot({ severity }: { severity: string }) {
  const c: Record<string, string> = {
    critical: "bg-red-500 animate-pulse", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-blue-500",
  };
  return <div className={`w-2 h-2 rounded-full ${c[severity] || "bg-gray-500"}`} />;
}

function EmotionIcon({ emotion }: { emotion: string | null }) {
  if (!emotion) return <Meh className="w-4 h-4 text-gray-500" />;
  const map: Record<string, { icon: React.ElementType; color: string }> = {
    happy: { icon: Smile, color: "text-green-400" },
    neutral: { icon: Meh, color: "text-gray-400" },
    angry: { icon: Frown, color: "text-red-400" },
    sad: { icon: Frown, color: "text-blue-400" },
    fear: { icon: AlertCircle, color: "text-yellow-400" },
    surprise: { icon: Zap, color: "text-purple-400" },
    disgust: { icon: Frown, color: "text-orange-400" },
  };
  const m = map[emotion] || { icon: Meh, color: "text-gray-400" };
  return <m.icon className={`w-4 h-4 ${m.color}`} />;
}

function MoodBadge({ mood }: { mood: string | null }) {
  if (!mood) return null;
  const styles: Record<string, string> = {
    positive: "bg-green-950 text-green-400 border-green-800",
    hostile: "bg-red-950 text-red-400 border-red-800",
    distressed: "bg-yellow-950 text-yellow-400 border-yellow-800",
    alert: "bg-purple-950 text-purple-400 border-purple-800",
    neutral: "bg-surface-3 text-gray-400 border-white/[0.06]",
  };
  return (
    <span className={cn("text-[10px] px-1.5 py-0.5 rounded border font-medium capitalize", styles[mood] || styles.neutral)}>
      {mood}
    </span>
  );
}

function ThreatBar({ score }: { score: number | null }) {
  if (score === null || score === undefined) return <span className="text-xs text-gray-600">—</span>;
  const pct = score * 100;
  const color = pct >= 70 ? "bg-red-500" : pct >= 50 ? "bg-orange-500" : pct >= 30 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-surface-3 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400">{pct.toFixed(0)}%</span>
    </div>
  );
}

function statusBadge(s: string) {
  const m: Record<string, string> = {
    active: "bg-red-950 text-red-400 border-red-800",
    acknowledged: "bg-blue-950 text-blue-400 border-blue-800",
    investigating: "bg-purple-950 text-purple-400 border-purple-800",
    resolved: "bg-green-950 text-green-400 border-green-800",
    false_positive: "bg-surface-3 text-gray-400 border-white/[0.06]",
  };
  return m[s] || "bg-surface-3 text-gray-400 border-white/[0.06]";
}

function threatTypeLabel(t: string) {
  return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function VisionPage() {
  const [tab, setTab] = useState<TabKey>("overview");
  const [selectedThreat, setSelectedThreat] = useState<string | null>(null);
  const qc = useQueryClient();

  const onThreat = useCallback((event: VisionEvent) => {
    qc.invalidateQueries({ queryKey: ["vision-threats"] });
    qc.invalidateQueries({ queryKey: ["vision-stats"] });
  }, [qc]);

  const { connected, events, unreadCount, clearEvents, markRead } = useVisionSocket({
    onThreat,
    enabled: true,
  });

  const { data: stats } = useQuery<VisionDashboardStats>({
    queryKey: ["vision-stats"], queryFn: () => api.vision.stats(), refetchInterval: 10000,
  });
  const { data: threatData } = useQuery({
    queryKey: ["vision-threats"], queryFn: () => api.vision.threats.list({ limit: 20 }), refetchInterval: 5000,
  });
  const { data: faceData } = useQuery({
    queryKey: ["vision-faces"], queryFn: () => api.vision.detections.faces({ limit: 30 }), refetchInterval: 5000,
  });
  const { data: trackData } = useQuery({
    queryKey: ["vision-tracks"], queryFn: () => api.vision.tracks.list({ limit: 20 }), refetchInterval: 10000,
  });
  const { data: cameraData } = useQuery({
    queryKey: ["vision-cameras"], queryFn: () => api.vision.cameras.list({ limit: 50 }), refetchInterval: 15000,
  });

  const ackMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.vision.threats.acknowledge(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vision-threats"] });
      qc.invalidateQueries({ queryKey: ["vision-stats"] });
    },
  });

  const threats: ThreatDetection[] = threatData?.data ?? [];
  const faces: FaceDetection[] = faceData?.data ?? [];
  const tracks: PersonTrack[] = trackData?.data ?? [];
  const cameras: CameraFeed[] = cameraData?.data ?? [];
  const s = stats;

  const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
    { key: "overview", label: "Command Center", icon: Eye },
    { key: "threats", label: "Threat Feed", icon: Crosshair },
    { key: "detections", label: "Person Scanner", icon: Brain },
    { key: "tracks", label: "Tracking", icon: Activity },
  ];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="AI Vision Command Center" subtitle="Real-time surveillance & threat detection" />
      <main className="flex-1 p-6 space-y-6">
        {/* Connection Status Bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border transition-all",
              connected
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 glow-green"
                : "bg-surface-2 text-gray-500 border-white/[0.06]"
            )}>
              <div className={cn("w-2 h-2 rounded-full", connected ? "bg-emerald-400 animate-pulse" : "bg-gray-500")} />
              {connected ? "LIVE — Real-time monitoring active" : "Connecting to threat feed..."}
            </div>
            {unreadCount > 0 && (
              <span className="text-xs text-red-400 font-semibold animate-pulse">
                {unreadCount} new alert{unreadCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard label="Active Cameras" value={s?.active_cameras ?? 0} icon={Camera} color="text-emerald-400" gradient="from-emerald-500 to-emerald-700" sub={`${s?.total_cameras ?? 0} total`} />
          <StatCard label="Active Threats" value={s?.active_threats ?? 0} icon={AlertTriangle} color={s?.active_threats ? "text-red-400" : "text-gray-400"} gradient="from-red-500 to-red-700" sub={`${s?.threats_today ?? 0} today`} />
          <StatCard label="Faces Scanned" value={s?.faces_detected_today ?? 0} icon={ScanFace} color="text-brand-400" gradient="from-brand-500 to-brand-700" sub={`${s?.unknown_faces_today ?? 0} unknown`} />
          <StatCard label="Active Tracks" value={s?.active_tracks ?? 0} icon={Activity} color="text-purple-400" gradient="from-purple-500 to-purple-700" />
          <StatCard label="Known Personnel" value={s?.authorized_persons ?? 0} icon={Users} color="text-cyan-400" gradient="from-cyan-500 to-cyan-700" />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-surface-2 border border-white/[0.04] rounded-xl p-1 overflow-x-auto w-fit">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={cn(
                "flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap",
                tab === t.key ? "bg-brand-600 text-white shadow-lg shadow-brand-600/20" : "text-gray-500 hover:text-gray-300"
              )}>
              <t.icon className="w-3.5 h-3.5" /> {t.label}
            </button>
          ))}
        </div>

        {/* ═══ COMMAND CENTER ═══ */}
        {tab === "overview" && (<>
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 glass-card rounded-2xl">
              <div className="px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Camera className="w-4 h-4 text-blue-400" /> Camera Feeds
                </h3>
                <span className="text-xs text-gray-500">{cameras.length} cameras</span>
              </div>
              <div className="p-4">
                {cameras.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-8">No cameras configured</p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {cameras.map((cam) => (
                      <div key={cam.id} className="bg-surface-2 rounded-xl border border-white/[0.06] overflow-hidden">
                        <div className="aspect-video bg-surface-0 flex items-center justify-center relative">
                          <Camera className="w-8 h-8 text-gray-700" />
                          <div className="absolute top-2 left-2 flex items-center gap-1.5">
                            <div className={cn("w-2 h-2 rounded-full",
                              cam.status === "active" ? "bg-green-500 animate-pulse" :
                              cam.status === "processing" ? "bg-blue-500 animate-pulse" :
                              cam.status === "error" ? "bg-red-500" : "bg-gray-600"
                            )} />
                            <span className="text-[10px] font-medium text-gray-400 uppercase">{cam.status}</span>
                          </div>
                          {cam.ai_enabled && (
                            <div className="absolute top-2 right-2">
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 font-medium">AI</span>
                            </div>
                          )}
                        </div>
                        <div className="p-2.5">
                          <p className="text-xs font-medium text-white truncate">{cam.name}</p>
                          <p className="text-[10px] text-gray-500 truncate mt-0.5">{cam.location_description || cam.zone || "—"}</p>
                          <div className="flex items-center gap-2 mt-1.5">
                            {cam.face_recognition_enabled && <ScanFace className="w-3 h-3 text-blue-400" />}
                            {cam.threat_detection_enabled && <Shield className="w-3 h-3 text-red-400" />}
                            {cam.person_tracking_enabled && <Activity className="w-3 h-3 text-purple-400" />}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-6">
              {/* Real-time WebSocket Threat Feed */}
              <ThreatNotificationPanel
                events={events}
                connected={connected}
                unreadCount={unreadCount}
                onClear={clearEvents}
                onMarkRead={markRead}
              />

              {/* Active Threats from DB */}
              <div className="glass-card rounded-2xl">
                <div className="px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400" /> Active Threats
                  </h3>
                  {threats.filter((t) => t.status === "active").length > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-950 text-red-400 font-semibold animate-pulse">
                      {threats.filter((t) => t.status === "active").length} ACTIVE
                    </span>
                  )}
                </div>
                <div className="divide-y divide-white/[0.04] max-h-[280px] overflow-y-auto">
                  {threats.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-6">No threats</p>
                  ) : threats.slice(0, 8).map((threat) => (
                    <div key={threat.id} className="px-4 py-3 hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-start gap-2">
                        <ThreatSeverityDot severity={threat.severity} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-white truncate">{threat.description}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={cn("text-[10px] px-1.5 py-0.5 rounded border", statusBadge(threat.status))}>{threat.status}</span>
                            <span className="text-[10px] text-gray-500">{timeAgo(threat.created_at)}</span>
                          </div>
                          {threat.status === "active" && (
                            <div className="flex gap-1.5 mt-2">
                              <button onClick={() => ackMutation.mutate({ id: threat.id, status: "acknowledged" })}
                                className="text-[10px] px-2 py-0.5 bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors">Acknowledge</button>
                              <button onClick={() => ackMutation.mutate({ id: threat.id, status: "false_positive" })}
                                className="text-[10px] px-2 py-0.5 bg-surface-3 hover:bg-surface-4 text-gray-300 rounded transition-colors">Dismiss</button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Scans */}
              <div className="glass-card rounded-2xl">
                <div className="px-5 py-4 border-b border-white/[0.04]">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" /> Recent Scans
                  </h3>
                </div>
                <div className="divide-y divide-white/[0.04] max-h-[280px] overflow-y-auto">
                  {faces.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-6">No scans yet</p>
                  ) : faces.slice(0, 6).map((f) => (
                    <div key={f.id} className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                          f.is_recognized ? "bg-green-950 border border-green-800" : "bg-yellow-950 border border-yellow-800"
                        )}>
                          <User className={cn("w-4 h-4", f.is_recognized ? "text-green-400" : "text-yellow-400")} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-white truncate">
                            {f.person_name || (f.is_recognized ? "Known" : "Unknown")}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                            {f.estimated_age && <span className="text-[10px] text-gray-400">~{f.estimated_age}y</span>}
                            {f.gender && <span className="text-[10px] text-gray-400 capitalize">{f.gender}</span>}
                            {f.primary_emotion && (
                              <span className="flex items-center gap-0.5">
                                <EmotionIcon emotion={f.primary_emotion} />
                                <span className="text-[10px] text-gray-400 capitalize">{f.primary_emotion}</span>
                              </span>
                            )}
                            <MoodBadge mood={f.mood_category} />
                          </div>
                        </div>
                        <ThreatBar score={f.threat_score} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Zone Map */}
          <ZoneMap cameras={cameras} tracks={tracks} threats={threats} />
        </>)}

        {/* ═══ THREAT FEED ═══ */}
        {tab === "threats" && (
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 glass-card rounded-2xl">
              <div className="px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">All Threat Detections</h3>
                <span className="text-xs text-gray-500">{threats.length} total</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b border-white/[0.04]">
                      <th className="px-5 py-3 font-medium">Severity</th>
                      <th className="px-5 py-3 font-medium">Type</th>
                      <th className="px-5 py-3 font-medium">Description</th>
                      <th className="px-5 py-3 font-medium">Zone</th>
                      <th className="px-5 py-3 font-medium">Confidence</th>
                      <th className="px-5 py-3 font-medium">Status</th>
                      <th className="px-5 py-3 font-medium">Time</th>
                      <th className="px-5 py-3 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {threats.map((t) => (
                      <tr
                        key={t.id}
                        onClick={() => setSelectedThreat(selectedThreat === t.id ? null : t.id)}
                        className={cn(
                          "cursor-pointer transition-colors",
                          selectedThreat === t.id ? "bg-brand-500/10" : "hover:bg-white/[0.02]"
                        )}
                      >
                        <td className="px-5 py-3">
                          <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", severityColor(t.severity))}>{t.severity}</span>
                        </td>
                        <td className="px-5 py-3 text-gray-300">{threatTypeLabel(t.threat_type)}</td>
                        <td className="px-5 py-3 text-gray-300 max-w-xs truncate">{t.description}</td>
                        <td className="px-5 py-3 text-gray-400">{t.zone || "—"}</td>
                        <td className="px-5 py-3"><ThreatBar score={t.confidence} /></td>
                        <td className="px-5 py-3">
                          <span className={cn("text-xs px-1.5 py-0.5 rounded border", statusBadge(t.status))}>{t.status}</span>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-500 whitespace-nowrap">{timeAgo(t.created_at)}</td>
                        <td className="px-5 py-3">
                          {t.status === "active" && (
                            <div className="flex gap-1">
                              <button onClick={(e) => { e.stopPropagation(); ackMutation.mutate({ id: t.id, status: "acknowledged" }); }}
                                className="p-1 text-blue-400 hover:text-blue-300" title="Acknowledge"><CheckCircle2 className="w-4 h-4" /></button>
                              <button onClick={(e) => { e.stopPropagation(); ackMutation.mutate({ id: t.id, status: "false_positive" }); }}
                                className="p-1 text-gray-500 hover:text-gray-300" title="Dismiss"><XCircle className="w-4 h-4" /></button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                    {threats.length === 0 && (
                      <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-500">No threat detections</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Response Panel */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-400" /> Threat Response
              </h3>
              {selectedThreat ? (
                <ThreatResponsePanel
                  threat={threats.find((t) => t.id === selectedThreat)!}
                  onClose={() => setSelectedThreat(null)}
                />
              ) : threats.filter((t) => t.status === "active").length > 0 ? (
                threats.filter((t) => t.status === "active").slice(0, 3).map((t) => (
                  <ThreatResponsePanel key={t.id} threat={t} />
                ))
              ) : (
                <div className="glass-card rounded-2xl py-8 text-center">
                  <Shield className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">Select a threat to view response options</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ═══ PERSON SCANNER ═══ */}
        {tab === "detections" && (
          <div className="space-y-4">
            {faces.length === 0 ? (
              <div className="glass-card rounded-2xl py-12 text-center">
                <Brain className="w-12 h-12 text-gray-700 mx-auto mb-3" />
                <p className="text-gray-500">No person scans yet. AI analysis will appear here as cameras detect people.</p>
              </div>
            ) : faces.map((f) => (
              <div key={f.id} className="glass-card rounded-2xl overflow-hidden hover:border-white/[0.06] transition-colors">
                <div className="p-5">
                  <div className="flex items-start gap-4">
                    <div className={cn(
                      "w-14 h-14 rounded-xl flex items-center justify-center shrink-0",
                      f.is_recognized ? "bg-green-950 border-2 border-green-800" :
                      (f.threat_score ?? 0) >= 0.5 ? "bg-red-950 border-2 border-red-800" :
                      "bg-surface-3 border-2 border-white/[0.06]"
                    )}>
                      <User className={cn("w-7 h-7",
                        f.is_recognized ? "text-green-400" :
                        (f.threat_score ?? 0) >= 0.5 ? "text-red-400" : "text-gray-400"
                      )} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-sm font-semibold text-white">
                          {f.person_name || (f.is_recognized ? "Known Person" : "Unknown Individual")}
                        </h4>
                        {f.is_recognized ? (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-950 text-green-400 border border-green-800 font-medium">IDENTIFIED</span>
                        ) : (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-950 text-yellow-400 border border-yellow-800 font-medium">UNIDENTIFIED</span>
                        )}
                        {!f.is_authorized && f.is_recognized && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-950 text-red-400 border border-red-800 font-medium">UNAUTHORIZED</span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-2 flex-wrap">
                        {f.estimated_age && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-gray-500 uppercase">Age</span>
                            <span className="text-xs text-white font-medium">~{f.estimated_age}</span>
                            {f.age_range && <span className="text-[10px] text-gray-500 capitalize">({f.age_range.replace("_", " ")})</span>}
                          </div>
                        )}
                        {f.gender && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-gray-500 uppercase">Gender</span>
                            <span className="text-xs text-white font-medium capitalize">{f.gender}</span>
                          </div>
                        )}
                        {f.match_confidence && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-gray-500 uppercase">Match</span>
                            <span className="text-xs text-white font-medium">{(f.match_confidence * 100).toFixed(1)}%</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-[10px] text-gray-500 uppercase">Threat</p>
                      <ThreatBar score={f.threat_score} />
                      {f.threat_level && f.threat_level !== "none" && (
                        <span className={cn("text-[10px] font-bold uppercase mt-1 block",
                          f.threat_level === "critical" ? "text-red-400" :
                          f.threat_level === "high" ? "text-orange-400" :
                          f.threat_level === "medium" ? "text-yellow-400" : "text-blue-400"
                        )}>{f.threat_level}</span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 pt-4 border-t border-white/[0.04]">
                    {/* Emotion */}
                    <div className="bg-surface-2/50 rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <EmotionIcon emotion={f.primary_emotion} />
                        <span className="text-[10px] text-gray-500 uppercase font-medium">Emotion / Mood</span>
                      </div>
                      <p className="text-xs text-white font-medium capitalize">{f.primary_emotion || "—"}</p>
                      <MoodBadge mood={f.mood_category} />
                      {f.emotion_scores && (
                        <div className="mt-2 space-y-1">
                          {Object.entries(f.emotion_scores).sort(([, a], [, b]) => b - a).slice(0, 3).map(([em, sc]) => (
                            <div key={em} className="flex items-center gap-1.5">
                              <span className="text-[10px] text-gray-500 w-14 capitalize truncate">{em}</span>
                              <div className="flex-1 h-1 bg-surface-3 rounded-full overflow-hidden">
                                <div className="h-full bg-purple-500 rounded-full" style={{ width: `${sc * 100}%` }} />
                              </div>
                              <span className="text-[10px] text-gray-500 w-8 text-right">{(sc * 100).toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Body Language */}
                    <div className="bg-surface-2/50 rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Activity className="w-3.5 h-3.5 text-cyan-400" />
                        <span className="text-[10px] text-gray-500 uppercase font-medium">Body Language</span>
                      </div>
                      {f.body_language ? (
                        <>
                          <div className="space-y-1.5 text-xs">
                            <div className="flex justify-between"><span className="text-gray-500">Posture</span><span className="text-white capitalize">{f.body_language.posture}</span></div>
                            <div className="flex justify-between"><span className="text-gray-500">Stance</span><span className="text-white capitalize">{f.body_language.stance}</span></div>
                            <div className="flex justify-between"><span className="text-gray-500">Hands</span><span className="text-white capitalize">{f.body_language.hand_position.replace("_", " ")}</span></div>
                          </div>
                          {f.body_language.indicators.length > 0 && (
                            <div className="flex gap-1 flex-wrap mt-2">
                              {f.body_language.indicators.map((ind) => (
                                <span key={ind} className="text-[9px] px-1 py-0.5 bg-red-950 text-red-400 rounded border border-red-900">{ind.replace("_", " ")}</span>
                              ))}
                            </div>
                          )}
                        </>
                      ) : <p className="text-xs text-gray-600">No data</p>}
                    </div>

                    {/* Appearance */}
                    <div className="bg-surface-2/50 rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Shirt className="w-3.5 h-3.5 text-pink-400" />
                        <span className="text-[10px] text-gray-500 uppercase font-medium">Appearance</span>
                      </div>
                      {f.appearance ? (
                        <>
                          <p className="text-xs text-white capitalize">{f.appearance.clothing_description}</p>
                          {f.appearance.dominant_colors?.length > 0 && (
                            <div className="flex gap-1 mt-2">
                              {f.appearance.dominant_colors.map((c) => (
                                <span key={c.color} className="text-[9px] px-1.5 py-0.5 bg-surface-3 text-gray-300 rounded capitalize">{c.color} {c.percentage}%</span>
                              ))}
                            </div>
                          )}
                          <div className="flex gap-2 mt-2 text-[10px] text-gray-500">
                            {f.appearance.has_mask && <span className="text-yellow-400">Mask</span>}
                            {f.appearance.has_hat && <span className="text-blue-400">Hat</span>}
                            {f.appearance.has_bag && <span className="text-gray-400">Bag</span>}
                            {f.appearance.has_glasses && <span className="text-gray-400">Glasses</span>}
                          </div>
                        </>
                      ) : <p className="text-xs text-gray-600">No data</p>}
                    </div>

                    {/* Threat Factors */}
                    <div className="bg-surface-2/50 rounded-xl p-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Shield className="w-3.5 h-3.5 text-red-400" />
                        <span className="text-[10px] text-gray-500 uppercase font-medium">Threat Factors</span>
                      </div>
                      {f.threat_factors && f.threat_factors.length > 0 ? (
                        <div className="space-y-1">
                          {f.threat_factors.map((factor) => (
                            <div key={factor} className="flex items-center gap-1.5">
                              <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                              <span className="text-xs text-red-300">{factor.replace(/_/g, " ").replace(":", ": ")}</span>
                            </div>
                          ))}
                        </div>
                      ) : <p className="text-xs text-green-400">No threat indicators</p>}
                    </div>
                  </div>
                </div>
                <div className="px-5 py-2 bg-surface-2/30 border-t border-white/[0.04] flex items-center justify-between">
                  <span className="text-[10px] text-gray-500">Scanned {timeAgo(f.frame_timestamp)}</span>
                  <span className="text-[10px] text-gray-600 font-mono">{f.id.slice(0, 8)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ═══ TRACKING ═══ */}
        {tab === "tracks" && (
          <div className="glass-card rounded-2xl">
            <div className="px-5 py-4 border-b border-white/[0.04]">
              <h3 className="text-sm font-semibold text-white">Active Person Tracks</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-white/[0.04]">
                    <th className="px-5 py-3 font-medium">Track</th>
                    <th className="px-5 py-3 font-medium">Person</th>
                    <th className="px-5 py-3 font-medium">ID</th>
                    <th className="px-5 py-3 font-medium">Dwell</th>
                    <th className="px-5 py-3 font-medium">Threat</th>
                    <th className="px-5 py-3 font-medium">Flags</th>
                    <th className="px-5 py-3 font-medium">First Seen</th>
                    <th className="px-5 py-3 font-medium">Last Seen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {tracks.map((t) => {
                    const mins = Math.floor(t.dwell_time_seconds / 60);
                    const secs = t.dwell_time_seconds % 60;
                    const tlc: Record<string, string> = {
                      none: "text-gray-400", low: "text-blue-400", medium: "text-yellow-400",
                      high: "text-orange-400", critical: "text-red-400",
                    };
                    return (
                      <tr key={t.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-3 font-mono text-xs text-gray-400">{t.track_id}</td>
                        <td className="px-5 py-3 text-gray-300">{t.person_label || "Unknown"}</td>
                        <td className="px-5 py-3">
                          {t.is_identified ? <CheckCircle2 className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-gray-500" />}
                        </td>
                        <td className="px-5 py-3 text-gray-300">{mins > 0 ? `${mins}m ${secs}s` : `${secs}s`}</td>
                        <td className="px-5 py-3">
                          <span className={cn("text-xs font-medium uppercase", tlc[t.threat_level] || "text-gray-400")}>{t.threat_level}</span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex gap-1 flex-wrap">
                            {t.flags?.map((fl) => (
                              <span key={fl} className="text-[10px] px-1.5 py-0.5 bg-surface-3 text-gray-400 rounded border border-white/[0.06]">{fl}</span>
                            )) ?? <span className="text-xs text-gray-600">—</span>}
                          </div>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-500 whitespace-nowrap">{timeAgo(t.first_seen_at)}</td>
                        <td className="px-5 py-3 text-xs text-gray-500 whitespace-nowrap">{timeAgo(t.last_seen_at)}</td>
                      </tr>
                    );
                  })}
                  {tracks.length === 0 && (
                    <tr><td colSpan={8} className="px-5 py-8 text-center text-gray-500">No active tracks</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
