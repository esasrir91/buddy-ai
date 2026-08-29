import React from 'react'
import type { PlanPayload } from '../../types'

interface Props {
  msgId: string
  plan: PlanPayload
  onConfirm: (msgId: string, confirmed: boolean) => void
}

export default function PlanView({ msgId, plan, onConfirm }: Props) {
  return (
    <div className="plan-card">
      <div className="plan-card__header">
        <span className="plan-card__title">📋 {plan.name}</span>
        {plan.confirmed === true && <span style={{ color: 'var(--ok)', fontSize: 12 }}>✓ Confirmed</span>}
        {plan.confirmed === false && <span style={{ color: 'var(--err)', fontSize: 12 }}>✕ Cancelled</span>}
      </div>
      <div className="plan-card__body">
        <p style={{ color: 'var(--text-dim)', marginBottom: 8, fontSize: 12.5 }}>{plan.overview}</p>
        {plan.todos && plan.todos.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {plan.todos.map((t, i) => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'baseline', gap: 8, fontSize: 12.5 }}>
                <span style={{ color: 'var(--text-faint)', minWidth: 16 }}>{i + 1}.</span>
                <span>{t.content}</span>
              </div>
            ))}
          </div>
        )}
        {plan.plan && !plan.todos && (
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, fontFamily: 'var(--font-ui)', color: 'var(--text)', lineHeight: 1.6 }}>
            {plan.plan}
          </pre>
        )}
      </div>
      {plan.confirmed == null && (
        <div className="plan-card__actions">
          <button className="btn btn--sm btn--primary" onClick={() => onConfirm(msgId, true)}>✓ Proceed</button>
          <button className="btn btn--sm btn--danger" onClick={() => onConfirm(msgId, false)}>✕ Cancel</button>
        </div>
      )}
    </div>
  )
}
