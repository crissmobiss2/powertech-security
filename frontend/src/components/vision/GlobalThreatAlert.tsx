"use client";
import { useState, useCallback, useRef } from "react";
import { useVisionSocket, type VisionEvent } from "@/hooks/useVisionSocket";
import { cn } from "@/lib/utils";
import { AlertTriangle, X, Shield, Skull, Radio, MapPin, Clock, Volume2, VolumeX } from "lucide-react";

interface AlertToast {
  id: string;
  event: VisionEvent;
  dismissed: boolean;
}

export function GlobalThreatAlert() {
  const [toasts, setToasts] = useState<AlertToast[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(true);

  const onThreat = useCallback((event: VisionEvent) => {
    const severity = String(event.payload.severity || "medium");
    if (severity !== "critical" && severity !== "high") return;

    const toast: AlertToast = { id: event.id, event, dismissed: false };
    setToasts((prev) => [toast, ...prev].slice(0, 5));

    if (soundEnabled && typeof window !== "undefined") {
      try {
        const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = severity === "critical" ? 880 : 660;
        osc.type = "square";
        gain.gain.value = 0.1;
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        osc.start();
        osc.stop(ctx.currentTime + 0.5);
      } catch {
        // audio not available
      }
    }

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== event.id));
    }, 15000);
  }, [soundEnabled]);

  useVisionSocket({ onThreat, enabled: true });

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-md w-full pointer-events-none">
      {toasts.filter((t) => !t.dismissed).map((toast) => {
        const severity = String(toast.event.payload.severity || "medium");
        const isCritical = severity === "critical";
        return (
          <div
            key={toast.id}
            className={cn(
              "pointer-events-auto rounded-2xl border shadow-2xl backdrop-blur-xl transition-all animate-slide-in-right",
              isCritical
                ? "bg-red-950/90 border-red-700/50 shadow-red-900/40"
                : "bg-orange-950/90 border-orange-700/50 shadow-orange-900/40"
            )}
          >
            <div className="px-4 py-3">
              <div className="flex items-start gap-3">
                <div className={cn(
                  "flex items-center justify-center w-10 h-10 rounded-xl shrink-0",
                  isCritical ? "bg-red-900/60" : "bg-orange-900/60"
                )}>
                  {toast.event.type === "banned_person" ? (
                    <Skull className={cn("w-5 h-5", isCritical ? "text-red-300" : "text-orange-300")} />
                  ) : (
                    <AlertTriangle className={cn("w-5 h-5", isCritical ? "text-red-300 animate-pulse" : "text-orange-300")} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md",
                      isCritical ? "bg-red-800/60 text-red-200" : "bg-orange-800/60 text-orange-200"
                    )}>
                      {severity}
                    </span>
                    <span className="text-[10px] text-gray-400 capitalize">
                      {String(toast.event.payload.threat_type || "Threat").replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className={cn("text-sm font-medium mt-1", isCritical ? "text-red-100" : "text-orange-100")}>
                    {String(toast.event.payload.description || "Threat detected")}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5">
                    {!!toast.event.payload.camera_name && (
                      <span className="flex items-center gap-1 text-[10px] text-gray-400">
                        <Radio className="w-2.5 h-2.5" />
                        {String(toast.event.payload.camera_name)}
                      </span>
                    )}
                    {!!toast.event.payload.zone && (
                      <span className="flex items-center gap-1 text-[10px] text-gray-400">
                        <MapPin className="w-2.5 h-2.5" />
                        {String(toast.event.payload.zone)}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-[10px] text-gray-500">
                      <Clock className="w-2.5 h-2.5" />
                      {new Date(toast.event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <button onClick={() => dismiss(toast.id)} className="p-1 text-gray-400 hover:text-white transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => setSoundEnabled(!soundEnabled)} className="p-1 text-gray-500 hover:text-gray-300 transition-colors">
                    {soundEnabled ? <Volume2 className="w-3 h-3" /> : <VolumeX className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            </div>
            {isCritical && (
              <div className="h-0.5 bg-gradient-to-r from-red-600 via-red-400 to-red-600 animate-pulse rounded-b-2xl" />
            )}
          </div>
        );
      })}
    </div>
  );
}
