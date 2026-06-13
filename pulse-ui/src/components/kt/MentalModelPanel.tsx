import { Brain, CheckCircle2, HelpCircle } from 'lucide-react'
import type { KTSessionState } from '../../types/pulse'

interface Props {
  state: KTSessionState | null
  employeeName: string
}

export function MentalModelPanel({ state, employeeName }: Props) {
  if (!state) {
    return (
      <div className="h-full flex items-center justify-center p-6 text-center">
        <div>
          <Brain size={40} className="text-slate-700 mx-auto mb-3" />
          <p className="text-sm text-slate-500">
            Start a KT session to see<br />{employeeName}'s mental model build in real-time.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Phase badge */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-blue-400" />
          <span className="text-xs font-medium text-blue-400 uppercase tracking-wide">
            {state.phase.replace('_', ' ')}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Mental model draft */}
        {state.mental_model_draft && (
          <div>
            <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-2">
              Mental Model
            </p>
            <div className="bg-slate-900 rounded-lg p-3 border border-slate-800">
              <p className="text-sm text-slate-300 leading-relaxed">
                {state.mental_model_draft}
              </p>
            </div>
          </div>
        )}

        {/* Key concepts */}
        {state.key_concepts.length > 0 && (
          <div>
            <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-2">
              Key Concepts
            </p>
            <div className="flex flex-wrap gap-1.5">
              {state.key_concepts.map((c) => (
                <span
                  key={c}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/10 border border-green-500/20 rounded-md text-xs text-green-400"
                >
                  <CheckCircle2 size={10} />
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Pending questions */}
        {state.pending_questions.length > 0 && (
          <div>
            <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-2">
              Open Questions
            </p>
            <div className="space-y-2">
              {state.pending_questions.map((q, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 p-2.5 bg-amber-500/5 border border-amber-500/20 rounded-lg"
                >
                  <HelpCircle size={13} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-200">{q}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Progress */}
        <div className="text-[11px] text-slate-600 pt-2 border-t border-slate-800">
          Round {state.rounds_completed} · {state.mode} mode
        </div>
      </div>
    </div>
  )
}
