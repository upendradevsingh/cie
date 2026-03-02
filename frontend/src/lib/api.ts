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

export async function getWeeklyReports(): Promise<WeeklyReportListItem[]> {
  const res = await api.get<WeeklyReportListItem[]>("/reports/weekly");
  return res.data;
}

export async function getWeeklyReport(id: string): Promise<WeeklyReport> {
  const res = await api.get<WeeklyReport>(`/reports/weekly/${id}`);
  return res.data;
}

export async function generateWeeklyReport(
  data: GenerateWeeklyReportRequest,
): Promise<WeeklyReportListItem> {
  const res = await api.post<WeeklyReportListItem>("/reports/weekly", data);
  return res.data;
}

export default api;
