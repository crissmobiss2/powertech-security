"use client";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { timeAgo, severityColor, statusColor } from "@/lib/utils";
import type { Incident, Ticket, Alert } from "@/types";
import {
  AlertTriangle, Cpu, Ticket as TicketIcon, Radio,
  Shield, Eye, Activity, TrendingUp, ArrowUpRight,
  Clock, Zap, ChevronRight,
} from "lucide-react";

function StatCard({
  label, value, icon: Icon, gradient, sub, trend,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  gradient: string;
  sub?: string;
  trend?: string;
}) {
  return (
    <div className="glass-card rounded-2xl p-5 group hover:border-white/[0.08] transition-all duration-300">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-[11px] text-gray-500 uppercase tracking-wider font-semibold">{label}</p>
          <div className="flex items-baseline gap-2 mt-2">
            <p className="text-3xl font-bold text-white tabular-nums">{value}</p>
            {trend && (
              <span className="flex items-center gap-0.5 text-[10px] font-semibold text-emerald-400">
                <TrendingUp className="w-3 h-3" />
                {trend}
              </span>
            )}
          </div>
          {sub && <p className="text-[11px] text-gray-600 mt-1">{sub}</p>}
        </div>
        <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-lg border font-semibold uppercase tracking-wider ${severityColor(severity)}`}>
      {severity}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-lg font-semibold ${statusColor(status)}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function SectionCard({
  title, viewAllHref, emptyIcon: EmptyIcon, emptyText, children,
}: {
  title: string;
  viewAllHref: string;
  emptyIcon: React.ElementType;
  emptyText: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.04]">
        <h2 className="text-sm font-bold text-white">{title}</h2>
        <a href={viewAllHref} className="flex items-center gap-1 text-[11px] text-brand-400 hover:text-brand-300 font-medium transition-colors">
          View all
          <ArrowUpRight className="w-3 h-3" />
        </a>
      </div>
      {children}
    </div>
  );
}

export default function DashboardPage() {
  const { data: incidents } = useQuery({
    queryKey: ["incidents", { status: "new,acknowledged,investigating,in_progress", limit: 5 }],
    queryFn: () => api.incidents.list({ limit: 5 }),
  });

  const { data: offlineAssets } = useQuery({
    queryKey: ["assets", { status: "offline", limit: 5 }],
    queryFn: () => api.assets.list({ status: "offline", limit: 5 }),
  });

  const { data: tickets } = useQuery({
    queryKey: ["tickets", { status: "open,assigned,in_progress", limit: 5 }],
    queryFn: () => api.tickets.list({ limit: 5 }),
  });

  const { data: alerts } = useQuery({
    queryKey: ["alerts", { limit: 5 }],
    queryFn: () => api.alerts.list({ limit: 5 }),
  });

  const openIncidents = incidents?.total ?? 0;
  const criticalCount = (incidents?.data as Incident[] ?? []).filter(
    (i) => i.severity === "critical"
  ).length;

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Security Operations Center" subtitle="Real-time security monitoring & response" />

      <main className="flex-1 p-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Open Incidents"
            value={openIncidents}
            icon={AlertTriangle}
            gradient="from-red-500 to-red-700"
            sub={`${criticalCount} critical`}
          />
          <StatCard
            label="Assets Offline"
            value={offlineAssets?.total ?? 0}
            icon={Cpu}
            gradient="from-orange-500 to-orange-700"
          />
          <StatCard
            label="Open Tickets"
            value={tickets?.total ?? 0}
            icon={TicketIcon}
            gradient="from-brand-500 to-brand-700"
          />
          <StatCard
            label="Alerts Today"
            value={alerts?.total ?? 0}
            icon={Radio}
            gradient="from-purple-500 to-purple-700"
          />
        </div>

        {/* Quick actions */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: "New Incident", href: "/incidents", icon: AlertTriangle, color: "text-red-400 bg-red-500/10 border-red-500/20" },
            { label: "AI Vision", href: "/dashboard/vision", icon: Eye, color: "text-brand-400 bg-brand-500/10 border-brand-500/20" },
            { label: "Run Playbook", href: "/playbooks", icon: Zap, color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20" },
            { label: "View Reports", href: "/reports", icon: Activity, color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
          ].map((action) => (
            <a
              key={action.label}
              href={action.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${action.color} hover:opacity-80 transition-opacity`}
            >
              <action.icon className="w-4 h-4" />
              <span className="text-xs font-semibold">{action.label}</span>
              <ChevronRight className="w-3 h-3 ml-auto opacity-40" />
            </a>
          ))}
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Active Incidents */}
          <SectionCard title="Active Incidents" viewAllHref="/incidents" emptyIcon={Shield} emptyText="No active incidents">
            <div className="divide-y divide-white/[0.04]">
              {(incidents?.data as Incident[] ?? []).length === 0 ? (
                <div className="px-5 py-10 text-center">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                    <Shield className="w-6 h-6 text-emerald-500/60" />
                  </div>
                  <p className="text-sm text-gray-500">No active incidents</p>
                  <p className="text-[11px] text-gray-700 mt-1">All clear across all sites</p>
                </div>
              ) : (
                (incidents?.data as Incident[] ?? []).map((incident) => (
                  <a key={incident.id} href={`/incidents/${incident.id}`}
                    className="flex items-start gap-3 px-5 py-3.5 hover:bg-white/[0.02] transition-colors group">
                    <div className={`w-1.5 rounded-full self-stretch mt-1 ${
                      incident.severity === "critical" ? "bg-red-500" : incident.severity === "high" ? "bg-orange-500" : "bg-yellow-500"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate group-hover:text-brand-300 transition-colors">{incident.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Clock className="w-3 h-3 text-gray-600" />
                        <p className="text-[11px] text-gray-600">{timeAgo(incident.created_at)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <SeverityBadge severity={incident.severity} />
                      <StatusBadge status={incident.status} />
                    </div>
                  </a>
                ))
              )}
            </div>
          </SectionCard>

          {/* Open Tickets */}
          <SectionCard title="Open Tickets" viewAllHref="/tickets" emptyIcon={TicketIcon} emptyText="No open tickets">
            <div className="divide-y divide-white/[0.04]">
              {(tickets?.data as Ticket[] ?? []).length === 0 ? (
                <div className="px-5 py-10 text-center">
                  <div className="w-12 h-12 rounded-2xl bg-brand-500/10 flex items-center justify-center mx-auto mb-3">
                    <TicketIcon className="w-6 h-6 text-brand-500/60" />
                  </div>
                  <p className="text-sm text-gray-500">No open tickets</p>
                </div>
              ) : (
                (tickets?.data as Ticket[] ?? []).map((ticket) => (
                  <div key={ticket.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{ticket.title}</p>
                      <p className="text-[11px] text-gray-600 mt-1">{timeAgo(ticket.created_at)}</p>
                    </div>
                    <StatusBadge status={ticket.status} />
                  </div>
                ))
              )}
            </div>
          </SectionCard>

          {/* Offline Assets */}
          <SectionCard title="Offline Assets" viewAllHref="/assets?status=offline" emptyIcon={Cpu} emptyText="All assets online">
            <div className="divide-y divide-white/[0.04]">
              {(offlineAssets?.data ?? []).length === 0 ? (
                <div className="px-5 py-10 text-center">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                    <Cpu className="w-6 h-6 text-emerald-500/60" />
                  </div>
                  <p className="text-sm text-gray-500">All assets online</p>
                  <p className="text-[11px] text-gray-700 mt-1">Infrastructure fully operational</p>
                </div>
              ) : (
                (offlineAssets?.data ?? []).map((asset: { id: string; name: string; type: string; last_seen_at: string | null }) => (
                  <div key={asset.id} className="flex items-center gap-3 px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
                    <div className="relative">
                      <div className="w-2 h-2 rounded-full bg-red-500" />
                      <div className="absolute inset-0 w-2 h-2 rounded-full bg-red-500 animate-ping opacity-40" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">{asset.name}</p>
                      <p className="text-[11px] text-gray-600 capitalize">{asset.type.replace("_", " ")}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[11px] text-red-400 font-semibold">Offline</p>
                      <p className="text-[10px] text-gray-700">{timeAgo(asset.last_seen_at)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>

          {/* Recent Alerts */}
          <SectionCard title="Recent Alerts" viewAllHref="/alerts" emptyIcon={Radio} emptyText="No recent alerts">
            <div className="divide-y divide-white/[0.04]">
              {(alerts?.data as Alert[] ?? []).length === 0 ? (
                <div className="px-5 py-10 text-center">
                  <div className="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center mx-auto mb-3">
                    <Radio className="w-6 h-6 text-purple-500/60" />
                  </div>
                  <p className="text-sm text-gray-500">No recent alerts</p>
                </div>
              ) : (
                (alerts?.data as Alert[] ?? []).map((alert) => (
                  <div key={alert.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{alert.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <p className="text-[11px] text-gray-600">{timeAgo(alert.created_at)}</p>
                        <span className="text-gray-800">&middot;</span>
                        <p className="text-[11px] text-gray-600">{alert.acknowledged_count}/{alert.total_recipients} acked</p>
                      </div>
                    </div>
                    <SeverityBadge severity={alert.severity} />
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>
      </main>
    </div>
  );
}
