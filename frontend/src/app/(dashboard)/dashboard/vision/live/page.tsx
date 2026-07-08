"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "@/components/layout/header";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import {
  Camera, CameraOff, Zap, ZapOff, AlertTriangle, User,
  Eye, Activity, Cpu, Shield, RefreshCw, Info, Video,
} from "lucide-react";

const WS_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
  .replace("http://", "ws://")
  .replace("https://", "wss://") + "/api/v1/ai-stream/ws/analyze";

interface FaceDetection {
  bbox: { x: number; y: number; w: number; h: number };
  det_score: number;
  estimated_age: number | null;
  gender: string | null;
  emotion: string | null;
  mood: string | null;
  emotion_confidence: number;
}

interface ThreatDetection {
  threat_type: string;
  severity: string;
  confidence: number;
  description: string;
}

interface AnalysisResult {
  faces: FaceDetection[];
  threats: ThreatDetection[];
  anomaly_score: number;
  anomaly_level?: string;
  processing_ms: number;
  error?: string;
}

interface VideoAction {
  security_category: string;
  confidence: number;
  severity: string;
  description: string;
  source: string;
}

const ACTION_COLORS: Record<string, string> = {
  fighting: "text-red-400 border-red-800 bg-red-950/40",
  falling: "text-orange-400 border-orange-800 bg-orange-950/30",
  running: "text-yellow-400 border-yellow-800 bg-yellow-950/30",
  crowd_formation: "text-orange-400 border-orange-800 bg-orange-950/30",
  suspicious_movement: "text-yellow-400 border-yellow-800 bg-yellow-950/30",
  loitering: "text-blue-400 border-blue-800 bg-blue-950/30",
  normal_activity: "text-emerald-400 border-emerald-800/30 bg-emerald-950/20",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-400 border-red-800 bg-red-950/40",
  high: "text-orange-400 border-orange-800 bg-orange-950/30",
  medium: "text-yellow-400 border-yellow-800 bg-yellow-950/30",
  low: "text-blue-400 border-blue-800 bg-blue-950/30",
};

const EMOTION_EMOJI: Record<string, string> = {
  happy: "😊", sad: "😢", angry: "😠", fear: "😨",
  surprise: "😲", disgust: "🤢", neutral: "😐", unknown: "❓",
};

