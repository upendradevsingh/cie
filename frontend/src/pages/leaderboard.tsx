import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Trophy,
  Medal,
  TrendingUp,
  TrendingDown,
  Minus,
  Flame,
  Phone,
  Target,
  BarChart3,
  LayoutGrid,
  List,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getLeaderboard } from "@/lib/api";
import type { AgentLeaderboardEntry, LeaderboardParams } from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Leaderboard Page
// ────────────────────────────────────────────────────────────────────

type TimePeriod = "week" | "month" | "quarter" | "all_time";
type ViewMode = "table" | "cards";

const PERIOD_LABELS: Record<TimePeriod, string> = {
  week: "This Week",
  month: "This Month",
  quarter: "This Quarter",
  all_time: "All Time",
};

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<TimePeriod>("month");
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  const params: LeaderboardParams = { period };

  const {
    data: leaderboard,
    isLoading,
    error,
  } = useQuery<AgentLeaderboardEntry[]>({
    queryKey: ["leaderboard", params],
    queryFn: () => getLeaderboard(params),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <Trophy className="h-6 w-6 text-amber-400" />
            Leaderboard
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Agent rankings by performance
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Period selector */}
          <div className="flex rounded-lg border border-slate-700 bg-slate-850 p-0.5">
            {(Object.keys(PERIOD_LABELS) as TimePeriod[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  period === p
                    ? "bg-accent-500/15 text-accent-400"
                    : "text-slate-500 hover:text-slate-300",
                )}
              >
                {PERIOD_LABELS[p]}
              </button>
            ))}
          </div>

          {/* View toggle */}
          <div className="flex rounded-lg border border-slate-700 bg-slate-850 p-0.5">
            <button
              onClick={() => setViewMode("table")}
              className={cn(
                "rounded-md p-1.5 transition-colors",
                viewMode === "table"
                  ? "bg-slate-700 text-white"
                  : "text-slate-500 hover:text-slate-300",
              )}
              aria-label="Table view"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("cards")}
              className={cn(
                "rounded-md p-1.5 transition-colors",
                viewMode === "cards"
                  ? "bg-slate-700 text-white"
                  : "text-slate-500 hover:text-slate-300",
              )}
              aria-label="Card view"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <LeaderboardSkeleton viewMode={viewMode} />
      ) : error ? (
        <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-slate-400">
          <AlertCircle className="h-8 w-8 text-red-400" />
          <p className="text-sm">Failed to load leaderboard data.</p>
        </div>
      ) : !leaderboard || leaderboard.length === 0 ? (
        <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3">
          <Trophy className="h-10 w-10 text-slate-600" />
          <p className="text-sm text-slate-500">
            No leaderboard data available for this period.
          </p>
        </div>
      ) : viewMode === "table" ? (
        <TableView entries={leaderboard} />
      ) : (
        <CardsView entries={leaderboard} />
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Table View
// ────────────────────────────────────────────────────────────────────

function TableView({ entries }: { entries: AgentLeaderboardEntry[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-slate-800 bg-slate-850/80">
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Rank
            </th>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Agent
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
              Total Calls
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
              Avg Quality
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
              Avg Intent
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
              Hot Leads
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-500">
              Trend
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {entries.map((entry) => (
            <tr
              key={entry.agent_id}
              className={cn(
                "transition-colors hover:bg-slate-800/40",
                entry.rank === 1 && "bg-amber-500/[0.03]",
              )}
            >
              <td className="px-4 py-3">
                <RankBadge rank={entry.rank} />
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <AgentAvatar
                    name={entry.agent_name}
                    url={entry.avatar_url}
                    rank={entry.rank}
                  />
                  <span className="text-sm font-medium text-white">
                    {entry.agent_name}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3 text-center">
                <span className="flex items-center justify-center gap-1 text-sm text-slate-300">
                  <Phone className="h-3 w-3 text-slate-500" />
                  {entry.total_calls}
                </span>
              </td>
              <td className="px-4 py-3 text-center">
                <ScoreGauge score={entry.avg_quality_score} />
              </td>
              <td className="px-4 py-3 text-center">
                <span className="text-sm font-semibold text-white">
                  {entry.avg_intent_score.toFixed(1)}
                </span>
              </td>
              <td className="px-4 py-3 text-center">
                <span className="flex items-center justify-center gap-1 text-sm font-semibold text-red-400">
                  <Flame className="h-3 w-3" />
                  {entry.hot_leads_count}
                </span>
              </td>
              <td className="px-4 py-3 text-center">
                <TrendIndicator
                  trend={entry.trend}
                  value={entry.improvement_trend}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Cards View
// ────────────────────────────────────────────────────────────────────

function CardsView({ entries }: { entries: AgentLeaderboardEntry[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {entries.map((entry) => (
        <div
          key={entry.agent_id}
          className={cn(
            "relative rounded-xl border p-5 transition-colors hover:border-slate-700",
            entry.rank === 1
              ? "border-amber-500/30 bg-amber-500/[0.03]"
              : entry.rank === 2
                ? "border-slate-500/30 bg-slate-850/60"
                : entry.rank === 3
                  ? "border-orange-800/30 bg-slate-850/60"
                  : "border-slate-800 bg-slate-850/60",
          )}
        >
          {/* Rank badge */}
          <div className="absolute right-4 top-4">
            <RankBadge rank={entry.rank} />
          </div>

          {/* Agent info */}
          <div className="flex items-center gap-3">
            <AgentAvatar
              name={entry.agent_name}
              url={entry.avatar_url}
              rank={entry.rank}
              size="lg"
            />
            <div>
              <p className="text-base font-semibold text-white">
                {entry.agent_name}
              </p>
              <TrendIndicator
                trend={entry.trend}
                value={entry.improvement_trend}
              />
            </div>
          </div>

          {/* Stats grid */}
          <div className="mt-4 grid grid-cols-2 gap-3">
            <StatMini
              icon={<Phone className="h-3.5 w-3.5" />}
              label="Calls"
              value={String(entry.total_calls)}
            />
            <StatMini
              icon={<BarChart3 className="h-3.5 w-3.5" />}
              label="Quality"
              value={entry.avg_quality_score.toFixed(1)}
              color={
                entry.avg_quality_score >= 75
                  ? "text-emerald-400"
                  : entry.avg_quality_score >= 50
                    ? "text-amber-400"
                    : "text-red-400"
              }
            />
            <StatMini
              icon={<Target className="h-3.5 w-3.5" />}
              label="Intent"
              value={entry.avg_intent_score.toFixed(1)}
            />
            <StatMini
              icon={<Flame className="h-3.5 w-3.5 text-red-400" />}
              label="Hot Leads"
              value={String(entry.hot_leads_count)}
              color="text-red-400"
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────────────────────────

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-500/20 text-sm font-bold text-amber-400">
        <Trophy className="h-4 w-4" />
      </span>
    );
  }
  if (rank === 2) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-500/20 text-sm font-bold text-slate-300">
        <Medal className="h-4 w-4" />
      </span>
    );
  }
  if (rank === 3) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-orange-800/20 text-sm font-bold text-orange-400">
        <Medal className="h-4 w-4" />
      </span>
    );
  }
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-xs font-bold text-slate-400">
      {rank}
    </span>
  );
}

function AgentAvatar({
  name,
  url,
  rank,
  size = "sm",
}: {
  name: string;
  url?: string;
  rank: number;
  size?: "sm" | "lg";
}) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const sizeClass = size === "lg" ? "h-12 w-12 text-base" : "h-8 w-8 text-xs";

  const ringColor =
    rank === 1
      ? "ring-2 ring-amber-500/40"
      : rank === 2
        ? "ring-2 ring-slate-400/30"
        : rank === 3
          ? "ring-2 ring-orange-700/30"
          : "";

  if (url) {
    return (
      <img
        src={url}
        alt={name}
        className={cn("rounded-full object-cover", sizeClass, ringColor)}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full bg-primary-600/30 font-semibold text-primary-200",
        sizeClass,
        ringColor,
      )}
    >
      {initials}
    </div>
  );
}

function ScoreGauge({ score }: { score: number }) {
  const color =
    score >= 75
      ? "text-emerald-400"
      : score >= 50
        ? "text-amber-400"
        : "text-red-400";

  return (
    <span className={cn("text-sm font-bold", color)}>
      {score.toFixed(1)}
    </span>
  );
}

function TrendIndicator({
  trend,
  value,
}: {
  trend: "up" | "down" | "stable";
  value: number;
}) {
  if (trend === "stable") {
    return (
      <span className="flex items-center gap-0.5 text-xs text-slate-500">
        <Minus className="h-3 w-3" />
        0%
      </span>
    );
  }

  const isUp = trend === "up";
  return (
    <span
      className={cn(
        "flex items-center gap-0.5 text-xs font-medium",
        isUp ? "text-emerald-400" : "text-red-400",
      )}
    >
      {isUp ? (
        <TrendingUp className="h-3 w-3" />
      ) : (
        <TrendingDown className="h-3 w-3" />
      )}
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

function StatMini({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-lg bg-slate-800/40 px-3 py-2">
      <div className="flex items-center gap-1 text-slate-500">{icon}</div>
      <p className={cn("mt-1 text-base font-bold", color ?? "text-white")}>
        {value}
      </p>
      <p className="text-2xs text-slate-500">{label}</p>
    </div>
  );
}

function LeaderboardSkeleton({ viewMode }: { viewMode: ViewMode }) {
  if (viewMode === "cards") {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-48 animate-pulse rounded-xl border border-slate-800 bg-slate-850/40"
            style={{ animationDelay: `${i * 80}ms` }}
          />
        ))}
      </div>
    );
  }

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
