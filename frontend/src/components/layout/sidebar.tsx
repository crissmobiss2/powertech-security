"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Shield, AlertTriangle, Monitor, Ticket, Cpu, Radio,
  Users, FileText, Settings, LogOut, ChevronRight, Zap,
  Eye, Camera, ScanFace, Fingerprint, Activity,
} from "lucide-react";
import { clearTokens } from "@/lib/auth";
import { useRouter } from "next/navigation";

const mainNav = [
  { name: "Dashboard", href: "/dashboard", icon: Monitor },
  { name: "Incidents", href: "/incidents", icon: AlertTriangle },
  { name: "Alerts", href: "/alerts", icon: Radio },
  { name: "Tickets", href: "/tickets", icon: Ticket },
  { name: "Assets", href: "/assets", icon: Cpu },
  { name: "Playbooks", href: "/playbooks", icon: Zap },
  { name: "Clients", href: "/clients", icon: Users },
  { name: "Reports", href: "/reports", icon: FileText },
];

const visionNav = [
  { name: "AI Vision", href: "/dashboard/vision", icon: Eye },
  { name: "Live Analysis", href: "/dashboard/vision/live", icon: Activity },
  { name: "Cameras", href: "/dashboard/vision/cameras", icon: Camera },
  { name: "Personnel", href: "/dashboard/vision/persons", icon: ScanFace },
  { name: "Biometrics", href: "/biometrics", icon: Fingerprint },
];

function NavItem({ item, active }: { item: typeof mainNav[0]; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200 relative",
        active
          ? "text-white"
          : "text-gray-500 hover:text-gray-200 hover:bg-white/[0.03]"
      )}
    >
      {active && (
        <div className="absolute inset-0 bg-gradient-to-r from-brand-600/20 to-brand-600/5 rounded-xl border border-brand-500/20" />
      )}
      <div className={cn(
        "relative w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 shrink-0",
        active
          ? "bg-brand-600 shadow-lg shadow-brand-600/25"
          : "bg-surface-2 group-hover:bg-surface-3"
      )}>
        <item.icon className={cn("w-4 h-4 relative z-10", active ? "text-white" : "text-gray-500 group-hover:text-gray-300")} />
      </div>
      <span className="relative z-10 flex-1">{item.name}</span>
      {active && <ChevronRight className="w-3 h-3 relative z-10 text-brand-300/60" />}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname === href || pathname.startsWith(href + "/");
  }

  function handleLogout() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <div className="flex flex-col h-full w-[260px] shrink-0 bg-surface-1 border-r border-white/[0.04] relative">
      {/* Subtle gradient accent */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-500/30 to-transparent" />

      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-600/20">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-white tracking-tight">Power Tech</h2>
          <p className="text-[10px] text-brand-400/60 uppercase tracking-[0.15em] font-semibold">Security Ops</p>
        </div>
      </div>

      {/* System status bar */}
      <div className="mx-4 mb-3 px-3 py-2 rounded-lg bg-surface-2 border border-white/[0.04] flex items-center gap-2">
        <Activity className="w-3 h-3 text-emerald-400" />
        <span className="text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">System Online</span>
        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
        {mainNav.map((item) => (
          <NavItem key={item.name} item={item} active={isActive(item.href)} />
        ))}

        {/* AI & Vision section */}
        <div className="mt-5 mb-2 pt-4 border-t border-white/[0.04]">
          <div className="flex items-center gap-2 px-3 mb-2">
            <div className="w-1 h-3 rounded-full bg-gradient-to-b from-brand-400 to-brand-600" />
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-[0.15em]">AI & Vision</p>
          </div>
        </div>
        {visionNav.map((item) => (
          <NavItem key={item.name} item={item} active={isActive(item.href)} />
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 pt-3 border-t border-white/[0.04] space-y-0.5">
        <NavItem
          item={{ name: "Settings", href: "/settings", icon: Settings }}
          active={isActive("/settings")}
        />
        <button
          onClick={handleLogout}
          className="w-full group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium text-gray-500 hover:text-red-400 hover:bg-red-500/[0.06] transition-all duration-200"
        >
          <div className="w-8 h-8 rounded-lg bg-surface-2 group-hover:bg-red-500/10 flex items-center justify-center transition-all">
            <LogOut className="w-4 h-4" />
          </div>
          <span>Sign out</span>
        </button>
      </div>
    </div>
  );
}
