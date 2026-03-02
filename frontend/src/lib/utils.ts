import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combines class names using clsx and merges Tailwind classes intelligently
 * with tailwind-merge to avoid conflicts.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Returns a CSS class name based on a score value (0-100).
 * High (>=70): green, Medium (40-69): amber, Low (<40): red
 */
export function getScoreColor(score: number): string {
  if (score >= 70) return "score-high";
  if (score >= 40) return "score-medium";
  return "score-low";
}

/**
 * Returns a CSS class name for background-styled score badges.
 */
export function getScoreBgColor(score: number): string {
  if (score >= 70) return "score-bg-high";
  if (score >= 40) return "score-bg-medium";
  return "score-bg-low";
}

/**
 * Returns the intent label based on classification.
 */
export function getIntentLabel(intent: "hot" | "warm" | "cold"): string {
  const labels: Record<string, string> = {
    hot: "Hot Lead",
    warm: "Warm Lead",
    cold: "Cold Lead",
  };
  return labels[intent] ?? "Unknown";
}

/**
 * Returns a Tailwind color class for intent classification.
 */
export function getIntentColor(intent: "hot" | "warm" | "cold"): string {
  const colors: Record<string, string> = {
    hot: "text-red-400",
    warm: "text-amber-400",
    cold: "text-blue-400",
  };
  return colors[intent] ?? "text-muted-foreground";
}

/**
 * Returns a Tailwind background+text class for intent classification badges.
 */
export function getIntentBgColor(intent: "hot" | "warm" | "cold"): string {
  const colors: Record<string, string> = {
    hot: "bg-red-400/10 text-red-400",
    warm: "bg-amber-400/10 text-amber-400",
    cold: "bg-blue-400/10 text-blue-400",
  };
  return colors[intent] ?? "bg-muted text-muted-foreground";
}

/**
 * Formats a duration in seconds to a human-readable string (e.g., "5m 30s").
 */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}

/**
 * Formats a timestamp in seconds to MM:SS format for transcript display.
 */
export function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Truncates a string to a maximum length, appending "..." if truncated.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + "...";
}

/**
 * Formats a number as a percentage string.
 */
export function formatPercent(value: number, decimals: number = 0): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Generates initials from a name string (up to 2 characters).
 */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/**
 * Returns a human-readable relative time string (e.g., "2 hours ago").
 */
export function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString();
}

/**
 * Converts a score (0-10) to a normalized percentage (0-100).
 */
export function scoreToPercent(score: number, max: number = 10): number {
  return Math.round((score / max) * 100);
}

/**
 * Returns a status-appropriate badge color class.
 */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "bg-yellow-400/10 text-yellow-400",
    processing: "bg-blue-400/10 text-blue-400",
    transcribing: "bg-blue-400/10 text-blue-400",
    analyzing: "bg-purple-400/10 text-purple-400",
    completed: "bg-emerald-400/10 text-emerald-400",
    failed: "bg-red-400/10 text-red-400",
    generating: "bg-blue-400/10 text-blue-400",
  };
  return colors[status] ?? "bg-muted text-muted-foreground";
}

/**
 * Formats a follow-up urgency value to a human-readable label.
 */
export function formatUrgency(urgency: string): string {
  const labels: Record<string, string> = {
    immediate: "Immediate",
    this_week: "This Week",
    next_week: "Next Week",
    nurture: "Nurture",
  };
  return labels[urgency] ?? urgency;
}

/**
 * Returns urgency-appropriate color class.
 */
export function getUrgencyColor(urgency: string): string {
  const colors: Record<string, string> = {
    immediate: "text-red-400",
    this_week: "text-amber-400",
    next_week: "text-blue-400",
    nurture: "text-muted-foreground",
  };
  return colors[urgency] ?? "text-muted-foreground";
}
