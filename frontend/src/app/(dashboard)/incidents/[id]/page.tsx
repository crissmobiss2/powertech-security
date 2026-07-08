"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, formatDate, severityColor, statusColor, cn } from "@/lib/utils";
import type { Incident, IncidentTimelineEntry } from "@/types";
import {
  ArrowLeft, Clock, User, AlertTriangle, MessageSquare,
  CheckCircle2, XCircle, Send,
} from "lucide-react";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [closeModal, setCloseModal] = useState(false);
  const [resolution, setResolution] = useState("");

  const { data: incident, isLoading } = useQuery({
    queryKey: ["incident", id],
    queryFn: () => api.incidents.get(id),
  });

  const { data: timeline } = useQuery({
    queryKey: ["incident-timeline", id],
    queryFn: () => api.incidents.timeline(id),
    enabled: !!id,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: () => api.incidents.acknowledge(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incident", id] }),
  });

  const closeMutation = useMutation({
    mutationFn: () => api.incidents.close(id, { status: "closed", resolution_summary: resolution }),
    onSuccess: () => {
      setCloseModal(false);
      qc.invalidateQueries({ queryKey: ["incident", id] });
    },
  });

  const commentMutation = useMutation({
    mutationFn: () => api.incidents.addComment(id, { content: comment }),
    onSuccess: () => {
      setComment("");
      qc.invalidateQueries({ queryKey: ["incident-timeline", id] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full overflow-auto bg-surface-0">
        <Header title="Incident Detail" subtitle="Investigation & response" />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-pulse text-gray-500">Loading...</div>
        </div>
      </div>
    );
  }

  const inc = incident as Incident | undefined;
  if (!inc) {
    return (
      <div className="flex flex-col h-full overflow-auto bg-surface-0">
        <Header title="Incident Detail" subtitle="Investigation & response" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">Incident not found</p>
        </div>
      </div>
    );
  }

  const timelineEntries: IncidentTimelineEntry[] = timeline ?? [];
  const isOpen = !["closed", "resolved", "false_positive"].includes(inc.status);
  const slaBreached = inc.sla_due_at && new Date(inc.sla_due_at) < new Date() && isOpen;

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Incident Detail" subtitle="Investigation & response" />
      <main className="flex-1 p-6 max-w-5xl">
        {/* Back button */}
        <button onClick={() => router.push("/incidents")}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to Incidents
        </button>

        {/* Header */}
        <div className="glass-card rounded-2xl p-6 mb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-white">{inc.title}</h2>
              {inc.description && <p className="text-sm text-gray-400 mt-1">{inc.description}</p>}
            </div>
            <div className="flex items-center gap-2">
              <span className={cn("inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border", severityColor(inc.severity))}>
                {inc.severity.toUpperCase()}
              </span>
              <span className={cn("inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium", statusColor(inc.status))}>
                {inc.status.replace("_", " ")}
              </span>
            </div>
          </div>

          {/* Meta grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5 pt-5 border-t border-white/[0.04]">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Type</p>
              <p className="text-sm text-white mt-1 capitalize">{inc.type}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Source</p>
              <p className="text-sm text-white mt-1 capitalize">{inc.source}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Created</p>
              <p className="text-sm text-white mt-1">{formatDate(inc.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">SLA Due</p>
              <p className={cn("text-sm mt-1", slaBreached ? "text-red-400 font-semibold" : "text-white")}>
                {inc.sla_due_at ? formatDate(inc.sla_due_at) : "—"}
                {slaBreached && <span className="ml-1 text-[10px] uppercase">Breached</span>}
              </p>
            </div>
          </div>

          {/* Actions */}
          {isOpen && (
            <div className="flex gap-2 mt-5 pt-5 border-t border-white/[0.04]">
              {inc.status === "new" && (
                <button onClick={() => acknowledgeMutation.mutate()} disabled={acknowledgeMutation.isPending}
                  className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors">
                  <CheckCircle2 className="w-4 h-4" />
                  Acknowledge
                </button>
              )}
              <button onClick={() => setCloseModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface-3 hover:bg-white/[0.04] text-gray-300 text-sm font-medium rounded-lg border border-white/[0.06] transition-colors">
                <XCircle className="w-4 h-4" />
                Close Incident
              </button>
            </div>
          )}
        </div>

        {/* Close modal */}
        {closeModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
            <div className="bg-surface-1 border border-white/[0.06] rounded-xl p-6 max-w-md w-full">
              <h3 className="text-base font-semibold text-white mb-3">Close Incident</h3>
              <textarea value={resolution} onChange={(e) => setResolution(e.target.value)} rows={4} placeholder="Resolution summary (required)..."
                className="w-full bg-surface-3 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500 resize-none" />
              <div className="flex gap-2 mt-4">
                <button onClick={() => closeMutation.mutate()} disabled={!resolution.trim() || closeMutation.isPending}
                  className="flex-1 px-3 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50">
                  Close Incident
                </button>
                <button onClick={() => setCloseModal(false)}
                  className="px-3 py-2 bg-surface-3 hover:bg-white/[0.04] text-gray-300 text-sm rounded-lg border border-white/[0.06] transition-colors">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="glass-card rounded-2xl">
          <div className="px-5 py-4 border-b border-white/[0.04]">
            <h3 className="text-sm font-semibold text-white">Timeline</h3>
          </div>
          <div className="p-5">
            {timelineEntries.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No timeline entries</p>
            ) : (
              <div className="space-y-4">
                {timelineEntries.map((entry) => (
                  <div key={entry.id} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full bg-surface-3 flex items-center justify-center shrink-0">
                        {entry.event_type === "created" && <AlertTriangle className="w-3 h-3 text-blue-400" />}
                        {entry.event_type === "acknowledged" && <CheckCircle2 className="w-3 h-3 text-green-400" />}
                        {entry.event_type === "closed" && <XCircle className="w-3 h-3 text-gray-400" />}
                        {entry.event_type === "comment" && <MessageSquare className="w-3 h-3 text-purple-400" />}
                        {!["created", "acknowledged", "closed", "comment"].includes(entry.event_type) && (
                          <Clock className="w-3 h-3 text-gray-400" />
                        )}
                      </div>
                      <div className="w-px flex-1 bg-surface-3 mt-1" />
                    </div>
                    <div className="pb-4">
                      <p className="text-sm text-white">{entry.description}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500 capitalize">{entry.event_type.replace("_", " ")}</span>
                        <span className="text-gray-700">·</span>
                        <span className="text-xs text-gray-500">{formatDate(entry.created_at)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add comment */}
            {isOpen && (
              <div className="flex gap-3 mt-4 pt-4 border-t border-white/[0.04]">
                <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
                  <User className="w-3 h-3 text-white" />
                </div>
                <div className="flex-1 flex gap-2">
                  <input type="text" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a comment..."
                    onKeyDown={(e) => { if (e.key === "Enter" && comment.trim()) commentMutation.mutate(); }}
                    className="flex-1 bg-surface-3 border border-white/[0.06] rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
                  <button onClick={() => commentMutation.mutate()} disabled={!comment.trim() || commentMutation.isPending}
                    className="px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm rounded-lg transition-colors disabled:opacity-50">
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
