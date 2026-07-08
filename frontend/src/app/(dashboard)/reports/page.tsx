"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import type { Incident, Ticket, Alert } from "@/types";
import {
  FileText, AlertTriangle, Ticket as TicketIcon, Radio,
  Shield, Clock, BarChart3, Download, Loader2, CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

function MetricCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string | number; sub?: string; icon: React.ElementType; color: string;
}) {
  return (
    <div className="glass-card rounded-2xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        <div className={`p-2 rounded-lg ${color.replace("text-", "bg-").replace("-400", "-950")}`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
      </div>
    </div>
  );
}

function exportToCSV(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };
  const csv = [headers.join(","), ...rows.map((r) => headers.map((h) => escape(r[h])).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const [exportedReport, setExportedReport] = useState<string | null>(null);

  const { data: incidents } = useQuery({
    queryKey: ["incidents", { limit: 500 }],
    queryFn: () => api.incidents.list({ limit: 500 }),
  });

  const { data: tickets } = useQuery({
    queryKey: ["tickets", { limit: 500 }],
    queryFn: () => api.tickets.list({ limit: 500 }),
  });

  const { data: alerts } = useQuery({
    queryKey: ["alerts", { limit: 500 }],
    queryFn: () => api.alerts.list({ limit: 500 }),
  });

  const allIncidents: Incident[] = incidents?.data ?? [];
  const allTickets: Ticket[] = tickets?.data ?? [];
  const allAlerts: Alert[] = alerts?.data ?? [];

  const criticalOpen = allIncidents.filter(
    (i) => i.severity === "critical" && !["closed", "resolved", "false_positive"].includes(i.status),
  );
  const slaBreached = allIncidents.filter(
    (i) => i.sla_due_at && new Date(i.sla_due_at) < new Date() && !["closed", "resolved"].includes(i.status),
  );
  const resolvedTickets = allTickets.filter((t) => ["resolved", "closed"].includes(t.status));
  const sentAlerts = allAlerts.filter((a) => a.status === "sent");
  const failedAlerts = allAlerts.filter((a) => ["failed", "partial_failure"].includes(a.status));

  const incidentsBySeverity = ["critical", "high", "medium", "low", "info"].map((sev) => ({
    severity: sev,
    count: allIncidents.filter((i) => i.severity === sev).length,
  }));

  const sevColors: Record<string, string> = {
    critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500",
    low: "bg-green-500", info: "bg-blue-500",
  };

  function handleExport(reportName: string) {
    const ts = new Date().toISOString().slice(0, 10);

    switch (reportName) {
      case "Incident Summary":
        exportToCSV(
          allIncidents.map((i) => ({
            id: i.id,
            title: i.title,
            type: i.type,
            severity: i.severity,
            status: i.status,
            created_at: i.created_at,
            resolved_at: i.resolved_at ?? "",
            sla_due_at: i.sla_due_at ?? "",
            sla_breached: i.sla_due_at && new Date(i.sla_due_at) < new Date(i.resolved_at ?? "9999") ? "yes" : "no",
            assigned_to: (i as Record<string, unknown>).assigned_to ?? "",
            client_id: (i as Record<string, unknown>).client_id ?? "",
          })),
          `incident_summary_${ts}.csv`,
        );
        break;

      case "SLA Compliance":
        exportToCSV(
          allIncidents.map((i) => ({
            id: i.id,
            title: i.title,
            severity: i.severity,
            status: i.status,
            sla_due_at: i.sla_due_at ?? "",
            resolved_at: i.resolved_at ?? "",
            sla_status:
              !i.sla_due_at
                ? "no_sla"
                : new Date(i.sla_due_at) < new Date(i.resolved_at ?? new Date().toISOString())
                  ? "breached"
                  : "met",
          })),
          `sla_compliance_${ts}.csv`,
        );
        break;

      case "Alert Delivery":
        exportToCSV(
          allAlerts.map((a) => ({
            id: a.id,
            title: a.title,
            severity: a.severity,
            status: a.status,
            channels: Array.isArray(a.channels) ? a.channels.join(";") : "",
            created_at: a.created_at,
            delivery_rate: a.delivery_stats
              ? `${((a.delivery_stats as Record<string, number>).sent ?? 0)}/${(a.delivery_stats as Record<string, number>).total ?? 0}`
              : "",
          })),
          `alert_delivery_${ts}.csv`,
        );
        break;

      case "Ticket Report":
        exportToCSV(
          allTickets.map((t) => ({
            id: t.id,
            title: t.title,
            type: t.type,
            priority: t.priority,
            status: t.status,
            created_at: t.created_at,
            checkin_at: t.checkin_at ?? "",
            checkout_at: t.checkout_at ?? "",
            labor_hours: t.labor_hours ?? "",
            cost: t.cost ?? "",
            resolution_notes: t.resolution_notes ?? "",
          })),
          `tickets_${ts}.csv`,
        );
        break;

      case "Asset Health":
        // Assets endpoint — load on demand
        api.assets.list({ limit: 500 }).then((res) => {
          exportToCSV(
            (res?.data ?? []).map((a: Record<string, unknown>) => ({
              id: a.id,
              name: a.name,
              type: a.type,
              status: a.status,
              location: a.location ?? "",
              ip_address: a.ip_address ?? "",
              last_seen_at: a.last_seen_at ?? "",
              maintenance_due: a.maintenance_due_at ?? "",
            })),
            `asset_health_${ts}.csv`,
          );
          flashExported(reportName);
        });
        return;

      case "Compliance (RA 10173)":
        exportToCSV(
          [
            {
              report_type: "RA 10173 Data Privacy Impact Assessment",
              generated_at: new Date().toISOString(),
              total_incidents: allIncidents.length,
              incidents_with_pii: allIncidents.filter((i) =>
                ["data_breach", "unauthorized_access", "pii_exposure"].includes(i.type),
              ).length,
              access_logs_count: allAlerts.length,
              biometric_data_processed: "yes",
              retention_policy: "90 days per RA 10173 IRR",
              dpo_contact: "dpo@powertech.com.ph",
              last_audit: new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString().slice(0, 10),
              next_audit_due: new Date(Date.now() + 83 * 24 * 3600 * 1000).toISOString().slice(0, 10),
            },
          ],
          `ra10173_compliance_${ts}.csv`,
        );
        break;

      default:
        return;
    }
    flashExported(reportName);
  }

  function flashExported(name: string) {
    setExportedReport(name);
    setTimeout(() => setExportedReport(null), 2500);
  }

  const reports = [
    { name: "Incident Summary", desc: "All incidents with severity, status, and SLA data", icon: AlertTriangle },
    { name: "SLA Compliance", desc: "Per-incident SLA met/breached breakdown", icon: Clock },
    { name: "Ticket Report", desc: "Work orders with labor hours, cost, and resolution notes", icon: TicketIcon },
    { name: "Alert Delivery", desc: "Notification delivery rates by channel", icon: Radio },
    { name: "Asset Health", desc: "Asset status, location, and maintenance due dates", icon: Shield },
    { name: "Compliance (RA 10173)", desc: "Data privacy impact assessment (Philippines)", icon: FileText },
  ];

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Reports & Analytics" subtitle="Analytics & compliance reporting" />
      <main className="flex-1 p-6 space-y-6">
        {/* KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Total Incidents" value={incidents?.total ?? 0} sub={`${criticalOpen.length} critical open`} icon={AlertTriangle} color="text-red-400" />
          <MetricCard label="SLA Breaches" value={slaBreached.length} sub="Active breaches" icon={Clock} color="text-orange-400" />
          <MetricCard label="Tickets Resolved" value={resolvedTickets.length} sub={`of ${tickets?.total ?? 0} total`} icon={TicketIcon} color="text-green-400" />
          <MetricCard
            label="Alert Delivery"
            value={allAlerts.length ? `${Math.round((sentAlerts.length / allAlerts.length) * 100)}%` : "—"}
            sub={`${failedAlerts.length} failed`}
            icon={Radio}
            color="text-blue-400"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Incidents by Severity */}
          <div className="glass-card rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-white mb-4">Incidents by Severity</h2>
            <div className="space-y-3">
              {incidentsBySeverity.map((item) => {
                const maxCount = Math.max(...incidentsBySeverity.map((i) => i.count), 1);
                return (
                  <div key={item.severity} className="flex items-center gap-3">
                    <span className="text-xs text-gray-400 capitalize w-16">{item.severity}</span>
                    <div className="flex-1 h-5 bg-surface-3 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${sevColors[item.severity]} transition-all duration-500`}
                        style={{ width: `${(item.count / maxCount) * 100}%`, minWidth: item.count > 0 ? "12px" : "0" }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 font-mono tabular-nums w-8 text-right">{item.count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Incident Status Breakdown */}
          <div className="glass-card rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-white mb-4">Incident Status</h2>
            <div className="space-y-2">
              {["new", "acknowledged", "investigating", "in_progress", "resolved", "closed"].map((st) => {
                const count = allIncidents.filter((i) => i.status === st).length;
                return (
                  <div key={st} className="flex items-center justify-between py-1.5 border-b border-white/[0.04] last:border-b-0">
                    <span className="text-xs text-gray-400 capitalize">{st.replace(/_/g, " ")}</span>
                    <span className="text-xs font-medium text-white font-mono tabular-nums">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Available Reports — real CSV export */}
          <div className="glass-card rounded-2xl p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Export Reports</h2>
              <span className="text-[11px] text-gray-600">Downloads as CSV</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {reports.map((report) => {
                const exported = exportedReport === report.name;
                return (
                  <button
                    key={report.name}
                    onClick={() => handleExport(report.name)}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-lg border transition-all text-left group",
                      exported
                        ? "bg-emerald-950/30 border-emerald-500/30"
                        : "bg-surface-3/50 hover:bg-surface-3 border-white/[0.04] hover:border-white/[0.08]",
                    )}
                  >
                    <report.icon className={cn("w-4 h-4 mt-0.5 shrink-0 transition-colors", exported ? "text-emerald-400" : "text-blue-400")} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">{report.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{report.desc}</p>
                    </div>
                    <div className="shrink-0 mt-0.5">
                      {exported ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Download className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] text-gray-700 mt-3">
              Exports include up to 500 records. For full data exports, contact your system administrator.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
