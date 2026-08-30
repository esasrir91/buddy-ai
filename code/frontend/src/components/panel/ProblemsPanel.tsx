import React from 'react'
import { useStore } from '../../store'
import { fsRead } from '../../api'
import type { Diagnostic } from '../../types'

export default function ProblemsPanel() {
  const { diagnostics, openTabs, openTab, setActiveTab } = useStore()

  const grouped: Record<string, Diagnostic[]> = {}
  for (const d of diagnostics) {
    if (!grouped[d.path]) grouped[d.path] = []
    grouped[d.path].push(d)
  }

  const goTo = async (d: Diagnostic) => {
    const existing = openTabs.find(t => t.path === d.path)
    if (existing) {
      setActiveTab(existing.id)
      return
    }
    try {
      const { content } = await fsRead(d.path)
      openTab(d.path, content)
    } catch {
      openTab(d.path, '')
    }
  }

  const total = diagnostics.length
  const errors = diagnostics.filter(d => d.severity === 'error').length
  const warnings = diagnostics.filter(d => d.severity === 'warning').length

  return (
    <div className="problems-list">
      {total === 0 ? (
        <div className="empty-state"><p>No problems detected ✓</p></div>
      ) : (
        <>
          <div style={{ padding: '4px 12px 2px', fontSize: 11, color: 'var(--text-faint)' }}>
            {errors > 0 && <span style={{ color: 'var(--err)', marginRight: 10 }}>● {errors} error{errors !== 1 ? 's' : ''}</span>}
            {warnings > 0 && <span style={{ color: 'var(--warn)', marginRight: 10 }}>● {warnings} warning{warnings !== 1 ? 's' : ''}</span>}
          </div>
          {Object.entries(grouped).map(([path, items]) => (
            <div key={path}>
              <div style={{ padding: '4px 12px 2px', fontSize: 11.5, color: 'var(--info)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                {path.split(/[\\/]/).pop()}
              </div>
              {items.map((d, i) => (
                <div key={i} className="problem-item" onClick={() => goTo(d)}>
                  <span className={`problem-icon--${d.severity}`}>
                    {d.severity === 'error' ? '●' : d.severity === 'warning' ? '▲' : 'ℹ'}
                  </span>
                  <span className="problem-item__msg">{d.message}</span>
                  <span className="problem-item__path">{path.split(/[\\/]/).pop()}</span>
                  <span className="problem-item__loc">({d.line},{d.column})</span>
                </div>
              ))}
            </div>
          ))}
        </>
      )}
    </div>
  )
}
