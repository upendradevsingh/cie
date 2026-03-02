import * as React from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { cn, getIntentLabel, getIntentBgColor } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ScoreGauge } from "@/components/charts/score-gauge";
import type { LeadIntelligence, IntentSignal } from "@/types/call";

export interface IntentPanelProps {
  intelligence: LeadIntelligence;
  className?: string;
}

function IntentPanel({ intelligence, className }: IntentPanelProps) {
  const [showObjections, setShowObjections] = React.useState(false);
  const [showSignalDetails, setShowSignalDetails] = React.useState<
    Record<string, boolean>
  >({});

  const detectedCount = intelligence.signals.filter((s) => s.detected).length;
  const totalSignals = intelligence.signals.length;

  const toggleSignalDetail = (id: string) => {
    setShowSignalDetails((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Top row: Score gauge + Classification */}
      <div className="flex items-center gap-6">
        <ScoreGauge
          score={intelligence.intent_score}
          size="md"
          label="Intent Score"
        />
        <div className="flex flex-col gap-2">
          <Badge
            className={cn(
              "text-sm px-3 py-1 font-semibold",
              getIntentBgColor(intelligence.classification)
            )}
          >
            {getIntentLabel(intelligence.classification)}
          </Badge>
          <p className="text-xs text-slate-500">
            {detectedCount}/{totalSignals} signals detected
          </p>
        </div>
      </div>

      {/* Intent signals list */}
      <div className="space-y-1">
        <h4 className="text-sm font-medium text-slate-300 mb-2">
          Intent Signals
        </h4>
        {intelligence.signals.map((signal) => (
          <SignalRow
            key={signal.id}
            signal={signal}
            expanded={!!showSignalDetails[signal.id]}
            onToggle={() => toggleSignalDetail(signal.id)}
          />
        ))}

        {intelligence.signals.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-3">
            No intent signals configured
          </p>
        )}
      </div>

      {/* Key objections */}
      {intelligence.key_objections.length > 0 && (
        <div>
          <button
            onClick={() => setShowObjections((prev) => !prev)}
            className="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors mb-2"
          >
            {showObjections ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Key Objections ({intelligence.key_objections.length})
          </button>

          {showObjections && (
            <div className="space-y-2 pl-6">
              {intelligence.key_objections.map((obj, index) => (
                <div
                  key={index}
                  className="rounded-lg border border-slate-800 p-3 bg-slate-800/20"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-slate-200">{obj.objection}</p>
                    <Badge variant="outline" className="text-[10px] shrink-0">
                      {obj.category}
                    </Badge>
                  </div>
                  {"severity" in obj && (
                    <Badge
                      variant={
                        obj.severity === "high"
                          ? "destructive"
                          : obj.severity === "medium"
                            ? "warning"
                            : "secondary"
                      }
                      className="mt-1.5 text-[10px]"
                    >
                      {obj.severity} severity
                    </Badge>
                  )}
                  {"rebuttal_suggestion" in obj && obj.rebuttal_suggestion && (
                    <p className="mt-2 text-xs text-teal-400 border-l-2 border-teal-500/30 pl-2">
                      Suggested rebuttal: {obj.rebuttal_suggestion}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Buying signals */}
      {"buying_signals" in intelligence &&
        intelligence.buying_signals &&
        intelligence.buying_signals.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-2">
              Buying Signals
            </h4>
            <ul className="space-y-1">
              {intelligence.buying_signals.map((signal, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2 text-sm text-emerald-400"
                >
                  <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                  <span className="text-slate-300">{signal}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
    </div>
  );
}

interface SignalRowProps {
  signal: IntentSignal;
  expanded: boolean;
  onToggle: () => void;
}

function SignalRow({ signal, expanded, onToggle }: SignalRowProps) {
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2 transition-colors",
        signal.detected
          ? "border-emerald-500/20 bg-emerald-500/5"
          : "border-slate-800 bg-slate-800/20"
      )}
    >
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between"
      >
        <div className="flex items-center gap-2">
          {signal.detected ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 text-slate-600 shrink-0" />
          )}
          <span
            className={cn(
              "text-sm",
              signal.detected ? "text-slate-200" : "text-slate-500"
            )}
          >
            {signal.name}
          </span>
        </div>
        {signal.details && (
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 text-slate-500 transition-transform",
              expanded && "rotate-180"
            )}
          />
        )}
      </button>
      {expanded && signal.details && (
        <p className="mt-1.5 pl-6 text-xs text-slate-400 leading-relaxed">
          {signal.details}
        </p>
      )}
    </div>
  );
}

export { IntentPanel };
