import React from 'react'
import { useStore } from '../store'
import { setWorkspace as apiSetWorkspace, getWorkspace } from '../api'
import { teamMeta } from '../teams'

export default function StatusBar() {
  const {
    gitBranch, gitDirtyCount, workspace,
    diagnostics, openTabs, activeTabId,
    chatMode, isStreaming, teamRole, orgName, userName,
    setSidebarView, setBottomTab, setBottomPanelVisible,
  } = useStore()

  const activeTab = openTabs.find(t => t.id === activeTabId)
  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length
  const team = teamMeta(teamRole)

  const wsName = workspace ? (workspace.split(/[\\/]/).filter(Boolean).pop() ?? workspace) : ''

  const openFolder = () => {
    const path = window.prompt('Open folder:', workspace || '')
    if (!path) return
    apiSetWorkspace(path)
      .then(() => getWorkspace())
      .then(({ path: resolved }) => useStore.getState().setWorkspace(resolved))
      .catch(e => alert(`Cannot open: ${e.message}`))
  }

  const openProblems = () => {
    setBottomPanelVisible(true)
    setBottomTab('problems')
  }

  return (
    <div className="status-bar">
      <div className="status-bar__left">
        {orgName && (
          <span className="status-item" onClick={() => setSidebarView('teams')} title="Organization">
            {orgName}
          </span>
        )}
        <span
          className="status-item"
          onClick={() => setSidebarView(teamRole === 'testing' ? 'testing' : 'teams')}
          title={team.description}
          style={{ background: 'rgba(0,0,0,.15)' }}
        >
          {team.short}
        </span>
        {gitBranch && (
          <span className="status-item" onClick={() => setSidebarView('git')} title="Source Control">
            <BranchIcon />
            {gitBranch}
            {gitDirtyCount > 0 && <span style={{ opacity: .75 }}>*{gitDirtyCount}</span>}
          </span>
        )}
        <span className="status-item" onClick={openFolder} title={workspace || 'Open folder'}>
          <FolderIcon />
          {wsName || 'Open Folder'}
        </span>
        <span
          className={`status-item${errCount > 0 ? ' status-item--err' : warnCount > 0 ? ' status-item--warn' : ' status-item--ok'}`}
          onClick={openProblems}
          title={`${errCount} errors, ${warnCount} warnings`}
        >
          {errCount > 0 && <><ErrIcon /> {errCount}</>}
          {warnCount > 0 && <><WarnIcon /> {warnCount}</>}
          {errCount === 0 && warnCount === 0 && <><OkIcon /> 0</>}
        </span>
      </div>

      <div className="status-bar__right">
        <span className="status-item" title="Agent mode">
          {isStreaming
            ? <><span className="spinner">⟳</span> Running</>
            : <>{chatMode.charAt(0).toUpperCase() + chatMode.slice(1)}</>
          }
        </span>
        {userName && (
          <span className="status-item" style={{ opacity: .8 }}>{userName}</span>
        )}
        {activeTab && (
          <span className="status-item" style={{ opacity: .75 }}>{activeTab.language}</span>
        )}
        <span className="status-item" style={{ opacity: .65, fontWeight: 600, fontSize: 11.5 }}>Aura</span>
      </div>
    </div>
  )
}

const s = { width: 12, height: 12, viewBox: '0 0 16 16', fill: 'currentColor' }

function BranchIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
      <circle cx="5" cy="4" r="2" /><circle cx="11" cy="4" r="2" /><circle cx="5" cy="12" r="2" />
      <path d="M5 6v4" /><path d="M11 6a4 4 0 01-4 4" />
    </svg>
  )
}
function FolderIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round">
      <path d="M2 5h5l1.5-2H14v9H2V5z" />
    </svg>
  )
}
function ErrIcon() {
  return (
    <svg {...s}><circle cx="8" cy="8" r="7" /><path d="M8 5v3M8 11v.5" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" /></svg>
  )
}
function WarnIcon() {
  return (
    <svg {...s}><path d="M8 2L1 14h14L8 2z" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" /><path d="M8 7v3M8 12v.5" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" /></svg>
  )
}
function OkIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 8l2 2L10.5 6" /></svg>
  )
}
