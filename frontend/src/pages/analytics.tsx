import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Loader2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getAnalyticsData } from "@/lib/api";
import type {
  AnalyticsData,
  CallTrend,
  AgentAnalytics,
  ConversionFunnel,
  ParameterTrend,
  ScoreDistribution,
} from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Analytics Page
// ────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [dateFrom, setDateFrom] = useState(
    format(subDays(new Date(), 30), "yyyy-MM-dd"),
  );
  const [dateTo, setDateTo] = useState(format(new Date(), "yyyy-MM-dd"));

  const {
    data: analytics,
    isLoading,
    error,
  } = useQuery<AnalyticsData>({
    queryKey: ["analytics", "trends", dateFrom, dateTo],
    queryFn: () => getAnalyticsData({ date_from: dateFrom, date_to: dateTo }),
  });

  if (isLoading) {
    return <AnalyticsSkeleton />;
  }

  if (error || !analytics) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-slate-400">
        <AlertCircle className="h-8 w-8 text-red-400" />
        <p className="text-sm">Failed to load analytics data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="mt-1 text-sm text-slate-400">
            Team performance and quality insights
          </p>
        </div>

        {/* Date range picker */}
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-slate-500" />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-850 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
          />
          <span className="text-sm text-slate-600">to</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-850 px-3 py-1.5 text-sm text-white focus:border-accent-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Call Volume & Quality Trend */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Call Volume" subtitle="Daily call count over time">
          <CallVolumeChart data={analytics.call_volume} />
        </ChartCard>

        <ChartCard
          title="Average Quality Trend"
          subtitle="Quality score over time"
        >
          <QualityTrendChart data={analytics.avg_quality_trend} />
        </ChartCard>
      </div>

      {/* Conversion Funnel & Lead Classification */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ChartCard title="Conversion Funnel" className="lg:col-span-1">
          <ConversionFunnelChart data={analytics.conversion_funnel} />
        </ChartCard>

        <ChartCard
          title="Lead Classification Breakdown"
          className="lg:col-span-1"
        >
          <LeadClassificationChart data={analytics.lead_classification} />
        </ChartCard>

        <ChartCard
          title="Score Distribution"
          subtitle="Quality score histogram"
          className="lg:col-span-1"
        >
          <ScoreDistributionChart data={analytics.score_distribution} />
        </ChartCard>
      </div>

      {/* Agent Comparison */}
      <ChartCard title="Agent Comparison" subtitle="Average quality score by agent">
        <AgentComparisonChart agents={analytics.agent_comparison} />
      </ChartCard>

      {/* Parameter Trends */}
      <div className="rounded-xl border border-slate-800 bg-slate-850/60 p-5">
        <h3 className="mb-4 text-sm font-semibold text-white">
          Quality Parameter Trends
        </h3>
        <p className="mb-4 text-xs text-slate-500">
          Comparing current period vs previous period
        </p>
        {analytics.parameter_trends.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Not enough data to show parameter trends.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {analytics.parameter_trends.map((trend) => (
              <ParameterTrendCard key={trend.parameter_name} trend={trend} />
            ))}
          </div>
        )}
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
  className,
  children,
}: {
  title: string;
  subtitle?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-800 bg-slate-850/60 p-5",
        className,
      )}
    >
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
// Call Volume Chart
// ────────────────────────────────────────────────────────────────────

