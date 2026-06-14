import { useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle, X } from 'lucide-react'
import { usePulseStore } from '../hooks/usePulseStore'
import { useKTSession } from '../hooks/useKTSession'
import { LiveKTChat, type ChatEntry } from '../components/kt/LiveKTChat'
import { ConfidenceMeter } from '../components/kt/ConfidenceMeter'
import { MentalModelPanel } from '../components/kt/MentalModelPanel'

export default function LiveKTSession() {
  const navigate = useNavigate()
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const { employeeId, employee } = usePulseStore()
  const employeeName = employee?.profile.full_name ?? 'PULSE'

  // Pass the session ID from the URL so the hook is ready immediately
  const kt = useKTSession(employeeId ?? '', urlSessionId)
  const [chatEntries, setChatEntries] = useState<ChatEntry[]>([])
  const [committed, setCommitted] = useState(false)
  const [sessionError, setSessionError] = useState('')

  const handleSend = useCallback(
    async (text: string) => {
      setSessionError('')
      const humanEntry: ChatEntry = { id: crypto.randomUUID(), role: 'human', text }
      setChatEntries((prev) => [...prev, humanEntry])

      // First message → human_explains; subsequent → human_answers
      const isFirst = chatEntries.length === 0
      const turn = isFirst
        ? await kt.explain(text)
        : await kt.answer({ response: text })

      if (!turn) {
        setSessionError(kt.error ?? 'No response from PULSE. Check the server.')
        return
      }
      const pulseEntry: ChatEntry = {
        id: crypto.randomUUID(),
        role: 'pulse',
        text: turn.pulse_message,
        turn,
      }
      setChatEntries((prev) => [...prev, pulseEntry])
    },
    [chatEntries, kt],
  )

  const handleCommit = async () => {
    const summary = await kt.commit()
    if (summary) setCommitted(true)
  }

  const confidence = kt.state?.confidence_score ?? 0
  const isReady = kt.turns.length > 0 && (kt.turns[kt.turns.length - 1]?.ready_to_commit ?? false)

  if (!urlSessionId) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500">
        <div className="text-center">
          <p className="text-3xl mb-2">⚠️</p>
          <p className="text-sm mb-3">No session ID found. Start a session from the KT Center.</p>
          <button onClick={() => navigate('/kt')} className="px-4 py-2 bg-blue-600 rounded-lg text-white text-sm">Back to KT Center</button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-3 bg-slate-900 border-b border-slate-800 flex-shrink-0">
        <div>
          <h1 className="text-sm font-semibold text-white">Live KT Session</h1>
          <p className="text-xs text-slate-500">with {employeeName}</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {isReady && !committed && (
            <button
              onClick={handleCommit}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-500 rounded-lg text-white text-xs font-medium"
            >
              <CheckCircle size={13} /> Commit KT
            </button>
          )}
          {committed && (
            <span className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600/20 text-green-400 rounded-lg text-xs font-medium">
              <CheckCircle size={13} /> KT Saved
            </span>
          )}
          <button onClick={() => navigate('/kt')} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400">
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Session error banner */}
      {sessionError && (
        <div className="px-4 py-2 bg-red-900/40 border-b border-red-700 text-red-300 text-xs flex items-center justify-between">
          <span>⚠️ {sessionError}</span>
          <button onClick={() => setSessionError('')} className="text-red-400 hover:text-red-200 ml-4">✕</button>
        </div>
      )}

      {/* 3-panel layout */}
      <div className="flex-1 overflow-hidden flex">
        {/* Left: chat */}
        <div className="flex-1 overflow-hidden border-r border-slate-800">
          <LiveKTChat
            entries={chatEntries}
            employeeName={employeeName}
            isLoading={kt.isLoading}
            onHumanSend={handleSend}
            placeholder="Explain the topic… (PULSE will ask clarifying questions)"
          />
        </div>

        {/* Right: confidence + mental model */}
        <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden">
          {/* Confidence meter */}
          <div className="p-4 border-b border-slate-800 flex justify-center">
            <ConfidenceMeter confidence={confidence} size={150} />
          </div>

          {/* Mental model */}
          <div className="flex-1 overflow-hidden">
            <MentalModelPanel state={kt.state} employeeName={employeeName} />
          </div>
        </div>
      </div>
    </div>
  )
}
