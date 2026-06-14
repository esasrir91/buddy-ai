// PULSE API client — all fetch calls to the FastAPI backend

import type {
  Employee,
  EmployeeProfile,
  KTSummary,
  KTSessionState,
  KTTurn,
  MeetingNotes,
  WorkItem,
  StatusUpdate,
  FeedbackEntry,
  ActivityEvent,
  PulseNotification,
  WorkspaceFile,
  MemoryFact,
  ChatHistoryMsg,
} from '../types/pulse'

const BASE = '/api/pulse'

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

// ---------------------------------------------------------------------------
// Employees
// ---------------------------------------------------------------------------

export function createEmployee(data: {
  full_name: string
  role: string
  department?: string
  skills?: string[]
  timezone?: string
  reporting_to?: string
  company_name?: string
  bio?: string
  model_id?: string
  model_provider?: string
}) {
  return request<{ employee_id: string; profile: EmployeeProfile }>('/employees', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getEmployee(employeeId: string) {
  return request<Employee>(`/employees/${employeeId}`)
}

export function updateEmployee(employeeId: string, data: Partial<EmployeeProfile>) {
  return request<{ updated: boolean }>(`/employees/${employeeId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function onboardEmployee(
  employeeId: string,
  data: { company_docs?: string[]; team_members?: Array<{ name: string; role: string }> },
) {
  return request<Record<string, unknown>>(`/employees/${employeeId}/onboard`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ---------------------------------------------------------------------------
// KT — async
// ---------------------------------------------------------------------------

export function runAsyncKT(
  employeeId: string,
  data: {
    source: string
    source_type?: string
    session_name: string
    knowledge_giver: string
    confidence_threshold?: number
  },
) {
  return request<KTSummary>(`/${employeeId}/kt/async`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ---------------------------------------------------------------------------
// KT — live
// ---------------------------------------------------------------------------

export function createLiveKTSession(
  employeeId: string,
  data: {
    session_name: string
    knowledge_giver: string
    source_type?: string
    confidence_threshold?: number
    max_rounds?: number
  },
) {
  return request<{ session_id: string; state: KTSessionState }>(
    `/${employeeId}/kt/live`,
    { method: 'POST', body: JSON.stringify(data) },
  )
}

export function humanExplains(employeeId: string, sessionId: string, text: string) {
  return request<KTTurn>(`/${employeeId}/kt/${sessionId}/explain`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export function humanAnswers(employeeId: string, sessionId: string, answers: Record<string, string>) {
  return request<KTTurn>(`/${employeeId}/kt/${sessionId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

export function humanCorrects(employeeId: string, sessionId: string, correction: string) {
  return request<KTTurn>(`/${employeeId}/kt/${sessionId}/correct`, {
    method: 'POST',
    body: JSON.stringify({ correction }),
  })
}

export function commitKTSession(employeeId: string, sessionId: string) {
  return request<KTSummary>(`/${employeeId}/kt/${sessionId}/commit`, { method: 'POST' })
}

export function listKTSessions(employeeId: string) {
  return request<{ sessions: KTSummary[] }>(`/${employeeId}/kt`)
}

// ---------------------------------------------------------------------------
// Meetings
// ---------------------------------------------------------------------------

export function processMeeting(
  employeeId: string,
  data: {
    transcript: string
    participants?: string[]
    platform?: string
    title?: string
  },
) {
  return request<MeetingNotes>(`/${employeeId}/meetings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export function assignTask(
  employeeId: string,
  data: {
    description: string
    title?: string
    priority?: string
    deadline?: string
    assigned_by?: string
    tags?: string[]
  },
) {
  return request<WorkItem>(`/${employeeId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function listTasks(employeeId: string) {
  return request<{ tasks: WorkItem[] }>(`/${employeeId}/tasks`)
}

export function updateTask(employeeId: string, taskId: string, data: Record<string, unknown>) {
  return request<WorkItem>(`/${employeeId}/tasks/${taskId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function getTaskStatusUpdate(employeeId: string, taskId: string) {
  return request<StatusUpdate>(`/${employeeId}/tasks/${taskId}/status-update`)
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export function sendChatMessage(employeeId: string, message: string) {
  return request<{ response: string; employee: string }>(`/${employeeId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export function createChatWebSocket(employeeId: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_API_HOST ?? window.location.hostname
  const port = import.meta.env.VITE_API_PORT ?? '8888'
  return new WebSocket(`${protocol}//${host}:${port}/api/pulse/${employeeId}/chat/stream`)
}

// ---------------------------------------------------------------------------
// Knowledge
// ---------------------------------------------------------------------------

export function searchKnowledge(employeeId: string, query: string) {
  return request<{ query: string; results: KTSummary[] }>(
    `/${employeeId}/knowledge/search?q=${encodeURIComponent(query)}`,
  )
}

export function getKnowledgeSummary(employeeId: string) {
  return request<{
    domains: string[]
    kt_sessions: KTSummary[]
    memory_summary: Record<string, unknown>
  }>(`/${employeeId}/knowledge/summary`)
}

// ---------------------------------------------------------------------------
// LLM Settings
// ---------------------------------------------------------------------------

export function getLLMSettings() {
  return request<import('../types/pulse').LLMSettingsState>('/settings/llm')
}

export function saveLLMSettings(data: {
  provider: string
  model_id: string
  api_key?: string
  base_url?: string
}) {
  return request<{
    saved: boolean
    provider: string
    model_id: string
    env_var: string
    key_set: boolean
    rewired: number
    errors: string[]
  }>('/settings/llm', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function testLLMConnection(data: {
  provider: string
  model_id: string
  api_key?: string
  base_url?: string
}) {
  return request<import('../types/pulse').LLMTestResult>('/settings/llm/test', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getEodSummary(employeeId: string) {
  return request<StatusUpdate>(`/${employeeId}/eod-summary`)
}

export function sendFeedback(
  employeeId: string,
  data: { content: string; given_by: string; category?: string; sentiment?: string },
) {
  return request<FeedbackEntry>(`/${employeeId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ---------------------------------------------------------------------------
// Activity & Notifications
// ---------------------------------------------------------------------------

export function getActivity(employeeId: string, limit = 50) {
  return request<{ events: ActivityEvent[] }>(`/${employeeId}/activity?limit=${limit}`)
}

export function getNotifications(employeeId: string) {
  return request<{ notifications: PulseNotification[]; unread: number }>(`/${employeeId}/notifications`)
}

export function markNotificationRead(employeeId: string, notifId: string) {
  return request<{ ok: boolean }>(`/${employeeId}/notifications/${notifId}/read`, { method: 'POST' })
}

export function markAllNotificationsRead(employeeId: string) {
  return request<{ ok: boolean }>(`/${employeeId}/notifications/read-all`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Standup & Task suggestions
// ---------------------------------------------------------------------------

export function generateStandup(employeeId: string) {
  return request<{ standup: string; ts: string }>(`/${employeeId}/standup`, { method: 'POST' })
}

export function suggestTasks(employeeId: string) {
  return request<{ suggestions: Array<{ title: string; description: string; priority: string }> }>(
    `/${employeeId}/suggest-tasks`,
    { method: 'POST' },
  )
}

// ---------------------------------------------------------------------------
// Workspace
// ---------------------------------------------------------------------------

export function listWorkspaceFiles(employeeId: string) {
  return request<{ workspace_path: string; files: WorkspaceFile[] }>(`/${employeeId}/workspace`)
}

export function getWorkspaceFile(employeeId: string, filename: string) {
  return request<{ filename: string; extension: string; size_bytes: number; content: string }>(
    `/${employeeId}/workspace/${encodeURIComponent(filename)}`,
  )
}

export function deleteWorkspaceFile(employeeId: string, filename: string) {
  return request<{ deleted: string }>(
    `/${employeeId}/workspace/${encodeURIComponent(filename)}`,
    { method: 'DELETE' },
  )
}

// ---------------------------------------------------------------------------
// Memory
// ---------------------------------------------------------------------------

export function getMemory(employeeId: string) {
  return request<{
    long_term_memories: MemoryFact[]
    chat_history: ChatHistoryMsg[]
    history_count: number
    memory_count: number
  }>(`/${employeeId}/memory`)
}

export function forgetMemory(employeeId: string, memoryId: string) {
  return request<{ deleted: string; remaining: number }>(
    `/${employeeId}/memory/${memoryId}`,
    { method: 'DELETE' },
  )
}

export function clearAllMemory(employeeId: string) {
  return request<{ cleared: boolean }>(`/${employeeId}/memory`, { method: 'DELETE' })
}

export function clearChatHistory(employeeId: string) {
  return request<{ cleared: boolean }>(
    `/${employeeId}/memory/history/clear`,
    { method: 'DELETE' },
  )
}
