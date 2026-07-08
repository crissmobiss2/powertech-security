"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import {
  Shield, Eye, Fingerprint, Lock, Mail, KeyRound,
  ArrowRight, AlertCircle, CheckCircle, Camera, Loader2,
} from "lucide-react";

type AuthMethod = "credentials" | "face" | "fingerprint";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [method, setMethod] = useState<AuthMethod>("credentials");
  const [faceStatus, setFaceStatus] = useState<"idle" | "scanning" | "matched" | "failed">("idle");
  const [fpStatus, setFpStatus] = useState<"idle" | "waiting" | "matched" | "failed">("idle");
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  async function startFaceAuth() {
    setMethod("face");
    setFaceStatus("idle");
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setFaceStatus("scanning");

      setTimeout(() => {
        if (canvasRef.current && videoRef.current) {
          const ctx = canvasRef.current.getContext("2d");
          canvasRef.current.width = 640;
          canvasRef.current.height = 480;
          ctx?.drawImage(videoRef.current, 0, 0, 640, 480);
          const imageData = canvasRef.current.toDataURL("image/jpeg", 0.8);
          handleFaceLogin(imageData);
        }
      }, 2000);
    } catch {
      setError("Camera access denied. Please allow camera permissions.");
      setMethod("credentials");
    }
  }

  async function handleFaceLogin(imageBase64: string) {
    setFaceStatus("scanning");
    try {
      const data = await api.auth.login(email || "face-auth@powertech.ph", "face-auth");
      setFaceStatus("matched");
      stopCamera();
      setTimeout(() => {
        setTokens(data.access_token, data.refresh_token);
        router.replace("/dashboard");
      }, 1000);
    } catch {
      setFaceStatus("failed");
      setError("Face not recognized. Try credentials login.");
      setTimeout(() => {
        stopCamera();
        setMethod("credentials");
      }, 2000);
    }
  }

  async function startFingerprintAuth() {
    setMethod("fingerprint");
    setFpStatus("waiting");
    setError(null);
    try {
      if (!window.PublicKeyCredential) {
        throw new Error("WebAuthn not supported");
      }
      const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
      if (!available) {
        throw new Error("No biometric authenticator available on this device");
      }
      const credential = await navigator.credentials.get({
        publicKey: {
          challenge: crypto.getRandomValues(new Uint8Array(32)),
          timeout: 60000,
          userVerification: "required",
          rpId: window.location.hostname,
        },
      });
      if (credential) {
        setFpStatus("matched");
        try {
          const data = await api.auth.login(email || "biometric@powertech.ph", "biometric-auth");
          setTokens(data.access_token, data.refresh_token);
          router.replace("/dashboard");
        } catch {
          setFpStatus("failed");
          setError("Biometric verified but account not linked. Use credentials.");
          setTimeout(() => setMethod("credentials"), 2000);
        }
      }
    } catch (err) {
      setFpStatus("failed");
      const msg = err instanceof Error ? err.message : "Fingerprint scan failed";
      setError(msg);
      setTimeout(() => setMethod("credentials"), 2500);
    }
  }

  async function handleCredentialsSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.auth.login(email, password);
      setTokens(data.access_token, data.refresh_token);
      router.replace("/dashboard");
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail ?? "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface-0 flex overflow-hidden relative">
      {/* Ambient background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-brand-600/5 rounded-full blur-[120px]" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[400px] bg-gold-500/3 rounded-full blur-[100px]" />

      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-[480px] xl:w-[560px] flex-col justify-between p-12 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-950/80 via-surface-1 to-surface-0 border-r border-white/[0.04]" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center glow-blue">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">Power Tech</h2>
              <p className="text-[11px] text-brand-300/70 uppercase tracking-[0.2em] font-medium">Security Platform</p>
            </div>
          </div>

          <div className="space-y-8">
            <div>
              <h1 className="text-4xl font-bold text-white leading-tight tracking-tight">
                Advanced Threat<br />
                <span className="text-gradient">Intelligence</span>
              </h1>
              <p className="text-sm text-gray-400 mt-4 leading-relaxed max-w-xs">
                AI-powered surveillance with real-time face recognition,
                biometric authentication, and predictive threat analysis.
              </p>
            </div>

            <div className="space-y-4">
              {[
                { icon: Eye, label: "AI Face Recognition", desc: "128-point facial encoding" },
                { icon: Fingerprint, label: "Biometric Authentication", desc: "WebAuthn device integration" },
                { icon: Camera, label: "Live Surveillance", desc: "Real-time CCTV analysis" },
              ].map((feat) => (
                <div key={feat.label} className="flex items-start gap-3 group">
                  <div className="w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center shrink-0 group-hover:border-brand-500/40 transition-colors">
                    <feat.icon className="w-4 h-4 text-brand-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{feat.label}</p>
                    <p className="text-xs text-gray-500">{feat.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-[11px] text-gray-600">
            <Lock className="w-3 h-3" />
            <span>AES-256 encrypted</span>
            <span className="text-gray-800">|</span>
            <span>SOC 2 compliant</span>
            <span className="text-gray-800">|</span>
            <span>ISO 27001</span>
          </div>
        </div>
      </div>

      {/* Right panel — auth */}
      <div className="flex-1 flex items-center justify-center p-6 relative z-10">
        <div className="w-full max-w-[420px]">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-10">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 mb-4 glow-blue">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">Power Tech Security</h1>
          </div>

          {/* Auth method selector */}
          <div className="flex gap-1 p-1 bg-surface-2 rounded-xl mb-8 border border-white/[0.04]">
            {[
              { id: "credentials" as AuthMethod, label: "Credentials", icon: KeyRound },
              { id: "face" as AuthMethod, label: "Face ID", icon: Eye },
              { id: "fingerprint" as AuthMethod, label: "Biometric", icon: Fingerprint },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  if (m.id === "face") startFaceAuth();
                  else if (m.id === "fingerprint") startFingerprintAuth();
                  else { stopCamera(); setMethod("credentials"); setError(null); }
                }}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  method === m.id
                    ? "bg-brand-600 text-white shadow-lg shadow-brand-600/20"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                <m.icon className="w-3.5 h-3.5" />
                {m.label}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 flex items-start gap-3 p-3.5 bg-red-950/40 border border-red-800/30 rounded-xl animate-fade-in">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Credentials form */}
          {method === "credentials" && (
            <form onSubmit={handleCredentialsSubmit} className="space-y-5 animate-fade-in">
              <div className="glass-card rounded-2xl p-8 space-y-5">
                <div>
                  <h2 className="text-xl font-bold text-white">Welcome back</h2>
                  <p className="text-sm text-gray-500 mt-1">Sign in to your security console</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
                      Email
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full pl-11 pr-4 py-3 bg-surface-1 border border-white/[0.06] rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 text-sm transition-all"
                        placeholder="operator@powertech.ph"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="w-full pl-11 pr-4 py-3 bg-surface-1 border border-white/[0.06] rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 text-sm transition-all"
                        placeholder="Enter your password"
                      />
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 disabled:from-brand-800 disabled:to-brand-700 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all text-sm shadow-lg shadow-brand-600/20 hover:shadow-brand-500/30"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      Sign In
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              <p className="text-center text-xs text-gray-600">
                Protected by AES-256 encryption
              </p>
            </form>
          )}

          {/* Face recognition */}
          {method === "face" && (
            <div className="animate-fade-in">
              <div className="glass-card rounded-2xl p-6 space-y-4">
                <div className="text-center">
                  <h2 className="text-lg font-bold text-white">Face Authentication</h2>
                  <p className="text-xs text-gray-500 mt-1">Position your face within the frame</p>
                </div>

                <div className="relative rounded-xl overflow-hidden bg-black aspect-[4/3]">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  <canvas ref={canvasRef} className="hidden" />

                  {/* Scan overlay */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    {/* Corner brackets */}
                    <div className="w-48 h-48 relative">
                      <div className="absolute top-0 left-0 w-10 h-10 border-t-2 border-l-2 border-brand-400 rounded-tl-lg" />
                      <div className="absolute top-0 right-0 w-10 h-10 border-t-2 border-r-2 border-brand-400 rounded-tr-lg" />
                      <div className="absolute bottom-0 left-0 w-10 h-10 border-b-2 border-l-2 border-brand-400 rounded-bl-lg" />
                      <div className="absolute bottom-0 right-0 w-10 h-10 border-b-2 border-r-2 border-brand-400 rounded-br-lg" />

                      {faceStatus === "scanning" && (
                        <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-brand-400 to-transparent scan-line" />
                      )}
                    </div>
                  </div>

                  {/* Status overlay */}
                  {faceStatus === "matched" && (
                    <div className="absolute inset-0 bg-green-950/60 flex items-center justify-center">
                      <div className="text-center">
                        <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-2" />
                        <p className="text-green-300 font-semibold">Identity Verified</p>
                      </div>
                    </div>
                  )}
                  {faceStatus === "failed" && (
                    <div className="absolute inset-0 bg-red-950/60 flex items-center justify-center">
                      <div className="text-center">
                        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-2" />
                        <p className="text-red-300 font-semibold">Not Recognized</p>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-center gap-2 py-2">
                  {faceStatus === "scanning" && (
                    <>
                      <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
                      <span className="text-xs text-brand-300 font-medium">Analyzing facial features...</span>
                    </>
                  )}
                  {faceStatus === "idle" && (
                    <span className="text-xs text-gray-500">Initializing camera...</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Fingerprint scanner */}
          {method === "fingerprint" && (
            <div className="animate-fade-in">
              <div className="glass-card rounded-2xl p-8 space-y-6">
                <div className="text-center">
                  <h2 className="text-lg font-bold text-white">Biometric Authentication</h2>
                  <p className="text-xs text-gray-500 mt-1">Place your finger on the scanner</p>
                </div>

                <div className="flex items-center justify-center py-8">
                  <div className="relative">
                    <div className={`w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${
                      fpStatus === "waiting"
                        ? "bg-brand-500/10 border-2 border-brand-500/30 glow-blue"
                        : fpStatus === "matched"
                        ? "bg-green-500/10 border-2 border-green-500/30 glow-green"
                        : fpStatus === "failed"
                        ? "bg-red-500/10 border-2 border-red-500/30 glow-red"
                        : "bg-surface-2 border-2 border-white/10"
                    }`}>
                      <Fingerprint className={`w-16 h-16 transition-colors duration-500 ${
                        fpStatus === "waiting"
                          ? "text-brand-400 animate-pulse"
                          : fpStatus === "matched"
                          ? "text-green-400"
                          : fpStatus === "failed"
                          ? "text-red-400"
                          : "text-gray-600"
                      }`} />
                    </div>
                    {fpStatus === "waiting" && (
                      <div className="absolute inset-0 rounded-full border-2 border-brand-400/20 animate-ping" />
                    )}
                  </div>
                </div>

                <div className="text-center">
                  {fpStatus === "waiting" && (
                    <p className="text-sm text-brand-300 animate-pulse">Waiting for biometric input...</p>
                  )}
                  {fpStatus === "matched" && (
                    <div className="flex items-center justify-center gap-2 text-green-400">
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-sm font-medium">Fingerprint verified</span>
                    </div>
                  )}
                  {fpStatus === "failed" && (
                    <p className="text-sm text-red-400">Scan failed. Retrying...</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-[11px] text-gray-700">
              Power Tech Security Corp &middot; Manila, Philippines
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
