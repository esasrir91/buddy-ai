// ── All Aura backend API calls ────────────────────────────────────────────

const BASE = '/api'

async function req<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<T>
}

const get = <T>(path: string) => req<T>('GET', path)
const post = <T>(path: string, body?: unknown) => req<T>('POST', path, body)
const put = <T>(path: string, body?: unknown) => req<T>('PUT', path, body)
const del = <T>(path: string, body?: unknown) => req<T>('DELETE', path, body)

// ── health ────────────────────────────────────────────────────────────────
export const health = () => get('/health')

// ── workspace ─────────────────────────────────────────────────────────────
export const getWorkspace = () => get<{ path: string }>('/workspace')
export const setWorkspace = (path: string) => post<{ ok: boolean; path: string }>('/workspace', { path })

// ── file system ───────────────────────────────────────────────────────────
export const fsList = (path = '.') => get<{ path: string; children: Array<{ name: string; path: string; type: string }> }>(`/fs/list?path=${encodeURIComponent(path)}`)
export const fsRead = (path: string) => get<{ path: string; content: string }>(`/fs/file?path=${encodeURIComponent(path)}`)
export const fsWrite = (path: string, content: string) => put('/fs/file', { path, content })

// ── settings ──────────────────────────────────────────────────────────────
export const getSettings = () => get<{ settings: Record<string, unknown>; workspace: string; providers: Record<string, string> }>('/settings')
export const updateSettings = (update: Record<string, unknown>) => put('/settings', update)

// ── models ────────────────────────────────────────────────────────────────
export const getModels = () => get<unknown[]>('/models')
export const getTools = () => get<unknown[]>('/tools')

// ── sessions (thread persistence) ─────────────────────────────────────────
export const getSessions = () => get<{ sessions: Array<{ id: string; title: string; updated: number }> }>('/sessions')
export const createSession = () => post<{ id: string }>('/sessions')
export const deleteSession = (id: string) => del(`/sessions/${id}`)

// ── chat (SSE) ────────────────────────────────────────────────────────────
export interface ChatRequest {
  message: string
  mode?: string
  session_id?: string
  context?: {
    active_file?: string
    active_file_content?: string
    selection?: string
    selection_start?: number
    selection_end?: number
    mentioned_files?: string[]
    images?: string[]
    notepad?: string
    rules?: string
    diagnostics?: string
  }
}

export function streamChat(
  req: ChatRequest,
  onEvent: (ev: Record<string, unknown>) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal,
    })
      .then(async (res) => {
        if (!res.ok) { reject(new Error(await res.text())); return }
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() ?? ''
          for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith('data:')) continue
            const data = line.slice(5).trim()
            if (data === '[DONE]') { resolve(); return }
            try { onEvent(JSON.parse(data)) } catch { /* skip */ }
          }
        }
        resolve()
      })
      .catch(reject)
  })
}

// ── cancel ────────────────────────────────────────────────────────────────
export const cancelRun = (sessionId?: string) => post('/chat/cancel', { session_id: sessionId })

