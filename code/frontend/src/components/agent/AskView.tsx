import React, { useState } from 'react'
import type { AskPayload } from '../../types'

interface Props {
  msgId: string
  ask: AskPayload
  onAnswer: (msgId: string, answers: Record<string, any>) => void
}

export default function AskView({ msgId, ask, onAnswer }: Props) {
  const [selections, setSelections] = useState<Record<string, string | string[]>>({})

  const toggle = (qId: string, optId: string, multi: boolean) => {
    setSelections(prev => {
      if (multi) {
        const cur = (prev[qId] as string[] | undefined) ?? []
        const next = cur.includes(optId) ? cur.filter(x => x !== optId) : [...cur, optId]
        return { ...prev, [qId]: next }
      }
      return { ...prev, [qId]: optId }
    })
  }

  const allAnswered = ask.questions.every(q => {
    const s = selections[q.id]
    return s != null && (Array.isArray(s) ? s.length > 0 : s !== '')
  })

  return (
    <div className="ask-card">
      <div className="ask-card__header">
        ❓ {ask.title ?? 'Question'}
      </div>
      <div className="ask-card__body">
        {ask.questions.map(q => (
          <div key={q.id} className="ask-question">
            <div className="ask-question__prompt">{q.prompt}</div>
            <div className="ask-options">
              {q.options.map(opt => {
                const sel = selections[q.id]
                const isSelected = Array.isArray(sel) ? sel.includes(opt.id) : sel === opt.id
                return (
                  <label
                    key={opt.id}
                    className={`ask-option${isSelected ? ' ask-option--selected' : ''}`}
                    onClick={() => toggle(q.id, opt.id, q.allow_multiple ?? false)}
                  >
                    {q.allow_multiple
                      ? <input type="checkbox" checked={isSelected} readOnly style={{ pointerEvents: 'none' }} />
                      : <input type="radio" checked={isSelected} readOnly style={{ pointerEvents: 'none' }} />
                    }
                    {opt.label}
                  </label>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="ask-card__submit">
        <button
          className="btn btn--sm btn--primary"
          disabled={!allAnswered}
          onClick={() => onAnswer(msgId, selections)}
        >
          Submit
        </button>
      </div>
    </div>
  )
}
