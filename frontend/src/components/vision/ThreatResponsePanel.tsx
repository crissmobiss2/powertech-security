"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ThreatDetection } from "@/types";
import {
  Lock, Shield, Phone, Bell, LogOut, CheckCircle, Slash, Mail,
  AlertTriangle, Loader2, ChevronDown, ChevronUp,
} from "lucide-react";

interface Props {
  threat: ThreatDetection;
  onClose?: () => void;
}

const ACTIONS = [
  { id: "dispatch_security", name: "Dispatch Security", icon: Shield, color: "bg-blue-600 hover:bg-blue-500", confirm: false },
  { id: "lockdown", name: "Zone Lockdown", icon: Lock, color: "bg-red-600 hover:bg-red-500", confirm: true },
  { id: "sound_alarm", name: "Sound Alarm", icon: Bell, color: "bg-orange-600 hover:bg-orange-500", confirm: true },
  { id: "notify_police", name: "Notify PNP", icon: Phone, color: "bg-red-700 hover:bg-red-600", confirm: true },
  { id: "evacuate", name: "Evacuate Zone", icon: LogOut, color: "bg-red-800 hover:bg-red-700", confirm: true },
  { id: "isolate_zone", name: "Isolate Zone", icon: Slash, color: "bg-yellow-600 hover:bg-yellow-500", confirm: false },
  { id: "notify_management", name: "Notify Management", icon: Mail, color: "bg-indigo-600 hover:bg-indigo-500", confirm: false },
  { id: "all_clear", name: "All Clear", icon: CheckCircle, color: "bg-green-600 hover:bg-green-500", confirm: true },
];

export function ThreatResponsePanel({ threat, onClose }: Props) {
  const [confirming, setConfirming] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [expanded, setExpanded] = useState(true);
  const qc = useQueryClient();

  const respondMutation = useMutation({
    mutationFn: (action: string) =>
      api.threatResponse.respond({
        action,
        threat_id: threat.id,
        notes: notes || undefined,
        zone: threat.zone || undefined,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["vision-threats"] });
      qc.invalidateQueries({ queryKey: ["vision-stats"] });
      setConfirming(null);
      setNotes("");
    },
  });

  const executeAction = (actionId: string) => {
    const action = ACTIONS.find((a) => a.id === actionId);
    if (!action) return;
    if (action.confirm && confirming !== actionId) {
      setConfirming(actionId);
      return;
    }
    respondMutation.mutate(actionId);
  };

  const severityColors: Record<string, string> = {
    critical: "border-red-600 bg-red-950/50",
    high: "border-orange-600 bg-orange-950/50",
    medium: "border-yellow-600 bg-yellow-950/50",
    low: "border-blue-600 bg-blue-950/50",
  };

  return (
    <div className={cn(
      "border rounded-xl overflow-hidden",
      severityColors[threat.severity] || severityColors.medium
    )}>
      {/* Threat Summary */}
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <AlertTriangle className={cn(
            "w-5 h-5 shrink-0",
            threat.severity === "critical" ? "text-red-400 animate-pulse" : "text-orange-400"
          )} />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">{threat.description}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={cn(
                "text-[10px] font-bold uppercase px-1.5 py-0.5 rounded",
                threat.severity === "critical" ? "bg-red-800 text-red-200" : "bg-orange-800 text-orange-200"
              )}>
                {threat.severity}
              </span>
              <span className="text-[10px] text-gray-500 capitalize">{threat.threat_type.replace(/_/g, " ")}</span>
              {threat.zone && <span className="text-[10px] text-gray-600">Zone: {threat.zone}</span>}
            </div>
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="p-1 text-gray-500 hover:text-white">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {expanded && (
        <div className="p-4 space-y-3">
          {/* Response Actions Grid */}
          <div className="grid grid-cols-2 gap-2">
            {ACTIONS.map((action) => {
              const Icon = action.icon;
              const isConfirming = confirming === action.id;
              const isLoading = respondMutation.isPending && respondMutation.variables === action.id;
              return (
                <button
                  key={action.id}
                  onClick={() => executeAction(action.id)}
                  disabled={respondMutation.isPending}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium text-white transition-all",
                    isConfirming ? "ring-2 ring-white/50 scale-[1.02]" : "",
                    respondMutation.isPending && respondMutation.variables !== action.id ? "opacity-40" : "",
                    action.color,
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" />
                  )}
                  <span>{isConfirming ? `Confirm ${action.name}?` : action.name}</span>
                </button>
              );
            })}
          </div>

          {/* Notes */}
          <div>
            <input
              type="text"
              placeholder="Add response notes (optional)..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-3 py-2 bg-surface-2 border border-white/[0.06] rounded-lg text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-brand-500/50"
            />
          </div>

          {/* Action History */}
          {threat.response_actions && threat.response_actions.length > 0 && (
            <div className="border-t border-white/[0.04] pt-2">
              <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-1">Actions Taken</p>
              <div className="space-y-1">
                {threat.response_actions.map((ra, i) => (
                  <div key={i} className="flex items-center justify-between text-[10px]">
                    <span className="text-gray-400 capitalize">{(ra as Record<string, string>).action?.replace(/_/g, " ")}</span>
                    <span className={cn(
                      "px-1.5 py-0.5 rounded",
                      (ra as Record<string, string>).status === "triggered" ? "bg-green-950 text-green-400" : "bg-surface-3 text-gray-400"
                    )}>
                      {(ra as Record<string, string>).status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
