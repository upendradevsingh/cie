import * as React from "react";
import {
  CheckCircle2,
  Circle,
  ArrowRight,
  MessageSquareReply,
  Clock,
} from "lucide-react";
import { cn, formatUrgency, getUrgencyColor } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { ActionItem, PathToConversion } from "@/types/call";

export interface ActionItemsListProps {
  items: ActionItem[];
  pathToConversion?: PathToConversion;
  className?: string;
  onToggleComplete?: (itemId: string, completed: boolean) => void;
}

function getUrgencyBadgeVariant(
  urgency: string
): "destructive" | "warning" | "default" | "secondary" {
  switch (urgency) {
    case "immediate":
      return "destructive";
    case "this_week":
      return "warning";
    case "next_week":
      return "default";
    default:
      return "secondary";
  }
}

function ActionItemsList({
  items,
  pathToConversion,
  className,
  onToggleComplete,
}: ActionItemsListProps) {
  // Sort by urgency priority: immediate > this_week > next_week > nurture
  const urgencyOrder: Record<string, number> = {
    immediate: 0,
    this_week: 1,
    next_week: 2,
    nurture: 3,
  };

  const sortedItems = React.useMemo(
    () =>
      [...items].sort((a, b) => {
        // Incomplete items first
        if (a.completed !== b.completed) return a.completed ? 1 : -1;
        // Then by urgency
        return (urgencyOrder[a.urgency] ?? 4) - (urgencyOrder[b.urgency] ?? 4);
      }),
    [items]
  );

  const completedCount = items.filter((i) => i.completed).length;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Action items */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-slate-300">
            Action Items
          </h4>
          <span className="text-xs text-slate-500">
            {completedCount}/{items.length} completed
          </span>
        </div>

        {sortedItems.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-4">
            No action items extracted
          </p>
        )}

        <div className="space-y-2">
          {sortedItems.map((item) => (
            <div
              key={item.id}
              className={cn(
                "flex items-start gap-3 rounded-lg border p-3 transition-colors",
                item.completed
                  ? "border-slate-800/50 bg-slate-800/10 opacity-60"
                  : "border-slate-800 bg-slate-800/20"
              )}
            >
              <button
                onClick={() => onToggleComplete?.(item.id, !item.completed)}
                className="mt-0.5 shrink-0"
                aria-label={
                  item.completed ? "Mark as incomplete" : "Mark as complete"
                }
              >
                {item.completed ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                ) : (
                  <Circle className="h-5 w-5 text-slate-600 hover:text-slate-400 transition-colors" />
                )}
              </button>

              <div className="flex-1 min-w-0">
                <p
                  className={cn(
                    "text-sm",
                    item.completed
                      ? "text-slate-500 line-through"
                      : "text-slate-200"
                  )}
                >
                  {item.text}
                </p>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <Badge
                    variant={getUrgencyBadgeVariant(item.urgency)}
                    className="text-[10px]"
                  >
                    <Clock className="h-3 w-3 mr-0.5" />
                    {formatUrgency(item.urgency)}
                  </Badge>
                  {item.category && (
                    <Badge variant="outline" className="text-[10px]">
                      {item.category}
                    </Badge>
                  )}
                  {"priority" in item && item.priority && (
                    <Badge
                      variant={
                        item.priority === "high"
                          ? "destructive"
                          : item.priority === "medium"
                            ? "warning"
                            : "secondary"
                      }
                      className="text-[10px]"
                    >
                      {item.priority}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Path to conversion */}
      {pathToConversion && (
        <>
          <Separator />

          {/* Next best action */}
          {"next_best_action" in pathToConversion &&
            pathToConversion.next_best_action && (
              <div className="rounded-lg border border-teal-500/20 bg-teal-500/5 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ArrowRight className="h-4 w-4 text-teal-400" />
                  <h4 className="text-sm font-medium text-teal-400">
                    Next Best Action
                  </h4>
                </div>
                <p className="text-sm text-slate-200">
                  {pathToConversion.next_best_action}
                </p>
              </div>
            )}

          {/* Talking points */}
          {pathToConversion.talking_points.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1.5">
                <ArrowRight className="h-4 w-4 text-teal-400" />
                Path to Conversion — Talking Points
              </h4>
              <ul className="space-y-2 pl-1">
                {pathToConversion.talking_points.map((point, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 text-sm text-slate-300"
                  >
                    <span className="text-teal-400 font-mono text-xs mt-0.5 shrink-0">
                      {index + 1}.
                    </span>
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Rebuttals */}
          {pathToConversion.rebuttals.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1.5">
                <MessageSquareReply className="h-4 w-4 text-amber-400" />
                Objection Rebuttals
              </h4>
              <div className="space-y-2">
                {pathToConversion.rebuttals.map((rebuttal, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-slate-800 p-3 bg-slate-800/20"
                  >
                    <p className="text-xs font-medium text-amber-400 mb-1">
                      Objection: {rebuttal.objection}
                    </p>
                    <p className="text-sm text-slate-300">
                      {rebuttal.rebuttal}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Follow-up urgency */}
          <div className="flex items-center gap-2 pt-2">
            <Clock className="h-4 w-4 text-slate-500" />
            <span className="text-xs text-slate-500">Follow-up urgency:</span>
            <span
              className={cn(
                "text-xs font-semibold",
                getUrgencyColor(pathToConversion.follow_up_urgency)
              )}
            >
              {formatUrgency(pathToConversion.follow_up_urgency)}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

export { ActionItemsList };
