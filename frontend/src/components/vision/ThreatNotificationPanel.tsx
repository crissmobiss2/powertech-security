"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { VisionEvent } from "@/hooks/useVisionSocket";
import {
  AlertTriangle, Wifi, WifiOff, ChevronDown, ChevronUp,
  Shield, Skull, Eye, Radio, Clock,
} from "lucide-react";

interface Props {
  events: VisionEvent[];
  connected: boolean;
  unreadCount: number;
  onClear: () => void;
  onMarkRead: (id: string) => void;
}

const severityConfig: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  critical: { bg: "bg-red-950/60", border: "border-red-800/40", text: "text-red-300", dot: "bg-red-500" },
  high: { bg: "bg-orange-950/60", border: "border-orange-800/40", text: "text-orange-300", dot: "bg-orange-500" },
  medium: { bg: "bg-yellow-950/60", border: "border-yellow-800/40", text: "text-yellow-300", dot: "bg-yellow-500" },
  low: { bg: "bg-blue-950/60", border: "border-blue-800/40", text: "text-blue-300", dot: "bg-blue-500" },
};

function threatIcon(type: string) {
  switch (type) {
    case "banned_person": return Skull;
    case "weapon_detected": return Shield;
    case "threat_detected": return AlertTriangle;
    default: return Eye;
  }
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "—";
  }
}

export function ThreatNotificationPanel({ events, connected, unreadCount, onClear, onMarkRead }: Props) {
  const [expanded, setExpanded] = useState(true);
  const recentEvents = events.slice(0, 20);

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <Radio className={cn("w-4 h-4", connected ? "text-emerald-400 animate-pulse" : "text-gray-600")} />
          <h3 className="text-sm font-bold text-white">Live Threat Feed</h3>
          {unreadCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-bold bg-red-600 text-white rounded-full min-w-[18px] text-center">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 mr-2">
            {connected ? (
              <><Wifi className="w-3 h-3 text-emerald-400" /><span className="text-[10px] text-emerald-400 font-semibold">LIVE</span></>
            ) : (
              <><WifiOff className="w-3 h-3 text-gray-600" /><span className="text-[10px] text-gray-600">OFFLINE</span></>
            )}
          </div>
          {events.length > 0 && (
            <button onClick={onClear} className="text-[10px] text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded-lg hover:bg-white/[0.04]">
              CLEAR
            </button>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-gray-500 hover:text-white transition-colors"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="max-h-[400px] overflow-y-auto">
          {recentEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-gray-600">
              <div className="w-12 h-12 rounded-2xl bg-surface-2 flex items-center justify-center mb-3">
                <Shield className="w-6 h-6 text-gray-700" />
              </div>
              <p className="text-xs text-gray-600">No live events &mdash; monitoring</p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.03]">
              {recentEvents.map((evt) => {
                const severity = (evt.payload.severity as string) || "medium";
                const config = severityConfig[severity] || severityConfig.medium;
                const Icon = threatIcon(evt.type);
                return (
                  <div
                    key={evt.id}
                    onClick={() => onMarkRead(evt.id)}
                    className={cn(
                      "flex gap-3 px-4 py-3 cursor-pointer transition-all hover:bg-white/[0.02]",
                      !evt.read && "border-l-2 border-l-red-500 bg-red-500/[0.03]"
                    )}
                  >
                    <div className={cn("flex items-center justify-center w-8 h-8 rounded-lg shrink-0", config.bg, "border", config.border)}>
                      <Icon className={cn("w-4 h-4", config.text)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dot)} />
                        <span className={cn("text-[10px] font-bold uppercase tracking-wider", config.text)}>
                          {severity}
                        </span>
                        <span className="text-[10px] text-gray-700">|</span>
                        <span className="text-[10px] text-gray-500 capitalize">
                          {(evt.payload.threat_type as string)?.replace(/_/g, " ") || evt.type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p className="text-xs text-gray-300 mt-0.5 truncate">
                        {(evt.payload.description as string) || "Threat event detected"}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        {!!evt.payload.camera_name && (
                          <span className="text-[10px] text-gray-500">
                            {String(evt.payload.camera_name)}
                          </span>
                        )}
                        {!!evt.payload.zone && (
                          <span className="text-[10px] text-gray-600">
                            Zone: {String(evt.payload.zone)}
                          </span>
                        )}
                        <span className="text-[10px] text-gray-700 ml-auto flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {formatTime(evt.timestamp)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
