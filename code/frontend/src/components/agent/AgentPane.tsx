import React, { useRef, useEffect, useState, useCallback } from 'react'
import { useStore } from '../../store'
import {
  streamChat, cancelRun, chatAnswer, confirmPlan, fsWrite,
  getSessions, createSession, deleteSession, renameSession, replaceMessages, getSession,
} from '../../api'
import ChatMessage from './ChatMessage'
import type { ChatMessage as ChatMsg, FileDiff, ToolCall, AskPayload, PlanPayload, Session } from '../../types'
import AtMentionMenu from './AtMentionMenu'
import TodoList from './TodoList'
import { teamMeta, teamWorkflows } from '../../teams'
import { writeToActiveTerminal } from '../panel/terminalBus'

let _msgSeq = 0
const nid = () => `msg_${Date.now()}_${++_msgSeq}`
let _toolSeq = 0
const tid = () => `tc_${Date.now()}_${++_toolSeq}`
let _diffSeq = 0
const did = () => `diff_${Date.now()}_${++_diffSeq}`

interface Props {
  style?: React.CSSProperties
}

export default function AgentPane({ style }: Props) {
  const {
    messages, isStreaming, chatMode, sessionId, inputDraft, mentionedFiles,
    openTabs, activeTabId, diagnostics, todos, sessions, useCodebase, teamRole,
    orgName, userName,
    setChatMode, addMessage, appendContent, addToolCall, updateToolCall,
    addFileDiff, updateFileDiff, setAskPayload, setPlanPayload,
    setIsStreaming, setStreamingMsgId, streamingMsgId,
    setInputDraft, setMentionedFiles, setSessions, setSessionId, addSession,
    removeSession: removeSessionStore, renameSession: renameSessionStore,
    openTab, updateTabContent, markTabDirty,
    setTodos, updateTodo, finalizeMessage, clearChat, loadMessages,
    truncateMessages, removeMessage, updateMessageContent, setMessageEditing,
    setUseCodebase, appendAgentTerminal, clearAgentTerminal, setBottomTab,
    setBottomPanelVisible,
  } = useStore()

  const bodyRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [showTodos, setShowTodos] = useState(false)
  const [atSearch, setAtSearch] = useState('')
  const [showAt, setShowAt] = useState(false)
  const [atAnchor, setAtAnchor] = useState<{ query: string; startPos: number } | null>(null)
  const [imgBase64, setImgBase64] = useState<string[]>([])
  const [showSessionMenu, setShowSessionMenu] = useState(false)
  const sessionMenuRef = useRef<HTMLDivElement>(null)

  // Load sessions on mount
  useEffect(() => {
    getSessions().then(r => setSessions(r.sessions)).catch(() => {})
  }, [])

  // Close session menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (sessionMenuRef.current && !sessionMenuRef.current.contains(e.target as Node)) {
        setShowSessionMenu(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // auto-scroll
  useEffect(() => {
    const el = bodyRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  // keyboard shortcut Ctrl+L / Cmd+L → focus input
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault()
        textareaRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const getActiveFileContext = useCallback(() => {
    const tab = openTabs.find(t => t.id === activeTabId)
    if (!tab) return {}
    return {
      active_file: tab.path,
      active_file_content: tab.content.slice(0, 12000),
    }
  }, [openTabs, activeTabId])

  // Core streaming logic, reusable for send + retry
  const runStream = useCallback(async (text: string, assistantId: string, existingSessionId: string) => {
    const diag = diagnostics.slice(0, 20)
    const diagStr = diag.map(d => `${d.path}:${d.line} [${d.severity}] ${d.message}`).join('\n')
    abortRef.current = new AbortController()
    try {
      await streamChat(
        {
          message: text,
          mode: chatMode,
          session_id: existingSessionId,
          workspace_tools: useCodebase,
          team_role: teamRole,
          context: {
            ...getActiveFileContext(),
            mentioned_files: mentionedFiles,
            images: imgBase64,
            diagnostics: diagStr || undefined,
          },
        },
        (ev) => handleEvent(ev, assistantId),
        abortRef.current.signal,
      )
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        appendContent(assistantId, `\n\n_Error: ${e.message}_`)
      }
    } finally {
      finalizeMessage(assistantId)
      setIsStreaming(false)
      setStreamingMsgId(null)
      // Refresh session list
      getSessions().then(r => setSessions(r.sessions)).catch(() => {})
    }
  }, [chatMode, sessionId, useCodebase, teamRole, mentionedFiles, imgBase64, diagnostics, openTabs, activeTabId])

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return

    const userMsg: ChatMsg = {
      id: nid(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }
    addMessage(userMsg)
    setInputDraft('')
    setMentionedFiles([])
    setImgBase64([])

    const assistantId = nid()
    const assistantMsg: ChatMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      toolCalls: [],
      fileDiffs: [],
      timestamp: Date.now(),
      streaming: true,
    }
    addMessage(assistantMsg)
    setIsStreaming(true)
    setStreamingMsgId(assistantId)
    await runStream(text, assistantId, sessionId)
  }, [isStreaming, sessionId, runStream])

  const handleEvent = useCallback((ev: Record<string, unknown>, msgId: string) => {
    const type = ev.type as string

    if (type === 'text' || type === 'assistant' || type === 'content') {
      appendContent(msgId, (ev.content ?? ev.delta ?? '') as string)
    }

    else if (type === 'tool_start' || (type === 'tool' && ev.phase === 'started')) {
      const tc: ToolCall = {
        id: tid(),
        name: (ev.tool_name ?? ev.tool) as string,
        args: (ev.args ?? ev.input ?? {}) as Record<string, unknown>,
        status: 'running',
      }
      addToolCall(msgId, tc)
    }

    else if (type === 'tool_end' || (type === 'tool' && ev.phase === 'completed')) {
      const name = (ev.tool_name ?? ev.tool) as string
      const result = String(ev.result ?? ev.output ?? '')
      const msgs = useStore.getState().messages
      const msg = msgs.find(m => m.id === msgId)
      const tc = msg?.toolCalls?.find(t => t.name === name && t.status === 'running')
      if (tc) updateToolCall(msgId, tc.id, { status: 'done', result })
    }

    else if (type === 'tool_error') {
      const name = ev.tool_name as string
      const result = String(ev.error ?? ev.message ?? '')
      const msgs = useStore.getState().messages
      const msg = msgs.find(m => m.id === msgId)
      const tc = msg?.toolCalls?.find(t => t.name === name && t.status === 'running')
      if (tc) updateToolCall(msgId, tc.id, { status: 'error', result })
    }

    else if (type === 'file_edit') {
      const diff: FileDiff = {
        id: did(),
        path: ev.path as string,
        oldContent: (ev.old_content ?? '') as string,
        newContent: (ev.new_content ?? ev.content ?? '') as string,
        applied: null,
      }
      addFileDiff(msgId, diff)
      const tab = useStore.getState().openTabs.find(t => t.path === diff.path)
      if (tab) {
        updateTabContent(tab.id, diff.newContent)
        markTabDirty(tab.id, true)
      }
    }

    else if (type === 'shell_start') {
      clearAgentTerminal()
      const cmd = String(ev.command ?? '')
      writeToActiveTerminal(`\r\n\x1b[36m$ ${cmd}\x1b[0m\r\n`)
      setBottomTab('terminal')
      setBottomPanelVisible(true)
    }

    else if (type === 'shell_output') {
      const chunk = String(ev.chunk ?? '')
      appendAgentTerminal(chunk)
      writeToActiveTerminal(chunk.replace(/\n/g, '\r\n'))
    }

    else if (type === 'shell_end') {
      const code = ev.exit_code as number
      const line = `\r\n\x1b[90m[exit ${code}]\x1b[0m\r\n`
      appendAgentTerminal(`\n[exit ${code}]\n`)
      writeToActiveTerminal(line)
    }

    else if (type === 'todo_update') {
      const todos = ev.todos as any[]
      if (todos) setTodos(todos)
    }

    else if (type === 'ask_question') {
      const payload = ev.payload as AskPayload
      setAskPayload(msgId, payload)
    }

    else if (type === 'plan_created') {
      const plan = ev.plan as PlanPayload
      setPlanPayload(msgId, plan)
    }

    else if (type === 'mode_switch') {
      const mode = ev.mode as 'agent' | 'plan' | 'ask'
      if (mode) setChatMode(mode)
    }
  }, [appendContent, addToolCall, updateToolCall, addFileDiff, setAskPayload, setPlanPayload, setTodos, setChatMode, updateTabContent, markTabDirty, appendAgentTerminal, clearAgentTerminal, setBottomTab, setBottomPanelVisible])

  // ── Edit message ─────────────────────────────────────────────────────────
  const handleEditMessage = useCallback((msgId: string) => {
    setMessageEditing(msgId, true)
  }, [setMessageEditing])

  const handleSaveEdit = useCallback(async (msgId: string, newContent: string) => {
    const msgs = useStore.getState().messages
    const idx = msgs.findIndex(m => m.id === msgId)
    if (idx < 0) return
    updateMessageContent(msgId, newContent)
    // truncate everything after this message
    truncateMessages(idx + 1)
    // sync to server
    try {
      const updated = useStore.getState().messages.slice(0, idx + 1)
      await replaceMessages(sessionId, updated.map(m => ({ role: m.role, content: m.content, ts: m.timestamp })))
    } catch {}
    // re-run agent from this message
    const assistantId = nid()
    const assistantMsg: ChatMsg = {
      id: assistantId, role: 'assistant', content: '', toolCalls: [], fileDiffs: [],
      timestamp: Date.now(), streaming: true,
    }
    addMessage(assistantMsg)
    setIsStreaming(true)
    setStreamingMsgId(assistantId)
    await runStream(newContent, assistantId, sessionId)
  }, [sessionId, truncateMessages, updateMessageContent, addMessage, setIsStreaming, setStreamingMsgId, runStream])

  const handleCancelEdit = useCallback((msgId: string) => {
    setMessageEditing(msgId, false)
  }, [setMessageEditing])

  // ── Delete message ────────────────────────────────────────────────────────
  const handleDeleteMessage = useCallback(async (msgId: string) => {
    const msgs = useStore.getState().messages
    const idx = msgs.findIndex(m => m.id === msgId)
    if (idx < 0) return
    // Remove this message + the following assistant if it's a pair
    const toRemove = [msgId]
    if (msgs[idx].role === 'user' && msgs[idx + 1]?.role === 'assistant') {
      toRemove.push(msgs[idx + 1].id)
    }
    toRemove.forEach(id => removeMessage(id))
    // sync to server
    try {
      const remaining = useStore.getState().messages
      await replaceMessages(sessionId, remaining.map(m => ({ role: m.role, content: m.content, ts: m.timestamp })))
    } catch {}
  }, [sessionId, removeMessage])

  // ── Retry (regenerate last assistant) ────────────────────────────────────
  const handleRetry = useCallback(async (msgId: string) => {
    const msgs = useStore.getState().messages
    const idx = msgs.findIndex(m => m.id === msgId)
    if (idx < 0) return
    // Remove this assistant message, find preceding user message
    removeMessage(msgId)
    const userMsg = msgs.slice(0, idx).reverse().find(m => m.role === 'user')
    if (!userMsg) return
    const assistantId = nid()
    const assistantMsg: ChatMsg = {
      id: assistantId, role: 'assistant', content: '', toolCalls: [], fileDiffs: [],
      timestamp: Date.now(), streaming: true,
    }
    addMessage(assistantMsg)
    setIsStreaming(true)
    setStreamingMsgId(assistantId)
    await runStream(userMsg.content, assistantId, sessionId)
  }, [sessionId, removeMessage, addMessage, setIsStreaming, setStreamingMsgId, runStream])

  // ── Diff handlers ─────────────────────────────────────────────────────────
  const handleApplyDiff = useCallback(async (msgId: string, diffId: string, diff: FileDiff) => {
    try {
      await fsWrite(diff.path, diff.newContent)
      updateFileDiff(msgId, diffId, { applied: true })
      const tab = useStore.getState().openTabs.find(t => t.path === diff.path)
      if (tab) {
        updateTabContent(tab.id, diff.newContent)
        markTabDirty(tab.id, false)
      }
    } catch (e: any) {
      alert(`Failed to apply: ${e.message}`)
    }
  }, [updateFileDiff, updateTabContent, markTabDirty])

  const handleRejectDiff = useCallback((msgId: string, diffId: string) => {
    updateFileDiff(msgId, diffId, { applied: false })
  }, [updateFileDiff])

  const handleAnswerAsk = useCallback(async (msgId: string, answers: Record<string, any>) => {
    setAskPayload(msgId, { ...useStore.getState().messages.find(m => m.id === msgId)?.askPayload!, answered: answers })
    try {
      await chatAnswer(sessionId, answers)
    } catch {}
  }, [sessionId, setAskPayload])

  const handleConfirmPlan = useCallback(async (msgId: string, confirmed: boolean) => {
    const msg = useStore.getState().messages.find(m => m.id === msgId)
    if (msg?.planPayload) {
      setPlanPayload(msgId, { ...msg.planPayload, confirmed })
    }
    try {
      await confirmPlan(sessionId, confirmed)
    } catch {}
  }, [sessionId, setPlanPayload])

  const handleCancel = useCallback(() => {
    abortRef.current?.abort()
    cancelRun(sessionId).catch(() => {})
    setIsStreaming(false)
    setStreamingMsgId(null)
  }, [sessionId])

  // ── Session management ───────────────────────────────────────────────────
  const handleNewChat = useCallback(async () => {
    setShowSessionMenu(false)
    clearChat()
    try {
      const { id } = await createSession()
      setSessionId(id)
      getSessions().then(r => setSessions(r.sessions)).catch(() => {})
    } catch {}
  }, [clearChat, setSessionId, setSessions])

  const handleSwitchSession = useCallback(async (s: Session) => {
    setShowSessionMenu(false)
    clearChat()
    setSessionId(s.id)
    // load messages from server
    try {
      const data = await getSession(s.id)
      const msgs = (data.messages as any[]).map((m: any, i: number) => ({
        id: nid(),
        role: m.role as 'user' | 'assistant',
        content: m.content ?? '',
        timestamp: (m.ts ?? i) * 1000,
        toolCalls: [],
        fileDiffs: [],
      }))
      loadMessages(msgs)
    } catch {}
  }, [clearChat, setSessionId, loadMessages])

  const handleDeleteSession = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await deleteSession(id).catch(() => {})
    removeSessionStore(id)
    if (id === sessionId) {
      clearChat()
    }
  }, [sessionId, removeSessionStore, clearChat])

  // @ mention handling
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setInputDraft(val)
    const caret = e.target.selectionStart ?? val.length
    const before = val.slice(0, caret)
    const atIdx = before.lastIndexOf('@')
    if (atIdx !== -1 && (atIdx === 0 || before[atIdx - 1] === ' ' || before[atIdx - 1] === '\n')) {
      const query = before.slice(atIdx + 1)
      if (!query.includes(' ')) {
        setShowAt(true)
        setAtSearch(query)
        setAtAnchor({ query, startPos: atIdx })
        return
      }
    }
    setShowAt(false)
    setAtAnchor(null)
  }

  const handleAtSelect = (path: string) => {
    if (!atAnchor) return
    const before = inputDraft.slice(0, atAnchor.startPos)
    const after = inputDraft.slice(atAnchor.startPos + 1 + atAnchor.query.length)
    const fileName = path.split(/[\\/]/).pop() ?? path
    setInputDraft(before + `@${fileName} ` + after)
    setMentionedFiles([...mentionedFiles, path])
    setShowAt(false)
    setAtAnchor(null)
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(inputDraft)
    }
    if (e.key === 'Escape') {
      setShowAt(false)
      if (isStreaming) handleCancel()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (!file) continue
        const reader = new FileReader()
        reader.onload = () => setImgBase64(prev => [...prev, reader.result as string])
        reader.readAsDataURL(file)
      }
    }
  }

  const modeColors: Record<string, string> = {
    agent: 'var(--accent)',
    plan: 'var(--info)',
    ask: 'var(--ok)',
  }

  const currentSession = sessions.find(s => s.id === sessionId)

  return (
    <div className="agent-pane" style={style}>
      {/* Header */}
      <div className="agent-pane__header">
        {/* Sessions dropdown */}
        <div className="session-dropdown" ref={sessionMenuRef}>
          <button
            className="session-trigger"
            onClick={() => setShowSessionMenu(v => !v)}
            title="Chat history"
          >
            <span className="session-title">{currentSession?.title ?? 'New chat'}</span>
            <span className="session-chevron">{showSessionMenu ? '▲' : '▼'}</span>
          </button>
          {showSessionMenu && (
            <div className="session-menu">
              <button className="session-menu__new" onClick={handleNewChat}>
                + New chat
              </button>
              <div className="session-menu__list">
                {sessions.length === 0 && (
                  <div style={{ padding: '8px 12px', color: 'var(--text-faint)', fontSize: 12 }}>No history yet</div>
                )}
                {sessions.map(s => (
                  <div
                    key={s.id}
                    className={`session-menu__item${s.id === sessionId ? ' session-menu__item--active' : ''}`}
                    onClick={() => handleSwitchSession(s)}
                  >
                    <span className="session-menu__item-title">{s.title}</span>
                    <button
                      className="session-menu__item-del"
                      onClick={(e) => handleDeleteSession(s.id, e)}
                      title="Delete"
                    >✕</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="agent-header-right">
          <div className="mode-tabs">
            {(['agent', 'plan', 'ask'] as const).map(m => (
              <button
                key={m}
                className={`mode-tab${chatMode === m ? ' mode-tab--active' : ''}`}
                onClick={() => setChatMode(m)}
                style={chatMode === m ? { background: modeColors[m] } : {}}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
          <button className="icon-btn" title="Todos" onClick={() => setShowTodos(v => !v)}>
            ☑{todos.length > 0 && <span style={{ marginLeft: 2, color: 'var(--accent-2)', fontSize: 10 }}>{todos.length}</span>}
          </button>
          <button className="icon-btn" title="Clear chat" onClick={handleNewChat}>🗑</button>
          {isStreaming && (
            <button className="btn btn--sm btn--danger" onClick={handleCancel}>■ Stop</button>
          )}
        </div>
      </div>

      {/* Todos panel */}
      {showTodos && todos.length > 0 && (
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-base)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.6px', color: 'var(--text-faint)', marginBottom: 6 }}>Agent Todos</div>
          <TodoList todos={todos} />
        </div>
      )}

      {/* Messages */}
      <div className="agent-pane__body" ref={bodyRef}>
        {messages.length === 0 && (
          <div className="empty-state" style={{ paddingTop: 32 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '4px 10px', borderRadius: 999, marginBottom: 10,
              background: teamMeta(teamRole).color, color: '#fff',
              fontSize: 11, fontWeight: 700, letterSpacing: '.3px',
            }}>
              {teamMeta(teamRole).short} · {teamMeta(teamRole).label}
            </div>
            <div style={{ fontWeight: 650, color: 'var(--text)', fontSize: 15 }}>
              {userName ? `Hi ${userName.split(' ')[0]}` : 'Aura Agent'}
              {orgName ? ` · ${orgName}` : ''}
            </div>
            <p style={{ maxWidth: 280 }}>
              {teamMeta(teamRole).description}
            </p>
            <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
              {teamWorkflows(teamRole).slice(0, 4).map(q => (
                <button key={q.id} className="btn btn--xs btn--ghost" onClick={() => send(q.prompt)}>{q.label}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <ChatMessage
            key={msg.id}
            msg={msg}
            onApplyDiff={handleApplyDiff}
            onRejectDiff={handleRejectDiff}
            onAnswerAsk={handleAnswerAsk}
            onConfirmPlan={handleConfirmPlan}
            onEdit={handleEditMessage}
            onSaveEdit={handleSaveEdit}
            onCancelEdit={handleCancelEdit}
            onDelete={handleDeleteMessage}
            onRetry={handleRetry}
          />
        ))}

        {isStreaming && streamingMsgId && (
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', color: 'var(--accent-ai)', fontSize: 12 }}>
            <span className="spinner">⟳</span> Thinking…
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="agent-input-wrap">
        {/* Use codebase toggle */}
        <div className="agent-input-meta">
          <label className="codebase-toggle" title="Toggle workspace file tools on/off">
            <input
              type="checkbox"
              checked={useCodebase}
              onChange={e => setUseCodebase(e.target.checked)}
            />
            <span>Use codebase</span>
          </label>
        </div>

        {/* mentioned files */}
        {mentionedFiles.length > 0 && (
          <div className="ctx-pills-row">
            {mentionedFiles.map(f => (
              <span key={f} className="ctx-pill" onClick={() => setMentionedFiles(mentionedFiles.filter(x => x !== f))}>
                📄 {f.split(/[\\/]/).pop()} ✕
              </span>
            ))}
          </div>
        )}
        {/* pasted images */}
        {imgBase64.length > 0 && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {imgBase64.map((b, i) => (
              <div key={i} style={{ position: 'relative' }}>
                <img src={b} style={{ height: 48, width: 48, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--border)' }} alt="" />
                <button onClick={() => setImgBase64(prev => prev.filter((_, j) => j !== i))}
                  style={{ position: 'absolute', top: -4, right: -4, background: 'var(--err)', color: '#fff', border: 'none', borderRadius: '50%', width: 14, height: 14, cursor: 'pointer', fontSize: 9, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
              </div>
            ))}
          </div>
        )}

        {/* active file context indicator */}
        {useCodebase && openTabs.find(t => t.id === activeTabId) && (
          <div className="ctx-pills-row">
            <span className="ctx-pill" title="Current file is in context">
              📄 {openTabs.find(t => t.id === activeTabId)?.name}
            </span>
          </div>
        )}

        <div className="agent-input-box" style={{ position: 'relative' }}>
          {showAt && (
            <AtMentionMenu
              query={atSearch}
              onSelect={handleAtSelect}
              onClose={() => { setShowAt(false); setAtAnchor(null) }}
            />
          )}
          <textarea
            ref={textareaRef}
            value={inputDraft}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={useCodebase ? `Message Aura (${chatMode} mode)… @ to mention files` : `Message Aura (no project)…`}
            rows={1}
            style={{ overflowY: 'hidden' }}
            onInput={(e) => {
              const t = e.target as HTMLTextAreaElement
              t.style.height = 'auto'
              t.style.height = Math.min(t.scrollHeight, 200) + 'px'
            }}
          />
        </div>
        <div className="agent-input-actions">
          <div className="agent-input-left">
            <span style={{ fontSize: 11, color: 'var(--text-faint)' }}>
              Enter↵ send · Shift+Enter newline
            </span>
          </div>
          <div className="agent-input-right">
            <button
              className="btn btn--sm btn--primary"
              onClick={() => send(inputDraft)}
              disabled={isStreaming || !inputDraft.trim()}
            >
              {isStreaming ? '…' : '→'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
