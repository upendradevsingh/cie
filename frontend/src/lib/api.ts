import axios, { type AxiosInstance, type AxiosError } from "axios";
import type {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  User,
  CreateUserRequest,
  UpdateUserRequest,
  Tenant,
  CreateTenantRequest,
  CallData,
  CallListItem,
  CallsListResponse,
  CallFilters,
  TranscriptSegment,
  QaOverrideRequest,
  TeamAnalytics,
  AgentAnalytics,
  AgentLeaderboardEntry,
  AnalyticsData,
  TrendParams,
  LeaderboardParams,
  QualityParameter,
  CreateQualityParameterRequest,
  UpdateQualityParameterRequest,
  IntentSignalConfig,
  CreateIntentSignalRequest,
  UpdateIntentSignalRequest,
  PersonaType,
  CreatePersonaTypeRequest,
  UpdatePersonaTypeRequest,
  Integration,
  CreateIntegrationRequest,
  UpdateIntegrationRequest,
  ApiKey,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  WeeklyReport,
  WeeklyReportListItem,
  GenerateWeeklyReportRequest,
  AgentSummary,
  PromptTemplate,
} from "@/lib/types";

// ── Axios instance ─────────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Request interceptor: attach JWT access token from localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor: handle 401 Unauthorized by clearing tokens and redirecting
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      // Only redirect if not already on login page to avoid redirect loops
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// ── Auth ────────────────────────────────────────────────────────────

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/login", data);
  return res.data;
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/register", data);
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await api.get<User>("/auth/me");
  return res.data;
}

export async function createTenant(data: CreateTenantRequest): Promise<Tenant> {
  const res = await api.post<Tenant>("/auth/tenant", data);
  return res.data;
}

// ── Calls ───────────────────────────────────────────────────────────

export async function getCalls(filters: CallFilters): Promise<CallsListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  });
  const res = await api.get<CallsListResponse>("/calls", { params });
  return res.data;
}

export async function getCall(id: string): Promise<CallData> {
  const res = await api.get<CallData>(`/calls/${id}`);
  return res.data;
}

export async function uploadCall(formData: FormData): Promise<CallListItem> {
  const res = await api.post<CallListItem>("/calls/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000, // 2 minutes for file upload
  });
  return res.data;
}

export async function webhookCall(data: {
  recording_url: string;
  agent_name: string;
  agent_id: string;
  lead_name: string;
  lead_id: string;
  lead_phone?: string;
  source?: string;
  custom_fields?: Record<string, string>;
}): Promise<CallListItem> {
  const res = await api.post<CallListItem>("/calls/webhook", data);
  return res.data;
}

export async function getTranscript(id: string): Promise<TranscriptSegment[]> {
  const res = await api.get<TranscriptSegment[]>(`/calls/${id}/transcript`);
  return res.data;
}

export async function qaOverrideScores(
  callId: string,
  data: QaOverrideRequest,
): Promise<CallData> {
  const res = await api.put<CallData>(`/calls/${callId}/qa-override`, data);
  return res.data;
}

// ── Analytics ───────────────────────────────────────────────────────

