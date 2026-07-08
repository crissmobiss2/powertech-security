"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, cn } from "@/lib/utils";
import type { Playbook } from "@/types";
import { Zap, Filter, RefreshCw, Plus, Play, ToggleLeft, ToggleRight } from "lucide-react";

const TRIGGER_OPTIONS = ["", "asset_offline", "incident_created", "incident_severity", "scheduled", "manual", "webhook", "threshold"];

function triggerLabel(trigger: string): string {
  const map: Record<string, string> = {
    asset_offline: "Asset Offline",
    incident_created: "Incident Created",
    incident_severity: "Severity Change",
    scheduled: "Scheduled",
    manual: "Manual",
    webhook: "Webhook",
    threshold: "Threshold",
  };
  return map[trigger] ?? trigger;
}

function triggerColor(trigger: string): string {
  const map: Record<string, string> = {
    asset_offline: "text-red-400 bg-red-950",
    incident_created: "text-orange-400 bg-orange-950",
    incident_severity: "text-yellow-400 bg-yellow-950",
    scheduled: "text-blue-400 bg-blue-950",
    manual: "text-purple-400 bg-purple-950",
    webhook: "text-cyan-400 bg-cyan-950",
    threshold: "text-pink-400 bg-pink-950",
  };
  return map[trigger] ?? "text-gray-400 bg-surface-3";
}

export default function PlaybooksPage() {
  const qc = useQueryClient();
  const [triggerType, setTriggerType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["playbooks", { trigger_type: triggerType, page }],
    queryFn: () =>
      api.playbooks.list({
        ...(triggerType && { trigger_type: triggerType }),
        page,
        limit: 20,
      }),
  });

  const executeMutation = useMutation({
    mutationFn: (id: string) => api.playbooks.execute(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["playbooks"] });
    },
  });

  const playbooks: Playbook[] = data?.data ?? [];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Playbooks" subtitle="Automated response workflows" />
      <main className="flex-1 p-6">
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <select value={triggerType} onChange={(e) => { setTriggerType(e.target.value); setPage(1); }}
              className="text-sm bg-surface-2 border border-white/[0.06] rounded-xl px-3 py-2 text-gray-300 focus:outline-none focus:border-blue-500">
              <option value="">All triggers</option>
              {TRIGGER_OPTIONS.filter(Boolean).map((t) => (<option key={t} value={t}>{triggerLabel(t)}</option>))}
            </select>
            <button onClick={() => refetch()} className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-surface-3 rounded-lg transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors">
            <Plus className="w-4 h-4" />
            Create Playbook
          </button>
        </div>

        {/* Playbook cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="glass-card rounded-2xl p-5 animate-pulse">
                <div className="h-4 bg-surface-3 rounded-lg w-48 mb-3" />
                <div className="h-3 bg-surface-3 rounded-lg w-full mb-2" />
                <div className="h-3 bg-surface-3 rounded-lg w-3/4" />
              </div>
            ))
          ) : playbooks.length === 0 ? (
            <div className="col-span-full flex flex-col items-center justify-center py-16">
              <Zap className="w-10 h-10 text-gray-700 mb-3" />
              <p className="text-gray-500 text-sm">No playbooks found</p>
              <p className="text-gray-600 text-xs mt-1">Create your first automated response playbook</p>
            </div>
          ) : (
            playbooks.map((pb) => (
              <div key={pb.id} className="glass-card rounded-2xl p-5 hover:border-white/[0.06] transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Zap className={cn("w-4 h-4", pb.enabled ? "text-blue-400" : "text-gray-600")} />
                    <h3 className="text-sm font-semibold text-white line-clamp-1">{pb.name}</h3>
                  </div>
                  {pb.enabled ? (
                    <span className="flex items-center gap-1 text-xs text-green-400">
                      <ToggleRight className="w-4 h-4" /> Active
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-gray-500">
                      <ToggleLeft className="w-4 h-4" /> Disabled
                    </span>
                  )}
                </div>

                {pb.description && (
                  <p className="text-xs text-gray-500 mb-3 line-clamp-2">{pb.description}</p>
                )}

                <div className="flex items-center gap-2 mb-3">
                  <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-medium", triggerColor(pb.trigger_type))}>
                    {triggerLabel(pb.trigger_type)}
                  </span>
                  <span className="text-xs text-gray-600">
                    {pb.actions.length} action{pb.actions.length !== 1 ? "s" : ""}
                  </span>
                </div>

                {/* Actions list */}
                <div className="space-y-1 mb-4">
                  {pb.actions.map((action, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-gray-400">
                      <span className="w-4 h-4 rounded-full bg-surface-3 flex items-center justify-center text-[9px] text-gray-500 shrink-0 font-mono">
                        {i + 1}
                      </span>
                      <span className="capitalize">{action.type.replace("_", " ")}</span>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-white/[0.04]">
                  <div className="text-xs text-gray-500">
                    <span className="font-mono tabular-nums">{pb.run_count}</span> runs
                    {pb.last_triggered_at && (
                      <span className="ml-2">Last: {timeAgo(pb.last_triggered_at)}</span>
                    )}
                  </div>
                  <button
                    onClick={() => executeMutation.mutate(pb.id)}
                    disabled={executeMutation.isPending}
                    className="flex items-center gap-1 text-xs px-2.5 py-1 bg-surface-3 hover:bg-blue-900 text-gray-300 hover:text-blue-300 rounded-lg border border-white/[0.06] hover:border-blue-700 transition-colors">
                    <Play className="w-3 h-3" />
                    Run
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {data && data.pages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-xs text-gray-500">
              Page {page} of {data.pages} ({data.total} playbooks)
            </p>
            <div className="flex gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                className="text-xs px-3 py-1.5 bg-surface-3 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-white/[0.04] transition-colors">Previous</button>
              <button onClick={() => setPage((p) => Math.min(data.pages, p + 1))} disabled={page === data.pages}
                className="text-xs px-3 py-1.5 bg-surface-3 border border-white/[0.06] rounded-lg text-gray-300 disabled:opacity-50 hover:bg-white/[0.04] transition-colors">Next</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
