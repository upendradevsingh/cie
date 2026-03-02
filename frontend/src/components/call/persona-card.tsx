import * as React from "react";
import { Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { BANTRadarChart } from "@/components/charts/radar-chart";
import type { PersonaData } from "@/types/call";

export interface PersonaCardProps {
  persona: PersonaData;
  className?: string;
  chartSize?: number;
}

function getBANTLabel(score: number): { label: string; color: string } {
  if (score >= 8) return { label: "Strong", color: "text-emerald-400" };
  if (score >= 5) return { label: "Moderate", color: "text-amber-400" };
  if (score >= 3) return { label: "Weak", color: "text-orange-400" };
  return { label: "Absent", color: "text-red-400" };
}

function getBANTBarColor(score: number): string {
  if (score >= 8) return "bg-emerald-500";
  if (score >= 5) return "bg-amber-500";
  if (score >= 3) return "bg-orange-500";
  return "bg-red-500";
}

function getBANTBarTrack(score: number): string {
  if (score >= 8) return "bg-emerald-500/15";
  if (score >= 5) return "bg-amber-500/15";
  if (score >= 3) return "bg-orange-500/15";
  return "bg-red-500/15";
}

function PersonaCard({
  persona,
  className,
  chartSize = 220,
}: PersonaCardProps) {
  const bantEntries: Array<{ key: string; label: string; value: number }> = [
    { key: "budget", label: "Budget", value: persona.bant.budget },
    { key: "authority", label: "Authority", value: persona.bant.authority },
    { key: "need", label: "Need", value: persona.bant.need },
    { key: "timeline", label: "Timeline", value: persona.bant.timeline },
  ];

  const totalBANT =
    persona.bant.budget +
    persona.bant.authority +
    persona.bant.need +
    persona.bant.timeline;
  const avgBANT = totalBANT / 4;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Persona type header */}
      <div className="flex items-center gap-3">
        <Badge
          variant="default"
          className="text-sm px-3 py-1 bg-[#1e3a5f]"
        >
          {persona.persona_type}
        </Badge>
        <span className="text-xs text-slate-500">
          BANT Avg: {avgBANT.toFixed(1)}/10
        </span>
      </div>

      {/* BANT Radar chart */}
      <div className="flex justify-center">
        <BANTRadarChart bant={persona.bant} size={chartSize} />
      </div>

      {/* Individual BANT scores */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-slate-300">BANT Breakdown</h4>
        {bantEntries.map((entry) => {
          const info = getBANTLabel(entry.value);
          const pct = (entry.value / 10) * 100;

          return (
            <div key={entry.key} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-300">{entry.label}</span>
                <div className="flex items-center gap-2">
                  <span className={cn("text-xs font-medium", info.color)}>
                    {info.label}
                  </span>
                  <span className="text-sm font-semibold text-white tabular-nums">
                    {entry.value}/10
                  </span>
                </div>
              </div>
              <div
                className={cn(
                  "h-1.5 w-full rounded-full overflow-hidden",
                  getBANTBarTrack(entry.value)
                )}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    getBANTBarColor(entry.value)
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Discovery insights */}
      {persona.discovery_insights.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1.5">
            <Lightbulb className="h-4 w-4 text-amber-400" />
            Discovery Insights
          </h4>
          <ul className="space-y-1.5">
            {persona.discovery_insights.map((insight, index) => (
              <li
                key={index}
                className="flex items-start gap-2 text-sm text-slate-300"
              >
                <span className="text-slate-600 shrink-0 mt-1.5 h-1 w-1 rounded-full bg-slate-600" />
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export { PersonaCard };
