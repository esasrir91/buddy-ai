// PULSE TypeScript interfaces — mirrors the Python Pydantic models

export interface EmployeeProfile {
  full_name: string
  role: string
  department: string
  team?: string
  skills: string[]
  timezone: string
  reporting_to?: string
  company_name?: string
  bio?: string
  email?: string
  slack_handle?: string
}

export interface Employee {
  employee_id: string
  profile: EmployeeProfile
  memory_summary: MemorySummary
  task_summary: Record<string, number>
  kt_domains: string[]
}

export interface MemorySummary {
  kt_sessions_completed: number
  kt_domains: string[]
  colleagues_known: number
  decisions_logged: number
  projects_tracked: string[]
}

// --- KT ---

export type KTSourceType =
  | 'document' | 'url' | 'audio_transcript' | 'video_transcript'
  | 'wiki_page' | 'meeting_recording' | 'codebase'
  | 'human_chat' | 'human_voice_call' | 'human_slack_thread' | 'human_video_call'

export type KTPhase = 'listening' | 'questioning' | 'summarizing' | 'confirming' | 'completed'

export interface KTTurn {
  turn_id: string
  phase: KTPhase
  pulse_message: string
  questions: string[]
  confidence_score: number
  mental_model_draft: string
  ready_to_commit: boolean
}

export interface KTSummary {
  session_id: string
  session_name: string
  knowledge_giver: string
  source_type: KTSourceType
  mode: 'async' | 'live'
  key_concepts: string[]
  mental_model: string
  open_questions: string[]
  connections_to_existing_knowledge: string[]
  confidence_score: number
  rounds_of_dialogue: number
  domain: string
  tags: string[]
  completed_at: string
}

export interface KTSessionState {
  session_id: string
  session_name: string
  source_type: KTSourceType
  mode: 'async' | 'live'
  phase: KTPhase
  rounds_completed: number
  confidence_score: number
  pending_questions: string[]
  mental_model_draft: string
  key_concepts: string[]
  committed: boolean
  started_at: string
}

// --- Meetings ---

export type MeetingPlatform = 'zoom' | 'microsoft_teams' | 'google_meet' | 'slack_huddle' | 'in_person' | 'other'
export type ActionItemPriority = 'low' | 'medium' | 'high' | 'critical'
export type ActionItemStatus = 'open' | 'in_progress' | 'done' | 'blocked'

export interface ActionItem {
  action_id: string
  description: string
  owner?: string
  due_date?: string
  priority: ActionItemPriority
  status: ActionItemStatus
  source_meeting_id?: string
}

export interface MeetingNotes {
  meeting_id: string
  title?: string
  platform: MeetingPlatform
  participants: string[]
  date: string
  summary: string
  key_decisions: string[]
  action_items: ActionItem[]
  open_questions: string[]
  topics_discussed: string[]
  pulse_contributions: string[]
}

// --- Tasks ---

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'
export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'in_review' | 'done' | 'cancelled'

export interface WorkItem {
  task_id: string
  title: string
  description: string
  task_type: string
  priority: TaskPriority
  status: TaskStatus
  assigned_by?: string
  assigned_to?: string
  deadline?: string
  estimated_hours?: number
  tags: string[]
  created_at: string
  updated_at: string
  completed_at?: string
  progress_notes: string[]
  blockers: string[]
}

// --- Status Update ---

export interface StatusUpdate {
  update_id: string
  employee_name: string
  update_type: string
  task_id?: string
  task_title?: string
  what_i_did: string[]
  what_i_will_do: string[]
  blockers: string[]
  percentage_complete?: number
  generated_at: string
  message: string
}

// --- Feedback ---

export interface FeedbackEntry {
  feedback_id: string
  given_by: string
  category: string
  sentiment: string
  content: string
  action_taken?: string
  received_at: string
  tags: string[]
}

// --- LLM Settings ---

export type LLMProvider = 'openai' | 'anthropic' | 'google' | 'groq' | 'ollama'

export interface LLMSettingsState {
  provider: LLMProvider
  model_id: string
  env_var: string
  key_set: boolean
  key_masked: string
  base_url: string
}

export interface LLMTestResult {
  success: boolean
  response?: string
  error?: string
}

export const LLM_PROVIDERS: {
  id: LLMProvider
  label: string
  env_var: string
  needs_key: boolean
  models: { id: string; label: string }[]
}[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    env_var: 'OPENAI_API_KEY',
    needs_key: true,
    models: [
      { id: 'gpt-4o',          label: 'GPT-4o (recommended)' },
      { id: 'gpt-4o-mini',     label: 'GPT-4o mini (fast)' },
      { id: 'gpt-4-turbo',     label: 'GPT-4 Turbo' },
      { id: 'gpt-3.5-turbo',   label: 'GPT-3.5 Turbo' },
    ],
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    env_var: 'ANTHROPIC_API_KEY',
    needs_key: true,
    models: [
      { id: 'claude-opus-4-5',   label: 'Claude Opus 4.5' },
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5 (fast)' },
      { id: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku (budget)' },
    ],
  },
  {
    id: 'google',
    label: 'Google Gemini',
    env_var: 'GOOGLE_API_KEY',
    needs_key: true,
    models: [
      { id: 'gemini-1.5-pro',   label: 'Gemini 1.5 Pro' },
      { id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (fast)' },
      { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
    ],
  },
  {
    id: 'groq',
    label: 'Groq',
    env_var: 'GROQ_API_KEY',
    needs_key: true,
    models: [
      { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B Versatile' },
      { id: 'llama-3.1-8b-instant',    label: 'Llama 3.1 8B Instant (fast)' },
      { id: 'mixtral-8x7b-32768',      label: 'Mixtral 8x7B' },
    ],
  },
  {
    id: 'ollama',
    label: 'Ollama (local)',
    env_var: '',
    needs_key: false,
    models: [
      { id: 'llama3.2',    label: 'Llama 3.2' },
      { id: 'mistral',     label: 'Mistral' },
      { id: 'phi4',        label: 'Phi-4' },
      { id: 'deepseek-r1', label: 'DeepSeek R1' },
    ],
  },
]
