"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, formatDate, severityColor, statusColor, cn } from "@/lib/utils";
import type { Ticket } from "@/types";
import {
  ArrowLeft, MapPin, MapPinOff, Clock, CheckCircle2,
  UserCheck, AlertTriangle, Wrench, Calendar, DollarSign,
  FileText, Save, X,
} from "lucide-react";

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-white/[0.04] last:border-0">
      <span className="text-xs text-gray-500 shrink-0 w-36">{label}</span>
      <span className="text-sm text-white text-right">{children}</span>
    </div>
  );
}

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [checkoutModal, setCheckoutModal] = useState(false);
  const [signoffModal, setSignoffModal] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [laborHours, setLaborHours] = useState("");
  const [cost, setCost] = useState("");
  const [signedBy, setSignedBy] = useState("");
  const [checkinNotes, setCheckinNotes] = useState("");
  const [showCheckinNotes, setShowCheckinNotes] = useState(false);

  const { data: ticket, isLoading } = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api.tickets.get(id),
  });

  const checkinMutation = useMutation({
    mutationFn: () => api.tickets.checkin(id, checkinNotes || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      setShowCheckinNotes(false);
      setCheckinNotes("");
    },
  });

  const checkoutMutation = useMutation({
    mutationFn: () =>
      api.tickets.checkout(id, {
        resolution_notes: resolutionNotes,
        labor_hours: laborHours ? parseFloat(laborHours) : undefined,
        cost: cost ? parseFloat(cost) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      setCheckoutModal(false);
    },
  });

  const signoffMutation = useMutation({
    mutationFn: () => api.tickets.signoff(id, signedBy),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      setSignoffModal(false);
    },
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full overflow-auto bg-surface-0">
        <Header title="Ticket Detail" subtitle="Work order management" />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-pulse text-gray-500">Loading...</div>
        </div>
      </div>
    );
  }

  const t = ticket as Ticket | undefined;
  if (!t) {
    return (
      <div className="flex flex-col h-full overflow-auto bg-surface-0">
        <Header title="Ticket Detail" subtitle="Work order management" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">Ticket not found</p>
        </div>
      </div>
    );
  }

  const slaBreached = t.sla_due_at && new Date(t.sla_due_at) < new Date() && !["resolved", "closed", "cancelled"].includes(t.status);
  const canCheckin = (t.status === "open" || t.status === "assigned") && !t.checkin_at;
  const canCheckout = !!t.checkin_at && !t.checkout_at && !["resolved", "closed", "cancelled"].includes(t.status);
  const canSignoff = !!t.checkout_at && !t.client_signoff_at && !["closed", "cancelled"].includes(t.status);

  const stages = [
    { label: "Created", done: true, time: t.created_at },
    { label: "Assigned", done: !!t.assigned_to || t.status !== "open", time: null },
    { label: "Checked In", done: !!t.checkin_at, time: t.checkin_at },
    { label: "Checked Out", done: !!t.checkout_at, time: t.checkout_at },
    { label: "Client Signoff", done: !!t.client_signoff_at, time: t.client_signoff_at },
    { label: "Closed", done: t.status === "closed", time: t.closed_at },
  ];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Ticket Detail" subtitle="Work order management" />
      <main className="flex-1 p-6 space-y-5 max-w-5xl">
        {/* Back + Title */}
        <div className="flex items-start gap-4">
          <button onClick={() => router.push("/tickets")}
            className="mt-0.5 p-2 text-gray-500 hover:text-white hover:bg-surface-2 rounded-xl transition-colors shrink-0">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <span className={cn("text-[11px] px-2.5 py-1 rounded-lg font-semibold border uppercase tracking-wider", severityColor(t.priority))}>
                {t.priority}
              </span>
              <span className={cn("text-[11px] px-2.5 py-1 rounded-lg font-semibold", statusColor(t.status))}>
                {t.status.replace("_", " ")}
              </span>
              <span className="text-xs text-gray-500 capitalize">{t.type}</span>
              {slaBreached && (
                <span className="flex items-center gap-1 text-xs text-red-400 font-medium">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  SLA Breached
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-white mt-2">{t.title}</h2>
            {t.description && <p className="text-sm text-gray-400 mt-1">{t.description}</p>}
          </div>
        </div>

        {/* Progress timeline */}
        <div className="glass-card rounded-2xl p-5">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Progress</h3>
          <div className="flex items-center gap-1">
            {stages.map((stage, i) => (
              <div key={stage.label} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all",
                    stage.done ? "bg-brand-600 shadow-lg shadow-brand-600/30" : "bg-surface-3 border border-white/[0.06]"
                  )}>
                    {stage.done ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-gray-600" />
                    )}
                  </div>
                  <p className="text-[10px] text-gray-500 mt-1.5 text-center leading-tight">{stage.label}</p>
                  {stage.time && (
                    <p className="text-[9px] text-gray-600 text-center leading-tight mt-0.5">{timeAgo(stage.time)}</p>
                  )}
                </div>
                {i < stages.length - 1 && (
                  <div className={cn("h-px flex-1 mx-1 transition-all", stage.done && stages[i + 1]?.done ? "bg-brand-600/50" : "bg-white/[0.06]")} />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Details */}
          <div className="glass-card rounded-2xl p-5">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Details</h3>
            <InfoRow label="Type">
              <span className="capitalize">{t.type}</span>
            </InfoRow>
            <InfoRow label="Priority">
              <span className={cn("text-[11px] px-2 py-0.5 rounded-lg border font-semibold capitalize", severityColor(t.priority))}>
                {t.priority}
              </span>
            </InfoRow>
            <InfoRow label="Status">
              <span className={cn("text-[11px] px-2 py-0.5 rounded-lg font-semibold capitalize", statusColor(t.status))}>
                {t.status.replace("_", " ")}
              </span>
            </InfoRow>
            <InfoRow label="Assigned To">
              {t.assigned_to ? (
                <span className="font-mono text-xs text-gray-400">{t.assigned_to.slice(0, 16)}…</span>
              ) : (
                <span className="text-gray-600">Unassigned</span>
              )}
            </InfoRow>
            <InfoRow label="SLA Due">
              <span className={slaBreached ? "text-red-400 font-semibold" : "text-gray-400"}>
                {t.sla_due_at ? formatDate(t.sla_due_at) : "—"}
              </span>
            </InfoRow>
            <InfoRow label="Created">
              <span className="text-gray-400">{formatDate(t.created_at)}</span>
            </InfoRow>
          </div>

          {/* Field Operations */}
          <div className="glass-card rounded-2xl p-5">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Field Operations</h3>
            <InfoRow label="Check-in">
              <span className="text-gray-400">{t.checkin_at ? formatDate(t.checkin_at) : "—"}</span>
            </InfoRow>
            <InfoRow label="Check-out">
              <span className="text-gray-400">{t.checkout_at ? formatDate(t.checkout_at) : "—"}</span>
            </InfoRow>
            <InfoRow label="Labor Hours">
              <span className={t.labor_hours ? "text-white font-medium" : "text-gray-600"}>
                {t.labor_hours != null ? `${t.labor_hours}h` : "—"}
              </span>
            </InfoRow>
            <InfoRow label="Cost">
              <span className={t.cost ? "text-white font-medium" : "text-gray-600"}>
                {t.cost != null ? `₱${t.cost.toLocaleString()}` : "—"}
              </span>
            </InfoRow>
            <InfoRow label="Client Signoff">
              <span className="text-gray-400">
                {t.client_signoff_at ? `${t.client_signoff_by ?? "Signed"} · ${timeAgo(t.client_signoff_at)}` : "—"}
              </span>
            </InfoRow>
          </div>
        </div>

        {/* Resolution notes */}
        {t.resolution_notes && (
          <div className="glass-card rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-4 h-4 text-gray-500" />
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Resolution Notes</h3>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">{t.resolution_notes}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {canCheckin && !showCheckinNotes && (
            <button onClick={() => setShowCheckinNotes(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-700 to-emerald-600 hover:from-emerald-600 hover:to-emerald-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-emerald-900/30">
              <MapPin className="w-4 h-4" />
              Check In
            </button>
          )}
          {canCheckout && (
            <button onClick={() => setCheckoutModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-700 to-brand-600 hover:from-brand-600 hover:to-brand-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-brand-900/30">
              <MapPinOff className="w-4 h-4" />
              Check Out
            </button>
          )}
          {canSignoff && (
            <button onClick={() => setSignoffModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-gold-700 to-gold-600 hover:from-gold-600 hover:to-gold-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-yellow-900/30">
              <UserCheck className="w-4 h-4" />
              Client Signoff
            </button>
          )}
        </div>

        {/* Checkin notes inline */}
        {showCheckinNotes && (
          <div className="glass-card rounded-2xl p-5 border border-emerald-800/40">
            <h3 className="text-sm font-semibold text-white mb-3">Check In</h3>
            <textarea
              value={checkinNotes}
              onChange={(e) => setCheckinNotes(e.target.value)}
              placeholder="Optional arrival notes..."
              rows={3}
              className="w-full text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-4 py-3 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-emerald-600 resize-none"
            />
            <div className="flex gap-3 mt-3">
              <button onClick={() => checkinMutation.mutate()} disabled={checkinMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium rounded-xl transition-colors disabled:opacity-50">
                <MapPin className="w-4 h-4" />
                {checkinMutation.isPending ? "Checking in..." : "Confirm Check-In"}
              </button>
              <button onClick={() => setShowCheckinNotes(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-surface-3 rounded-xl transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Checkout Modal */}
      {checkoutModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setCheckoutModal(false)} />
          <div className="relative glass-card rounded-2xl w-full max-w-md animate-scale-in p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-bold text-white">Check Out</h3>
              <button onClick={() => setCheckoutModal(false)} className="p-1 text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block">Resolution Notes *</label>
                <textarea value={resolutionNotes} onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Describe work performed and outcome..."
                  rows={4}
                  className="w-full text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-4 py-3 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-brand-600 resize-none" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block flex items-center gap-1"><Clock className="w-3 h-3" />Labor Hours</label>
                  <input type="number" step="0.5" value={laborHours} onChange={(e) => setLaborHours(e.target.value)}
                    placeholder="e.g. 3.5"
                    className="w-full text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-brand-600" />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block flex items-center gap-1"><DollarSign className="w-3 h-3" />Cost (₱)</label>
                  <input type="number" step="100" value={cost} onChange={(e) => setCost(e.target.value)}
                    placeholder="e.g. 5000"
                    className="w-full text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-brand-600" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => checkoutMutation.mutate()} disabled={!resolutionNotes.trim() || checkoutMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-brand-700 to-brand-600 hover:from-brand-600 hover:to-brand-500 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50">
                <Save className="w-4 h-4" />
                {checkoutMutation.isPending ? "Saving..." : "Complete Checkout"}
              </button>
              <button onClick={() => setCheckoutModal(false)}
                className="px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-surface-3 rounded-xl transition-colors">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Signoff Modal */}
      {signoffModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSignoffModal(false)} />
          <div className="relative glass-card rounded-2xl w-full max-w-sm animate-scale-in p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-bold text-white">Client Signoff</h3>
              <button onClick={() => setSignoffModal(false)} className="p-1 text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1.5 block flex items-center gap-1"><UserCheck className="w-3 h-3" />Signed By (Client Representative)</label>
              <input type="text" value={signedBy} onChange={(e) => setSignedBy(e.target.value)}
                placeholder="Full name of client signing off"
                className="w-full text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2.5 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-gold-600" />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => signoffMutation.mutate()} disabled={!signedBy.trim() || signoffMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-gold-700 to-gold-600 hover:from-gold-600 hover:to-gold-500 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50">
                <CheckCircle2 className="w-4 h-4" />
                {signoffMutation.isPending ? "Signing..." : "Confirm Signoff"}
              </button>
              <button onClick={() => setSignoffModal(false)}
                className="px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-surface-3 rounded-xl transition-colors">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
