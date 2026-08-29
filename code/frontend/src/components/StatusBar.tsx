import React from 'react'
import { useStore } from '../store'

export default function StatusBar() {
  const {
    gitBranch, gitDirtyCount, workspace,
    diagnostics, openTabs, activeTabId,
    chatMode, isStreaming,
    setSidebarView, setBottomTab,
  } = useStore()

  const activeTab = openTabs.find(t => t.id === activeTabId)
  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length

  const wsName = workspace.split(/[\\/]/).pop() ?? ''

  return (
    <div className="status-bar">
      <div className="status-bar__left">
        {/* Branch */}
        {gitBranch && (
          <span className="status-item" onClick={() => setSidebarView('git')} title="Source control">
            ⎇ {gitBranch}{gitDirtyCount > 0 ? ` (${gitDirtyCount})` : ''}
          </span>
        )}

        {/* Workspace */}
        {wsName && (
          <span className="status-item" style={{ color: 'rgba(255,255,255,.8)', fontSize: 11 }}
            onClick={() => setSidebarView('explorer')}>
            {wsName}
          </span>
        )}

        {/* Problems */}
        <span
          className={`status-item${errCount > 0 ? ' status-item--err' : warnCount > 0 ? ' status-item--warn' : ''}`}
          onClick={() => setBottomTab('problems')}
          title="Problems"
          style={{ color: errCount > 0 ? 'var(--err)' : warnCount > 0 ? 'var(--warn)' : undefined }}
        >
          {errCount > 0 && `● ${errCount}`}
          {warnCount > 0 && ` ▲ ${warnCount}`}
          {errCount === 0 && warnCount === 0 && '✓'}
        </span>
      </div>

      <div className="status-bar__right">
        {/* Agent mode */}
        <span className="status-item" style={{ background: 'rgba(0,0,0,.2)', borderRadius: 4, padding: '0 6px' }}>
          {isStreaming ? '⟳ ' : ''}
          {chatMode.toUpperCase()}
        </span>

        {/* Active file info */}
        {activeTab && (
          <>
            <span className="status-item" style={{ color: 'rgba(255,255,255,.8)' }}>
              {activeTab.language}
            </span>
            <span className="status-item" style={{ color: 'rgba(255,255,255,.6)', fontSize: 11 }}>
              {activeTab.name}
            </span>
          </>
        )}

        {/* Aura branding */}
        <span style={{ marginLeft: 8, opacity: .7, fontSize: 11.5, fontWeight: 600 }}>Aura</span>
      </div>
    </div>
  )
}
