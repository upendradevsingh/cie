// ─── Auth & Users ────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  organization_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export type UserRole = "admin" | "team_lead" | "agent";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string;
  is_active: boolean;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

export interface UpdateUserRequest {
  email?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
}

// ─── Tenant ──────────────────────────────────────────────────────────────────

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTenantRequest {
  name: string;
  slug: string;
}

// ─── Transcription ───────────────────────────────────────────────────────────

export type Speaker = "agent" | "customer" | "unknown";

export interface TranscriptSegment {
  id: string;
  speaker: Speaker;
  speaker_name: string;
  text: string;
  start_time: number;
  end_time: number;
  confidence: number;
  is_key_moment?: boolean;
  key_moment_label?: string;
}

// ─── Quality Scoring ─────────────────────────────────────────────────────────

export interface QualityScore {
  parameter_id: string;
  parameter_name: string;
  category: string;
  score: number;
  max_score: number;
  weight: number;
  justification: string;
}

export interface QualityParameter {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  category: string;
  weight: number;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface CreateQualityParameterRequest {
  name: string;
  description: string;
  category: string;
  weight: number;
  is_active?: boolean;
  display_order?: number;
}

export interface UpdateQualityParameterRequest {
  name?: string;
  description?: string;
  category?: string;
  weight?: number;
  is_active?: boolean;
  display_order?: number;
}

// ─── Intent Signals ──────────────────────────────────────────────────────────

export interface IntentSignal {
  id: string;
  name: string;
  description: string;
  detected: boolean;
  details?: string;
}

export interface IntentSignalConfig {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface CreateIntentSignalRequest {
  name: string;
  description: string;
  is_active?: boolean;
  display_order?: number;
}

export interface UpdateIntentSignalRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
  display_order?: number;
}

// ─── Lead Intelligence ───────────────────────────────────────────────────────

export type IntentClassification = "hot" | "warm" | "cold";

export interface LeadIntelligence {
  intent_score: number;
  classification: IntentClassification;
  signals: IntentSignal[];
  key_objections: Objection[];
  buying_signals: string[];
}

export interface Objection {
  objection: string;
  category: string;
  severity: "low" | "medium" | "high";
  rebuttal_suggestion?: string;
}

// ─── BANT & Persona ─────────────────────────────────────────────────────────

export interface BANTScore {
  budget: number;
  authority: number;
  need: number;
  timeline: number;
}

export interface PersonaData {
  persona_type: string;
  persona_type_id: string | null;
  bant: BANTScore;
  discovery_insights: string[];
}

export interface PersonaType {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  bant_profile: {
    min_budget: number;
    min_authority: number;
    min_need: number;
    min_timeline: number;
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePersonaTypeRequest {
  name: string;
  description: string;
  bant_profile: {
    min_budget: number;
    min_authority: number;
    min_need: number;
    min_timeline: number;
  };
  is_active?: boolean;
}

export interface UpdatePersonaTypeRequest {
  name?: string;
  description?: string;
  bant_profile?: {
    min_budget: number;
    min_authority: number;
    min_need: number;
    min_timeline: number;
  };
  is_active?: boolean;
}

// ─── Action Items & Path to Conversion ───────────────────────────────────────

export type FollowUpUrgency = "immediate" | "this_week" | "next_week" | "nurture";

export interface ActionItem {
  id: string;
  call_id: string;
  text: string;
  type: "follow_up" | "internal" | "send_info" | "schedule" | "other";
  urgency: FollowUpUrgency;
  category: string;
  priority: "low" | "medium" | "high";
  due_date: string | null;
  completed: boolean;
  created_at: string;
}

export interface PathToConversion {
  talking_points: string[];
  rebuttals: Array<{
    objection: string;
    rebuttal: string;
  }>;
  follow_up_urgency: FollowUpUrgency;
  next_best_action: string;
}

// ─── Enhanced Analysis ───────────────────────────────────────────────────────

export interface EscalationKeyword {
  keyword: string;
  context: string;
  severity: "high" | "medium" | "low";
}

export interface SentimentData {
  positive_keywords: string[];
  negative_keywords: string[];
  overall_sentiment: "positive" | "negative" | "mixed" | "neutral";
}

export interface SalesAuditKeyword {
  keyword: string;
  context: string;
  severity: "high" | "medium" | "low";
}

export interface SalesAuditKeywords {
  compliance_violations: SalesAuditKeyword[];
  missed_opportunities: SalesAuditKeyword[];
  pricing_discounts: SalesAuditKeyword[];
  competitor_mentions: SalesAuditKeyword[];
  customer_pain_points: SalesAuditKeyword[];
  commitment_closing: SalesAuditKeyword[];
  objection_handling: SalesAuditKeyword[];
  negative_reactions: SalesAuditKeyword[];
}

export interface PromptTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  template_content: string;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Calls ───────────────────────────────────────────────────────────────────

export type CallStatus =
  | "pending"
  | "processing"
  | "transcribing"
  | "analyzing"
  | "completed"
  | "failed";

export interface CallCustomField {
  key: string;
  value: string;
}

export interface CallData {
  id: string;
  tenant_id: string;
  recording_url: string;
  duration: number;
  agent_name: string;
  agent_id: string;
  lead_name: string;
  lead_id: string;
  lead_phone: string;
  source: string;
  status: CallStatus;
  custom_fields: CallCustomField[];
  transcript: TranscriptSegment[];
  quality_scores: QualityScore[];
  overall_score: number;
  lead_intelligence: LeadIntelligence;
  persona: PersonaData;
  action_items: ActionItem[];
  path_to_conversion: PathToConversion;
  metadata_extraction: Record<string, string>;
  follow_up_urgency: FollowUpUrgency | null;
  escalation_keywords: EscalationKeyword[];
  sentiment: SentimentData;
  call_tags: string[];
  sales_audit_keywords: SalesAuditKeywords | null;
  created_at: string;
  updated_at: string;
}

export interface CallListItem {
  id: string;
  agent_name: string;
  agent_id: string;
  lead_name: string;
  lead_id: string;
  lead_phone: string;
  duration: number;
  overall_score: number;
  intent_classification: IntentClassification;
  intent_score: number;
  status: CallStatus;
  source: string;
  follow_up_urgency: FollowUpUrgency | null;
  call_tags: string[];
  overall_sentiment: string | null;
  created_at: string;
}

export interface CallsListResponse {
  items: CallListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CallFilters {
  agent_id?: string;
  date_from?: string;
  date_to?: string;
  score_min?: number;
  score_max?: number;
  intent_classification?: IntentClassification;
  status?: CallStatus;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface CallUploadInput {
  file: File;
  agent_name: string;
  agent_id: string;
  lead_name: string;
  lead_id: string;
  lead_phone: string;
  source: string;
  custom_fields?: Record<string, string>;
}

export interface WebhookCallRequest {
  recording_url: string;
  agent_name: string;
  agent_id: string;
  lead_name: string;
  lead_id: string;
  lead_phone?: string;
  source?: string;
  custom_fields?: CallCustomField[];
}

export interface QaOverrideRequest {
  scores: Array<{
    parameter_id: string;
    score: number;
    justification: string;
  }>;
  override_reason: string;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface DashboardStats {
  calls_today: number;
  calls_today_change: number;
  avg_quality_score: number;
  avg_quality_change: number;
  hot_leads_count: number;
  hot_leads_change: number;
  team_performance: number;
  team_performance_change: number;
}

export interface CallTrend {
  date: string;
  count: number;
  avg_score: number;
}

export interface ScoreDistribution {
  range: string;
  count: number;
}

export interface HotLead {
  call_id: string;
  lead_name: string;
  lead_phone: string;
  intent_score: number;
  agent_name: string;
  created_at: string;
}

export interface TeamAnalytics {
  stats: DashboardStats;
  call_trends: CallTrend[];
  score_distribution: ScoreDistribution[];
  hot_leads: HotLead[];
  recent_calls: CallListItem[];
}

export interface AgentAnalytics {
  agent_id: string;
  agent_name: string;
  total_calls: number;
  avg_quality_score: number;
  avg_intent_score: number;
  hot_leads_count: number;
  improvement_trend: number;
  quality_trend: CallTrend[];
  parameter_averages: Array<{
    parameter_name: string;
    avg_score: number;
  }>;
  intent_breakdown: {
    hot: number;
    warm: number;
    cold: number;
  };
  improvement_areas: string[];
  strengths: string[];
}

export interface AgentLeaderboardEntry {
  rank: number;
  agent_id: string;
  agent_name: string;
  avatar_url?: string;
  total_calls: number;
  avg_quality_score: number;
  avg_intent_score: number;
  hot_leads_count: number;
  improvement_trend: number;
  trend: "up" | "down" | "stable";
}

export interface ConversionFunnel {
  stage: string;
  count: number;
}

export interface ParameterTrend {
  parameter_name: string;
  current_avg: number;
  previous_avg: number;
  change: number;
}

export interface AnalyticsData {
  call_volume: CallTrend[];
  avg_quality_trend: CallTrend[];
  conversion_funnel: ConversionFunnel[];
  agent_comparison: AgentAnalytics[];
  parameter_trends: ParameterTrend[];
  lead_classification: Array<{ classification: string; count: number }>;
  score_distribution: ScoreDistribution[];
}

export interface TrendParams {
  period: "daily" | "weekly" | "monthly";
  date_from?: string;
  date_to?: string;
  agent_id?: string;
}

export interface LeaderboardParams {
  period?: "week" | "month" | "quarter" | "all_time";
  sort_by?: "quality_score" | "intent_score" | "calls" | "hot_leads";
  limit?: number;
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export interface WeeklyReport {
  id: string;
  tenant_id: string;
  week_start: string;
  week_end: string;
  status: "generating" | "completed" | "failed";
  summary: {
    total_calls: number;
    avg_quality_score: number;
    quality_change: number;
    hot_leads: number;
    top_agent: string;
    areas_for_improvement: string[];
  };
  agent_breakdowns: AgentWeeklyBreakdown[];
  top_calls: Array<{
    call_id: string;
    agent_name: string;
    lead_name: string;
    overall_score: number;
    intent_classification: string;
  }>;
  hot_leads_summary: HotLead[];
  key_insights: string[];
  created_at: string;
}

export interface AgentWeeklyBreakdown {
  agent_id: string;
  agent_name: string;
  total_calls: number;
  avg_quality_score: number;
  quality_change: number;
  hot_leads: number;
  top_call_id: string;
  areas_for_improvement: string[];
  strengths: string[];
}

export interface WeeklyReportListItem {
  id: string;
  week_start: string;
  week_end: string;
  status: "generating" | "completed" | "failed";
  summary_total_calls: number;
  summary_avg_quality: number;
  created_at: string;
}

export interface GenerateWeeklyReportRequest {
  week_start: string;
  week_end?: string;
}

// ─── Integrations ────────────────────────────────────────────────────────────

export type IntegrationType = "inbound_webhook" | "outbound_crm" | "email" | "slack" | "custom";

export interface Integration {
  id: string;
  tenant_id: string;
  name: string;
  type: IntegrationType;
  config: Record<string, string>;
  is_active: boolean;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateIntegrationRequest {
  name: string;
  type: IntegrationType;
  config: Record<string, string>;
  is_active?: boolean;
}

export interface UpdateIntegrationRequest {
  name?: string;
  type?: IntegrationType;
  config?: Record<string, string>;
  is_active?: boolean;
}

// ─── API Keys ────────────────────────────────────────────────────────────────

export interface ApiKey {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_by: string;
  created_at: string;
}

export interface CreateApiKeyRequest {
  name: string;
  expires_in_days?: number;
}

export interface CreateApiKeyResponse {
  id: string;
  name: string;
  key: string; // Full key, shown only once at creation
  key_prefix: string;
  expires_at: string | null;
  created_at: string;
}

// ─── Common ──────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface SuccessResponse {
  message: string;
}

// ─── Agent list (for filters/dropdowns) ──────────────────────────────────────

export interface AgentSummary {
  id: string;
  name: string;
  avatar_url?: string;
}
