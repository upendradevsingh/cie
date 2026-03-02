import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import { cn } from "@/lib/utils";

export interface TrendChartProps<T extends Record<string, unknown>> {
  data: T[];
  xKey: keyof T & string;
  yKey: keyof T & string;
  color?: string;
  height?: number;
  showGrid?: boolean;
  showXAxis?: boolean;
  showYAxis?: boolean;
  yDomain?: [number, number];
  xLabel?: string;
  yLabel?: string;
  tooltipFormatter?: (value: number) => string;
  className?: string;
  strokeWidth?: number;
  dot?: boolean;
  additionalLines?: Array<{
    key: keyof T & string;
    color: string;
    strokeDasharray?: string;
  }>;
}

function CustomTooltip({
  active,
  payload,
  label,
  formatter,
}: TooltipProps<number, string> & {
  formatter?: (value: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3 shadow-lg">
      <p className="mb-1 text-xs text-slate-400">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-sm font-medium text-white">
            {formatter
              ? formatter(entry.value as number)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function TrendChart<T extends Record<string, unknown>>({
  data,
  xKey,
  yKey,
  color = "#0d9488",
  height = 300,
  showGrid = true,
  showXAxis = true,
  showYAxis = true,
  yDomain,
  tooltipFormatter,
  className,
  strokeWidth = 2,
  dot = false,
  additionalLines = [],
}: TrendChartProps<T>) {
  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              vertical={false}
            />
          )}
          {showXAxis && (
            <XAxis
              dataKey={xKey}
              stroke="#64748b"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
          )}
          {showYAxis && (
            <YAxis
              stroke="#64748b"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={yDomain}
            />
          )}
          <RechartsTooltip
            content={
              <CustomTooltip formatter={tooltipFormatter} />
            }
          />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke={color}
            strokeWidth={strokeWidth}
            dot={dot}
            activeDot={{ r: 4, fill: color }}
          />
          {additionalLines.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              stroke={line.color}
              strokeWidth={strokeWidth}
              strokeDasharray={line.strokeDasharray}
              dot={false}
              activeDot={{ r: 4, fill: line.color }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export { TrendChart };
