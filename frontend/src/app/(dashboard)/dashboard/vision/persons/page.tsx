"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { api } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import type { AuthorizedPerson, Client, PaginatedResponse } from "@/types";
import {
  Users, Plus, Search, ScanFace, Shield, UserCheck,
  UserX, Trash2, Edit3, ChevronLeft, ChevronRight, Eye, X, Loader2, Camera,
  CheckCircle2,
} from "lucide-react";

// ── Shared client dropdown hook ───────────────────────────────────────────────
function useClients() {
  return useQuery<PaginatedResponse<Client>>({
    queryKey: ["clients-all"],
    queryFn: () => api.clients.list({ limit: 100 }),
    staleTime: 60_000,
  });
}

// ── Shared form fields ────────────────────────────────────────────────────────
function PersonFormFields({
  form,
  set,
  clients,
}: {
  form: Record<string, string>;
  set: (field: string, value: string) => void;
  clients: Client[];
}) {
  return (
    <>
      {clients.length > 1 && (
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Client</label>
          <select value={form.client_id} onChange={(e) => set("client_id", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
            {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">First name *</label>
          <input value={form.first_name} onChange={(e) => set("first_name", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            placeholder="Juan" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Last name *</label>
          <input value={form.last_name} onChange={(e) => set("last_name", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            placeholder="Dela Cruz" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Type</label>
          <select value={form.person_type} onChange={(e) => set("person_type", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
            <option value="employee">Employee</option>
            <option value="contractor">Contractor</option>
            <option value="visitor">Visitor</option>
            <option value="vip">VIP</option>
            <option value="banned">Banned</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Access level</label>
          <select value={form.access_level} onChange={(e) => set("access_level", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
            <option value="restricted">Restricted</option>
            <option value="standard">Standard</option>
            <option value="elevated">Elevated</option>
            <option value="full">Full</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Employee ID</label>
          <input value={form.employee_id} onChange={(e) => set("employee_id", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            placeholder="EMP-001" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Department</label>
          <input value={form.department} onChange={(e) => set("department", e.target.value)}
            className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            placeholder="Operations" />
        </div>
      </div>
      <div>
        <label className="block text-xs text-gray-400 mb-1.5">Notes</label>
        <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)} rows={2}
          className="w-full bg-surface-1 border border-white/[0.06] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500 resize-none"
          placeholder="Optional notes..." />
      </div>
    </>
  );
}

// ── Add Person Modal ──────────────────────────────────────────────────────────
function AddPersonModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const { data: clientsData } = useClients();
  const clients = clientsData?.data ?? [];

  const [form, setForm] = useState({
    client_id: "",
    first_name: "",
    last_name: "",
    person_type: "employee",
    employee_id: "",
    department: "",
    access_level: "standard",
    notes: "",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    if (clients.length > 0 && !form.client_id) {
      setForm((f) => ({ ...f, client_id: clients[0].id }));
    }
  }, [clients]); // eslint-disable-line react-hooks/exhaustive-deps

  const createMutation = useMutation({
    mutationFn: (data: typeof form) =>
      api.vision.persons.create({ ...data, client_id: data.client_id || clients[0]?.id }),
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to create person");
    },
  });

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setError("");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass-card rounded-2xl w-full max-w-md mx-4 shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-base font-semibold text-white">Add authorized person</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          <PersonFormFields form={form} set={set} clients={clients} />
          {error && <p className="text-xs text-red-400 bg-red-950/50 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06]">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button
            onClick={() => createMutation.mutate(form)}
            disabled={createMutation.isPending || !form.first_name || !form.last_name}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Add person
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Edit Person Modal ─────────────────────────────────────────────────────────
function EditPersonModal({ person, onClose, onSuccess }: { person: AuthorizedPerson; onClose: () => void; onSuccess: () => void }) {
  const { data: clientsData } = useClients();
  const clients = clientsData?.data ?? [];

  const [form, setForm] = useState({
    client_id: person.client_id,
    first_name: person.first_name,
    last_name: person.last_name,
    person_type: person.person_type,
    employee_id: person.employee_id ?? "",
    department: person.department ?? "",
    access_level: person.access_level,
    notes: person.notes ?? "",
  });
  const [error, setError] = useState("");

  const updateMutation = useMutation({
    mutationFn: (data: typeof form) => api.vision.persons.update(person.id, data),
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Failed to update person");
    },
  });

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setError("");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass-card rounded-2xl w-full max-w-md mx-4 shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <div>
            <h2 className="text-base font-semibold text-white">Edit person</h2>
            <p className="text-xs text-gray-500 mt-0.5">{person.first_name} {person.last_name}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          <PersonFormFields form={form} set={set} clients={clients} />
          {error && <p className="text-xs text-red-400 bg-red-950/50 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06]">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button
            onClick={() => updateMutation.mutate(form)}
            disabled={updateMutation.isPending || !form.first_name || !form.last_name}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {updateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Face Enroll Modal ─────────────────────────────────────────────────────────
function FaceEnrollModal({ person, onClose, onSuccess }: { person: AuthorizedPerson; onClose: () => void; onSuccess: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [base64, setBase64] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const enrollMutation = useMutation({
    mutationFn: (image_base64: string) =>
      api.vision.persons.enroll(person.id, { image_base64, is_primary: person.face_encoding_count === 0 }),
    onSuccess: () => { setDone(true); onSuccess(); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Enrollment failed — check photo quality");
    },
  });

  function handleFile(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("Please select an image file");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Image must be under 10 MB");
      return;
    }
    setError("");
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      setPreview(dataUrl);
      // Strip the data:image/...;base64, prefix — API expects raw base64
      setBase64(dataUrl.split(",")[1]);
    };
    reader.readAsDataURL(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
        <div className="glass-card rounded-2xl w-full max-w-sm mx-4 shadow-2xl p-8 text-center">
          <div className="w-14 h-14 rounded-full bg-green-950 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-7 h-7 text-green-400" />
          </div>
          <h2 className="text-base font-semibold text-white mb-1">Face enrolled</h2>
          <p className="text-sm text-gray-400 mb-6">
            {person.first_name}&apos;s biometric profile has been updated.
          </p>
          <button onClick={onClose}
            className="w-full px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 text-white text-sm font-medium rounded-lg transition-all">
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass-card rounded-2xl w-full max-w-sm mx-4 shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <div>
            <h2 className="text-base font-semibold text-white">Enroll face</h2>
            <p className="text-xs text-gray-500 mt-0.5">{person.first_name} {person.last_name} · {person.face_encoding_count} encoding{person.face_encoding_count !== 1 ? "s" : ""}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          {/* Drop zone */}
          <div
            onClick={() => fileRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className={cn(
              "relative border-2 border-dashed rounded-xl cursor-pointer transition-colors flex items-center justify-center overflow-hidden",
              preview ? "border-transparent h-48" : "border-white/[0.10] hover:border-brand-500/50 h-36"
            )}
          >
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="Preview" className="w-full h-full object-cover" />
            ) : (
              <div className="text-center py-6 px-4">
                <Camera className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Drop a photo here or click to browse</p>
                <p className="text-xs text-gray-600 mt-1">Clear front-facing photo · JPG, PNG · Max 10 MB</p>
              </div>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />

          {preview && (
            <button onClick={() => { setPreview(null); setBase64(null); setError(""); }}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
              Remove photo
            </button>
          )}

          <div className="text-xs text-gray-600 space-y-1">
            <p className="font-medium text-gray-500">Tips for best results:</p>
            <p>· Face clearly visible, good lighting</p>
            <p>· No sunglasses or heavy obstructions</p>
            <p>· Recent photo matching current appearance</p>
          </div>

          {error && <p className="text-xs text-red-400 bg-red-950/50 px-3 py-2 rounded-lg">{error}</p>}
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06]">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button
            onClick={() => base64 && enrollMutation.mutate(base64)}
            disabled={!base64 || enrollMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {enrollMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            <ScanFace className="w-4 h-4" />
            Enroll face
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Badge helpers ─────────────────────────────────────────────────────────────
function personTypeBadge(type: string) {
  const map: Record<string, string> = {
    employee: "bg-blue-950 text-blue-400 border-blue-800",
    contractor: "bg-purple-950 text-purple-400 border-purple-800",
    visitor: "bg-surface-3 text-gray-300 border-white/[0.06]",
    vip: "bg-amber-950 text-amber-400 border-amber-800",
    banned: "bg-red-950 text-red-400 border-red-800",
  };
  return map[type] || "bg-surface-3 text-gray-400 border-white/[0.06]";
}

function accessBadge(level: string) {
  const map: Record<string, string> = {
    restricted: "text-red-400",
    standard: "text-gray-400",
    elevated: "text-yellow-400",
    full: "text-green-400",
  };
  return map[level] || "text-gray-400";
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function PersonsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editPerson, setEditPerson] = useState<AuthorizedPerson | null>(null);
  const [enrollPerson, setEnrollPerson] = useState<AuthorizedPerson | null>(null);
  const qc = useQueryClient();

  const params: Record<string, string | number> = { page, limit: 20 };
  if (search) params.search = search;
  if (typeFilter) params.person_type = typeFilter;
  if (statusFilter) params.status = statusFilter;

  const { data, isLoading } = useQuery<PaginatedResponse<AuthorizedPerson>>({
    queryKey: ["vision-persons", params],
    queryFn: () => api.vision.persons.list(params),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.vision.persons.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vision-persons"] }),
  });

  const persons = data?.data ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  function invalidate() {
    qc.invalidateQueries({ queryKey: ["vision-persons"] });
  }

  return (
    <div className="flex flex-col h-full overflow-auto bg-surface-0">
      {showAdd && (
        <AddPersonModal onClose={() => setShowAdd(false)} onSuccess={invalidate} />
      )}
      {editPerson && (
        <EditPersonModal person={editPerson} onClose={() => setEditPerson(null)} onSuccess={invalidate} />
      )}
      {enrollPerson && (
        <FaceEnrollModal person={enrollPerson} onClose={() => setEnrollPerson(null)} onSuccess={invalidate} />
      )}

      <Header title="Authorized Persons" subtitle="Authorized personnel registry" />
      <main className="flex-1 p-6 space-y-6">

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { type: "employee", Icon: UserCheck, label: "Employees" },
            { type: "contractor", Icon: Users, label: "Contractors" },
            { type: "visitor", Icon: Eye, label: "Visitors" },
            { type: "banned", Icon: UserX, label: "Banned" },
          ].map(({ type, Icon, label }) => {
            const count = persons.filter((p) => p.person_type === type).length;
            return (
              <div key={type} className="glass-card rounded-2xl p-4 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-surface-3">
                  <Icon className={cn("w-4 h-4", type === "banned" ? "text-red-400" : "text-blue-400")} />
                </div>
                <div>
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-lg font-bold text-white">{count}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Filters + Add button */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-full pl-9 pr-3 py-2 bg-surface-1 border border-white/[0.04] rounded-lg text-sm text-gray-300 focus:outline-none focus:border-blue-500"
            />
          </div>
          <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="bg-surface-1 border border-white/[0.04] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
            <option value="">All Types</option>
            <option value="employee">Employee</option>
            <option value="contractor">Contractor</option>
            <option value="visitor">Visitor</option>
            <option value="vip">VIP</option>
            <option value="banned">Banned</option>
          </select>
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="bg-surface-1 border border-white/[0.04] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="banned">Banned</option>
            <option value="expired">Expired</option>
          </select>
          <button
            onClick={() => setShowAdd(true)}
            className="ml-auto flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-sm font-medium rounded-lg transition-all"
          >
            <Plus className="w-4 h-4" />
            Add Person
          </button>
        </div>

        {/* Table */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-white/[0.04]">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium hidden md:table-cell">Employee ID</th>
                  <th className="px-5 py-3 font-medium hidden md:table-cell">Department</th>
                  <th className="px-5 py-3 font-medium">Access</th>
                  <th className="px-5 py-3 font-medium">Face Data</th>
                  <th className="px-5 py-3 font-medium hidden sm:table-cell">Status</th>
                  <th className="px-5 py-3 font-medium hidden lg:table-cell">Added</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {isLoading
                  ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      <td className="px-5 py-3.5"><div className="h-4 bg-surface-3 rounded w-36" /></td>
                      <td className="px-5 py-3.5"><div className="h-4 bg-surface-3 rounded w-20" /></td>
                      <td className="px-5 py-3.5 hidden md:table-cell"><div className="h-4 bg-surface-3 rounded w-20" /></td>
                      <td className="px-5 py-3.5 hidden md:table-cell"><div className="h-4 bg-surface-3 rounded w-24" /></td>
                      <td className="px-5 py-3.5"><div className="h-4 bg-surface-3 rounded w-16" /></td>
                      <td className="px-5 py-3.5"><div className="h-4 bg-surface-3 rounded w-20" /></td>
                      <td className="px-5 py-3.5 hidden sm:table-cell"><div className="h-4 bg-surface-3 rounded w-16" /></td>
                      <td className="px-5 py-3.5 hidden lg:table-cell"><div className="h-4 bg-surface-3 rounded w-24" /></td>
                      <td className="px-5 py-3.5" />
                    </tr>
                  ))
                  : persons.length === 0
                    ? (
                      <tr>
                        <td colSpan={9} className="px-5 py-16 text-center">
                          <Shield className="w-10 h-10 text-gray-700 mx-auto mb-3" />
                          <p className="text-gray-500 text-sm mb-1">No authorized persons found</p>
                          <p className="text-gray-600 text-xs mb-4">Add personnel to enable facial recognition access control</p>
                          <button onClick={() => setShowAdd(true)}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-surface-2 border border-white/[0.06] hover:border-white/[0.10] text-gray-300 text-sm font-medium rounded-lg transition-colors">
                            <Plus className="w-4 h-4" />Add first person
                          </button>
                        </td>
                      </tr>
                    )
                    : persons.map((p) => (
                      <tr key={p.id} className="hover:bg-white/[0.02] transition-colors group">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-surface-3 flex items-center justify-center shrink-0">
                              <span className="text-xs font-bold text-gray-400">
                                {p.first_name?.[0] ?? "?"}{p.last_name?.[0] ?? ""}
                              </span>
                            </div>
                            <p className="text-sm font-medium text-white">{p.first_name} {p.last_name}</p>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium capitalize", personTypeBadge(p.person_type))}>
                            {p.person_type}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-gray-400 font-mono text-xs hidden md:table-cell">{p.employee_id || "—"}</td>
                        <td className="px-5 py-3 text-gray-400 text-xs hidden md:table-cell">{p.department || "—"}</td>
                        <td className="px-5 py-3">
                          <span className={cn("text-xs font-medium uppercase", accessBadge(p.access_level))}>
                            {p.access_level}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-1.5">
                            <ScanFace className={cn("w-4 h-4", p.face_encoding_count > 0 ? "text-green-400" : "text-gray-600")} />
                            <span className={cn("text-xs", p.face_encoding_count > 0 ? "text-green-400" : "text-gray-600")}>
                              {p.face_encoding_count}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-3 hidden sm:table-cell">
                          <span className={cn(
                            "text-xs px-2 py-0.5 rounded-full border font-medium",
                            p.status === "active" ? "bg-green-950 text-green-400 border-green-800" :
                            p.status === "banned" ? "bg-red-950 text-red-400 border-red-800" :
                            "bg-surface-3 text-gray-400 border-white/[0.06]"
                          )}>
                            {p.status}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-xs text-gray-500 whitespace-nowrap hidden lg:table-cell">{formatDate(p.created_at)}</td>
                        <td className="px-5 py-3">
                          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => setEnrollPerson(p)}
                              className="p-1.5 text-gray-500 hover:text-blue-400 hover:bg-blue-950/50 rounded-lg transition-colors"
                              title="Enroll face"
                            >
                              <Camera className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setEditPerson(p)}
                              className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.04] rounded-lg transition-colors"
                              title="Edit person"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Delete ${p.first_name} ${p.last_name}? This removes all face encodings.`)) {
                                  deleteMutation.mutate(p.id);
                                }
                              }}
                              className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-950/50 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-white/[0.04]">
              <p className="text-xs text-gray-500">{total} person{total !== 1 ? "s" : ""}</p>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="p-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs text-gray-400">{page} / {pages}</span>
                <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}
                  className="p-1 text-gray-400 hover:text-white disabled:opacity-30 transition-colors">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
