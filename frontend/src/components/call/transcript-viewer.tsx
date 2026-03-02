import * as React from "react";
import { Search, MessageSquare, Clock } from "lucide-react";
import { cn, formatTimestamp } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { TranscriptSegment } from "@/types/call";

export interface TranscriptViewerProps {
  segments: TranscriptSegment[];
  className?: string;
  maxHeight?: string;
  onTimestampClick?: (time: number) => void;
  highlightSegmentIds?: Set<string>;
}

function TranscriptViewer({
  segments,
  className,
  maxHeight = "600px",
  onTimestampClick,
  highlightSegmentIds,
}: TranscriptViewerProps) {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [filteredSegments, setFilteredSegments] = React.useState(segments);
  const scrollContainerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredSegments(segments);
      return;
    }

    const query = searchQuery.toLowerCase();
    setFilteredSegments(
      segments.filter(
        (seg) =>
          seg.text.toLowerCase().includes(query) ||
          seg.speaker_name.toLowerCase().includes(query)
      )
    );
  }, [searchQuery, segments]);

  const matchCount = searchQuery.trim()
    ? filteredSegments.length
    : undefined;

  return (
    <div className={cn("flex flex-col", className)}>
      {/* Search bar */}
      <div className="relative mb-3">
        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search transcript..."
          className="pl-9 h-8 bg-slate-900/50 border-slate-800"
        />
        {matchCount !== undefined && (
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-500">
            {matchCount} match{matchCount !== 1 ? "es" : ""}
          </span>
        )}
      </div>

      {/* Transcript messages */}
      <div
        ref={scrollContainerRef}
        className="space-y-1 overflow-y-auto pr-1 custom-scrollbar"
        style={{ maxHeight }}
      >
        {filteredSegments.length === 0 && searchQuery.trim() && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <MessageSquare className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No matches found</p>
          </div>
        )}

        {filteredSegments.length === 0 && !searchQuery.trim() && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <MessageSquare className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No transcript available</p>
          </div>
        )}

        {filteredSegments.map((segment) => {
          const isAgent = segment.speaker === "agent";
          const isHighlighted = highlightSegmentIds?.has(segment.id);
          const isKeyMoment = segment.is_key_moment;

          return (
            <div
              key={segment.id}
              className={cn(
                "group flex gap-3 rounded-lg p-3 transition-colors",
                isHighlighted && "bg-teal-500/10 ring-1 ring-teal-500/20",
                isKeyMoment && !isHighlighted && "bg-amber-500/5 ring-1 ring-amber-500/10",
                !isHighlighted && !isKeyMoment && "hover:bg-slate-800/30"
              )}
            >
              {/* Speaker indicator */}
              <div className="flex flex-col items-center gap-1 shrink-0 pt-0.5">
                <div
                  className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold",
                    isAgent
                      ? "bg-[#1e3a5f] text-blue-200"
                      : "bg-slate-700 text-slate-300"
                  )}
                >
                  {isAgent ? "A" : "C"}
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={cn(
                      "text-xs font-semibold",
                      isAgent ? "text-blue-400" : "text-slate-400"
                    )}
                  >
                    {segment.speaker_name}
                  </span>
                  <button
                    onClick={() => onTimestampClick?.(segment.start_time)}
                    className="flex items-center gap-0.5 text-xs text-slate-600 hover:text-teal-400 transition-colors"
                  >
                    <Clock className="h-3 w-3" />
                    {formatTimestamp(segment.start_time)}
                  </button>
                  {isKeyMoment && segment.key_moment_label && (
                    <Badge variant="warning" className="text-[10px] px-1.5 py-0">
                      {segment.key_moment_label}
                    </Badge>
                  )}
                </div>
                <p
                  className={cn(
                    "text-sm leading-relaxed",
                    isAgent ? "text-slate-200" : "text-slate-300"
                  )}
                >
                  {searchQuery.trim()
                    ? highlightText(segment.text, searchQuery)
                    : segment.text}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary footer */}
      {segments.length > 0 && (
        <div className="mt-2 flex items-center gap-4 border-t border-slate-800 pt-2 text-xs text-slate-500">
          <span>{segments.length} messages</span>
          <span>
            Duration: {formatTimestamp(segments[segments.length - 1]?.end_time ?? 0)}
          </span>
          <span>
            Agent: {segments.filter((s) => s.speaker === "agent").length} |
            Customer: {segments.filter((s) => s.speaker === "customer").length}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Highlights occurrences of `query` within `text` using a <mark> element.
 */
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;

  const regex = new RegExp(`(${escapeRegex(query)})`, "gi");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark
            key={i}
            className="bg-teal-500/30 text-teal-200 rounded-sm px-0.5"
          >
            {part}
          </mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        )
      )}
    </>
  );
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export { TranscriptViewer };
