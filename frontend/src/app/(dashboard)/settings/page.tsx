"use client";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { getClaims } from "@/lib/auth";
import type { TokenClaims } from "@/types";
import { User, Bell, Shield, Database, Key, Save, Check } from "lucide-react";

function SectionCard({ title, icon: Icon, children }: { title: string; icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="glass-card rounded-2xl">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.04]">
        <Icon className="w-4 h-4 text-gray-400" />
        <h2 className="text-sm font-semibold text-white">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-b-0">
      <label className="text-sm text-gray-400">{label}</label>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const [claims, setClaims] = useState<TokenClaims | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setClaims(getClaims());
  }, []);

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.auth.me(),
  });

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      <Header title="Settings" subtitle="Platform configuration" />
      <main className="flex-1 p-6 space-y-6 max-w-3xl">
        {/* Profile */}
        <SectionCard title="Profile" icon={User}>
          <FieldRow label="Email">
            <span className="text-sm text-white">{user?.email ?? "—"}</span>
          </FieldRow>
          <FieldRow label="Name">
            <span className="text-sm text-white">{user?.full_name ?? "—"}</span>
          </FieldRow>
          <FieldRow label="Role">
            <span className="text-xs px-2 py-0.5 bg-blue-950 text-blue-400 rounded-full font-medium capitalize">
              {user?.role?.replace("_", " ") ?? "—"}
            </span>
          </FieldRow>
          <FieldRow label="Tenant ID">
            <span className="text-xs text-gray-500 font-mono">{user?.tenant_id ?? "—"}</span>
          </FieldRow>
        </SectionCard>

        {/* Notifications */}
        <SectionCard title="Notification Preferences" icon={Bell}>
          <FieldRow label="Email notifications">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-white/[0.06] bg-surface-3 text-blue-600 focus:ring-blue-500 focus:ring-offset-surface-0" />
          </FieldRow>
          <FieldRow label="SMS alerts (critical only)">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-white/[0.06] bg-surface-3 text-blue-600 focus:ring-blue-500 focus:ring-offset-surface-0" />
          </FieldRow>
          <FieldRow label="Push notifications">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-white/[0.06] bg-surface-3 text-blue-600 focus:ring-blue-500 focus:ring-offset-surface-0" />
          </FieldRow>
          <FieldRow label="In-app alerts">
            <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-white/[0.06] bg-surface-3 text-blue-600 focus:ring-blue-500 focus:ring-offset-surface-0" />
          </FieldRow>
        </SectionCard>

        {/* Security */}
        <SectionCard title="Security" icon={Shield}>
          <FieldRow label="Two-factor authentication">
            <span className="text-xs px-2 py-0.5 bg-surface-3 text-gray-400 rounded-full">Not enabled</span>
            <button className="text-xs px-3 py-1 bg-surface-3 hover:bg-white/[0.04] text-gray-300 rounded-lg border border-white/[0.06] transition-colors">
              Enable
            </button>
          </FieldRow>
          <FieldRow label="Password">
            <button className="text-xs px-3 py-1 bg-surface-3 hover:bg-white/[0.04] text-gray-300 rounded-lg border border-white/[0.06] transition-colors">
              Change password
            </button>
          </FieldRow>
          <FieldRow label="Active sessions">
            <span className="text-sm text-gray-400">1 active</span>
            <button className="text-xs px-3 py-1 bg-surface-3 hover:bg-red-900 text-gray-300 hover:text-red-300 rounded-lg border border-white/[0.06] hover:border-red-700 transition-colors">
              Revoke all
            </button>
          </FieldRow>
        </SectionCard>

        {/* System (super_admin only) */}
        {claims?.role === "super_admin" && (
          <SectionCard title="System Configuration" icon={Database}>
            <FieldRow label="Environment">
              <span className="text-xs px-2 py-0.5 bg-yellow-950 text-yellow-400 rounded-full font-medium">Development</span>
            </FieldRow>
            <FieldRow label="API Version">
              <span className="text-sm text-gray-400">v1</span>
            </FieldRow>
            <FieldRow label="Database">
              <span className="text-sm text-gray-400">PostgreSQL 16</span>
            </FieldRow>
            <FieldRow label="Cache">
              <span className="text-sm text-gray-400">Redis 7</span>
            </FieldRow>
          </SectionCard>
        )}

        {/* Permissions */}
        <SectionCard title="Permissions" icon={Key}>
          <div className="flex flex-wrap gap-1.5">
            {(claims?.permissions ?? []).map((perm) => (
              <span key={perm} className="text-[11px] px-2 py-0.5 bg-surface-3 text-gray-400 rounded font-mono">
                {perm}
              </span>
            ))}
          </div>
        </SectionCard>

        {/* Save */}
        <div className="flex justify-end">
          <button onClick={handleSave}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-colors">
            {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            {saved ? "Saved" : "Save Changes"}
          </button>
        </div>
      </main>
    </div>
  );
}
