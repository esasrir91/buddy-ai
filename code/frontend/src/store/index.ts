import { create } from 'zustand'
import type {
  ChatMessage,
  ChatMode,
  Diagnostic,
  EditorTab,
  FileNode,
  FileDiff,
  McpServer,
  Session,
  SidebarView,
  BottomTab,
  TeamRole,
  Todo,
  ToolCall,
  TerminalSession,
} from '../types'

// ── helper ────────────────────────────────────────────────────────────────
let _tabSeq = 0
const nextId = () => `${Date.now()}_${++_tabSeq}`

function extToLang(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescriptreact', js: 'javascript', jsx: 'javascriptreact',
    py: 'python', rs: 'rust', go: 'go', java: 'java', cs: 'csharp',
    cpp: 'cpp', c: 'c', h: 'c', hpp: 'cpp',
    html: 'html', css: 'css', scss: 'scss', less: 'less',
    json: 'json', yaml: 'yaml', yml: 'yaml', toml: 'toml',
    md: 'markdown', mdx: 'markdown', txt: 'plaintext',
    sh: 'shell', bash: 'shell', ps1: 'powershell', bat: 'bat',
    sql: 'sql', xml: 'xml', svg: 'xml', graphql: 'graphql',
    dockerfile: 'dockerfile', makefile: 'makefile',
    rb: 'ruby', php: 'php', swift: 'swift', kt: 'kotlin',
  }
  return map[ext] ?? 'plaintext'
}

// ── state shape ───────────────────────────────────────────────────────────
interface AuraState {
  // workspace
  workspace: string
  workspaceTree: FileNode[]
  treeLoading: boolean

  // editor
  openTabs: EditorTab[]
  activeTabId: string | null

  // sessions
  sessions: Session[]
  sessionId: string

  // chat / agent
  messages: ChatMessage[]
  chatMode: ChatMode
  teamRole: TeamRole
  useCodebase: boolean       // "Use codebase" toggle
  isStreaming: boolean
  streamingMsgId: string | null
  inputDraft: string
  mentionedFiles: string[]

  // agent todos
  todos: Todo[]

  // agent terminal buffer (for shell output mirroring)
  agentTerminalLines: string[]

  // sidebar
  sidebarView: SidebarView
  sidebarWidth: number
  sidebarVisible: boolean

  // agent pane
  agentPaneWidth: number
  agentPaneVisible: boolean

  // bottom panel
  bottomPanelHeight: number
  bottomPanelVisible: boolean
  bottomTab: BottomTab
  bottomPanelMaximized: boolean
  bottomPanelPrevHeight: number

  // terminal sessions (Cursor-style multi-instance)
  terminals: TerminalSession[]
  activeTerminalId: string | null

  // problems
  diagnostics: Diagnostic[]

  // mcp
  mcpServers: McpServer[]

  // theme
  theme: 'dark' | 'light'

  // org profile / onboarding
  orgName: string
  userName: string
  userTitle: string
  focusAreas: string[]
  onboardingComplete: boolean | null  // null = still loading

  // git
  gitBranch: string
  gitDirtyCount: number

  // actions ─────────────────────────────────────────────────────────────
  setWorkspace: (p: string) => void
  setWorkspaceTree: (tree: FileNode[]) => void
  setTreeLoading: (v: boolean) => void
  setOrgProfile: (p: {
    orgName?: string
    userName?: string
    userTitle?: string
    focusAreas?: string[]
    teamRole?: TeamRole
    onboardingComplete?: boolean
  }) => void
  resetOnboarding: () => void

  openTab: (path: string, content: string) => void
  closeTab: (id: string) => void
  setActiveTab: (id: string) => void
  updateTabContent: (id: string, content: string) => void
  markTabDirty: (id: string, dirty: boolean) => void

  setSessions: (s: Session[]) => void
  addSession: (s: Session) => void
  removeSession: (id: string) => void
  renameSession: (id: string, title: string) => void
  setSessionId: (id: string) => void

