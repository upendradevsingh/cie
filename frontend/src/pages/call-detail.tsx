import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import {
  ArrowLeft,
  Clock,
  User,
  Phone,
  Globe,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  MessageSquare,
  BarChart3,
  Target,
  ListChecks,
  ChevronRight,
  Star,
  Shield,
  Lightbulb,
  ArrowUpRight,
  Edit3,
  Save,
  X,
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { cn } from "@/lib/utils";
import { getCall, qaOverrideScores } from "@/lib/api";
import { useRequireRole } from "@/hooks/use-auth";
import type {
  CallData,
  CallStatus,
  TranscriptSegment,
  QualityScore,
  ActionItem,
  PathToConversion,
  LeadIntelligence,
  PersonaData,
  BANTScore,
  IntentClassification,
  FollowUpUrgency,
  Objection,
} from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Call Detail Page
// ────────────────────────────────────────────────────────────────────

type TabId = "transcript" | "quality" | "lead-intel" | "action-items";

export default function CallDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>("transcript");

  const {
    data: call,
    isLoading,
    error,
  } = useQuery<CallData>({
    queryKey: ["call", id],
    queryFn: () => getCall(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "processing" || data.status === "transcribing" || data.status === "analyzing")) {
        return 5000;
      }
      return false;
    },
  });

  if (isLoading) {
    return <DetailSkeleton />;
  }

  if (error || !call) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-slate-400">
        <AlertCircle className="h-8 w-8 text-red-400" />
        <p className="text-sm">Failed to load call details.</p>
        <button
          onClick={() => navigate("/calls")}
          className="text-sm text-accent-400 hover:text-accent-300 transition-colors"
        >
          Back to calls
        </button>
      </div>
    );
  }

  const isProcessing =
    call.status === "pending" ||
    call.status === "processing" ||
    call.status === "transcribing" ||
    call.status === "analyzing";

  const isFailed = call.status === "failed";

  const tabs: Array<{ id: TabId; label: string; icon: React.ReactNode }> = [
    { id: "transcript", label: "Transcript", icon: <MessageSquare className="h-4 w-4" /> },
    { id: "quality", label: "Quality", icon: <BarChart3 className="h-4 w-4" /> },
    { id: "lead-intel", label: "Lead Intel", icon: <Target className="h-4 w-4" /> },
    { id: "action-items", label: "Action Items", icon: <ListChecks className="h-4 w-4" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <button
          onClick={() => navigate("/calls")}
          className="mb-4 flex items-center gap-1 text-sm text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to calls
        </button>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white">
                {call.lead_name || "Unknown Lead"}
              </h1>
              <StatusBadge status={call.status} />
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-400">
              <span className="flex items-center gap-1">
                <User className="h-3.5 w-3.5" />
                {call.agent_name}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {formatDuration(call.duration)}
              </span>
              <span className="flex items-center gap-1">
                <Phone className="h-3.5 w-3.5" />
                {call.lead_phone || "N/A"}
              </span>
              {call.source && (
                <span className="flex items-center gap-1">
                  <Globe className="h-3.5 w-3.5" />
                  {call.source}
                </span>
              )}
              <span>
                {format(parseISO(call.created_at), "MMM d, yyyy 'at' h:mm a")}
              </span>
            </div>
          </div>

          {/* Overall score gauge */}
          {call.status === "completed" && (
            <div className="flex-shrink-0">
              <ScoreGauge score={call.overall_score} size="lg" />
            </div>
          )}
        </div>
      </div>

      {/* Processing state */}
      {isProcessing && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-blue-500/20 bg-blue-500/5 py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
          <div className="text-center">
            <p className="text-sm font-medium text-blue-300">
              {call.status === "pending"
                ? "Call queued for processing..."
                : call.status === "transcribing"
                  ? "Transcribing audio..."
                  : call.status === "analyzing"
                    ? "Analyzing conversation..."
                    : "Processing call..."}
            </p>
            <p className="mt-1 text-xs text-blue-400/70">
              This usually takes 1-3 minutes. The page will update automatically.
            </p>
          </div>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/5 py-12">
          <XCircle className="h-8 w-8 text-red-400" />
          <div className="text-center">
            <p className="text-sm font-medium text-red-300">
              Processing failed
            </p>
            <p className="mt-1 text-xs text-red-400/70">
              There was an error processing this call. Please try uploading again
              or contact support.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      {call.status === "completed" && (
        <>
          <div className="flex gap-1 overflow-x-auto border-b border-slate-800 pb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
                  activeTab === tab.id
                    ? "border-accent-500 text-accent-400"
                    : "border-transparent text-slate-500 hover:text-slate-300",
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="animate-fade-in">
            {activeTab === "transcript" && (
              <TranscriptTab segments={call.transcript} />
            )}
            {activeTab === "quality" && (
              <QualityTab
                callId={call.id}
                scores={call.quality_scores}
                overallScore={call.overall_score}
              />
            )}
            {activeTab === "lead-intel" && (
              <LeadIntelTab
                intelligence={call.lead_intelligence}
                persona={call.persona}
              />
            )}
            {activeTab === "action-items" && (
              <ActionItemsTab
                items={call.action_items}
                pathToConversion={call.path_to_conversion}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Transcript Tab
// ────────────────────────────────────────────────────────────────────

function TranscriptTab({ segments }: { segments: TranscriptSegment[] }) {
  const [filter, setFilter] = useState<"all" | "agent" | "customer" | "key">(
    "all",
  );

  const filtered = segments.filter((s) => {
    if (filter === "agent") return s.speaker === "agent";
    if (filter === "customer") return s.speaker === "customer";
    if (filter === "key") return s.is_key_moment;
    return true;
  });

  if (segments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-16 text-slate-500">
        <MessageSquare className="h-8 w-8" />
        <p className="text-sm">No transcript available for this call.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter buttons */}
      <div className="flex gap-2">
        {(
          [
            { id: "all", label: "All" },
            { id: "agent", label: "Agent" },
            { id: "customer", label: "Customer" },
            { id: "key", label: "Key Moments" },
          ] as const
        ).map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              filter === f.id
                ? "bg-accent-500/15 text-accent-400"
                : "bg-slate-800 text-slate-500 hover:text-slate-300",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Segments */}
      <div className="space-y-1">
        {filtered.map((segment) => (
          <div
            key={segment.id}
            className={cn(
              "group flex gap-3 rounded-lg px-4 py-3 transition-colors hover:bg-slate-800/30",
              segment.is_key_moment && "border-l-2 border-accent-500 bg-accent-500/5",
            )}
          >
            {/* Timestamp */}
            <span className="flex-shrink-0 pt-0.5 font-mono text-xs text-slate-600">
              {formatTimestamp(segment.start_time)}
            </span>

            {/* Speaker badge */}
            <span
              className={cn(
                "mt-0.5 flex h-5 flex-shrink-0 items-center rounded px-1.5 text-2xs font-semibold uppercase",
                segment.speaker === "agent"
                  ? "bg-primary-600/20 text-primary-300"
                  : segment.speaker === "customer"
                    ? "bg-amber-500/15 text-amber-400"
                    : "bg-slate-700 text-slate-400",
              )}
            >
              {segment.speaker_name || segment.speaker}
            </span>

            {/* Text */}
            <div className="flex-1">
              <p className="text-sm leading-relaxed text-slate-300">
                {segment.text}
              </p>
              {segment.is_key_moment && segment.key_moment_label && (
                <span className="mt-1 inline-flex items-center gap-1 rounded bg-accent-500/10 px-2 py-0.5 text-2xs font-medium text-accent-400">
                  <Star className="h-2.5 w-2.5" />
                  {segment.key_moment_label}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Quality Tab
// ────────────────────────────────────────────────────────────────────

function QualityTab({
  callId,
  scores,
  overallScore,
}: {
  callId: string;
  scores: QualityScore[];
  overallScore: number;
}) {
  const canOverride = useRequireRole(["admin", "team_lead"]);
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editedScores, setEditedScores] = useState<
    Array<{ parameter_id: string; score: number; justification: string }>
  >([]);
  const [overrideReason, setOverrideReason] = useState("");

  const overrideMutation = useMutation({
    mutationFn: () =>
      qaOverrideScores(callId, {
        scores: editedScores,
        override_reason: overrideReason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["call", callId] });
      setIsEditing(false);
    },
  });

  const startEditing = () => {
    setEditedScores(
      scores.map((s) => ({
        parameter_id: s.parameter_id,
        score: s.score,
        justification: s.justification,
      })),
    );
    setOverrideReason("");
    setIsEditing(true);
  };

  // Group by category
  const categories = scores.reduce<Record<string, QualityScore[]>>(
    (acc, score) => {
      const cat = score.category || "General";
      if (!acc[cat]) acc[cat] = [];
      acc[cat]!.push(score);
      return acc;
    },
    {},
  );

  const chartData = scores.map((s) => ({
    name: s.parameter_name.length > 20
      ? s.parameter_name.slice(0, 18) + "..."
      : s.parameter_name,
    score: s.score,
    maxScore: s.max_score,
  }));

  return (
    <div className="space-y-6">
      {/* Header with override button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <ScoreGauge score={overallScore} size="md" />
          <div>
            <p className="text-lg font-bold text-white">
              Overall Quality Score
            </p>
            <p className="text-sm text-slate-400">
              Based on {scores.length} parameters
            </p>
          </div>
        </div>
        {canOverride && !isEditing && (
          <button
            onClick={startEditing}
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <Edit3 className="h-3.5 w-3.5" />
            QA Override
          </button>
        )}
        {isEditing && (
          <div className="flex gap-2">
            <button
              onClick={() => setIsEditing(false)}
              className="flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              Cancel
            </button>
            <button
              onClick={() => overrideMutation.mutate()}
              disabled={overrideMutation.isPending || !overrideReason.trim()}
              className="flex items-center gap-1 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 disabled:opacity-60 transition-colors"
            >
              {overrideMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              Save Override
            </button>
          </div>
        )}
      </div>

      {isEditing && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Override reason (required)
          </label>
          <input
            type="text"
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder="Reason for score adjustment..."
            className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-accent-500 focus:outline-none"
          />
        </div>
      )}

      {/* Bar chart */}
      {chartData.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <h3 className="mb-4 text-sm font-semibold text-white">
            Parameter Breakdown
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  type="number"
                  domain={[0, 10]}
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  width={150}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<QualityTooltip />} />
                <Bar
                  dataKey="score"
                  fill="#0d9488"
                  radius={[0, 4, 4, 0]}
                  barSize={16}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Categories */}
      {Object.entries(categories).map(([category, catScores]) => (
        <div key={category}>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            {category}
          </h3>
          <div className="space-y-2">
            {catScores.map((score) => {
              const editItem = isEditing
                ? editedScores.find(
                    (e) => e.parameter_id === score.parameter_id,
                  )
                : null;

              return (
                <div
                  key={score.parameter_id}
                  className="rounded-lg border border-slate-800 bg-slate-850/40 p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-white">
                          {score.parameter_name}
                        </p>
                        <span className="text-2xs text-slate-600">
                          (weight: {score.weight})
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        {score.justification}
                      </p>
                    </div>

                    {isEditing && editItem ? (
                      <input
                        type="number"
                        min={0}
                        max={score.max_score}
                        value={editItem.score}
                        onChange={(e) => {
                          setEditedScores((prev) =>
                            prev.map((p) =>
                              p.parameter_id === score.parameter_id
                                ? { ...p, score: Number(e.target.value) }
                                : p,
                            ),
                          );
                        }}
                        className="w-16 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-center text-sm font-bold text-white focus:border-accent-500 focus:outline-none"
                      />
                    ) : (
                      <div className="flex-shrink-0 text-right">
                        <span
                          className={cn(
                            "text-lg font-bold",
                            score.score >= 7
                              ? "text-emerald-400"
                              : score.score >= 4
                                ? "text-amber-400"
                                : "text-red-400",
                          )}
                        >
                          {score.score}
                        </span>
                        <span className="text-sm text-slate-600">
                          /{score.max_score}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Score bar */}
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        score.score >= 7
                          ? "bg-emerald-500"
                          : score.score >= 4
                            ? "bg-amber-500"
                            : "bg-red-500",
                      )}
                      style={{
                        width: `${(score.score / score.max_score) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function QualityTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { name: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0]!;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-slate-300">{item.payload.name}</p>
      <p className="text-white">
        Score: <span className="font-semibold">{item.value}/10</span>
      </p>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Lead Intel Tab
// ────────────────────────────────────────────────────────────────────

function LeadIntelTab({
  intelligence,
  persona,
}: {
  intelligence: LeadIntelligence;
  persona: PersonaData;
}) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Intent Panel */}
      <div className="space-y-4">
        <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">
              Lead Intent Score
            </h3>
            <IntentChip classification={intelligence.classification} />
          </div>
          <div className="mt-3 flex items-center gap-4">
            <ScoreGauge score={intelligence.intent_score} size="md" />
            <div>
              <p className="text-2xl font-bold text-white">
                {intelligence.intent_score}
              </p>
              <p className="text-xs text-slate-500">out of 100</p>
            </div>
          </div>
        </div>

        {/* Signals */}
        <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <h3 className="mb-3 text-sm font-semibold text-white">
            Intent Signals
          </h3>
          <div className="space-y-2">
            {intelligence.signals.map((signal) => (
              <div
                key={signal.id}
                className="flex items-start gap-3 rounded-lg bg-slate-800/30 px-3 py-2"
              >
                {signal.detected ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-400" />
                ) : (
                  <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-600" />
                )}
                <div>
                  <p
                    className={cn(
                      "text-sm font-medium",
                      signal.detected ? "text-white" : "text-slate-500",
                    )}
                  >
                    {signal.name}
                  </p>
                  {signal.details && (
                    <p className="mt-0.5 text-xs text-slate-400">
                      {signal.details}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Buying signals */}
        {intelligence.buying_signals.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
            <h3 className="mb-3 text-sm font-semibold text-white">
              Buying Signals
            </h3>
            <ul className="space-y-1">
              {intelligence.buying_signals.map((signal, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                  {signal}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Objections */}
        {intelligence.key_objections.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
            <h3 className="mb-3 text-sm font-semibold text-white">
              Key Objections
            </h3>
            <div className="space-y-2">
              {intelligence.key_objections.map(
                (obj: Objection, i: number) => (
                  <div
                    key={i}
                    className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-white">
                        {obj.objection}
                      </p>
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-2xs font-medium",
                          obj.severity === "high"
                            ? "bg-red-500/10 text-red-400"
                            : obj.severity === "medium"
                              ? "bg-amber-500/10 text-amber-400"
                              : "bg-slate-700 text-slate-400",
                        )}
                      >
                        {obj.severity}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {obj.category}
                    </p>
                    {obj.rebuttal_suggestion && (
                      <p className="mt-1 text-xs text-accent-400">
                        Suggested rebuttal: {obj.rebuttal_suggestion}
                      </p>
                    )}
                  </div>
                ),
              )}
            </div>
          </div>
        )}
      </div>

      {/* Persona + BANT */}
      <div className="space-y-4">
        {/* Persona Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <h3 className="mb-3 text-sm font-semibold text-white">
            Persona Analysis
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600/20">
              <Shield className="h-5 w-5 text-primary-300" />
            </div>
            <div>
              <p className="text-base font-semibold text-white">
                {persona.persona_type}
              </p>
            </div>
          </div>
        </div>

        {/* BANT Radar */}
        <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <h3 className="mb-3 text-sm font-semibold text-white">
            BANT Analysis
          </h3>
          <BANTRadarChart bant={persona.bant} />
          <div className="mt-4 grid grid-cols-2 gap-2">
            {(
              Object.entries(persona.bant) as Array<
                [keyof BANTScore, number]
              >
            ).map(([key, value]) => (
              <div
                key={key}
                className="rounded-lg bg-slate-800/40 px-3 py-2 text-center"
              >
                <p className="text-lg font-bold text-white">{value}</p>
                <p className="text-2xs uppercase tracking-wider text-slate-500">
                  {key}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Discovery Insights */}
        {persona.discovery_insights.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
              <Lightbulb className="h-4 w-4 text-amber-400" />
              Discovery Insights
            </h3>
            <ul className="space-y-2">
              {persona.discovery_insights.map((insight, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-slate-300"
                >
                  <ChevronRight className="mt-0.5 h-3 w-3 flex-shrink-0 text-slate-600" />
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function BANTRadarChart({ bant }: { bant: BANTScore }) {
  const data = [
    { subject: "Budget", value: bant.budget, fullMark: 10 },
    { subject: "Authority", value: bant.authority, fullMark: 10 },
    { subject: "Need", value: bant.need, fullMark: 10 },
    { subject: "Timeline", value: bant.timeline, fullMark: 10 },
  ];

  return (
    <div className="h-52">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
          <PolarGrid stroke="#1e293b" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 10]}
            tick={{ fill: "#475569", fontSize: 10 }}
          />
          <Radar
            name="BANT"
            dataKey="value"
            stroke="#0d9488"
            fill="#0d9488"
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Action Items Tab
// ────────────────────────────────────────────────────────────────────

function ActionItemsTab({
  items,
  pathToConversion,
}: {
  items: ActionItem[];
  pathToConversion: PathToConversion;
}) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Action Items */}
      <div className="space-y-4">
        <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">
              Next Steps ({items.length})
            </h3>
            {pathToConversion.follow_up_urgency && (
              <UrgencyBadge urgency={pathToConversion.follow_up_urgency} />
            )}
          </div>

          {items.length === 0 ? (
            <p className="mt-4 text-center text-sm text-slate-500">
              No action items extracted.
            </p>
          ) : (
            <div className="mt-3 space-y-2">
              {items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-start gap-3 rounded-lg border px-3 py-2.5",
                    item.completed
                      ? "border-slate-800 bg-slate-900/30 opacity-60"
                      : "border-slate-800 bg-slate-800/30",
                  )}
                >
                  <div
                    className={cn(
                      "mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full border",
                      item.completed
                        ? "border-emerald-500 bg-emerald-500"
                        : "border-slate-600",
                    )}
                  >
                    {item.completed && (
                      <CheckCircle2 className="h-3 w-3 text-white" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p
                      className={cn(
                        "text-sm",
                        item.completed
                          ? "text-slate-500 line-through"
                          : "text-white",
                      )}
                    >
                      {item.text}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <UrgencyBadge urgency={item.urgency} />
                      <span className="text-2xs text-slate-600">
                        {item.category}
                      </span>
                      {item.priority && (
                        <span
                          className={cn(
                            "text-2xs font-medium",
                            item.priority === "high"
                              ? "text-red-400"
                              : item.priority === "medium"
                                ? "text-amber-400"
                                : "text-slate-500",
                          )}
                        >
                          {item.priority} priority
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Path to Conversion */}
      <div className="space-y-4">
        {/* Next best action */}
        {pathToConversion.next_best_action && (
          <div className="rounded-xl border border-accent-500/20 bg-accent-500/5 p-5">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-accent-400">
              <Target className="h-4 w-4" />
              Next Best Action
            </h3>
            <p className="mt-2 text-sm text-white">
              {pathToConversion.next_best_action}
            </p>
          </div>
        )}

        {/* Talking points */}
        {pathToConversion.talking_points.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
            <h3 className="mb-3 text-sm font-semibold text-white">
              Talking Points for Follow-Up
            </h3>
            <ul className="space-y-2">
              {pathToConversion.talking_points.map((point, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-slate-300"
                >
                  <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary-600/20 text-2xs font-bold text-primary-300">
                    {i + 1}
                  </span>
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Rebuttals */}
        {pathToConversion.rebuttals.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
            <h3 className="mb-3 text-sm font-semibold text-white">
              Objection Rebuttals
            </h3>
            <div className="space-y-3">
              {pathToConversion.rebuttals.map((r, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-slate-800 bg-slate-900/40 p-3"
                >
                  <p className="text-xs font-medium text-red-400">
                    Objection: {r.objection}
                  </p>
                  <p className="mt-1 text-sm text-slate-300">
                    {r.rebuttal}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Shared micro-components
// ────────────────────────────────────────────────────────────────────

function ScoreGauge({
  score,
  size = "md",
}: {
  score: number;
  size?: "sm" | "md" | "lg";
}) {
  const radius = size === "lg" ? 40 : size === "md" ? 32 : 24;
  const strokeWidth = size === "lg" ? 6 : size === "md" ? 5 : 4;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  const color =
    score >= 75
      ? "text-emerald-400"
      : score >= 50
        ? "text-amber-400"
        : "text-red-400";

  const strokeColor =
    score >= 75 ? "#34d399" : score >= 50 ? "#fbbf24" : "#f87171";

  const svgSize = (radius + strokeWidth) * 2;
  const center = radius + strokeWidth;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={svgSize} height={svgSize}>
        {/* Background circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#1e293b"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          transform={`rotate(-90 ${center} ${center})`}
          className="transition-all duration-700"
        />
      </svg>
      <span
        className={cn(
          "absolute font-bold",
          color,
          size === "lg"
            ? "text-xl"
            : size === "md"
              ? "text-base"
              : "text-sm",
        )}
      >
        {Math.round(score)}
      </span>
    </div>
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
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize",
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
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        styles[status] ?? styles.pending,
      )}
    >
      {status}
    </span>
  );
}

function UrgencyBadge({ urgency }: { urgency: FollowUpUrgency }) {
  const styles: Record<FollowUpUrgency, string> = {
    immediate: "bg-red-500/10 text-red-400",
    this_week: "bg-amber-500/10 text-amber-400",
    next_week: "bg-blue-500/10 text-blue-400",
    nurture: "bg-slate-700 text-slate-400",
  };

  const labels: Record<FollowUpUrgency, string> = {
    immediate: "Immediate",
    this_week: "This week",
    next_week: "Next week",
    nurture: "Nurture",
  };

  return (
    <span
      className={cn(
        "inline-flex rounded px-1.5 py-0.5 text-2xs font-medium",
        styles[urgency],
      )}
    >
      {labels[urgency]}
    </span>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-6 w-24 animate-pulse rounded bg-slate-800" />
      <div className="flex items-start justify-between">
        <div>
          <div className="h-8 w-48 animate-pulse rounded bg-slate-800" />
          <div className="mt-2 h-4 w-64 animate-pulse rounded bg-slate-800/60" />
        </div>
        <div className="h-20 w-20 animate-pulse rounded-full bg-slate-800" />
      </div>
      <div className="flex gap-4 border-b border-slate-800 pb-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-8 w-24 animate-pulse rounded bg-slate-800/60"
          />
        ))}
      </div>
      <div className="h-96 animate-pulse rounded-xl border border-slate-800 bg-slate-850/40" />
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
