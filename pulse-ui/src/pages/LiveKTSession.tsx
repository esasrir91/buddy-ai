import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, X } from 'lucide-react'
import { usePulseStore } from '../hooks/usePulseStore'
import { useKTSession } from '../hooks/useKTSession'
import { LiveKTChat, type ChatEntry } from '../components/kt/LiveKTChat'
import { ConfidenceMeter } from '../components/kt/ConfidenceMeter'
import { MentalModelPanel } from '../components/kt/MentalModelPanel'

export default function LiveKTSession() {
  const navigate = useNavigate()
  const { employeeId, employee } = usePulseStore()
  const employeeName = employee?.profile.full_name ?? 'PULSE'

  const kt = useKTSession(employeeId ?? '')
  const [chatEntries, setChatEntries] = useState<ChatEntry[]>([])
  const [committed, setCommitted] = useState(false)

  // Pre-load the session if we have a sessionId from the URL
  const handleSend = useCallback(
    async (text: string) => {
      const humanEntry: ChatEntry = { id: crypto.randomUUID(), role: 'human', text }
      setChatEntries((prev) => [...prev, humanEntry])

      // First message → human_explains; subsequent → human_answers
      const isFirst = chatEntries.length === 0
      const turn = isFirst
        ? await kt.explain(text)
        : await kt.answer({ response: text })

      if (!turn) return
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