function CallVolumeChart({ data }: { data: CallTrend[] }) {
  if (data.length === 0) {
    return <EmptyChart />;
  }

  const chartData = data.map((d) => ({
    ...d,
    label: format(new Date(d.date), "MMM d"),
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="volumeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1e3a5f" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#1e3a5f" stopOpacity={0} />
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
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="count"
            name="Calls"
            stroke="#3b699f"
            strokeWidth={2}
            fill="url(#volumeGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Quality Trend Chart
// ────────────────────────────────────────────────────────────────────

function QualityTrendChart({ data }: { data: CallTrend[] }) {
  if (data.length === 0) {
    return <EmptyChart />;
  }

  const chartData = data.map((d) => ({
    ...d,
    label: format(new Date(d.date), "MMM d"),
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="qualityGrad" x1="0" y1="0" x2="0" y2="1">
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
            domain={[0, 100]}
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="avg_score"
            name="Avg Score"
            stroke="#0d9488"
            strokeWidth={2}
            fill="url(#qualityGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Conversion Funnel
// ────────────────────────────────────────────────────────────────────

function ConversionFunnelChart({ data }: { data: ConversionFunnel[] }) {
  if (data.length === 0) {
    return <EmptyChart />;
  }

  const max = Math.max(...data.map((d) => d.count));

  return (
    <div className="space-y-3">
      {data.map((stage, i) => {
        const width = max > 0 ? (stage.count / max) * 100 : 0;
        return (
          <div key={stage.stage}>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs text-slate-400">{stage.stage}</span>
              <span className="text-xs font-semibold text-white">
                {stage.count}
              </span>
            </div>
            <div className="h-6 overflow-hidden rounded bg-slate-800">
              <div
                className="h-full rounded transition-all duration-500"
                style={{
                  width: `${width}%`,
                  background: `linear-gradient(90deg, #1e3a5f ${100 - i * 15}%, #0d9488)`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Lead Classification Pie
// ────────────────────────────────────────────────────────────────────

const INTENT_COLORS: Record<string, string> = {
  hot: "#ef4444",
  warm: "#f59e0b",
  cold: "#3b82f6",
};

function LeadClassificationChart({
  data,
}: {
  data: Array<{ classification: string; count: number }>;
}) {
  if (data.length === 0 || data.every((d) => d.count === 0)) {
    return <EmptyChart />;
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            dataKey="count"
            nameKey="classification"
            strokeWidth={0}
          >
            {data.map((entry) => (
              <Cell
                key={entry.classification}
                fill={INTENT_COLORS[entry.classification] ?? "#475569"}
              />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
          <Legend
            formatter={(value: string) => (
              <span className="text-xs capitalize text-slate-400">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Score Distribution Histogram
// ────────────────────────────────────────────────────────────────────

function ScoreDistributionChart({ data }: { data: ScoreDistribution[] }) {
  if (data.length === 0) {
    return <EmptyChart />;
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
          <Tooltip content={<ChartTooltip />} />
          <Bar
            dataKey="count"
            name="Calls"
            fill="#1e3a5f"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Agent Comparison Chart
// ────────────────────────────────────────────────────────────────────

function AgentComparisonChart({ agents }: { agents: AgentAnalytics[] }) {
  if (agents.length === 0) {
    return <EmptyChart />;
  }

  const chartData = agents.map((a) => ({
    name: a.agent_name,
    quality: Math.round(a.avg_quality_score * 10) / 10,
    intent: Math.round(a.avg_intent_score * 10) / 10,
    calls: a.total_calls,
  }));

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="name"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "#64748b", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend
            formatter={(value: string) => (
              <span className="text-xs text-slate-400">{value}</span>
            )}
          />
          <Bar
            dataKey="quality"
            name="Quality Score"
            fill="#0d9488"
            radius={[4, 4, 0, 0]}
            barSize={24}
          />
          <Bar
            dataKey="intent"
            name="Intent Score"
            fill="#1e3a5f"
            radius={[4, 4, 0, 0]}
            barSize={24}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Parameter Trend Card
// ────────────────────────────────────────────────────────────────────

function ParameterTrendCard({ trend }: { trend: ParameterTrend }) {
  const isPositive = trend.change > 0;
  const isNeutral = trend.change === 0;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-800/30 p-3">
      <p className="truncate text-xs font-medium text-white" title={trend.parameter_name}>
        {trend.parameter_name}
      </p>
      <div className="mt-2 flex items-end justify-between">
        <span className="text-lg font-bold text-white">
          {trend.current_avg.toFixed(1)}
        </span>
        <div
          className={cn(
            "flex items-center gap-0.5 text-xs font-medium",
            isPositive
              ? "text-emerald-400"
              : isNeutral
                ? "text-slate-500"
                : "text-red-400",
          )}
        >
          {isPositive ? (
            <TrendingUp className="h-3 w-3" />
          ) : isNeutral ? (
            <Minus className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {isNeutral ? "0%" : `${isPositive ? "+" : ""}${trend.change.toFixed(1)}%`}
        </div>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-700">
        <div
          className={cn(
            "h-full rounded-full",
            trend.current_avg >= 7
              ? "bg-emerald-500"
              : trend.current_avg >= 4
                ? "bg-amber-500"
                : "bg-red-500",
          )}
          style={{ width: `${(trend.current_avg / 10) * 100}%` }}
        />
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Shared chart helpers
// ────────────────────────────────────────────────────────────────────

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-xl">
      {label && <p className="mb-1 font-medium text-slate-300">{label}</p>}
      {payload.map((entry, i) => (
        <p key={i} className="text-white">
          <span
            className="mr-1 inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          {entry.name}: <span className="font-semibold">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="flex h-48 items-center justify-center text-sm text-slate-500">
      Not enough data to display chart.
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="h-8 w-36 animate-pulse rounded bg-slate-800" />
          <div className="mt-2 h-4 w-56 animate-pulse rounded bg-slate-800/60" />
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-32 animate-pulse rounded bg-slate-800" />
          <div className="h-9 w-32 animate-pulse rounded bg-slate-800" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="h-80 animate-pulse rounded-xl border border-slate-800 bg-slate-850/40"
          />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-80 animate-pulse rounded-xl border border-slate-800 bg-slate-850/40"
          />
        ))}
      </div>
      <div className="flex justify-center py-10">
        <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
      </div>
    </div>
  );
}
