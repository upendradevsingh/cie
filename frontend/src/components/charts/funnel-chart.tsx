import * as React from "react";
import { cn } from "@/lib/utils";

export interface FunnelSegment {
  label: string;
  count: number;
  color: string;
  bgColor: string;
}

export interface FunnelChartProps {
  segments?: FunnelSegment[];
  hotCount?: number;
  warmCount?: number;
  coldCount?: number;
  className?: string;
  showPercentages?: boolean;
}

const defaultSegments = (
  hot: number,
  warm: number,
  cold: number
): FunnelSegment[] => [
  {
    label: "Hot",
    count: hot,
    color: "text-red-400",
    bgColor: "bg-red-500",
  },
  {
    label: "Warm",
    count: warm,
    color: "text-amber-400",
    bgColor: "bg-amber-500",
  },
  {
    label: "Cold",
    count: cold,
    color: "text-blue-400",
    bgColor: "bg-blue-500",
  },
];

function FunnelChart({
  segments,
  hotCount = 0,
  warmCount = 0,
  coldCount = 0,
  className,
  showPercentages = true,
}: FunnelChartProps) {
  const funnelSegments =
    segments || defaultSegments(hotCount, warmCount, coldCount);
  const total = funnelSegments.reduce((sum, s) => sum + s.count, 0);

  // Calculate widths for the funnel visual — widest at top, narrowest at bottom
  const maxWidth = 100;
  const minWidth = 40;
  const widthStep =
    funnelSegments.length > 1
      ? (maxWidth - minWidth) / (funnelSegments.length - 1)
      : 0;

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      {funnelSegments.map((segment, index) => {
        const widthPercent = maxWidth - widthStep * index;
        const percentage = total > 0 ? ((segment.count / total) * 100).toFixed(0) : "0";

        return (
          <div
            key={segment.label}
            className="flex flex-col items-center w-full"
          >
            <div
              className={cn(
                "relative flex items-center justify-center rounded-md py-3 transition-all",
                segment.bgColor
              )}
              style={{
                width: `${widthPercent}%`,
                opacity: 0.85 + index * 0.05,
              }}
            >
              <div className="flex items-center gap-2 text-white">
                <span className="text-sm font-bold">{segment.count}</span>
                <span className="text-xs font-medium opacity-90">
                  {segment.label}
                </span>
                {showPercentages && total > 0 && (
                  <span className="text-xs opacity-75">({percentage}%)</span>
                )}
              </div>
            </div>
            {/* Connector triangle/trapezoid between segments */}
            {index < funnelSegments.length - 1 && (
              <div
                className="h-1 opacity-30"
                style={{
                  width: `${widthPercent - widthStep / 2}%`,
                  background: `linear-gradient(to bottom, ${getComputedBgColor(segment.bgColor)}, ${getComputedBgColor(funnelSegments[index + 1].bgColor)})`,
                }}
              />
            )}
          </div>
        );
      })}

      {/* Legend */}
      <div className="mt-3 flex items-center gap-4">
        {funnelSegments.map((segment) => (
          <div key={segment.label} className="flex items-center gap-1.5">
            <div className={cn("h-2.5 w-2.5 rounded-sm", segment.bgColor)} />
            <span className={cn("text-xs font-medium", segment.color)}>
              {segment.label}: {segment.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Maps Tailwind bg color classes to approximate CSS colors for gradients.
 * This is a fallback approach since we cannot read computed styles in JSX.
 */
function getComputedBgColor(bgClass: string): string {
  const colorMap: Record<string, string> = {
    "bg-red-500": "#ef4444",
    "bg-amber-500": "#f59e0b",
    "bg-blue-500": "#3b82f6",
    "bg-emerald-500": "#10b981",
    "bg-purple-500": "#a855f7",
    "bg-teal-500": "#14b8a6",
  };
  return colorMap[bgClass] || "#64748b";
}

export { FunnelChart };