  addMessage: (msg: ChatMessage) => void
  appendContent: (id: string, delta: string) => void
  finalizeMessage: (id: string) => void
  addToolCall: (msgId: string, tc: ToolCall) => void
  updateToolCall: (msgId: string, tcId: string, patch: Partial<ToolCall>) => void
  addFileDiff: (msgId: string, diff: FileDiff) => void
  updateFileDiff: (msgId: string, diffId: string, patch: Partial<FileDiff>) => void
  setAskPayload: (msgId: string, ask: ChatMessage['askPayload']) => void
  setPlanPayload: (msgId: string, plan: ChatMessage['planPayload']) => void
  setChatMode: (mode: ChatMode) => void
  setTeamRole: (role: TeamRole) => void
  setUseCodebase: (v: boolean) => void
  setIsStreaming: (v: boolean) => void
  setStreamingMsgId: (id: string | null) => void
  setInputDraft: (v: string) => void
  setMentionedFiles: (files: string[]) => void

  /** Remove all messages after (and including) the given index */
  truncateMessages: (fromIndex: number) => void
  /** Update a specific message's content (for inline edit) */
  updateMessageContent: (id: string, content: string) => void
  /** Remove a single message by id */
  removeMessage: (id: string) => void
  setMessageEditing: (id: string, editing: boolean) => void

  clearChat: () => void
  loadMessages: (msgs: ChatMessage[]) => void

  setTodos: (todos: Todo[]) => void
  updateTodo: (id: string, patch: Partial<Todo>) => void

  appendAgentTerminal: (chunk: string) => void
  clearAgentTerminal: () => void

  setSidebarView: (v: SidebarView) => void
  setSidebarWidth: (w: number) => void
  setSidebarVisible: (v: boolean) => void

  setAgentPaneWidth: (w: number) => void
  setAgentPaneVisible: (v: boolean) => void

  setBottomPanelHeight: (h: number) => void
  setBottomPanelVisible: (v: boolean) => void
  setBottomTab: (t: BottomTab) => void
  toggleBottomPanelMaximize: () => void

  addTerminal: (shell?: string) => string
  removeTerminal: (id: string) => void
  setActiveTerminal: (id: string) => void
  renameTerminal: (id: string, name: string) => void

  setDiagnostics: (d: Diagnostic[]) => void
  setMcpServers: (s: McpServer[]) => void
  setTheme: (t: 'dark' | 'light') => void
  setGitInfo: (branch: string, dirty: number) => void
}

