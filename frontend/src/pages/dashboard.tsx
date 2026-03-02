import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Phone,
  TrendingUp,
  Flame,
  Users,
  ArrowUpRight,
  ArrowDownRight,
  Upload,
  FileText,
  Clock,
  ChevronRight,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { format, parseISO } from "date-fns";
import { cn } from "@/lib/utils";
import { getTeamAnalytics } from "@/lib/api";
import type {
  TeamAnalytics,
  CallListItem,
  CallTrend,
  ScoreDistribution,
  HotLead,
} from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Dashboard Page
// ────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();

  const {
    data: analytics,
    isLoading,
    error,
  } = useQuery<TeamAnalytics>({
    queryKey: ["analytics", "team"],
    queryFn: () => getTeamAnalytics(),
    refetchInterval: 60_000, // refresh every minute
  });

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !analytics) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-slate-400">
        <AlertCircle className="h-8 w-8 text-red-400" />
        <p className="text-sm">Failed to load dashboard data.</p>
        <button
          onClick={() => window.location.reload()}
          className="text-sm text-accent-400 hover:text-accent-300 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const { stats, call_trends, score_distribution, hot_leads, recent_calls } =
    analytics;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-400">
            Overview of your sales call intelligence
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate("/calls?upload=true")}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-750 hover:text-white transition-colors"
          >
            <Upload className="h-4 w-4" />
            Upload Call
          </button>
          <button
            onClick={() => navigate("/reports")}
            className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
          >
            <FileText className="h-4 w-4" />
            View Reports
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Calls Today"
          value={stats.calls_today}
          change={stats.calls_today_change}
          icon={<Phone className="h-5 w-5" />}
          iconBg="bg-primary-600/20 text-primary-300"
        />
        <StatCard
          title="Avg Quality Score"
          value={stats.avg_quality_score}
          change={stats.avg_quality_change}
          icon={<TrendingUp className="h-5 w-5" />}
          iconBg="bg-accent-500/20 text-accent-300"
          format="score"
        />
        <StatCard
          title="Hot Leads"
          value={stats.hot_leads_count}
          change={stats.hot_leads_change}
          icon={<Flame className="h-5 w-5" />}
          iconBg="bg-red-500/20 text-red-400"
        />
        <StatCard
          title="Team Performance"
          value={stats.team_performance}
          change={stats.team_performance_change}
          icon={<Users className="h-5 w-5" />}
          iconBg="bg-amber-500/20 text-amber-400"
          format="percent"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Call trends - takes 2 cols */}
        <div className="lg:col-span-2">
          <ChartCard title="Calls Trend" subtitle="Last 30 days">
            <CallTrendChart data={call_trends} />
          </ChartCard>
        </div>

        {/* Score distribution */}
        <div>
          <ChartCard title="Quality Score Distribution">
            <ScoreDistributionChart data={score_distribution} />
          </ChartCard>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent calls */}
        <div className="rounded-xl border border-slate-800 bg-slate-850/60">
          <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
            <h3 className="text-sm font-semibold text-white">Recent Calls</h3>
            <button
              onClick={() => navigate("/calls")}
              className="flex items-center gap-1 text-xs text-accent-400 hover:text-accent-300 transition-colors"
            >
              View all
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>
          <div className="divide-y divide-slate-800/60">
            {recent_calls.length === 0 ? (
              <EmptyState message="No calls recorded yet." />
            ) : (
              recent_calls.slice(0, 10).map((call) => (
                <RecentCallRow
                  key={call.id}
                  call={call}
                  onClick={() => navigate(`/calls/${call.id}`)}
                />
              ))
            )}
          </div>
        </div>

        {/* Hot leads */}
        <div className="rounded-xl border border-slate-800 bg-slate-850/60">
          <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
              <Flame className="h-4 w-4 text-red-400" />
              Hot Leads
            </h3>
          </div>
          <div className="divide-y divide-slate-800/60">
            {hot_leads.length === 0 ? (
              <EmptyState message="No hot leads detected yet." />
            ) : (
              hot_leads.slice(0, 8).map((lead) => (
                <HotLeadRow
                  key={lead.call_id}
                  lead={lead}
                  onClick={() => navigate(`/calls/${lead.call_id}`)}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Stat Card
// ────────────────────────────────────────────────────────────────────

interface StatCardProps {
  title: string;
  value: number;
  change: number;
  icon: React.ReactNode;
  iconBg: string;
  format?: "number" | "score" | "percent";
}

function StatCard({
  title,
  value,
  change,
  icon,
  iconBg,
  format = "number",
}: StatCardProps) {
  const isPositive = change >= 0;
  const formattedValue =
    format === "score"
      ? value.toFixed(1)
      : format === "percent"
        ? `${value}%`
        : value.toLocaleString();

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5 transition-colors hover:border-slate-700">
      <div className="flex items-start justify-between">
        <div className={cn("rounded-lg p-2.5", iconBg)}>{icon}</div>
        <div
          className={cn(
            "flex items-center gap-0.5 text-xs font-medium",
            isPositive ? "text-emerald-400" : "text-red-400",
          )}
        >
          {isPositive ? (
            <ArrowUpRight className="h-3.5 w-3.5" />
          ) : (
            <ArrowDownRight className="h-3.5 w-3.5" />
          )}
          {Math.abs(change)}%
        </div>
      </div>
      <div className="mt-4">
        <p className="text-2xl font-bold text-white">{formattedValue}</p>
        <p className="mt-1 text-xs text-slate-400">{title}</p>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Chart wrapper
// ────────────────────────────────────────────────────────────────────

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
        )}
      </div>
      {children}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Call Trend Chart
// ────────────────────────────────────────────────────────────────────

function CallTrendChart({ data }: { data: CallTrend[] }) {
  if (data.length === 0) {
    return <EmptyState message="No trend data available." />;
  }

  const chartData = data.map((d) => ({
    ...d,
    label: format(parseISO(d.date), "MMM d"),
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="callCountGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="label"
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#0d9488"
            strokeWidth={2}
            fill="url(#callCountGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Score Distribution Chart
// ────────────────────────────────────────────────────────────────────

function ScoreDistributionChart({ data }: { data: ScoreDistribution[] }) {
  if (data.length === 0) {
    return <EmptyState message="No score data available." />;
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="range"
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="count" fill="#1e3a5f" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Custom Tooltip
// ────────────────────────────────────────────────────────────────────

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-medium text-slate-300">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-white">
          {entry.name}: <span className="font-semibold">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Recent Call Row
// ────────────────────────────────────────────────────────────────────

function RecentCallRow({
  call,
  onClick,
}: {
  call: CallListItem;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-slate-800/40 transition-colors"
    >
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-white">
          {call.lead_name || "Unknown Lead"}
        </p>
        <p className="text-xs text-slate-500">
          {call.agent_name} &middot;{" "}
          {formatDuration(call.duration)}
        </p>
      </div>
      <ScoreBadge score={call.overall_score} />
      <IntentChip classification={call.intent_classification} />
      <div className="flex items-center gap-1 text-xs text-slate-500">
        <Clock className="h-3 w-3" />
        {format(parseISO(call.created_at), "h:mm a")}
      </div>
    </button>
  );
}

// ────────────────────────────────────────────────────────────────────
// Hot Lead Row
// ────────────────────────────────────────────────────────────────────

function HotLeadRow({
  lead,
  onClick,
}: {
  lead: HotLead;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-slate-800/40 transition-colors"
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-500/10 text-red-400">
        <Flame className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-white">
          {lead.lead_name}
        </p>
        <p className="text-xs text-slate-500">{lead.agent_name}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-red-400">
          {lead.intent_score}
        </p>
        <p className="text-2xs text-slate-500">intent</p>
      </div>
    </button>
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
  classification: "hot" | "warm" | "cold";
}) {
  const styles = {
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

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-sm text-slate-500">
      {message}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Skeleton loading state
// ────────────────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <div className="h-8 w-40 animate-pulse rounded bg-slate-800" />
        <div className="mt-2 h-4 w-64 animate-pulse rounded bg-slate-800/60" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-xl border border-slate-800 bg-slate-850/60"
          />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="h-80 animate-pulse rounded-xl border border-slate-800 bg-slate-850/60" />
        </div>
        <div className="h-80 animate-pulse rounded-xl border border-slate-800 bg-slate-850/60" />
      </div>
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
      </div>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
