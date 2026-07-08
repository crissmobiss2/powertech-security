"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Search, X, AlertTriangle, Cpu, Ticket, ScanFace, ChevronRight } from "lucide-react";
import { getClaims } from "@/lib/auth";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

interface SearchResult {
  id: string;
  label: string;
  sublabel?: string;
  type: "incident" | "asset" | "ticket" | "person";
  href: string;
  badge?: string;
  badgeColor?: string;
}

const TYPE_ICON: Record<string, React.ElementType> = {
  incident: AlertTriangle,
  asset: Cpu,
  ticket: Ticket,
  person: ScanFace,
};

const TYPE_COLOR: Record<string, string> = {
  incident: "text-red-400",
  asset: "text-blue-400",
  ticket: "text-purple-400",
  person: "text-emerald-400",
};

export function Header({ title, subtitle }: HeaderProps) {
  const claims = getClaims();
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const roleDisplay: Record<string, string> = {
    super_admin: "System Admin",
    client_admin: "Client Admin",
    security_director: "Security Director",
    soc_analyst: "SOC Analyst",
    it_engineer: "IT Engineer",
    field_technician: "Field Tech",
    site_supervisor: "Site Supervisor",
    executive: "Executive",
    auditor: "Auditor",
  };

  const roleColors: Record<string, string> = {
    super_admin: "from-red-500 to-red-700",
    client_admin: "from-brand-500 to-brand-700",
    security_director: "from-purple-500 to-purple-700",
    soc_analyst: "from-cyan-500 to-cyan-700",
    it_engineer: "from-emerald-500 to-emerald-700",
    field_technician: "from-orange-500 to-orange-700",
    site_supervisor: "from-yellow-500 to-yellow-700",
    executive: "from-gold-500 to-gold-700",
    auditor: "from-gray-400 to-gray-600",
  };

  const openSearch = useCallback(() => {
    setSearchOpen(true);
    setQuery("");
    setResults([]);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  const closeSearch = useCallback(() => {
    setSearchOpen(false);
    setQuery("");
    setResults([]);
    setSelectedIdx(0);
  }, []);

  // Cmd/Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchOpen ? closeSearch() : openSearch();
      }
      if (e.key === "Escape" && searchOpen) closeSearch();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [searchOpen, openSearch, closeSearch]);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const [incidents, assets, tickets, persons] = await Promise.allSettled([
        api.incidents.list({ search: q, limit: 5 }),
        api.assets.list({ search: q, limit: 5 }),
        api.tickets.list({ search: q, limit: 5 }),
        api.vision.persons.list({ search: q, limit: 5 }),
      ]);

      const out: SearchResult[] = [];

      if (incidents.status === "fulfilled") {
        for (const inc of incidents.value?.data ?? []) {
          out.push({
            id: inc.id,
            label: inc.title,
            sublabel: inc.type,
            type: "incident",
            href: `/incidents/${inc.id}`,
            badge: inc.severity,
            badgeColor: inc.severity === "critical" ? "text-red-400" : inc.severity === "high" ? "text-orange-400" : "text-yellow-400",
          });
        }
      }
      if (assets.status === "fulfilled") {
        for (const a of assets.value?.data ?? []) {
          out.push({
            id: a.id,
            label: a.name,
            sublabel: `${a.type} · ${a.status}`,
            type: "asset",
            href: `/assets`,
            badge: a.status,
          });
        }
      }
      if (tickets.status === "fulfilled") {
        for (const t of tickets.value?.data ?? []) {
          out.push({
            id: t.id,
            label: t.title,
            sublabel: t.type,
            type: "ticket",
            href: `/tickets/${t.id}`,
            badge: t.priority,
          });
        }
      }
      if (persons.status === "fulfilled") {
        for (const p of persons.value?.data ?? []) {
          out.push({
            id: p.id,
            label: `${p.first_name} ${p.last_name}`,
            sublabel: `${p.person_type} · ${p.department ?? ""}`,
            type: "person",
            href: `/dashboard/vision/persons`,
            badge: p.access_level,
          });
        }
      }

      setResults(out);
      setSelectedIdx(0);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(q), 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && results[selectedIdx]) {
      navigateTo(results[selectedIdx].href);
    }
  };

  const navigateTo = (href: string) => {
    closeSearch();
    router.push(href);
  };

  return (
    <>
      <header className="h-16 border-b border-white/[0.04] bg-surface-1/80 backdrop-blur-xl flex items-center justify-between px-6 shrink-0 relative">
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-500/10 to-transparent" />

        <div>
          <h1 className="text-[15px] font-bold text-white tracking-tight">{title}</h1>
          {subtitle && <p className="text-[11px] text-gray-500 mt-0.5">{subtitle}</p>}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={openSearch}
            className="flex items-center gap-2.5 px-3.5 py-2 bg-surface-2 border border-white/[0.06] rounded-xl text-gray-500 text-xs hover:border-white/[0.1] transition-all group"
          >
            <Search className="w-3.5 h-3.5 group-hover:text-gray-400" />
            <span className="hidden sm:inline text-gray-600">Search everything...</span>
            <div className="hidden sm:flex items-center gap-0.5">
              <kbd className="text-[10px] bg-surface-3 px-1.5 py-0.5 rounded font-mono text-gray-600 border border-white/[0.04]">⌘</kbd>
              <kbd className="text-[10px] bg-surface-3 px-1.5 py-0.5 rounded font-mono text-gray-600 border border-white/[0.04]">K</kbd>
            </div>
          </button>

          <button className="relative p-2.5 text-gray-500 hover:text-white rounded-xl hover:bg-white/[0.04] transition-all">
            <Bell className="w-4 h-4" />
            <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full ring-2 ring-surface-1" />
          </button>

          <div className="flex items-center gap-3 pl-2 ml-1 border-l border-white/[0.06]">
            <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${roleColors[claims?.role ?? ""] ?? "from-brand-500 to-brand-700"} flex items-center justify-center shadow-lg`}>
              <span className="text-[11px] font-bold text-white uppercase">
                {claims?.role?.[0] ?? "U"}
              </span>
            </div>
            <div className="hidden md:block">
              <p className="text-xs font-semibold text-white leading-tight">
                {roleDisplay[claims?.role ?? ""] ?? "Operator"}
              </p>
              <p className="text-[10px] text-gray-600 leading-tight" suppressHydrationWarning>
                {claims?.tenant_id ? `Tenant ${claims.tenant_id.slice(0, 8)}` : "Active"}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Global Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[12vh]">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeSearch} />
          <div className="relative w-full max-w-xl glass-card rounded-2xl shadow-2xl">

            {/* Input */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.06]">
              <Search className="w-4 h-4 text-gray-500 shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={handleQueryChange}
                onKeyDown={handleKeyDown}
                placeholder="Search incidents, assets, tickets, personnel..."
                className="flex-1 bg-transparent text-sm text-white placeholder-gray-600 focus:outline-none"
              />
              {isSearching && (
                <span className="text-[10px] text-gray-600 font-mono">searching...</span>
              )}
              <button onClick={closeSearch} className="p-1 text-gray-600 hover:text-white transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Results */}
            <div className="max-h-80 overflow-y-auto">
              {query.length < 2 ? (
                <div className="p-5 text-center">
                  <p className="text-xs text-gray-600">Type at least 2 characters to search across all modules</p>
                  <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-gray-700">
                    {["Incidents", "Assets", "Tickets", "Personnel"].map((t) => (
                      <span key={t} className="flex items-center gap-1">{t}</span>
                    ))}
                  </div>
                </div>
              ) : results.length === 0 && !isSearching ? (
                <div className="p-5 text-center">
                  <p className="text-xs text-gray-600">No results for "{query}"</p>
                </div>
              ) : (
                <div className="py-2">
                  {results.map((result, i) => {
                    const Icon = TYPE_ICON[result.type];
                    const color = TYPE_COLOR[result.type];
                    return (
                      <button
                        key={`${result.type}-${result.id}`}
                        onClick={() => navigateTo(result.href)}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                          i === selectedIdx ? "bg-white/[0.04]" : "hover:bg-white/[0.02]",
                        )}
                      >
                        <div className={cn("w-7 h-7 rounded-lg bg-surface-3 flex items-center justify-center shrink-0", color)}>
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white truncate">{result.label}</p>
                          {result.sublabel && (
                            <p className="text-[10px] text-gray-500 truncate capitalize">{result.sublabel}</p>
                          )}
                        </div>
                        {result.badge && (
                          <span className={cn("text-[10px] uppercase font-semibold", result.badgeColor ?? "text-gray-500")}>
                            {result.badge}
                          </span>
                        )}
                        <ChevronRight className="w-3.5 h-3.5 text-gray-700 shrink-0" />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer hints */}
            <div className="px-4 py-2.5 border-t border-white/[0.04] flex items-center gap-4 text-[10px] text-gray-600">
              <span><kbd className="bg-surface-3 px-1 py-0.5 rounded font-mono">↑↓</kbd> navigate</span>
              <span><kbd className="bg-surface-3 px-1 py-0.5 rounded font-mono">↵</kbd> open</span>
              <span><kbd className="bg-surface-3 px-1 py-0.5 rounded font-mono">Esc</kbd> close</span>
              <span className="ml-auto">{results.length > 0 && `${results.length} results`}</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