export const useStore = create<AuraState>()((set) => ({
  workspace: '',
  workspaceTree: [],
  treeLoading: false,

  openTabs: [],
  activeTabId: null,

  sessions: [],
  sessionId: nextId(),
  messages: [],
  chatMode: 'agent',
  teamRole: 'testing',
  useCodebase: true,
  isStreaming: false,
  streamingMsgId: null,
  inputDraft: '',
  mentionedFiles: [],

  todos: [],
  agentTerminalLines: [],

  sidebarView: 'explorer',
  sidebarWidth: 240,
  sidebarVisible: true,

  agentPaneWidth: 380,
  agentPaneVisible: true,

  bottomPanelHeight: 260,
  bottomPanelVisible: false,
  bottomTab: 'terminal',
  bottomPanelMaximized: false,
  bottomPanelPrevHeight: 260,

  terminals: [{ id: 'term-1', name: 'powershell', shell: 'powershell' }],
  activeTerminalId: 'term-1',

  diagnostics: [],
  mcpServers: [],
  theme: 'light',
  orgName: '',
  userName: '',
  userTitle: '',
  focusAreas: [],
  onboardingComplete: null,

  gitBranch: '',
  gitDirtyCount: 0,

  setWorkspace: (p) => set({ workspace: p }),
  setWorkspaceTree: (tree) => set({ workspaceTree: tree }),
  setTreeLoading: (v) => set({ treeLoading: v }),
  setOrgProfile: (p) => set((s) => ({
    orgName: p.orgName ?? s.orgName,
    userName: p.userName ?? s.userName,
    userTitle: p.userTitle ?? s.userTitle,
    focusAreas: p.focusAreas ?? s.focusAreas,
    teamRole: p.teamRole ?? s.teamRole,
    onboardingComplete: p.onboardingComplete ?? s.onboardingComplete,
  })),
  resetOnboarding: () => set({ onboardingComplete: false }),

  openTab: (path, content) =>
    set((s) => {
      const existing = s.openTabs.find((t) => t.path === path)
      if (existing) return { activeTabId: existing.id }
      const tab: EditorTab = {
        id: nextId(),
        path,
        name: path.split(/[\\/]/).pop() ?? path,
        content,
        language: extToLang(path),
        dirty: false,
      }
      return { openTabs: [...s.openTabs, tab], activeTabId: tab.id }
    }),

  closeTab: (id) =>
    set((s) => {
      const tabs = s.openTabs.filter((t) => t.id !== id)
      let activeTabId = s.activeTabId
      if (activeTabId === id) {
        const idx = s.openTabs.findIndex((t) => t.id === id)
        activeTabId = tabs[Math.max(0, idx - 1)]?.id ?? tabs[0]?.id ?? null
      }
      return { openTabs: tabs, activeTabId }
    }),

  setActiveTab: (id) => set({ activeTabId: id }),

  updateTabContent: (id, content) =>
    set((s) => ({
      openTabs: s.openTabs.map((t) => (t.id === id ? { ...t, content } : t)),
    })),

  markTabDirty: (id, dirty) =>
    set((s) => ({
      openTabs: s.openTabs.map((t) => (t.id === id ? { ...t, dirty } : t)),
    })),

  setSessions: (sessions) => set({ sessions }),
  addSession: (s) => set((st) => ({ sessions: [s, ...st.sessions] })),
  removeSession: (id) => set((s) => ({ sessions: s.sessions.filter((x) => x.id !== id) })),
  renameSession: (id, title) =>
    set((s) => ({ sessions: s.sessions.map((x) => (x.id === id ? { ...x, title } : x)) })),

  setSessionId: (id) => set({ sessionId: id }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendContent: (id, delta) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + delta } : m,
      ),
    })),

  finalizeMessage: (id) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, streaming: false } : m,
      ),
    })),

  addToolCall: (msgId, tc) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId
          ? { ...m, toolCalls: [...(m.toolCalls ?? []), tc] }
          : m,
      ),
    })),

  updateToolCall: (msgId, tcId, patch) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId
          ? {
              ...m,
              toolCalls: (m.toolCalls ?? []).map((tc) =>
                tc.id === tcId ? { ...tc, ...patch } : tc,
              ),
            }
          : m,
      ),
    })),

  addFileDiff: (msgId, diff) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId
          ? { ...m, fileDiffs: [...(m.fileDiffs ?? []), diff] }
          : m,
      ),
    })),

  updateFileDiff: (msgId, diffId, patch) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId
          ? {
              ...m,
              fileDiffs: (m.fileDiffs ?? []).map((d) =>
                d.id === diffId ? { ...d, ...patch } : d,
              ),
            }
          : m,
      ),
    })),

  setAskPayload: (msgId, ask) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId ? { ...m, askPayload: ask } : m,
      ),
    })),

  setPlanPayload: (msgId, plan) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === msgId ? { ...m, planPayload: plan } : m,
      ),
    })),

  setChatMode: (mode) => set({ chatMode: mode }),
  setTeamRole: (role) => set({ teamRole: role }),
  setUseCodebase: (v) => set({ useCodebase: v }),
  setIsStreaming: (v) => set({ isStreaming: v }),
  setStreamingMsgId: (id) => set({ streamingMsgId: id }),
  setInputDraft: (v) => set({ inputDraft: v }),
  setMentionedFiles: (files) => set({ mentionedFiles: files }),

  truncateMessages: (fromIndex) =>
    set((s) => ({ messages: s.messages.slice(0, fromIndex) })),

  updateMessageContent: (id, content) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content, editing: false } : m,
      ),
    })),

  removeMessage: (id) =>
    set((s) => ({ messages: s.messages.filter((m) => m.id !== id) })),

  setMessageEditing: (id, editing) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, editing } : m,
      ),
    })),

  clearChat: () =>
    set({ messages: [], streamingMsgId: null, isStreaming: false, sessionId: nextId() }),

  loadMessages: (msgs) => set({ messages: msgs }),

  setTodos: (todos) => set({ todos }),
  updateTodo: (id, patch) =>
    set((s) => ({
      todos: s.todos.map((t) => (t.id === id ? { ...t, ...patch } : t)),
    })),

  appendAgentTerminal: (chunk) =>
    set((s) => ({ agentTerminalLines: [...s.agentTerminalLines, chunk] })),
  clearAgentTerminal: () => set({ agentTerminalLines: [] }),

  setSidebarView: (v) =>
    set((s) => ({
      sidebarView: v,
      sidebarVisible: v === null ? false : v === s.sidebarView ? !s.sidebarVisible : true,
    })),

  setSidebarWidth: (w) => set({ sidebarWidth: Math.max(150, Math.min(w, 600)) }),
  setSidebarVisible: (v) => set({ sidebarVisible: v }),

  setAgentPaneWidth: (w) => set({ agentPaneWidth: Math.max(260, Math.min(w, 700)) }),
  setAgentPaneVisible: (v) => set({ agentPaneVisible: v }),

  setBottomPanelHeight: (h) => set({ bottomPanelHeight: Math.max(100, Math.min(h, 900)), bottomPanelMaximized: false }),
  setBottomPanelVisible: (v) => set({ bottomPanelVisible: v }),
  setBottomTab: (t) => set({ bottomTab: t, bottomPanelVisible: true }),
  toggleBottomPanelMaximize: () =>
    set((s) => {
      if (s.bottomPanelMaximized) {
        return {
          bottomPanelMaximized: false,
          bottomPanelHeight: s.bottomPanelPrevHeight || 260,
        }
      }
      return {
        bottomPanelMaximized: true,
        bottomPanelPrevHeight: s.bottomPanelHeight,
        bottomPanelHeight: Math.max(400, Math.floor(window.innerHeight * 0.7)),
      }
    }),

  addTerminal: (shell = 'powershell') => {
    const id = `term-${Date.now()}`
    let name = shell
    set((s) => {
      const same = s.terminals.filter(t => t.shell === shell).length
      name = same === 0 ? shell : `${shell} (${same + 1})`
      return {
        terminals: [...s.terminals, { id, name, shell }],
        activeTerminalId: id,
        bottomTab: 'terminal' as BottomTab,
        bottomPanelVisible: true,
      }
    })
    return id
  },
  removeTerminal: (id) =>
    set((s) => {
      const next = s.terminals.filter(t => t.id !== id)
      if (next.length === 0) {
        const nid = `term-${Date.now()}`
        return {
          terminals: [{ id: nid, name: 'powershell', shell: 'powershell' }],
          activeTerminalId: nid,
        }
      }
      const active = s.activeTerminalId === id
        ? next[next.length - 1].id
        : s.activeTerminalId
      return { terminals: next, activeTerminalId: active }
    }),
  setActiveTerminal: (id) => set({ activeTerminalId: id, bottomTab: 'terminal', bottomPanelVisible: true }),
  renameTerminal: (id, name) =>
    set((s) => ({
      terminals: s.terminals.map(t => t.id === id ? { ...t, name } : t),
    })),

  setDiagnostics: (d) => set({ diagnostics: d }),
  setMcpServers: (s) => set({ mcpServers: s }),
  setTheme: (t) => set({ theme: t }),
  setGitInfo: (branch, dirty) => set({ gitBranch: branch, gitDirtyCount: dirty }),
}))
