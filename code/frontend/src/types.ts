// ── Shared TypeScript types for Aura ──────────────────────────────────────

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'dir'
  children?: FileNode[]
  expanded?: boolean
}

export interface EditorTab {
  id: string
  path: string
  name: string
  content: string
  language: string
  dirty: boolean
  viewState?: unknown // Monaco ICodeEditorViewState
}

export type ChatMode = 'agent' | 'plan' | 'ask'

/** Org-wide team role that shapes agent prompts + UI workflows */
export type TeamRole =
  | 'engineering'
  | 'testing'
  | 'platform'
  | 'hardware'
  | 'security'
  | 'product'
  | 'data'
  | 'general'

export interface TeamMeta {
  id: TeamRole
  label: string
  short: string
  description: string
  color: string
  icon: string
}

export interface TeamWorkflow {
  id: string
  label: string
  prompt: string
}

export type ToolStatus = 'running' | 'done' | 'error'

export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
  status: ToolStatus
  expanded?: boolean
}

export interface FileDiff {
  id: string
  path: string
  oldContent: string
  newContent: string
  applied?: boolean | null // null = pending, true = applied, false = rejected
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
  fileDiffs?: FileDiff[]
  askPayload?: AskPayload
  planPayload?: PlanPayload
  timestamp: number
  streaming?: boolean
  editing?: boolean
}

export interface AskPayload {
  title?: string
  questions: Array<{
    id: string
    prompt: string
    options: Array<{ id: string; label: string }>
    allow_multiple?: boolean
  }>
  answered?: Record<string, string | string[]>
}

export interface PlanPayload {
  name: string
  overview: string
  plan: string
  todos?: Array<{ id: string; content: string; status: string }>
  confirmed?: boolean
}

export interface Diagnostic {
  path: string
  line: number
  column: number
  severity: 'error' | 'warning' | 'info' | 'hint'
  message: string
  source?: string
  endLine?: number
  endColumn?: number
}

export interface Todo {
  id: string
  content: string
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
}

export interface McpServer {
  name: string
  command?: string
  url?: string
  transport?: 'stdio' | 'sse' | 'streamable-http'
  enabled: boolean
  tools?: string[]
  env?: Record<string, string>
}

export interface GitFile {
  path: string
  status: string
  staged: boolean
}

export interface GitStatus {
  branch: string
  files: GitFile[]
  ahead: number
  behind: number
}

export interface Session {
  id: string
  title: string
  updated: number
}

export interface OrgProfile {
  org_name: string
  user_name: string
  user_title: string
  team_role: TeamRole
  focus_areas: string[]
  onboarding_complete: boolean
}

export type SidebarView = 'explorer' | 'search' | 'git' | 'mcp' | 'teams' | 'testing' | 'settings' | null
export type BottomTab = 'terminal' | 'agent' | 'problems' | 'output'

export interface TerminalSession {
  id: string
  name: string
  shell: string
}
