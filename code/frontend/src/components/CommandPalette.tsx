import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useStore } from '../store'
import { fsList, fsRead } from '../api'

interface PaletteItem {
  id: string
  label: string
  detail?: string
  icon?: string
  kbd?: string
  action: () => void
}

interface Props {
  onClose: () => void
  mode?: 'files' | 'commands'
}

export default function CommandPalette({ onClose, mode = 'files' }: Props) {
  const {
    openTabs, workspaceTree,
    openTab, setActiveTab, closeTab,
    setSidebarView,
    setBottomPanelVisible, setBottomTab,
    setAgentPaneVisible, agentPaneVisible,
    setSidebarVisible, sidebarVisible,
    setChatMode,
  } = useStore()

  const [query, setQuery] = useState(mode === 'commands' ? '>' : '')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    if (mode === 'commands') {
      // Place caret after ">"
      requestAnimationFrame(() => {
        const el = inputRef.current
        if (el) el.setSelectionRange(el.value.length, el.value.length)
      })
    }
  }, [mode])
  const openFile = useCallback(async (path: string) => {
    const existing = openTabs.find(t => t.path === path)
    if (existing) { setActiveTab(existing.id); onClose(); return }
    try {
      const { content } = await fsRead(path)
      openTab(path, content)
    } catch { openTab(path, '') }
    onClose()
  }, [openTabs, openTab, setActiveTab, onClose])

  // Flatten tree to file paths
  const allFiles = React.useMemo(() => {
    const collect = (nodes: any[], out: string[] = []) => {
      for (const n of nodes) {
        if (n.type === 'file') out.push(n.path)
        if (n.children) collect(n.children, out)
      }
      return out
    }
    return collect(workspaceTree)
  }, [workspaceTree])

  const commands: PaletteItem[] = [
    { id: 'explorer', icon: '📁', label: 'Show Explorer', action: () => { setSidebarView('explorer'); onClose() } },
    { id: 'search', icon: '🔍', label: 'Show Search', action: () => { setSidebarView('search'); onClose() } },
    { id: 'git', icon: '⎇', label: 'Show Source Control', action: () => { setSidebarView('git'); onClose() } },
    { id: 'mcp', icon: '🔌', label: 'Show MCP Servers', action: () => { setSidebarView('mcp'); onClose() } },
    { id: 'settings', icon: '⚙️', label: 'Show Settings', action: () => { setSidebarView('settings'); onClose() } },
    { id: 'terminal', icon: '▶', label: 'Open Terminal', kbd: 'Ctrl+`', action: () => { setBottomTab('terminal'); onClose() } },
    { id: 'problems', icon: '●', label: 'Show Problems', action: () => { setBottomTab('problems'); onClose() } },
    { id: 'agent', icon: '🤖', label: agentPaneVisible ? 'Hide Agent Pane' : 'Show Agent Pane', action: () => { setAgentPaneVisible(!agentPaneVisible); onClose() } },
    { id: 'sidebar', icon: '◧', label: sidebarVisible ? 'Hide Sidebar' : 'Show Sidebar', action: () => { setSidebarVisible(!sidebarVisible); onClose() } },
    { id: 'mode-agent', icon: '⚡', label: 'Switch to Agent mode', action: () => { setChatMode('agent'); onClose() } },
    { id: 'mode-plan', icon: '📋', label: 'Switch to Plan mode', action: () => { setChatMode('plan'); onClose() } },
    { id: 'mode-ask', icon: '❓', label: 'Switch to Ask mode', action: () => { setChatMode('ask'); onClose() } },
    ...openTabs.map(tab => ({
      id: `tab-${tab.id}`,
      icon: '📄',
      label: tab.name,
      detail: tab.path,
      action: () => { setActiveTab(tab.id); onClose() },
    })),
  ]

  const fileItems: PaletteItem[] = allFiles.map(path => ({
    id: `file-${path}`,
    icon: '📄',
    label: path.split(/[\\/]/).pop() ?? path,
    detail: path,
    action: () => openFile(path),
  }))

  const q = query.startsWith('>') ? query.slice(1).toLowerCase() : query.toLowerCase()
  const isCmd = query.startsWith('>')

  const items = isCmd
    ? commands.filter(c => c.label.toLowerCase().includes(q))
    : fileItems.filter(f => f.label.toLowerCase().includes(q) || (f.detail ?? '').toLowerCase().includes(q)).slice(0, 50)

  useEffect(() => { setSelected(0) }, [query])

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, items.length - 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)) }
    if (e.key === 'Enter') { e.preventDefault(); items[selected]?.action() }
    if (e.key === 'Escape') { e.preventDefault(); onClose() }
  }

  return (
    <div className="palette-overlay" onClick={onClose}>
      <div className="palette" onClick={e => e.stopPropagation()}>
        <div className="palette__input-row">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.099zm-5.44 1.406a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11z"/>
          </svg>
          <input
            ref={inputRef}
            className="palette__input"
            placeholder="Search files or type > for commands…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKey}
          />
        </div>
        <div className="palette__list">
          {items.length === 0 && (
            <div className="palette__empty">No results for "{q}"</div>
          )}
          {items.map((item, i) => (
            <div
              key={item.id}
              className={`palette__item${i === selected ? ' palette__item--selected' : ''}`}
              onClick={item.action}
              onMouseEnter={() => setSelected(i)}
            >
              <span className="palette__item-icon">{item.icon}</span>
              <span className="palette__item-label">{item.label}</span>
              {item.detail && <span className="palette__item-kbd" style={{ color: 'var(--text-faint)', fontSize: 11 }}>{item.detail}</span>}
              {item.kbd && <span className="palette__item-kbd"><kbd>{item.kbd}</kbd></span>}
            </div>
          ))}
        </div>
        <div className="palette__hint">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span>Esc close</span>
          <span>&gt; for commands</span>
        </div>
      </div>
    </div>
  )
}
