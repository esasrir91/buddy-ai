import React, { useEffect, useRef, useState } from 'react'
import { useStore } from '../../store'
import TerminalPanel from './TerminalPanel'
import ProblemsPanel from './ProblemsPanel'
import type { BottomTab } from '../../types'

interface Props {
  style?: React.CSSProperties
}

export default function BottomPanel({ style }: Props) {
  const { bottomTab, setBottomTab, setBottomPanelVisible, diagnostics } = useStore()

  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length

  const tabs: Array<{ id: BottomTab; label: string; badge?: number }> = [
    { id: 'terminal', label: 'Terminal' },
    { id: 'problems', label: `Problems ${errCount + warnCount > 0 ? `(${errCount + warnCount})` : ''}` },
    { id: 'output', label: 'Output' },
  ]

  return (
    <div className="bottom-panel" style={style}>
      <div className="panel-tabs">
        {tabs.map(t => (
          <button
            key={t.id}
            className={`panel-tab${bottomTab === t.id ? ' panel-tab--active' : ''}`}
            onClick={() => setBottomTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        <button className="panel-close" title="Close panel" onClick={() => setBottomPanelVisible(false)}>×</button>
      </div>
      <div className="panel-body">
        {bottomTab === 'terminal' && <TerminalPanel />}
        {bottomTab === 'problems' && <ProblemsPanel />}
        {bottomTab === 'output' && <OutputPanel />}
      </div>
    </div>
  )
}

function OutputPanel() {
  return (
    <div style={{ padding: 8, height: '100%', overflow: 'auto', fontFamily: 'var(--font-mono)', fontSize: 12.5, color: 'var(--text-dim)' }}>
      <p style={{ color: 'var(--text-faint)', fontStyle: 'italic' }}>Agent and tool output will appear here.</p>
    </div>
  )
}
