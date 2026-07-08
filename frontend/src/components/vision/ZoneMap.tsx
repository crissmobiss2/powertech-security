"use client";
import { cn } from "@/lib/utils";
import type { CameraFeed, PersonTrack, ThreatDetection } from "@/types";
import { Camera, User, AlertTriangle, Shield, MapPin } from "lucide-react";

interface Props {
  cameras: CameraFeed[];
  tracks: PersonTrack[];
  threats: ThreatDetection[];
}

const ZONES = [
  { id: "main-entrance", name: "Main Entrance", x: 10, y: 10, w: 25, h: 20, type: "entry" },
  { id: "lobby", name: "Lobby", x: 10, y: 32, w: 25, h: 25, type: "common" },
  { id: "corridor-a", name: "Corridor A", x: 37, y: 10, w: 8, h: 47, type: "transit" },
  { id: "office-a", name: "Office Block A", x: 47, y: 10, w: 22, h: 22, type: "restricted" },
  { id: "office-b", name: "Office Block B", x: 47, y: 35, w: 22, h: 22, type: "restricted" },
  { id: "server-room", name: "Server Room", x: 71, y: 10, w: 20, h: 15, type: "critical" },
  { id: "parking", name: "Parking Area", x: 71, y: 28, w: 20, h: 15, type: "outdoor" },
  { id: "emergency-exit", name: "Emergency Exit", x: 71, y: 46, w: 20, h: 11, type: "exit" },
  { id: "break-room", name: "Break Room", x: 10, y: 60, w: 22, h: 15, type: "common" },
  { id: "conference", name: "Conference Room", x: 35, y: 60, w: 20, h: 15, type: "restricted" },
  { id: "loading-dock", name: "Loading Dock", x: 57, y: 60, w: 34, h: 15, type: "outdoor" },
  { id: "perimeter-n", name: "North Perimeter", x: 10, y: 2, w: 81, h: 6, type: "perimeter" },
  { id: "perimeter-s", name: "South Perimeter", x: 10, y: 77, w: 81, h: 6, type: "perimeter" },
];

const zoneColors: Record<string, { bg: string; border: string; text: string }> = {
  entry: { bg: "rgba(59, 130, 246, 0.1)", border: "rgba(59, 130, 246, 0.4)", text: "text-blue-400" },
  common: { bg: "rgba(34, 197, 94, 0.08)", border: "rgba(34, 197, 94, 0.3)", text: "text-green-400" },
  transit: { bg: "rgba(156, 163, 175, 0.06)", border: "rgba(156, 163, 175, 0.2)", text: "text-gray-500" },
  restricted: { bg: "rgba(234, 179, 8, 0.08)", border: "rgba(234, 179, 8, 0.3)", text: "text-yellow-400" },
  critical: { bg: "rgba(239, 68, 68, 0.1)", border: "rgba(239, 68, 68, 0.4)", text: "text-red-400" },
  outdoor: { bg: "rgba(139, 92, 246, 0.06)", border: "rgba(139, 92, 246, 0.2)", text: "text-purple-400" },
  exit: { bg: "rgba(249, 115, 22, 0.08)", border: "rgba(249, 115, 22, 0.3)", text: "text-orange-400" },
  perimeter: { bg: "rgba(100, 116, 139, 0.04)", border: "rgba(100, 116, 139, 0.15)", text: "text-slate-500" },
};

export function ZoneMap({ cameras, tracks, threats }: Props) {
  const activeThreats = threats.filter((t) => t.status === "active");

  function getZoneThreats(zoneId: string) {
    const zoneName = ZONES.find((z) => z.id === zoneId)?.name;
    return activeThreats.filter((t) => {
      const tz = typeof t.zone === "string" ? t.zone.toLowerCase() : "";
      return tz === zoneName?.toLowerCase() || t.zone === zoneId;
    });
  }

  function getZoneCameras(zoneId: string) {
    const zoneName = ZONES.find((z) => z.id === zoneId)?.name;
    return cameras.filter((c) => {
      const cz = typeof c.zone === "string" ? c.zone.toLowerCase() : "";
      return cz === zoneName?.toLowerCase() || c.zone === zoneId;
    });
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.04] flex items-center justify-between">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <MapPin className="w-4 h-4 text-cyan-400" /> Zone Map
        </h3>
        <div className="flex items-center gap-4 text-[10px] text-gray-500">
          <span className="flex items-center gap-1"><Camera className="w-3 h-3 text-blue-400" /> {cameras.filter((c) => c.status === "active").length} cams</span>
          <span className="flex items-center gap-1"><User className="w-3 h-3 text-green-400" /> {tracks.length} tracked</span>
          <span className="flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-red-400" /> {activeThreats.length} threats</span>
        </div>
      </div>
      <div className="p-4">
        <div className="relative w-full" style={{ paddingBottom: "55%" }}>
          <div className="absolute inset-0 bg-surface-0 rounded-xl border border-white/[0.04] overflow-hidden">
            <svg className="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="zone-grid" width="5%" height="5%" patternUnits="userSpaceOnUse">
                  <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#1e293b" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#zone-grid)" />
            </svg>

            {ZONES.map((zone) => {
              const colors = zoneColors[zone.type] || zoneColors.common;
              const zoneThreats = getZoneThreats(zone.id);
              const zoneCams = getZoneCameras(zone.id);
              const hasActiveThreat = zoneThreats.length > 0;

              return (
                <div
                  key={zone.id}
                  className={cn(
                    "absolute rounded-lg border transition-all group cursor-default",
                    hasActiveThreat && "animate-pulse"
                  )}
                  style={{
                    left: `${zone.x}%`,
                    top: `${zone.y}%`,
                    width: `${zone.w}%`,
                    height: `${zone.h}%`,
                    background: hasActiveThreat ? "rgba(239, 68, 68, 0.15)" : colors.bg,
                    borderColor: hasActiveThreat ? "rgba(239, 68, 68, 0.6)" : colors.border,
                  }}
                >
                  <div className="px-1.5 py-0.5 flex items-center justify-between">
                    <span className={cn("text-[8px] font-semibold truncate", hasActiveThreat ? "text-red-400" : colors.text)}>
                      {zone.name}
                    </span>
                    <div className="flex items-center gap-0.5">
                      {hasActiveThreat && <AlertTriangle className="w-2.5 h-2.5 text-red-400" />}
                      {zoneCams.length > 0 && (
                        <span className="text-[7px] text-blue-400 flex items-center gap-0.5">
                          <Camera className="w-2 h-2" />{zoneCams.length}
                        </span>
                      )}
                    </div>
                  </div>
                  {zone.type === "critical" && (
                    <Shield className="absolute bottom-1 right-1 w-3 h-3 text-red-400/40" />
                  )}
                </div>
              );
            })}

            <div className="absolute bottom-2 left-2 flex flex-wrap gap-2">
              {[
                { label: "Entry", color: "bg-blue-500" },
                { label: "Restricted", color: "bg-yellow-500" },
                { label: "Critical", color: "bg-red-500" },
                { label: "Common", color: "bg-green-500" },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-1">
                  <div className={cn("w-1.5 h-1.5 rounded-full", item.color)} />
                  <span className="text-[7px] text-gray-500">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
