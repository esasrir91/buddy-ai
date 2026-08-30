import React, { useEffect, useState } from 'react'
import { useStore } from '../store'
import { setWorkspace as apiSetWorkspace, getWorkspace, getRecents } from '../api'
import MenuBar from './MenuBar'

interface Props {
  onOpenPalette?: (mode?: 'files' | 'commands') => void
}

export default function TitleBar({ onOpenPalette }: Props) {
  const { workspace, setWorkspace, orgName } = useStore()
  const [recents, setRecents] = useState<string[]>([])

  useEffect(() => {
    getRecents().then(r => setRecents(r.recent)).catch(() => {})
  }, [workspace])

  const wsName = workspace
    ? workspace.split(/[\\/]/).filter(Boolean).pop() ?? workspace
    : 'Aura'

  const centerLabel = orgName
    ? `${orgName}${workspace ? `  ·  ${wsName}` : ''}`
    : (workspace ? wsName : 'No folder open')

  const handleOpenFolder = () => {
    const path = window.prompt('Open folder:', workspace || '')
    if (!path) return
    apiSetWorkspace(path).then(() => getWorkspace()).then(({ path: resolved }) => {
      setWorkspace(resolved)
    }).catch(e => alert(`Cannot open: ${e.message}`))
  }

  return (
    <div className="titlebar">
      <div className="titlebar__left">
        <MenuBar onOpenPalette={onOpenPalette} />
      </div>

      <div className="titlebar__center">
        <span
          className="titlebar__workspace"
          title={workspace || orgName || 'Aura'}
          onClick={handleOpenFolder}
        >
          {centerLabel}
        </span>
      </div>

      <div className="titlebar__right">
        {recents.length > 0 && (
          <button
            className="titlebar__btn"
            title="Open recent folder"
            onClick={() => {
              const p = recents[0]
              if (!p) return
              apiSetWorkspace(p).then(() => getWorkspace()).then(({ path: resolved }) => {
                setWorkspace(resolved)
              }).catch(() => {})
            }}
          >
            <RecentIcon />
          </button>
        )}
        <button
          className="titlebar__btn"
          title="Command Palette (Ctrl+Shift+P)"
          onClick={() => onOpenPalette?.('commands')}
        >
          <CommandIcon />
        </button>
        <button
          className="titlebar__btn"
          title="Go to File (Ctrl+P)"
          onClick={() => onOpenPalette?.('files')}
        >
          <SearchIcon />
        </button>
      </div>
    </div>
  )
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
      <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M10 10L13.5 13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function CommandIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M3 5h10M3 8h7M3 11h10" />
    </svg>
  )
}

function RecentIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 5v3.5L10.5 10" />
    </svg>
  )
}
