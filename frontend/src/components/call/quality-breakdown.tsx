import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn, scoreToPercent } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { QualityScore } from "@/types/call";

export interface QualityBreakdownProps {
  scores: QualityScore[];
  className?: string;
  defaultExpanded?: boolean;
}

interface CategoryGroup {
  category: string;
  scores: QualityScore[];
  avgScore: number;
  avgMaxScore: number;
}

function getBarColor(score: number, maxScore: number): string {
  const pct = (score / maxScore) * 100;
  if (pct >= 70) return "bg-emerald-500";
  if (pct >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function getBarTrackColor(score: number, maxScore: number): string {
  const pct = (score / maxScore) * 100;
  if (pct >= 70) return "bg-emerald-500/15";
  if (pct >= 40) return "bg-amber-500/15";
  return "bg-red-500/15";
}

function getScoreTextColor(score: number, maxScore: number): string {
  const pct = (score / maxScore) * 100;
  if (pct >= 70) return "text-emerald-400";
  if (pct >= 40) return "text-amber-400";
  return "text-red-400";
}

function QualityBreakdown({
  scores,
  className,
  defaultExpanded = false,
}: QualityBreakdownProps) {
  // Group scores by category
  const groups = React.useMemo<CategoryGroup[]>(() => {
    const map = new Map<string, QualityScore[]>();
    for (const score of scores) {
      const existing = map.get(score.category) || [];
      existing.push(score);
      map.set(score.category, existing);
    }

    return Array.from(map.entries()).map(([category, categoryScores]) => {
      const totalScore = categoryScores.reduce((sum, s) => sum + s.score, 0);
      const totalMax = categoryScores.reduce((sum, s) => sum + s.max_score, 0);
      return {
        category,
        scores: categoryScores,
        avgScore: totalScore / categoryScores.length,
        avgMaxScore: totalMax / categoryScores.length,
      };
    });
  }, [scores]);

  return (
    <div className={cn("space-y-4", className)}>
      {groups.map((group) => (
        <CategorySection
          key={group.category}
          group={group}
          defaultExpanded={defaultExpanded}
        />
      ))}

      {scores.length === 0 && (
        <p className="text-sm text-slate-500 text-center py-4">
          No quality scores available
        </p>
      )}
    </div>
  );
}

interface CategorySectionProps {
  group: CategoryGroup;
  defaultExpanded: boolean;
}

function CategorySection({ group, defaultExpanded }: CategorySectionProps) {
  const [expanded, setExpanded] = React.useState(defaultExpanded);

  const categoryPct = scoreToPercent(group.avgScore, group.avgMaxScore);

  return (
    <div className="rounded-lg border border-slate-800 overflow-hidden">
      {/* Category header */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 bg-slate-800/30 hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-400" />
          )}
          <span className="text-sm font-medium text-white">
            {group.category}
          </span>
          <Badge variant="secondary" className="text-[10px]">
            {group.scores.length} parameter{group.scores.length !== 1 ? "s" : ""}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "text-sm font-bold tabular-nums",
              getScoreTextColor(group.avgScore, group.avgMaxScore)
            )}
          >
            {group.avgScore.toFixed(1)}/{group.avgMaxScore.toFixed(0)}
          </span>
          <span className="text-xs text-slate-500">avg</span>
        </div>
      </button>

      {/* Parameter list */}
      {expanded && (
        <div className="divide-y divide-slate-800/50">
          {group.scores.map((score) => (
            <ParameterRow key={score.parameter_id} score={score} />
          ))}
        </div>
      )}
    </div>
  );
}

interface ParameterRowProps {
  score: QualityScore;
}

function ParameterRow({ score }: ParameterRowProps) {
  const [showJustification, setShowJustification] = React.useState(false);
  const pct = (score.score / score.max_score) * 100;

  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between mb-1.5">
        <button
          onClick={() => setShowJustification((prev) => !prev)}
          className="text-sm text-slate-300 hover:text-white transition-colors text-left"
        >
          {score.parameter_name}
        </button>
        <span
          className={cn(
            "text-sm font-semibold tabular-nums",
            getScoreTextColor(score.score, score.max_score)
          )}
        >
          {score.score}/{score.max_score}
        </span>
      </div>

      {/* Bar */}
      <div
        className={cn(
          "h-1.5 w-full rounded-full overflow-hidden",
          getBarTrackColor(score.score, score.max_score)
        )}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            getBarColor(score.score, score.max_score)
          )}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Justification */}
      {showJustification && score.justification && (
        <p className="mt-2 text-xs text-slate-400 leading-relaxed border-l-2 border-slate-700 pl-3">
          {score.justification}
        </p>
      )}
    </div>
  );
}

export { QualityBreakdown };
