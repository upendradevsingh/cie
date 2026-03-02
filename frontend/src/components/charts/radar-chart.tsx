import {
  RadarChart as RechartsRadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  type TooltipProps,
} from "recharts";
import { cn } from "@/lib/utils";
import type { BANTScore } from "@/types/call";

export interface BANTRadarChartProps {
  bant: BANTScore;
  maxValue?: number;
  size?: number;
  color?: string;
  fillOpacity?: number;
  className?: string;
}

interface RadarDataPoint {
  axis: string;
  value: number;
  fullMark: number;
}

function CustomTooltip({
  active,
  payload,
}: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0];
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-2 shadow-lg">
      <p className="text-xs text-slate-400">{data?.payload?.axis}</p>
      <p className="text-sm font-medium text-white">
        {data?.value}/10
      </p>
    </div>
  );
}

function BANTRadarChart({
  bant,
  maxValue = 10,
  size = 250,
  color = "#0d9488",
  fillOpacity = 0.3,
  className,
}: BANTRadarChartProps) {
  const data: RadarDataPoint[] = [
    { axis: "Budget", value: bant.budget, fullMark: maxValue },
    { axis: "Authority", value: bant.authority, fullMark: maxValue },
    { axis: "Need", value: bant.need, fullMark: maxValue },
    { axis: "Timeline", value: bant.timeline, fullMark: maxValue },
  ];

  return (
    <div className={cn("w-full", className)} style={{ height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsRadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{
              fill: "#94a3b8",
              fontSize: 12,
              fontWeight: 500,
            }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, maxValue]}
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickCount={6}
            stroke="#334155"
          />
          <RechartsTooltip content={<CustomTooltip />} />
          <Radar
            name="BANT"
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={fillOpacity}
            strokeWidth={2}
          />
        </RechartsRadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export { BANTRadarChart };
