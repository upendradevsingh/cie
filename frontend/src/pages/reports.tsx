import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO, subDays, startOfWeek } from "date-fns";
import {
  FileText,
  Calendar,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Trophy,
  Flame,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Phone,
  Target,
  Lightbulb,
  CheckCircle2,
  XCircle,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getWeeklyReports, getWeeklyReport, generateWeeklyReport } from "@/lib/api";
import type {
  WeeklyReportListItem,
  WeeklyReport,
  AgentWeeklyBreakdown,
} from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Reports Page
// ────────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showGenerate, setShowGenerate] = useState(false);
  const [weekStart, setWeekStart] = useState(
    format(startOfWeek(subDays(new Date(), 7), { weekStartsOn: 1 }), "yyyy-MM-dd"),
  );
  const [expandedReport, setExpandedReport] = useState<string | null>(null);

  const {
    data: reports,
    isLoading,
    error,
  } = useQuery<WeeklyReportListItem[]>({
    queryKey: ["weekly-reports"],
    queryFn: getWeeklyReports,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateWeeklyReport({ week_start: weekStart }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["weekly-reports"] });
      setShowGenerate(false);
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <FileText className="h-6 w-6 text-slate-400" />
            Reports
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Weekly performance summaries and insights
          </p>
        </div>
        <button
          onClick={() => setShowGenerate((p) => !p)}
          className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Generate Report
        </button>
      </div>

      {/* Generate report panel */}
      {showGenerate && (
        <div className="animate-fade-in rounded-xl border border-slate-800 bg-slate-850/60 p-5">
          <h3 className="text-sm font-semibold text-white">
            Generate Weekly Report
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Select the week start date. The report will cover 7 days from this
            date.
          </p>
          <div className="mt-3 flex items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Week starting
              </label>
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-slate-500" />
                <input
                  type="date"
                  value={weekStart}
                  onChange={(e) => setWeekStart(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
                />
              </div>
            </div>
            <button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-accent-600 disabled:opacity-60 transition-colors"
            >
              {generateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              Generate
            </button>
          </div>
          {generateMutation.error && (
            <p className="mt-2 text-xs text-red-400">
              Failed to generate report. Please try again.
            </p>
          )}
        </div>
      )}

      {/* Reports list */}
      {isLoading ? (
        <ReportsSkeleton />
      ) : error ? (
        <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-slate-400">
          <AlertCircle className="h-8 w-8 text-red-400" />
          <p className="text-sm">Failed to load reports.</p>
        </div>
      ) : !reports || reports.length === 0 ? (
        <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-800">
            <FileText className="h-7 w-7 text-slate-500" />
          </div>
          <p className="text-sm text-slate-400">
            No reports generated yet. Create your first weekly report.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              isExpanded={expandedReport === report.id}
              onToggle={() =>
                setExpandedReport((prev) =>
                  prev === report.id ? null : report.id,
                )
              }
              onNavigateToCall={(callId) => navigate(`/calls/${callId}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Report Card
// ────────────────────────────────────────────────────────────────────

function ReportCard({
  report,
  isExpanded,
  onToggle,
  onNavigateToCall,
}: {
  report: WeeklyReportListItem;
  isExpanded: boolean;
  onToggle: () => void;
  onNavigateToCall: (callId: string) => void;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-850/60 transition-colors hover:border-slate-700">
      {/* Card header */}
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600/15">
            <FileText className="h-5 w-5 text-primary-300" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">
              Week of {format(parseISO(report.week_start), "MMM d")} -{" "}
              {format(parseISO(report.week_end), "MMM d, yyyy")}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              Generated {format(parseISO(report.created_at), "MMM d 'at' h:mm a")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Quick stats */}
          <div className="hidden items-center gap-4 sm:flex">
            <StatPill
              icon={<Phone className="h-3 w-3" />}
              value={report.summary_total_calls}
              label="calls"
            />
            <StatPill
              icon={<BarChart3 className="h-3 w-3" />}
              value={report.summary_avg_quality.toFixed(1)}
              label="avg quality"
            />
          </div>
          <ReportStatusBadge status={report.status} />
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-slate-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-500" />
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {isExpanded && report.status === "completed" && (
        <ReportDetail reportId={report.id} onNavigateToCall={onNavigateToCall} />
      )}
      {isExpanded && report.status === "generating" && (
        <div className="border-t border-slate-800 px-5 py-8 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-blue-400" />
          <p className="mt-2 text-sm text-blue-300">
            Report is being generated...
          </p>
        </div>
      )}
      {isExpanded && report.status === "failed" && (
        <div className="border-t border-slate-800 px-5 py-8 text-center">
          <XCircle className="mx-auto h-6 w-6 text-red-400" />
          <p className="mt-2 text-sm text-red-300">
            Report generation failed.
          </p>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Report Detail (expanded)
// ────────────────────────────────────────────────────────────────────

function ReportDetail({
  reportId,
  onNavigateToCall,
}: {
  reportId: string;
  onNavigateToCall: (callId: string) => void;
}) {
  const {
    data: report,
    isLoading,
    error,
  } = useQuery<WeeklyReport>({
    queryKey: ["weekly-report", reportId],
    queryFn: () => getWeeklyReport(reportId),
  });

  if (isLoading) {
    return (
      <div className="border-t border-slate-800 px-5 py-8 text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="border-t border-slate-800 px-5 py-8 text-center text-sm text-red-400">
        Failed to load report details.
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6 border-t border-slate-800 px-5 py-5">
      {/* Summary stats */}
      <div>
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Summary
        </h4>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SummaryCard
            label="Total Calls"
            value={String(report.summary.total_calls)}
            icon={<Phone className="h-4 w-4 text-primary-300" />}
          />
          <SummaryCard
            label="Avg Quality"
            value={report.summary.avg_quality_score.toFixed(1)}
            icon={<BarChart3 className="h-4 w-4 text-accent-400" />}
            change={report.summary.quality_change}
          />
          <SummaryCard
            label="Hot Leads"
            value={String(report.summary.hot_leads)}
            icon={<Flame className="h-4 w-4 text-red-400" />}
          />
          <SummaryCard
            label="Top Agent"
            value={report.summary.top_agent}
            icon={<Trophy className="h-4 w-4 text-amber-400" />}
          />
        </div>
      </div>

      {/* Key Insights */}
      {report.key_insights && report.key_insights.length > 0 && (
        <div>
          <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
            Key Insights
          </h4>
          <ul className="space-y-2">
            {report.key_insights.map((insight, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-lg bg-slate-800/30 px-3 py-2 text-sm text-slate-300"
              >
                <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-accent-500/20 text-2xs font-bold text-accent-400">
                  {i + 1}
                </span>
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Areas for Improvement */}
      {report.summary.areas_for_improvement.length > 0 && (
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Areas for Improvement
          </h4>
          <ul className="space-y-1">
            {report.summary.areas_for_improvement.map((area, i) => (
              <li
                key={i}
                className="flex items-center gap-2 text-sm text-slate-400"
              >
                <Target className="h-3 w-3 flex-shrink-0 text-amber-500" />
                {area}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Agent Breakdowns */}
      {report.agent_breakdowns.length > 0 && (
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Agent Breakdowns
          </h4>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {report.agent_breakdowns.map((agent) => (
              <AgentBreakdownCard key={agent.agent_id} agent={agent} />
            ))}
          </div>
        </div>
      )}

      {/* Top Calls */}
      {report.top_calls.length > 0 && (
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Top Calls
          </h4>
          <div className="space-y-2">
            {report.top_calls.map((call, i) => (
              <button
                key={call.call_id}
                onClick={() => onNavigateToCall(call.call_id)}
                className="flex w-full items-center gap-3 rounded-lg bg-slate-800/30 px-4 py-2.5 text-left transition-colors hover:bg-slate-800/50"
              >
                <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary-600/20 text-2xs font-bold text-primary-300">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-white">
                    {call.lead_name}
                  </p>
                  <p className="text-xs text-slate-500">{call.agent_name}</p>
                </div>
                <ScoreBadge score={call.overall_score} />
                <IntentBadge classification={call.intent_classification} />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Hot Leads */}
      {report.hot_leads_summary.length > 0 && (
        <div>
          <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <Flame className="h-3.5 w-3.5 text-red-400" />
            Hot Leads This Week
          </h4>
          <div className="space-y-2">
            {report.hot_leads_summary.map((lead) => (
              <button
                key={lead.call_id}
                onClick={() => onNavigateToCall(lead.call_id)}
                className="flex w-full items-center gap-3 rounded-lg bg-slate-800/30 px-4 py-2.5 text-left transition-colors hover:bg-slate-800/50"
              >
                <Flame className="h-4 w-4 flex-shrink-0 text-red-400" />
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-white">
                    {lead.lead_name}
                  </p>
                  <p className="text-xs text-slate-500">{lead.agent_name}</p>
                </div>
                <span className="text-sm font-bold text-red-400">
                  {lead.intent_score}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Agent Breakdown Card
// ────────────────────────────────────────────────────────────────────

function AgentBreakdownCard({ agent }: { agent: AgentWeeklyBreakdown }) {
  const isPositive = agent.quality_change >= 0;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-800/20 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-white">{agent.agent_name}</p>
        <div
          className={cn(
            "flex items-center gap-0.5 text-xs font-medium",
            isPositive ? "text-emerald-400" : "text-red-400",
          )}
        >
          {isPositive ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {Math.abs(agent.quality_change).toFixed(1)}%
        </div>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-lg font-bold text-white">{agent.total_calls}</p>
          <p className="text-2xs text-slate-500">Calls</p>
        </div>
        <div>
          <p className="text-lg font-bold text-white">
            {agent.avg_quality_score.toFixed(1)}
          </p>
          <p className="text-2xs text-slate-500">Quality</p>
        </div>
        <div>
          <p className="text-lg font-bold text-red-400">{agent.hot_leads}</p>
          <p className="text-2xs text-slate-500">Hot Leads</p>
        </div>
      </div>
      {agent.strengths.length > 0 && (
        <div className="mt-2">
          <p className="text-2xs font-medium text-emerald-400">Strengths:</p>
          <p className="text-xs text-slate-400">
            {agent.strengths.join(", ")}
          </p>
        </div>
      )}
      {agent.areas_for_improvement.length > 0 && (
        <div className="mt-1">
          <p className="text-2xs font-medium text-amber-400">Improve:</p>
          <p className="text-xs text-slate-400">
            {agent.areas_for_improvement.join(", ")}
          </p>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Shared micro-components
// ────────────────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  icon,
  change,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  change?: number;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-2xs uppercase tracking-wider text-slate-500">
          {label}
        </span>
      </div>
      <div className="mt-1 flex items-end gap-2">
        <p className="text-lg font-bold text-white">{value}</p>
        {change !== undefined && (
          <span
            className={cn(
              "mb-0.5 flex items-center gap-0.5 text-2xs font-medium",
              change >= 0 ? "text-emerald-400" : "text-red-400",
            )}
          >
            {change >= 0 ? (
              <TrendingUp className="h-2.5 w-2.5" />
            ) : (
              <TrendingDown className="h-2.5 w-2.5" />
            )}
            {Math.abs(change).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

function StatPill({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: string | number;
  label: string;
}) {
  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-400">
      {icon}
      <span className="font-semibold text-white">{value}</span>
      {label}
    </span>
  );
}

function ReportStatusBadge({
  status,
}: {
  status: "generating" | "completed" | "failed";
}) {
  const styles: Record<string, string> = {
    generating: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-2xs font-medium capitalize",
        styles[status],
      )}
    >
      {status === "generating" && (
        <Loader2 className="mr-1 h-2.5 w-2.5 animate-spin" />
      )}
      {status === "completed" && (
        <CheckCircle2 className="mr-1 h-2.5 w-2.5" />
      )}
      {status === "failed" && <XCircle className="mr-1 h-2.5 w-2.5" />}
      {status}
    </span>
  );
}

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

function IntentBadge({ classification }: { classification: string }) {
  const styles: Record<string, string> = {
    hot: "bg-red-500/10 text-red-400 border-red-500/20",
    warm: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    cold: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-2xs font-medium capitalize",
        styles[classification] ?? "bg-slate-700 text-slate-400 border-slate-600",
      )}
    >
      {classification}
    </span>
  );
}

function ReportsSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="h-20 animate-pulse rounded-xl border border-slate-800 bg-slate-850/40"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}
