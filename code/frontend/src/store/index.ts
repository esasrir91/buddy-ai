import { create } from 'zustand'
import type {
  ChatMessage,
  ChatMode,
  Diagnostic,
  EditorTab,
  FileNode,
  FileDiff,
  McpServer,
  SidebarView,
  BottomTab,
  Todo,
  ToolCall,
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

  // chat / agent
  sessionId: string
  messages: ChatMessage[]
  chatMode: ChatMode
  isStreaming: boolean
  streamingMsgId: string | null
  inputDraft: string
  mentionedFiles: string[]

  // agent todos
  todos: Todo[]

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

  // problems
  diagnostics: Diagnostic[]

  // mcp
  mcpServers: McpServer[]

  // theme
  theme: 'dark' | 'light'

  // git
  gitBranch: string
  gitDirtyCount: number

  // actions ─────────────────────────────────────────────────────────────
  setWorkspace: (p: string) => void
  setWorkspaceTree: (tree: FileNode[]) => void
  setTreeLoading: (v: boolean) => void

  openTab: (path: string, content: string) => void
  closeTab: (id: string) => void
  setActiveTab: (id: string) => void
  updateTabContent: (id: string, content: string) => void
  markTabDirty: (id: string, dirty: boolean) => void

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
  setIsStreaming: (v: boolean) => void
  setStreamingMsgId: (id: string | null) => void
  setInputDraft: (v: string) => void
  setMentionedFiles: (files: string[]) => void
  clearChat: () => void

  setTodos: (todos: Todo[]) => void
  updateTodo: (id: string, patch: Partial<Todo>) => void

  setSidebarView: (v: SidebarView) => void
  setSidebarWidth: (w: number) => void
  setSidebarVisible: (v: boolean) => void

  setAgentPaneWidth: (w: number) => void
  setAgentPaneVisible: (v: boolean) => void

  setBottomPanelHeight: (h: number) => void
  setBottomPanelVisible: (v: boolean) => void
  setBottomTab: (t: BottomTab) => void

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

  sessionId: nextId(),
  messages: [],
  chatMode: 'agent',
  isStreaming: false,
  streamingMsgId: null,
  inputDraft: '',
  mentionedFiles: [],

  todos: [],

  sidebarView: 'explorer',
  sidebarWidth: 240,
  sidebarVisible: true,

  agentPaneWidth: 380,
  agentPaneVisible: true,

  bottomPanelHeight: 220,
  bottomPanelVisible: false,
  bottomTab: 'terminal',

  diagnostics: [],
  mcpServers: [],
  theme: 'dark',
  gitBranch: '',
  gitDirtyCount: 0,

  setWorkspace: (p) => set({ workspace: p }),
  setWorkspaceTree: (tree) => set({ workspaceTree: tree }),
  setTreeLoading: (v) => set({ treeLoading: v }),

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
  setIsStreaming: (v) => set({ isStreaming: v }),
  setStreamingMsgId: (id) => set({ streamingMsgId: id }),
  setInputDraft: (v) => set({ inputDraft: v }),
  setMentionedFiles: (files) => set({ mentionedFiles: files }),

  clearChat: () =>
    set({ messages: [], streamingMsgId: null, isStreaming: false, sessionId: nextId() }),

  setTodos: (todos) => set({ todos }),
  updateTodo: (id, patch) =>
    set((s) => ({
      todos: s.todos.map((t) => (t.id === id ? { ...t, ...patch } : t)),
    })),

  setSidebarView: (v) =>
    set((s) => ({
      sidebarView: v,
      sidebarVisible: v === null ? false : v === s.sidebarView ? !s.sidebarVisible : true,
    })),

  setSidebarWidth: (w) => set({ sidebarWidth: Math.max(150, Math.min(w, 600)) }),
  setSidebarVisible: (v) => set({ sidebarVisible: v }),

  setAgentPaneWidth: (w) => set({ agentPaneWidth: Math.max(260, Math.min(w, 700)) }),
  setAgentPaneVisible: (v) => set({ agentPaneVisible: v }),

  setBottomPanelHeight: (h) => set({ bottomPanelHeight: Math.max(100, Math.min(h, 600)) }),
  setBottomPanelVisible: (v) => set({ bottomPanelVisible: v }),
  setBottomTab: (t) => set({ bottomTab: t, bottomPanelVisible: true }),

  setDiagnostics: (d) => set({ diagnostics: d }),
  setMcpServers: (s) => set({ mcpServers: s }),
  setTheme: (t) => set({ theme: t }),
  setGitInfo: (branch, dirty) => set({ gitBranch: branch, gitDirtyCount: dirty }),
}))
