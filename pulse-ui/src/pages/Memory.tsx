import { useState, useEffect, useCallback } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { getMemory, forgetMemory, clearAllMemory, clearChatHistory } from '../api/pulse'
import type { MemoryFact, ChatHistoryMsg } from '../types/pulse'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

type Tab = 'facts' | 'history'

export default function Memory() {
  const { employee } = usePulseStore()
  const [tab, setTab] = useState<Tab>('facts')
  const [facts, setFacts] = useState<MemoryFact[]>([])
  const [history, setHistory] = useState<ChatHistoryMsg[]>([])
  const [loading, setLoading] = useState(false)
  const [confirmClear, setConfirmClear] = useState<'all' | 'history' | null>(null)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    if (!employee) return
    setLoading(true)
    try {
      const data = await getMemory(employee.employee_id)
      setFacts(data.long_term_memories)
      setHistory(data.chat_history)
    } catch {
      setError('Failed to load memory.')
    } finally {
      setLoading(false)
    }
  }, [employee])

  useEffect(() => { refresh() }, [refresh])

  const handleForget = async (id: string) => {
    if (!employee) return
    try {
      await forgetMemory(employee.employee_id, id)
      setFacts((prev) => prev.filter((f) => f.id !== id))
    } catch {
      setError('Failed to remove memory.')
    }
  }

  const handleClear = async () => {
    if (!employee || !confirmClear) return
    try {
      if (confirmClear === 'all') {
        await clearAllMemory(employee.employee_id)
        setFacts([])
        setHistory([])
      } else {
        await clearChatHistory(employee.employee_id)
        setHistory([])
      }
    } catch {
      setError('Failed to clear memory.')
    } finally {
      setConfirmClear(null)
    }
  }

  if (!employee) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500">
        No employee selected.
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-zinc-950 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-zinc-200 flex items-center gap-2">
            <span>🧠</span> Memory
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            What {employee.profile.full_name.split(' ')[0]} remembers across sessions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors px-2 py-1 rounded border border-zinc-700 hover:border-zinc-500"
          >
            ↻ Refresh
          </button>
          <button
            onClick={() => setConfirmClear('history')}
            className="text-xs text-zinc-500 hover:text-amber-400 transition-colors px-2 py-1 rounded border border-zinc-700 hover:border-amber-600"
          >
            Clear History
          </button>
          <button
            onClick={() => setConfirmClear('all')}
            className="text-xs text-zinc-500 hover:text-red-400 transition-colors px-2 py-1 rounded border border-zinc-700 hover:border-red-600"
          >
            Clear All Memory
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-800 bg-zinc-900">
        {([['facts', '🧠 Long-term Memories', facts.length], ['history', '💬 Conversation History', history.length]] as const).map(
          ([id, label, count]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`px-5 py-2.5 text-sm font-medium transition-colors border-b-2 ${
                tab === id
                  ? 'text-blue-400 border-blue-500 bg-blue-500/5'
                  : 'text-zinc-500 border-transparent hover:text-zinc-300'
              }`}
            >
              {label}
              <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${tab === id ? 'bg-blue-600/30 text-blue-300' : 'bg-zinc-800 text-zinc-500'}`}>
                {count}
              </span>
            </button>
          ),
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading && (
          <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">Loading…</div>
        )}

        {/* Long-term facts */}
        {!loading && tab === 'facts' && (
          <>
            {facts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-zinc-500">
                <p className="text-3xl mb-2">🧠</p>
                <p className="text-sm font-medium mb-1">No memories yet</p>
                <p className="text-xs text-center max-w-sm">
                  PULSE automatically extracts and stores important facts from every conversation — preferences, deadlines, project details, names, and more.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-zinc-600 mb-3">
                  Auto-extracted from conversations · {facts.length} facts stored · newest first
                </p>
                {facts.map((fact) => (
                  <div
                    key={fact.id}
                    className="group flex items-start gap-3 px-4 py-3 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-colors"
                  >
                    <span className="text-blue-400 mt-0.5 shrink-0 text-base">💡</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-zinc-200 leading-relaxed">{fact.fact}</p>
                      <p className="text-[10px] text-zinc-600 mt-1">
                        {fact.source} · {timeAgo(fact.ts)}
                      </p>
                    </div>
                    <button
                      onClick={() => handleForget(fact.id)}
                      className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all text-xs shrink-0 mt-0.5"
                      title="Forget this"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Conversation history */}
        {!loading && tab === 'history' && (
          <>
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-zinc-500">
                <p className="text-3xl mb-2">💬</p>
                <p className="text-sm font-medium mb-1">No conversation history</p>
                <p className="text-xs">Start chatting with PULSE to build up context.</p>
              </div>
            ) : (
              <div className="space-y-2 max-w-3xl">
                <p className="text-xs text-zinc-600 mb-3">
                  Last {history.length} messages · used to give PULSE context in each new conversation
                </p>
                {history.map((msg, i) => (
                  <div
                    key={i}
                    className={`px-4 py-3 rounded-lg text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-blue-500/10 border border-blue-500/20 text-blue-100'
                        : 'bg-zinc-900 border border-zinc-800 text-zinc-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-[10px] font-semibold uppercase tracking-wide ${msg.role === 'user' ? 'text-blue-400' : 'text-emerald-400'}`}>
                        {msg.role === 'user' ? '👤 You' : `🤖 ${employee.profile.full_name.split(' ')[0]}`}
                      </span>
                      <span className="text-[10px] text-zinc-600">{timeAgo(msg.ts)}</span>
                    </div>
                    <p className="whitespace-pre-wrap break-words">
                      {msg.content.length > 500 ? msg.content.slice(0, 500) + '…' : msg.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Confirm dialog */}
      {confirmClear && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setConfirmClear(null)}>
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-6 max-w-sm w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-zinc-200 mb-2">
              {confirmClear === 'all' ? 'Clear all memory?' : 'Clear conversation history?'}
            </h3>
            <p className="text-xs text-zinc-400 mb-4">
              {confirmClear === 'all'
                ? 'This will erase all long-term memories AND conversation history. PULSE will start fresh.'
                : 'This will clear the recent conversation history. Long-term memory facts are kept.'}
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleClear}
                className="flex-1 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors"
              >
                {confirmClear === 'all' ? 'Clear Everything' : 'Clear History'}
              </button>
              <button
                onClick={() => setConfirmClear(null)}
                className="flex-1 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="fixed bottom-4 right-4 bg-red-900/80 text-red-200 text-xs px-4 py-2 rounded-lg border border-red-700">
          {error}
          <button onClick={() => setError('')} className="ml-3 text-red-400 hover:text-red-200">✕</button>
        </div>
      )}
    </div>
  )
}
