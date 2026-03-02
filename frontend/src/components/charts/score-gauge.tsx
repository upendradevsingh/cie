import * as React from "react";
import { cn } from "@/lib/utils";

export interface ScoreGaugeProps {
  score: number;
  maxScore?: number;
  size?: "sm" | "md" | "lg";
  label?: string;
  showLabel?: boolean;
  className?: string;
  animated?: boolean;
}

const sizeConfig = {
  sm: { dimension: 80, strokeWidth: 6, fontSize: "text-lg", labelSize: "text-xs" },
  md: { dimension: 120, strokeWidth: 8, fontSize: "text-2xl", labelSize: "text-sm" },
  lg: { dimension: 160, strokeWidth: 10, fontSize: "text-3xl", labelSize: "text-base" },
} as const;

function getScoreColorHex(score: number): string {
  if (score >= 70) return "#10b981"; // emerald-500
  if (score >= 40) return "#f59e0b"; // amber-500
  return "#ef4444"; // red-500
}

function getScoreTrackColor(score: number): string {
  if (score >= 70) return "rgba(16, 185, 129, 0.15)";
  if (score >= 40) return "rgba(245, 158, 11, 0.15)";
  return "rgba(239, 68, 68, 0.15)";
}

function ScoreGauge({
  score,
  maxScore = 100,
  size = "md",
  label,
  showLabel = true,
  className,
  animated = true,
}: ScoreGaugeProps) {
  const config = sizeConfig[size];
  const normalizedScore = Math.min(Math.max(score, 0), maxScore);
  const percentage = (normalizedScore / maxScore) * 100;

  const radius = (config.dimension - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const color = getScoreColorHex(percentage);
  const trackColor = getScoreTrackColor(percentage);

  const [displayOffset, setDisplayOffset] = React.useState(
    animated ? circumference : strokeDashoffset
  );

  React.useEffect(() => {
    if (animated) {
      // Small delay to trigger the CSS transition
      const timer = requestAnimationFrame(() => {
        setDisplayOffset(strokeDashoffset);
      });
      return () => cancelAnimationFrame(timer);
    } else {
      setDisplayOffset(strokeDashoffset);
    }
  }, [strokeDashoffset, animated, circumference]);

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <div className="relative" style={{ width: config.dimension, height: config.dimension }}>
        <svg
          width={config.dimension}
          height={config.dimension}
          viewBox={`0 0 ${config.dimension} ${config.dimension}`}
          className="-rotate-90"
        >
          {/* Background track */}
          <circle
            cx={config.dimension / 2}
            cy={config.dimension / 2}
            r={radius}
            fill="none"
            stroke={trackColor}
            strokeWidth={config.strokeWidth}
          />
          {/* Progress arc */}
          <circle
            cx={config.dimension / 2}
            cy={config.dimension / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={config.strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={displayOffset}
            style={{
              transition: animated ? "stroke-dashoffset 1s ease-out" : "none",
            }}
          />
        </svg>
        {/* Score number in center */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={cn("font-bold tabular-nums", config.fontSize)}
            style={{ color }}
          >
            {Math.round(normalizedScore)}
          </span>
        </div>
      </div>
      {showLabel && label && (
        <span className={cn("text-slate-400 font-medium", config.labelSize)}>
          {label}
        </span>
      )}
    </div>
  );
}

export { ScoreGauge };