// ── inline edit ───────────────────────────────────────────────────────────
export function streamInlineEdit(
  payload: { file_path: string; selection: string; instruction: string; start_line: number },
  onEvent: (ev: Record<string, unknown>) => void,
  signal?: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    fetch(`${BASE}/inline-edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
      .then(async (res) => {
        if (!res.ok) { reject(new Error(await res.text())); return }
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() ?? ''
          for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith('data:')) continue
            const data = line.slice(5).trim()
            if (data === '[DONE]') { resolve(); return }
            try { onEvent(JSON.parse(data)) } catch { /* skip */ }
          }
        }
        resolve()
      })
      .catch(reject)
  })
}

// ── completions ───────────────────────────────────────────────────────────
export const getCompletion = (payload: { file_path: string; content_before: string; content_after: string; language: string }) =>
  post<{ completion: string }>('/completions', payload)

// ── git ───────────────────────────────────────────────────────────────────
export const gitStatus = () => get<{ output: string; branch: string; files: Array<{ path: string; status: string; staged: boolean }> }>('/git/status')
export const gitLog = (limit = 30) => get<{ output: string }>(`/git/log?limit=${limit}`)
export const gitDiff = (staged = false) => get<{ output: string }>(`/git/diff?staged=${staged}`)
export const gitStage = (paths: string[]) => post('/git/stage', { paths })
export const gitUnstage = (paths: string[]) => post('/git/unstage', { paths })
export const gitCommit = (message: string) => post<{ output: string }>('/git/commit', { message })
export const gitDiscard = (paths: string[]) => post('/git/discard', { paths })
export const gitBranches = () => get<{ output: string }>('/git/branches')
export const gitCheckout = (branch: string) => post('/git/checkout', { branch })
export const gitCommitMsg = () => post<{ message: string }>('/git/commit-message')

// ── rules ─────────────────────────────────────────────────────────────────
export const getRules = () => get<{ content: string }>('/rules')
export const setRules = (content: string) => put('/rules', { content })

// ── diagnostics ───────────────────────────────────────────────────────────
export const postDiagnostics = (markers: unknown[]) => post('/diagnostics', { markers })
export const getDiagnostics = () => get<{ markers: unknown[] }>('/diagnostics')

// ── run (shell) ───────────────────────────────────────────────────────────
export const runCmd = (command: string, cwd?: string) => post<{ output: string; exit_code: number }>('/run', { command, cwd })

// ── search ────────────────────────────────────────────────────────────────
export const search = (q: string) => get<{ results: Array<{ path: string; line: number; text: string }> }>(`/search?q=${encodeURIComponent(q)}`)

// ── MCP servers ───────────────────────────────────────────────────────────
export const getMcpServers = () => get<{ servers: unknown[] }>('/mcp/servers')
export const addMcpServer = (server: unknown) => post('/mcp/servers', server)
export const removeMcpServer = (name: string) => del(`/mcp/servers/${encodeURIComponent(name)}`)
export const toggleMcpServer = (name: string, enabled: boolean) => put(`/mcp/servers/${encodeURIComponent(name)}`, { enabled })

// ── custom tools ──────────────────────────────────────────────────────────
export const getCustomTools = () => get<{ tools: unknown[] }>('/tools/custom')
export const generateTool = (prompt: string) => post<{ code: string; name: string; description: string }>('/tools/generate', { prompt })
export const saveCustomTool = (name: string, code: string, description: string) => post('/tools/custom', { name, code, description })
export const deleteCustomTool = (name: string) => del(`/tools/custom/${encodeURIComponent(name)}`)

// ── account ───────────────────────────────────────────────────────────────
export const getAccount = () => get('/account')
export const activate = (token: string) => post('/account/activate', { token })

// ── observer ──────────────────────────────────────────────────────────────
export const getObserverStatus = () => get('/observer/status')
export const getObserverConfig = () => get('/observer/config')
export const updateObserverConfig = (cfg: unknown) => put('/observer/config', cfg)
export const startObserver = () => post('/observer/start')
export const stopObserver = () => post('/observer/stop')
export const getObserverJournal = (limit = 50) => get(`/observer/journal?limit=${limit}`)

// ── file watcher SSE ──────────────────────────────────────────────────────
export function subscribeFileWatch(
  workspacePath: string,
  onEvent: (ev: { type: string; path: string }) => void,
): () => void {
  const es = new EventSource(`${BASE}/fs/watch?workspace=${encodeURIComponent(workspacePath)}`)
  es.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)) } catch { /* skip */ }
  }
  return () => es.close()
}

// ── chat answer (for AskQuestion pause) ──────────────────────────────────
export const chatAnswer = (sessionId: string, answers: Record<string, unknown>) =>
  post('/chat/answer', { session_id: sessionId, answers })

// ── plan confirm ──────────────────────────────────────────────────────────
export const confirmPlan = (sessionId: string, confirmed: boolean) =>
  post('/chat/plan-confirm', { session_id: sessionId, confirmed })
