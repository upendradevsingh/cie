import * as React from "react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface BarChartItem {
  label: string;
  value: number;
  maxValue: number;
  color?: string;
  tooltip?: string;
}

export interface HorizontalBarChartProps {
  data: BarChartItem[];
  showValues?: boolean;
  barHeight?: number;
  className?: string;
  animated?: boolean;
}

function getDefaultColor(value: number, maxValue: number): string {
  const percentage = (value / maxValue) * 100;
  if (percentage >= 70) return "bg-emerald-500";
  if (percentage >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function HorizontalBarChart({
  data,
  showValues = true,
  barHeight = 8,
  className,
  animated = true,
}: HorizontalBarChartProps) {
  const [mounted, setMounted] = React.useState(!animated);

  React.useEffect(() => {
    if (animated) {
      const timer = requestAnimationFrame(() => setMounted(true));
      return () => cancelAnimationFrame(timer);
    }
  }, [animated]);

  return (
    <TooltipProvider delayDuration={200}>
      <div className={cn("space-y-3", className)}>
        {data.map((item, index) => {
          const percentage = Math.min((item.value / item.maxValue) * 100, 100);
          const colorClass = item.color || getDefaultColor(item.value, item.maxValue);

          return (
            <div key={`${item.label}-${index}`} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 truncate mr-2">{item.label}</span>
                {showValues && (
                  <span className="text-slate-400 tabular-nums shrink-0">
                    {item.value}/{item.maxValue}
                  </span>
                )}
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div
                    className="w-full rounded-full bg-slate-800 overflow-hidden"
                    style={{ height: barHeight }}
                  >
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        colorClass,
                        animated ? "duration-700 ease-out" : ""
                      )}
                      style={{
                        width: mounted ? `${percentage}%` : "0%",
                      }}
                    />
                  </div>
                </TooltipTrigger>
                {item.tooltip && (
                  <TooltipContent>
                    <p className="max-w-xs">{item.tooltip}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            </div>
          );
        })}
      </div>
    </TooltipProvider>
  );
}

export { HorizontalBarChart };
