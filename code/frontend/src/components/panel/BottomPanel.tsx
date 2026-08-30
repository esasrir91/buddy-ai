import React from 'react'
import { useStore } from '../../store'
import TerminalPanel from './TerminalPanel'
import ProblemsPanel from './ProblemsPanel'
import type { BottomTab } from '../../types'

interface Props {
  style?: React.CSSProperties
}

export default function BottomPanel({ style }: Props) {
  const {
    bottomTab, setBottomTab, setBottomPanelVisible,
    diagnostics, terminals, activeTerminalId,
    setActiveTerminal, addTerminal, removeTerminal,
    toggleBottomPanelMaximize, bottomPanelMaximized,
  } = useStore()

  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length
  const issueCount = errCount + warnCount

  const isTerminal =
    bottomTab === 'terminal' || bottomTab === 'agent' || bottomTab === 'output'

  const tabs: Array<{ id: BottomTab; label: string }> = [
    { id: 'problems', label: issueCount > 0 ? `PROBLEMS ${issueCount}` : 'PROBLEMS' },
    { id: 'terminal', label: 'TERMINAL' },
  ]

  const defaultShell = /Win/i.test(navigator.userAgent) ? 'powershell' : 'bash'

  return (
    <div className="bottom-panel" style={style}>
      <div className="panel-tabs">
        <div className="panel-tabs__views">
          {tabs.map(t => {
            const active =
              (t.id === 'problems' && bottomTab === 'problems') ||
              (t.id === 'terminal' && isTerminal)
            return (
              <button
                key={t.id}
                type="button"
                className={`panel-tab${active ? ' panel-tab--active' : ''}`}
                onClick={() => setBottomTab(t.id)}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        {isTerminal && (
          <div className="panel-tabs__terminals">
            <div className="term-tabs">
              {terminals.map(t => (
                <button
                  key={t.id}
                  type="button"
                  className={`term-tab${t.id === activeTerminalId ? ' term-tab--active' : ''}`}
                  onClick={() => setActiveTerminal(t.id)}
                  title={t.name}
                >
                  <TermGlyph />
                  <span className="term-tab__name">{t.name}</span>
                  <span
                    className="term-tab__kill"
                    title="Kill Terminal"
                    role="button"
                    onClick={e => {
                      e.stopPropagation()
                      removeTerminal(t.id)
                    }}
                  >
                    ×
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="panel-tabs__actions">
          {isTerminal && (
            <>
              <button
                type="button"
                className="panel-action"
                title="New Terminal (Ctrl+Shift+`)"
                onClick={() => addTerminal(defaultShell)}
              >
                <PlusIcon />
              </button>
              <button
                type="button"
                className="panel-action"
                title="Kill Terminal"
                onClick={() => activeTerminalId && removeTerminal(activeTerminalId)}
              >
                <TrashIcon />
              </button>
              <div className="panel-action-sep" />
            </>
          )}
          <button
            type="button"
            className="panel-action"
            title={bottomPanelMaximized ? 'Restore Panel Size' : 'Maximize Panel Size'}
            onClick={toggleBottomPanelMaximize}
          >
            {bottomPanelMaximized ? <RestoreIcon /> : <MaximizeIcon />}
          </button>
          <button
            type="button"
            className="panel-action"
            title="Close Panel"
            onClick={() => setBottomPanelVisible(false)}
          >
            <CloseIcon />
          </button>
        </div>
      </div>

      <div className="panel-body">
        {isTerminal && <TerminalPanel />}
        {bottomTab === 'problems' && <ProblemsPanel />}
      </div>
    </div>
  )
}

const ico = {
  width: 16, height: 16, viewBox: '0 0 16 16', fill: 'currentColor',
} as const

function TermGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M2 3.5h12a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-.5.5H2a.5.5 0 0 1-.5-.5V4a.5.5 0 0 1 .5-.5zm1 2.2 2.4 1.8L3 9.3l.7.7 3-2.3-3-2.3-.7.7zm4.5 3.8h4v1h-4v-1z" />
    </svg>
  )
}
function PlusIcon() {
  return (
    <svg {...ico}><path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" /></svg>
  )
}
function TrashIcon() {
  return (
    <svg {...ico}><path d="M4.5 3.5h7M6 3.5V2.5h4v1M5.5 5.5l.5 7h4l.5-7" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
  )
}
function MaximizeIcon() {
  return (
    <svg {...ico}><path d="M3 9.5V13h3.5M13 6.5V3H9.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
  )
}
function RestoreIcon() {
  return (
    <svg {...ico}><path d="M6.5 3H3v3.5M9.5 13H13V9.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
  )
}
function CloseIcon() {
  return (
    <svg {...ico}><path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
  )
}