export default function LiveVisionPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [cameraOn, setCameraOn] = useState(false);
  const [aiOn, setAiOn] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [fps, setFps] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<"disconnected" | "connecting" | "connected" | "error">("disconnected");
  const [processInterval, setProcessInterval] = useState(500);
  const [enableFace, setEnableFace] = useState(true);
  const [enableThreat, setEnableThreat] = useState(true);
  const [enableAnomaly, setEnableAnomaly] = useState(false);
  const [videoAction, setVideoAction] = useState<VideoAction | null>(null);
  const fpsCountRef = useRef(0);
  const frameBufferRef = useRef<string[]>([]);
  const actionIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setCameraOn(true);
        setCameraError(null);
      }
    } catch (err) {
      setCameraError(err instanceof Error ? err.message : "Camera access denied");
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      (videoRef.current.srcObject as MediaStream).getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    stopAI();
    setCameraOn(false);
    setResult(null);
  }, []);

  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setWsStatus("connecting");
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setWsStatus("connected");
    ws.onclose = () => setWsStatus("disconnected");
    ws.onerror = () => setWsStatus("error");
    ws.onmessage = (e) => {
      try {
        const data: AnalysisResult = JSON.parse(e.data);
        setResult(data);
        fpsCountRef.current += 1;
        drawOverlay(data);
      } catch {}
    };
    wsRef.current = ws;
  }, []);

  const startAI = useCallback(() => {
    if (!cameraOn) return;
    connectWS();
    setAiOn(true);
    frameBufferRef.current = [];
    if (actionIntervalRef.current) clearInterval(actionIntervalRef.current);

    intervalRef.current = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ws = wsRef.current;
      if (!video || !canvas || ws?.readyState !== WebSocket.OPEN) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const frame = canvas.toDataURL("image/jpeg", 0.75).split(",")[1];
      ws.send(JSON.stringify({
        frame,
        enable_face: enableFace,
        enable_threat: enableThreat,
        enable_anomaly: enableAnomaly,
        confidence_threshold: 0.55,
      }));

      // Accumulate frames for video action analysis (every 16 frames → 4s at 4fps)
      frameBufferRef.current.push(frame);
      if (frameBufferRef.current.length > 16) frameBufferRef.current.shift();

      setFrameCount((c) => c + 1);
    }, processInterval);

    // Video action analysis every 4 seconds (once we have 16 frames)
    actionIntervalRef.current = setInterval(async () => {
      const frames = [...frameBufferRef.current];
      if (frames.length < 4) return;
      try {
        const result = await api.aiStream.videoAction.analyze(frames.slice(-16));
        if (result?.action) setVideoAction(result.action as VideoAction);
      } catch {
        // non-critical
      }
    }, 4000);

    const fpsTimer = setInterval(() => {
      setFps(fpsCountRef.current);
      fpsCountRef.current = 0;
    }, 1000);

    return () => clearInterval(fpsTimer);
  }, [cameraOn, connectWS, processInterval, enableFace, enableThreat, enableAnomaly]);

  const stopAI = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (actionIntervalRef.current) clearInterval(actionIntervalRef.current);
    wsRef.current?.close();
    wsRef.current = null;
    frameBufferRef.current = [];
    setAiOn(false);
    setWsStatus("disconnected");
    setVideoAction(null);
    clearOverlay();
  }, []);

  const drawOverlay = useCallback((data: AnalysisResult) => {
    const overlay = overlayRef.current;
    const video = videoRef.current;
    if (!overlay || !video) return;

    overlay.width = video.videoWidth || 640;
    overlay.height = video.videoHeight || 480;
    const ctx = overlay.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, overlay.width, overlay.height);

    // Draw face bounding boxes
    for (const face of data.faces) {
      const { x, y, w, h } = face.bbox;
      const mood = face.mood ?? "unknown";
      const isThreat = ["hostile", "distressed"].includes(mood);

      ctx.strokeStyle = isThreat ? "#ef4444" : "#3b82f6";
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);

      // Corner accents
      const cSize = 12;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x, y + cSize); ctx.lineTo(x, y); ctx.lineTo(x + cSize, y);
      ctx.moveTo(x + w - cSize, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + cSize);
      ctx.moveTo(x + w, y + h - cSize); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - cSize, y + h);
      ctx.moveTo(x + cSize, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - cSize);
      ctx.stroke();

      // Label background
      const label = [
        face.emotion ? `${EMOTION_EMOJI[face.emotion] ?? ""} ${face.emotion}` : null,
        face.estimated_age ? `${face.estimated_age}y` : null,
        face.gender,
      ].filter(Boolean).join(" · ");

      if (label) {
        ctx.fillStyle = isThreat ? "rgba(239,68,68,0.85)" : "rgba(59,130,246,0.85)";
        const textW = ctx.measureText(label).width + 12;
        ctx.fillRect(x, y - 22, textW, 20);
        ctx.fillStyle = "#ffffff";
        ctx.font = "12px monospace";
        ctx.fillText(label, x + 6, y - 7);
      }
    }

    // Draw threat boxes
    for (const threat of data.threats) {
      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 3;
      const margin = 20;
      ctx.strokeRect(margin, margin, overlay.width - margin * 2, overlay.height - margin * 2);

      ctx.fillStyle = "rgba(239,68,68,0.9)";
      ctx.fillRect(margin, margin, 300, 24);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 12px monospace";
      ctx.fillText(`⚠ ${threat.threat_type.toUpperCase().replace("_", " ")}`, margin + 8, margin + 16);
    }

    // Anomaly score overlay
    if (data.anomaly_score > 0.45) {
      const alpha = Math.min(data.anomaly_score - 0.35, 0.4);
      ctx.fillStyle = `rgba(239,68,68,${alpha})`;
      ctx.fillRect(0, 0, overlay.width, overlay.height);
    }
  }, []);

  const clearOverlay = useCallback(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;
    const ctx = overlay.getContext("2d");
    ctx?.clearRect(0, 0, overlay.width, overlay.height);
  }, []);

  useEffect(() => () => { stopCamera(); }, []);

  const hasCriticalThreat = result?.threats.some((t) => ["critical", "high"].includes(t.severity));

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Live AI Vision" subtitle="Real-time webcam face & threat analysis" />
      <main className="flex-1 p-6 grid grid-cols-1 xl:grid-cols-3 gap-5">

        {/* Camera Feed */}
        <div className="xl:col-span-2 space-y-4">
          <div className={cn(
            "relative glass-card rounded-2xl overflow-hidden aspect-video bg-surface-2 flex items-center justify-center",
            hasCriticalThreat && "ring-2 ring-red-600/70 shadow-lg shadow-red-900/30",
          )}>
            {!cameraOn && (
              <div className="text-center">
                <Camera className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Camera off</p>
                {cameraError && <p className="text-red-400 text-xs mt-1">{cameraError}</p>}
              </div>
            )}
            <video
              ref={videoRef}
              className="absolute inset-0 w-full h-full object-cover"
              muted
              playsInline
              style={{ display: cameraOn ? "block" : "none" }}
            />
            <canvas ref={canvasRef} className="hidden" />
            <canvas
              ref={overlayRef}
              className="absolute inset-0 w-full h-full object-cover pointer-events-none"
              style={{ display: cameraOn ? "block" : "none" }}
            />

            {/* Status overlays */}
            {cameraOn && (
              <>
                <div className="absolute top-3 left-3 flex items-center gap-2">
                  <span className={cn(
                    "flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg font-semibold",
                    aiOn ? "bg-emerald-900/80 text-emerald-300" : "bg-surface-3/80 text-gray-400",
                  )}>
                    <span className={cn("w-1.5 h-1.5 rounded-full", aiOn ? "bg-emerald-400 animate-pulse" : "bg-gray-600")} />
                    {aiOn ? "AI LIVE" : "AI OFF"}
                  </span>
                  {aiOn && (
                    <span className="text-[10px] px-2 py-1 bg-surface-3/80 text-gray-400 rounded-lg font-mono">
                      {fps} FPS · {result?.processing_ms ?? 0}ms
                    </span>
                  )}
                </div>
                {hasCriticalThreat && (
                  <div className="absolute top-3 right-3 flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg bg-red-900/80 text-red-300 font-bold animate-pulse">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    THREAT DETECTED
                  </div>
                )}
              </>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3 flex-wrap">
            {!cameraOn ? (
              <button onClick={startCamera}
                className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-brand-700 to-brand-600 hover:from-brand-600 hover:to-brand-500 text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-brand-900/30">
                <Camera className="w-4 h-4" />
                Start Camera
              </button>
            ) : (
              <>
                <button onClick={stopCamera}
                  className="flex items-center gap-2 px-4 py-2.5 bg-surface-3 hover:bg-surface-4 text-gray-300 text-sm font-medium rounded-xl border border-white/[0.06] transition-colors">
                  <CameraOff className="w-4 h-4" />
                  Stop Camera
                </button>
                {!aiOn ? (
                  <button onClick={startAI}
                    className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-700 to-emerald-600 hover:from-emerald-600 hover:to-emerald-500 text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-emerald-900/30">
                    <Zap className="w-4 h-4" />
                    Start AI Analysis
                  </button>
                ) : (
                  <button onClick={stopAI}
                    className="flex items-center gap-2 px-4 py-2.5 bg-surface-3 hover:bg-surface-4 text-gray-300 text-sm font-medium rounded-xl border border-white/[0.06] transition-colors">
                    <ZapOff className="w-4 h-4" />
                    Stop AI
                  </button>
                )}
              </>
            )}

            {/* AI toggle switches */}
            <div className="flex items-center gap-4 ml-auto">
              {(["face", "threat", "anomaly"] as const).map((key) => {
                const enabled = key === "face" ? enableFace : key === "threat" ? enableThreat : enableAnomaly;
                const setter = key === "face" ? setEnableFace : key === "threat" ? setEnableThreat : setEnableAnomaly;
                return (
                  <label key={key} className="flex items-center gap-1.5 cursor-pointer select-none">
                    <button onClick={() => setter(!enabled)}
                      className={cn(
                        "relative w-8 h-4 rounded-full transition-colors",
                        enabled ? "bg-brand-600" : "bg-surface-3 border border-white/[0.06]",
                      )}>
                      <span className={cn(
                        "absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform",
                        enabled ? "translate-x-4" : "translate-x-0.5",
                      )} />
                    </button>
                    <span className="text-xs text-gray-400 capitalize">{key}</span>
                  </label>
                );
              })}
              <select value={processInterval} onChange={(e) => setProcessInterval(+e.target.value)}
                className="text-xs bg-surface-2 border border-white/[0.06] rounded-xl px-2 py-1.5 text-gray-300 focus:outline-none">
                <option value={250}>4 fps</option>
                <option value={500}>2 fps</option>
                <option value={1000}>1 fps</option>
                <option value={2000}>0.5 fps</option>
              </select>
            </div>
          </div>
        </div>

        {/* Analysis Panel */}
        <div className="space-y-4">
          {/* WebSocket status */}
          <div className="glass-card rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Backend Connection</span>
              <span className={cn(
                "text-[10px] px-2 py-0.5 rounded-full font-semibold",
                wsStatus === "connected" ? "bg-emerald-900/50 text-emerald-400" :
                wsStatus === "connecting" ? "bg-yellow-900/50 text-yellow-400" :
                wsStatus === "error" ? "bg-red-900/50 text-red-400" :
                "bg-surface-3 text-gray-500",
              )}>
                {wsStatus.toUpperCase()}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-center">
              <div>
                <p className="text-lg font-bold text-white font-mono">{result?.faces.length ?? 0}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">Faces</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white font-mono">{result?.threats.length ?? 0}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">Threats</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white font-mono">{fps}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">Resp/s</p>
              </div>
              <div>
                <p className="text-lg font-bold text-white font-mono">{result?.processing_ms ?? 0}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">ms/frame</p>
              </div>
            </div>
          </div>

          {/* Anomaly score */}
          {enableAnomaly && (
            <div className="glass-card rounded-2xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Anomaly Score</span>
                <span className="text-xs text-gray-500">{((result?.anomaly_score ?? 0) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full h-2 bg-surface-3 rounded-full overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-300",
                    (result?.anomaly_score ?? 0) > 0.85 ? "bg-red-500" :
                    (result?.anomaly_score ?? 0) > 0.65 ? "bg-orange-500" :
                    (result?.anomaly_score ?? 0) > 0.45 ? "bg-yellow-500" : "bg-emerald-500",
                  )}
                  style={{ width: `${(result?.anomaly_score ?? 0) * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1.5 capitalize">{result?.anomaly_level ?? "normal"}</p>
            </div>
          )}

          {/* Detected faces */}
          {result?.faces.length ? (
            <div className="glass-card rounded-2xl p-4 space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <User className="w-4 h-4 text-gray-500" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Detected Faces</span>
              </div>
              {result.faces.map((face, i) => (
                <div key={i} className="bg-surface-2 rounded-xl p-3 border border-white/[0.04]">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">
                      {EMOTION_EMOJI[face.emotion ?? "unknown"]} Person {i + 1}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono">
                      {(face.det_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
                    {face.estimated_age && <span>{face.estimated_age}y</span>}
                    {face.gender && <span className="capitalize">{face.gender}</span>}
                    {face.emotion && (
                      <span className={cn(
                        "capitalize",
                        face.mood === "hostile" ? "text-red-400" :
                        face.mood === "distressed" ? "text-orange-400" :
                        face.mood === "positive" ? "text-emerald-400" : "text-gray-400",
                      )}>{face.emotion}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : aiOn ? (
            <div className="glass-card rounded-2xl p-6 text-center">
              <Eye className="w-7 h-7 text-gray-600 mx-auto mb-2" />
              <p className="text-xs text-gray-500">No faces detected</p>
            </div>
          ) : null}

          {/* Threats */}
          {result?.threats.map((threat, i) => (
            <div key={i} className={cn(
              "rounded-2xl p-4 border",
              SEVERITY_COLORS[threat.severity] ?? SEVERITY_COLORS.low,
            )}>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm font-bold uppercase tracking-wide">
                  {threat.threat_type.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-xs opacity-80">{threat.description}</p>
              <div className="flex items-center gap-3 mt-2 text-[10px] opacity-70">
                <span className="uppercase font-semibold">{threat.severity}</span>
                <span>{(threat.confidence * 100).toFixed(0)}% confidence</span>
              </div>
            </div>
          ))}

          {/* Video Action Classification */}
          {aiOn && (
            <div className={cn(
              "rounded-2xl p-4 border",
              videoAction && videoAction.security_category !== "normal_activity"
                ? ACTION_COLORS[videoAction.security_category] ?? ACTION_COLORS.suspicious_movement
                : "glass-card border-white/[0.04]",
            )}>
              <div className="flex items-center gap-2 mb-2">
                <Video className="w-4 h-4 text-gray-500" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Action Recognition</span>
                <span className="text-[10px] text-gray-600 ml-auto">VideoMAE</span>
              </div>
              {videoAction ? (
                <>
                  <p className="text-sm font-bold text-white capitalize">
                    {videoAction.security_category.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs opacity-75 mt-0.5">{videoAction.description}</p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] opacity-60">
                    <span className="uppercase font-semibold">{videoAction.severity}</span>
                    <span>{(videoAction.confidence * 100).toFixed(0)}% conf</span>
                    <span className="capitalize">{videoAction.source}</span>
                  </div>
                </>
              ) : (
                <p className="text-xs text-gray-600">Buffering frames for action classification…</p>
              )}
            </div>
          )}

          {/* Info */}
          {!aiOn && (
            <div className="glass-card rounded-2xl p-4 border border-white/[0.04]">
              <div className="flex items-start gap-3">
                <Info className="w-4 h-4 text-gray-500 mt-0.5 shrink-0" />
                <div className="text-xs text-gray-500 space-y-1.5">
                  <p className="font-medium text-gray-400">InsightFace ArcFace · YOLO11 · DeepFace · VideoMAE</p>
                  <p>Enable camera, then Start AI Analysis to run real-time face detection, age/gender estimation, emotion analysis, threat detection, and video action recognition.</p>
                  <p>Frames are processed by the backend AI pipeline via WebSocket — no data is stored from this live session.</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