export async function getTeamAnalytics(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<TeamAnalytics> {
  const res = await api.get<TeamAnalytics>("/analytics/team", { params });
  return res.data;
}

export async function getAgentAnalytics(
  agentId: string,
  params?: { date_from?: string; date_to?: string },
): Promise<AgentAnalytics> {
  const res = await api.get<AgentAnalytics>(`/analytics/agent/${agentId}`, { params });
  return res.data;
}

export async function getTrends(params: TrendParams): Promise<AnalyticsData> {
  const res = await api.get<AnalyticsData>("/analytics/trends", { params });
  return res.data;
}

export async function getAnalyticsData(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<AnalyticsData> {
  const res = await api.get<AnalyticsData>("/analytics/trends", { params });
  return res.data;
}

export async function getLeaderboard(
  params?: LeaderboardParams,
): Promise<AgentLeaderboardEntry[]> {
  const res = await api.get<AgentLeaderboardEntry[]>("/analytics/leaderboard", {
    params,
  });
  return res.data;
}

// ── Agents ──────────────────────────────────────────────────────────

export async function getAgents(): Promise<AgentSummary[]> {
  const res = await api.get<AgentSummary[]>("/agents");
  return res.data;
}

// ── Quality Parameters ──────────────────────────────────────────────

export async function getQualityParameters(): Promise<QualityParameter[]> {
  const res = await api.get<QualityParameter[]>("/quality-parameters");
  return res.data;
}

export async function createQualityParameter(
  data: CreateQualityParameterRequest,
): Promise<QualityParameter> {
  const res = await api.post<QualityParameter>("/quality-parameters", data);
  return res.data;
}

export async function updateQualityParameter(
  id: string,
  data: UpdateQualityParameterRequest,
): Promise<QualityParameter> {
  const res = await api.put<QualityParameter>(`/quality-parameters/${id}`, data);
  return res.data;
}

export async function deleteQualityParameter(id: string): Promise<void> {
  await api.delete(`/quality-parameters/${id}`);
}

export async function seedQualityParameters(): Promise<QualityParameter[]> {
  const res = await api.post<QualityParameter[]>("/quality-parameters/seed");
  return res.data;
}

// ── Intent Signals ──────────────────────────────────────────────────

export async function getIntentSignals(): Promise<IntentSignalConfig[]> {
  const res = await api.get<IntentSignalConfig[]>("/intent-signals");
  return res.data;
}

export async function createIntentSignal(
  data: CreateIntentSignalRequest,
): Promise<IntentSignalConfig> {
  const res = await api.post<IntentSignalConfig>("/intent-signals", data);
  return res.data;
}

export async function updateIntentSignal(
  id: string,
  data: UpdateIntentSignalRequest,
): Promise<IntentSignalConfig> {
  const res = await api.put<IntentSignalConfig>(`/intent-signals/${id}`, data);
  return res.data;
}

export async function deleteIntentSignal(id: string): Promise<void> {
  await api.delete(`/intent-signals/${id}`);
}

export async function seedIntentSignals(): Promise<IntentSignalConfig[]> {
  const res = await api.post<IntentSignalConfig[]>("/intent-signals/seed");
  return res.data;
}

// ── Persona Types ───────────────────────────────────────────────────

export async function getPersonaTypes(): Promise<PersonaType[]> {
  const res = await api.get<PersonaType[]>("/persona-types");
  return res.data;
}

export async function createPersonaType(
  data: CreatePersonaTypeRequest,
): Promise<PersonaType> {
  const res = await api.post<PersonaType>("/persona-types", data);
  return res.data;
}

export async function updatePersonaType(
  id: string,
  data: UpdatePersonaTypeRequest,
): Promise<PersonaType> {
  const res = await api.put<PersonaType>(`/persona-types/${id}`, data);
  return res.data;
}

export async function deletePersonaType(id: string): Promise<void> {
  await api.delete(`/persona-types/${id}`);
}

// ── Integrations ────────────────────────────────────────────────────

export async function getIntegrations(): Promise<Integration[]> {
  const res = await api.get<Integration[]>("/integrations");
  return res.data;
}

export async function createIntegration(
  data: CreateIntegrationRequest,
): Promise<Integration> {
  const res = await api.post<Integration>("/integrations", data);
  return res.data;
}

export async function updateIntegration(
  id: string,
  data: UpdateIntegrationRequest,
): Promise<Integration> {
  const res = await api.put<Integration>(`/integrations/${id}`, data);
  return res.data;
}

export async function deleteIntegration(id: string): Promise<void> {
  await api.delete(`/integrations/${id}`);
}

// ── API Keys ────────────────────────────────────────────────────────

export async function getApiKeys(): Promise<ApiKey[]> {
  const res = await api.get<ApiKey[]>("/api-keys");
  return res.data;
}

export async function createApiKey(data: CreateApiKeyRequest): Promise<CreateApiKeyResponse> {
  const res = await api.post<CreateApiKeyResponse>("/api-keys", data);
  return res.data;
}

export async function deleteApiKey(id: string): Promise<void> {
  await api.delete(`/api-keys/${id}`);
}

// ── Users ───────────────────────────────────────────────────────────

export async function getUsers(): Promise<User[]> {
  const res = await api.get<User[]>("/users");
  return res.data;
}

export async function createUser(data: CreateUserRequest): Promise<User> {
  const res = await api.post<User>("/users", data);
  return res.data;
}

export async function updateUser(id: string, data: UpdateUserRequest): Promise<User> {
  const res = await api.put<User>(`/users/${id}`, data);
  return res.data;
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`/users/${id}`);
}

// ── Reports ─────────────────────────────────────────────────────────

/* eslint-disable @typescript-eslint/no-explicit-any */

/** Map the backend WeeklyReportResponse into the frontend WeeklyReportListItem shape. */
function _mapReportListItem(raw: any): WeeklyReportListItem {
  const rd = raw.report_data ?? {};
  const summary = rd.summary ?? {};
  return {
    id: raw.id,
    week_start: raw.week_start,
    week_end: raw.week_end,
    status: raw.status,
    summary_total_calls: summary.total_calls ?? 0,
    summary_avg_quality: summary.avg_quality_score ?? 0,
    created_at: raw.created_at,
  };
}

/** Map the backend WeeklyReportResponse into the full frontend WeeklyReport shape. */
function _mapReportDetail(raw: any): WeeklyReport {
  const rd = raw.report_data ?? {};
  const summary = rd.summary ?? {};
  const highlights = rd.highlights ?? {};

  // Map agent_performance → agent_breakdowns
  const agentPerf: any[] = rd.agent_performance ?? [];
  const agentBreakdowns: import("@/lib/types").AgentWeeklyBreakdown[] = agentPerf.map(
    (a: any) => ({
      agent_id: a.agent_id ?? "",
      agent_name: a.agent_name ?? "Unknown",
      total_calls: a.total_calls ?? 0,
      avg_quality_score: a.avg_quality_score ?? 0,
      quality_change: 0,
      hot_leads: a.hot_leads ?? 0,
      top_call_id: "",
      areas_for_improvement: Object.keys(a.bottom_parameter_scores ?? {}),
      strengths: Object.keys(a.top_parameter_scores ?? {}),
    }),
  );

  // Map hot_leads → hot_leads_summary
  const rawHotLeads: any[] = rd.hot_leads ?? [];
  const hotLeadsSummary: import("@/lib/types").HotLead[] = rawHotLeads.map(
    (h: any) => ({
      call_id: h.call_id ?? "",
      lead_name: h.lead_name ?? "Unknown",
      lead_phone: h.lead_phone ?? "",
      intent_score: h.intent_score ?? 0,
      agent_name: h.agent_name ?? "Unknown",
      created_at: h.created_at ?? "",
    }),
  );

  // Map top_calls
  const rawTopCalls: any[] = rd.top_calls ?? [];
  const topCalls = rawTopCalls.map((c: any) => ({
    call_id: c.call_id ?? "",
    agent_name: c.agent_name ?? "Unknown",
    lead_name: c.lead_name ?? "Unknown",
    overall_score: c.overall_score ?? 0,
    intent_classification: c.intent_classification ?? "cold",
  }));

  // Derive areas_for_improvement from the raw data
  const rawAreas: any[] = rd.areas_for_improvement ?? [];
  const areasForImprovement = rawAreas.map(
    (a: any) =>
      `${a.parameter_name ?? "Unknown"}: ${(a.avg_score ?? 0).toFixed(1)}/10`,
  );

  // Derive top agent name from highlights
  const topAgent: string =
    highlights.top_agent_quality?.agent_name ??
    agentBreakdowns[0]?.agent_name ??
    "—";

  // Build key_insights from trends data
  const keyInsights: string[] = [];
  const trends = rd.trends ?? {};
  if (trends.avg_quality_score?.change_pct) {
    const pct = trends.avg_quality_score.change_pct;
    keyInsights.push(
      pct >= 0
        ? `Quality score improved by ${pct}% vs last week`
        : `Quality score decreased by ${Math.abs(pct)}% vs last week`,
    );
  }
  if (trends.hot_leads_count?.change) {
    const change = trends.hot_leads_count.change;
    if (change > 0) keyInsights.push(`${change} more hot leads than last week`);
    else if (change < 0)
      keyInsights.push(`${Math.abs(change)} fewer hot leads than last week`);
  }
  if (highlights.top_agent_quality) {
    keyInsights.push(
      `Top performer: ${highlights.top_agent_quality.agent_name} (avg ${highlights.top_agent_quality.avg_quality_score})`,
    );
  }

  return {
    id: raw.id,
    tenant_id: raw.tenant_id,
    week_start: raw.week_start,
    week_end: raw.week_end,
    status: raw.status,
    summary: {
      total_calls: summary.total_calls ?? 0,
      avg_quality_score: summary.avg_quality_score ?? 0,
      quality_change: trends.avg_quality_score?.change_pct ?? 0,
      hot_leads: summary.hot_leads_count ?? 0,
      top_agent: topAgent,
      areas_for_improvement: areasForImprovement,
    },
    agent_breakdowns: agentBreakdowns,
    top_calls: topCalls,
    hot_leads_summary: hotLeadsSummary,
    key_insights: keyInsights,
    created_at: raw.created_at,
  };
}

/* eslint-enable @typescript-eslint/no-explicit-any */

export async function getWeeklyReports(): Promise<WeeklyReportListItem[]> {
  const res = await api.get("/reports/weekly");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (res.data as any[]).map(_mapReportListItem);
}

export async function getWeeklyReport(id: string): Promise<WeeklyReport> {
  const res = await api.get(`/reports/weekly/${id}`);
  return _mapReportDetail(res.data);
}

export async function generateWeeklyReport(
  data: GenerateWeeklyReportRequest,
): Promise<WeeklyReportListItem> {
  const res = await api.post("/reports/weekly", data);
  return _mapReportListItem(res.data);
}

// ── Prompt Templates ─────────────────────────────────────────────

export async function getPromptTemplates(): Promise<PromptTemplate[]> {
  const res = await api.get<PromptTemplate[]>("/prompt-templates");
  return res.data;
}

export async function getPromptTemplate(id: string): Promise<PromptTemplate> {
  const res = await api.get<PromptTemplate>(`/prompt-templates/${id}`);
  return res.data;
}

export async function updatePromptTemplate(
  id: string,
  data: { description?: string; template_content?: string },
): Promise<PromptTemplate> {
  const res = await api.put<PromptTemplate>(`/prompt-templates/${id}`, data);
  return res.data;
}

export async function seedPromptTemplates(): Promise<PromptTemplate[]> {
  const res = await api.post<PromptTemplate[]>("/prompt-templates/seed");
  return res.data;
}

export async function resetPromptTemplate(id: string): Promise<PromptTemplate> {
  const res = await api.post<PromptTemplate>(`/prompt-templates/${id}/reset`);
  return res.data;
}

export default api;
