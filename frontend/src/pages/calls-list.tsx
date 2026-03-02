import { useState, useCallback, useRef, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import {
  Upload,
  Search,
  X,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  Loader2,
  AlertCircle,
  FileAudio,
  Phone,
  SmilePlus,
  Frown,
  Meh,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getCalls, uploadCall, getAgents } from "@/lib/api";
import type {
  CallFilters,
  CallsListResponse,
  CallStatus,
  IntentClassification,
  AgentSummary,
} from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Calls List Page
// ────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function CallsListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  // Upload modal
  const [showUpload, setShowUpload] = useState(
    searchParams.get("upload") === "true",
  );

  // Filters state
  const [filters, setFilters] = useState<CallFilters>({
    agent_id: searchParams.get("agent_id") ?? undefined,
    date_from: searchParams.get("date_from") ?? undefined,
    date_to: searchParams.get("date_to") ?? undefined,
    score_min: searchParams.get("score_min")
      ? Number(searchParams.get("score_min"))
      : undefined,
    score_max: searchParams.get("score_max")
      ? Number(searchParams.get("score_max"))
      : undefined,
    intent_classification:
      (searchParams.get("intent_classification") as IntentClassification) ??
      undefined,
    status: (searchParams.get("status") as CallStatus) ?? undefined,
    search: searchParams.get("search") ?? undefined,
    page: Number(searchParams.get("page")) || 1,
    page_size: PAGE_SIZE,
  });

  const [showFilters, setShowFilters] = useState(false);
  const [searchInput, setSearchInput] = useState(filters.search ?? "");

  // Agents for filter dropdown
  const { data: agents } = useQuery<AgentSummary[]>({
    queryKey: ["agents"],
    queryFn: getAgents,
  });

  // Calls query
  const {
    data: callsData,
    isLoading,
    error,
  } = useQuery<CallsListResponse>({
    queryKey: ["calls", filters],
    queryFn: () => getCalls(filters),
  });

  // Update filters & sync URL
  const applyFilters = useCallback(
    (updated: Partial<CallFilters>) => {
      const newFilters = { ...filters, ...updated, page: updated.page ?? 1 };
      setFilters(newFilters);
      const params = new URLSearchParams();
      Object.entries(newFilters).forEach(([k, v]) => {
        if (v !== undefined && v !== "" && v !== null) {
          params.set(k, String(v));
        }
      });
      setSearchParams(params, { replace: true });
    },
    [filters, setSearchParams],
  );

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    applyFilters({ search: searchInput || undefined });
  };

  const clearFilters = () => {
    setSearchInput("");
    setFilters({ page: 1, page_size: PAGE_SIZE });
    setSearchParams({}, { replace: true });
  };

  const hasActiveFilters =
    filters.agent_id ||
    filters.date_from ||
    filters.date_to ||
    filters.score_min !== undefined ||
    filters.score_max !== undefined ||
    filters.intent_classification ||
    filters.status ||
    filters.search;

  const totalPages = callsData?.total_pages ?? 1;
  const currentPage = callsData?.page ?? 1;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Calls</h1>
          <p className="mt-1 text-sm text-slate-400">
            {callsData
              ? `${callsData.total} total call${callsData.total !== 1 ? "s" : ""}`
              : "Loading calls..."}
          </p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
        >
          <Upload className="h-4 w-4" />
          Upload Call
        </button>
      </div>

      {/* Search + Filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <form onSubmit={handleSearch} className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by lead name, agent, phone..."
            className="w-full rounded-lg border border-slate-700 bg-slate-850 py-2 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/50 transition-colors"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                applyFilters({ search: undefined });
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </form>
        <button
          onClick={() => setShowFilters((p) => !p)}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
            showFilters || hasActiveFilters
              ? "border-accent-500/50 bg-accent-500/10 text-accent-400"
              : "border-slate-700 bg-slate-850 text-slate-400 hover:text-white",
          )}
        >
          <Filter className="h-4 w-4" />
          Filters
          {hasActiveFilters && (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-accent-500 text-2xs font-bold text-white">
              !
            </span>
          )}
        </button>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="animate-fade-in grid grid-cols-2 gap-3 rounded-xl border border-slate-800 bg-slate-850/60 p-4 sm:grid-cols-3 lg:grid-cols-6">
          {/* Agent */}
          <div>
            <label className="mb-1 block text-2xs font-medium uppercase tracking-wider text-slate-500">
              Agent
            </label>
            <select
              value={filters.agent_id ?? ""}
              onChange={(e) =>
                applyFilters({ agent_id: e.target.value || undefined })
              }
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
            >
              <option value="">All agents</option>
              {agents?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Date from */}
          <div>
            <label className="mb-1 block text-2xs font-medium uppercase tracking-wider text-slate-500">
              From
            </label>
            <input
              type="date"
              value={filters.date_from ?? ""}
              onChange={(e) =>
                applyFilters({ date_from: e.target.value || undefined })
              }
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
            />
          </div>

          {/* Date to */}
          <div>
            <label className="mb-1 block text-2xs font-medium uppercase tracking-wider text-slate-500">
              To
            </label>
            <input
              type="date"
              value={filters.date_to ?? ""}
              onChange={(e) =>
                applyFilters({ date_to: e.target.value || undefined })
              }
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
            />
          </div>

          {/* Score range */}
          <div>
            <label className="mb-1 block text-2xs font-medium uppercase tracking-wider text-slate-500">
              Score range
            </label>
            <div className="flex gap-1">
              <input
                type="number"
                min={0}
                max={100}
                placeholder="Min"
                value={filters.score_min ?? ""}
                onChange={(e) =>
                  applyFilters({
                    score_min: e.target.value
                      ? Number(e.target.value)
                      : undefined,
                  })
                }
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
              />
              <input
                type="number"
                min={0}
                max={100}
                placeholder="Max"
                value={filters.score_max ?? ""}
                onChange={(e) =>
                  applyFilters({
                    score_max: e.target.value
                      ? Number(e.target.value)
                      : undefined,
                  })
                }
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Intent */}
          <div>
            <label className="mb-1 block text-2xs font-medium uppercase tracking-wider text-slate-500">
              Intent
            </label>
            <select
              value={filters.intent_classification ?? ""}
              onChange={(e) =>
                applyFilters({
                  intent_classification:
                    (e.target.value as IntentClassification) || undefined,
                })
              }
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
            >
              <option value="">All</option>
              <option value="hot">Hot</option>
              <option value="warm">Warm</option>
              <option value="cold">Cold</option>
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="mb-1 block text-2xs font-medium uppercase tracking-wider text-slate-500">
              Status
            </label>
            <select
              value={filters.status ?? ""}
              onChange={(e) =>
                applyFilters({
                  status: (e.target.value as CallStatus) || undefined,
                })
              }
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="transcribing">Transcribing</option>
              <option value="analyzing">Analyzing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <TableSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center justify-center gap-3 py-20 text-slate-400">
          <AlertCircle className="h-8 w-8 text-red-400" />
          <p className="text-sm">Failed to load calls.</p>
        </div>
      ) : !callsData || callsData.items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-800">
            <Phone className="h-7 w-7 text-slate-500" />
          </div>
          <p className="text-sm text-slate-400">
            {hasActiveFilters
              ? "No calls match your filters."
              : "No calls recorded yet. Upload your first call to get started."}
          </p>
          {!hasActiveFilters && (
            <button
              onClick={() => setShowUpload(true)}
              className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
            >
              <Upload className="h-4 w-4" />
              Upload Call
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden overflow-hidden rounded-xl border border-slate-800 lg:block">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-850/80">
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Date
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Agent
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Lead
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Duration
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Quality
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Intent
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Sentiment
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Tags
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {callsData.items.map((call) => (
                  <tr
                    key={call.id}
                    onClick={() => navigate(`/calls/${call.id}`)}
                    className="cursor-pointer transition-colors hover:bg-slate-800/40"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-300">
                      {format(parseISO(call.created_at), "MMM d, h:mm a")}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-white">
                      {call.agent_name}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-white">
                          {call.lead_name || "Unknown"}
                        </p>
                        {call.lead_phone && (
                          <p className="text-xs text-slate-500">
                            {call.lead_phone}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDuration(call.duration)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <ScoreBadge score={call.overall_score} />
                    </td>
                    <td className="px-4 py-3">
                      <IntentChip
                        classification={call.intent_classification}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <SentimentDot sentiment={call.overall_sentiment} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(call.call_tags ?? []).slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="inline-flex items-center rounded bg-slate-800 px-1.5 py-0.5 text-2xs text-slate-400"
                          >
                            {tag.replace(/_/g, " ")}
                          </span>
                        ))}
                        {(call.call_tags ?? []).length > 2 && (
                          <span className="text-2xs text-slate-600">
                            +{call.call_tags.length - 2}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={call.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="space-y-2 lg:hidden">
            {callsData.items.map((call) => (
              <button
                key={call.id}
                onClick={() => navigate(`/calls/${call.id}`)}
                className="w-full rounded-xl border border-slate-800 bg-slate-850/60 p-4 text-left transition-colors hover:border-slate-700"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">
                      {call.lead_name || "Unknown Lead"}
                    </p>
                    <p className="text-xs text-slate-500">
                      {call.agent_name} &middot;{" "}
                      {format(parseISO(call.created_at), "MMM d, h:mm a")}
                    </p>
                  </div>
                  <ScoreBadge score={call.overall_score} />
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <IntentChip classification={call.intent_classification} />
                  <SentimentDot sentiment={call.overall_sentiment} />
                  <StatusBadge status={call.status} />
                  <span className="ml-auto flex items-center gap-1 text-xs text-slate-500">
                    <Clock className="h-3 w-3" />
                    {formatDuration(call.duration)}
                  </span>
                </div>
                {(call.call_tags ?? []).length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {call.call_tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center rounded bg-slate-800 px-1.5 py-0.5 text-2xs text-slate-400"
                      >
                        {tag.replace(/_/g, " ")}
                      </span>
                    ))}
                    {call.call_tags.length > 3 && (
                      <span className="text-2xs text-slate-600">
                        +{call.call_tags.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-xs text-slate-500">
                Page {currentPage} of {totalPages} ({callsData.total} results)
              </p>
              <div className="flex gap-1">
                <button
                  disabled={currentPage <= 1}
                  onClick={() =>
                    applyFilters({ page: currentPage - 1 })
                  }
                  className="flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                >
                  <ChevronLeft className="h-3 w-3" />
                  Previous
                </button>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() =>
                    applyFilters({ page: currentPage + 1 })
                  }
                  className="flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                >
                  Next
                  <ChevronRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <UploadModal
          onClose={() => {
            setShowUpload(false);
            searchParams.delete("upload");
            setSearchParams(searchParams, { replace: true });
          }}
          onSuccess={() => {
            setShowUpload(false);
            queryClient.invalidateQueries({ queryKey: ["calls"] });
          }}
        />
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Upload Modal
// ────────────────────────────────────────────────────────────────────

interface UploadModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

function UploadModal({ onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [agentId, setAgentId] = useState("");
  const [leadName, setLeadName] = useState("");
  const [leadId, setLeadId] = useState("");
  const [leadPhone, setLeadPhone] = useState("");
  const [source, setSource] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: agents } = useQuery<AgentSummary[]>({
    queryKey: ["agents"],
    queryFn: getAgents,
  });

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => uploadCall(formData),
    onSuccess: () => onSuccess(),
    onError: (err: Error) => {
      const axErr = err as unknown as {
        response?: { data?: { detail?: string } };
      };
      setUploadError(
        axErr.response?.data?.detail ?? "Upload failed. Please try again.",
      );
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setUploadError("Please select a recording file.");
      return;
    }
    if (!agentId) {
      setUploadError("Please select an agent.");
      return;
    }
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("agent_id", agentId);
    formData.append("lead_name", leadName);
    if (leadId) formData.append("lead_id", leadId);
    if (leadPhone) formData.append("lead_phone", leadPhone);
    if (source) formData.append("source", source);

    uploadMutation.mutate(formData);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      const validTypes = [
        "audio/mpeg",
        "audio/wav",
        "audio/mp4",
        "audio/x-m4a",
        "audio/webm",
        "audio/mp3",
      ];
      if (
        !validTypes.includes(selected.type) &&
        !selected.name.match(/\.(mp3|wav|m4a|webm)$/i)
      ) {
        setUploadError(
          "Invalid file type. Supported: mp3, wav, m4a, webm.",
        );
        return;
      }
      setFile(selected);
      setUploadError(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-lg animate-fade-in rounded-xl border border-slate-800 bg-slate-850 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">Upload Call Recording</h2>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          {uploadError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {uploadError}
            </div>
          )}

          {/* File drop zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed py-8 transition-colors",
              file
                ? "border-accent-500/50 bg-accent-500/5"
                : "border-slate-700 hover:border-slate-600",
            )}
          >
            <FileAudio
              className={cn(
                "h-8 w-8",
                file ? "text-accent-400" : "text-slate-500",
              )}
            />
            {file ? (
              <div className="text-center">
                <p className="text-sm font-medium text-white">{file.name}</p>
                <p className="text-xs text-slate-500">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-sm text-slate-400">
                  Click to select a recording file
                </p>
                <p className="text-xs text-slate-600">
                  Supports mp3, wav, m4a, webm
                </p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp3,.wav,.m4a,.webm,audio/*"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          {/* Metadata fields */}
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Agent *
              </label>
              <select
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
              >
                <option value="">Select an agent</option>
                {agents?.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </div>
            <ModalField
              label="Lead name"
              value={leadName}
              onChange={setLeadName}
              placeholder="John Doe"
            />
            <ModalField
              label="Lead ID"
              value={leadId}
              onChange={setLeadId}
              placeholder="lead-456"
            />
            <ModalField
              label="Lead phone"
              value={leadPhone}
              onChange={setLeadPhone}
              placeholder="+1 555-0123"
            />
            <ModalField
              label="Source"
              value={source}
              onChange={setSource}
              placeholder="Website, Referral..."
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploadMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-600 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-400">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white placeholder:text-slate-600 focus:border-accent-500 focus:outline-none"
      />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Shared micro-components
// ────────────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 75
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : score >= 50
        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
        : "bg-red-500/10 text-red-400 border-red-500/20";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold",
        color,
      )}
    >
      {score}
    </span>
  );
}

function IntentChip({
  classification,
}: {
  classification: IntentClassification;
}) {
  const styles: Record<IntentClassification, string> = {
    hot: "bg-red-500/10 text-red-400 border-red-500/20",
    warm: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    cold: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-2xs font-medium capitalize",
        styles[classification],
      )}
    >
      {classification}
    </span>
  );
}

function StatusBadge({ status }: { status: CallStatus }) {
  const styles: Record<string, string> = {
    pending: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    transcribing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    analyzing: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-2xs font-medium capitalize",
        styles[status] ?? styles.pending,
      )}
    >
      {status === "processing" || status === "transcribing" || status === "analyzing" ? (
        <Loader2 className="mr-1 h-2.5 w-2.5 animate-spin" />
      ) : null}
      {status}
    </span>
  );
}

function SentimentDot({ sentiment }: { sentiment: string | null }) {
  if (!sentiment) return null;
  const config: Record<string, { icon: React.ReactNode; color: string }> = {
    positive: {
      icon: <SmilePlus className="h-3 w-3" />,
      color: "text-emerald-400",
    },
    negative: {
      icon: <Frown className="h-3 w-3" />,
      color: "text-red-400",
    },
    mixed: {
      icon: <Meh className="h-3 w-3" />,
      color: "text-amber-400",
    },
    neutral: {
      icon: <Meh className="h-3 w-3" />,
      color: "text-slate-500",
    },
  };
  const entry = config[sentiment] ?? config.neutral;
  return (
    <span
      className={cn("flex items-center gap-1 text-2xs font-medium capitalize", entry!.color)}
      title={`Sentiment: ${sentiment}`}
    >
      {entry!.icon}
      {sentiment}
    </span>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded-lg border border-slate-800 bg-slate-850/40"
          style={{ animationDelay: `${i * 50}ms` }}
        />
      ))}
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
