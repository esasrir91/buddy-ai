import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useStore } from '../store'
import {
  setWorkspace as apiSetWorkspace,
  getWorkspace,
  getRecents,
  fsWrite,
  saveProfile,
} from '../api'
import { ORG_TEAMS } from '../teams'
import type { TeamRole } from '../types'

interface Props {
  onOpenPalette?: (mode?: 'files' | 'commands') => void
}

type MenuKey = 'file' | 'edit' | 'selection' | 'view' | 'go' | 'run' | 'terminal' | 'help'

interface MenuEntry {
  type?: 'item' | 'sep' | 'label'
  label?: string
  kbd?: string
  disabled?: boolean
  action?: () => void
  submenu?: MenuEntry[]
}

export default function MenuBar({ onOpenPalette }: Props) {
  const store = useStore()
  const {
    workspace, setWorkspace, openTabs, activeTabId, closeTab, markTabDirty,
    setSidebarView, setSidebarVisible, sidebarVisible,
    setAgentPaneVisible, agentPaneVisible,
    setBottomPanelVisible, bottomPanelVisible, setBottomTab,
    setTheme, theme, setChatMode, chatMode, teamRole, setTeamRole,
    resetOnboarding, orgName,
  } = store

  const [open, setOpen] = useState<MenuKey | null>(null)
  const [recents, setRecents] = useState<string[]>([])
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getRecents().then(r => setRecents(r.recent)).catch(() => {})
  }, [workspace])

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(null)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(null) }
    document.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const close = () => setOpen(null)

  const openFolder = useCallback(() => {
    close()
    const path = window.prompt('Open folder:', workspace || '')
    if (!path) return
    apiSetWorkspace(path)
      .then(() => getWorkspace())
      .then(({ path: resolved }) => setWorkspace(resolved))
      .catch(e => alert(`Cannot open: ${e.message}`))
  }, [workspace, setWorkspace])

  const openRecent = (path: string) => {
    close()
    apiSetWorkspace(path)
      .then(() => getWorkspace())
      .then(({ path: resolved }) => setWorkspace(resolved))
      .catch(() => {})
  }

  const saveActive = async () => {
    close()
    const tab = openTabs.find(t => t.id === activeTabId)
    if (!tab) return
    try {
      await fsWrite(tab.path, tab.content)
      markTabDirty(tab.id, false)
    } catch (e: any) {
      alert(`Save failed: ${e.message}`)
    }
  }

  const saveAll = async () => {
    close()
    for (const tab of openTabs.filter(t => t.dirty)) {
      try {
        await fsWrite(tab.path, tab.content)
        markTabDirty(tab.id, false)
      } catch { /* continue */ }
    }
  }

  const copyPath = async () => {
    close()
    const tab = openTabs.find(t => t.id === activeTabId)
    const text = tab?.path || workspace
    if (!text) return
    try { await navigator.clipboard.writeText(text) } catch { /* ignore */ }
  }

  const switchTeam = (role: TeamRole) => {
    close()
    setTeamRole(role)
    import('../api').then(({ updateSettings }) => updateSettings({ team_role: role }).catch(() => {}))
    setSidebarView(role === 'testing' ? 'testing' : 'teams')
  }

  const menus: Record<MenuKey, { title: string; items: MenuEntry[] }> = {
    file: {
      title: 'File',
      items: [
        { label: 'New Text File', kbd: 'Ctrl+N', action: () => { close(); store.openTab('untitled.txt', '') } },
        { type: 'sep' },
        { label: 'Open Folder…', kbd: 'Ctrl+O', action: openFolder },
        {
          label: 'Open Recent',
          submenu: recents.length
            ? recents.slice(0, 10).map(p => ({
                label: p.split(/[\\/]/).filter(Boolean).pop() ?? p,
                action: () => openRecent(p),
              }))
            : [{ label: 'No recent folders', disabled: true }],
        },
        { type: 'sep' },
        { label: 'Save', kbd: 'Ctrl+S', disabled: !activeTabId, action: saveActive },
        { label: 'Save All', kbd: 'Ctrl+K S', disabled: !openTabs.some(t => t.dirty), action: saveAll },
        { type: 'sep' },
        { label: 'Close Editor', kbd: 'Ctrl+W', disabled: !activeTabId, action: () => { close(); if (activeTabId) closeTab(activeTabId) } },
        { label: 'Close All Editors', disabled: openTabs.length === 0, action: () => { close(); openTabs.forEach(t => closeTab(t.id)) } },
        { type: 'sep' },
        { label: 'Copy Path of Active File', disabled: !activeTabId, action: copyPath },
        { type: 'sep' },
        {
          label: 'Change Org / Team Setup…',
          action: async () => {
            close()
            if (!window.confirm('Re-run org setup?')) return
            try { await saveProfile({ onboarding_complete: false }) } catch { /* ignore */ }
            resetOnboarding()
          },
        },
        { type: 'sep' },
        { label: 'Exit', kbd: 'Alt+F4', action: () => { close(); window.close() } },
      ],
    },
    edit: {
      title: 'Edit',
      items: [
        { label: 'Undo', kbd: 'Ctrl+Z', action: () => { close(); document.execCommand('undo') } },
        { label: 'Redo', kbd: 'Ctrl+Y', action: () => { close(); document.execCommand('redo') } },
        { type: 'sep' },
        { label: 'Cut', kbd: 'Ctrl+X', action: () => { close(); document.execCommand('cut') } },
        { label: 'Copy', kbd: 'Ctrl+C', action: () => { close(); document.execCommand('copy') } },
        { label: 'Paste', kbd: 'Ctrl+V', action: () => { close(); document.execCommand('paste') } },
        { type: 'sep' },
        { label: 'Find in Files…', kbd: 'Ctrl+Shift+F', action: () => { close(); setSidebarView('search') } },
        { label: 'Replace in Files…', action: () => { close(); setSidebarView('search') } },
        { type: 'sep' },
        { label: 'Command Palette…', kbd: 'Ctrl+Shift+P', action: () => { close(); onOpenPalette?.('commands') } },
      ],
    },
    selection: {
      title: 'Selection',
      items: [
        { label: 'Select All', kbd: 'Ctrl+A', action: () => { close(); document.execCommand('selectAll') } },
        { type: 'sep' },
        { label: 'Expand Selection', kbd: 'Shift+Alt+→', disabled: true },
        { label: 'Shrink Selection', kbd: 'Shift+Alt+←', disabled: true },
        { type: 'sep' },
        { label: 'Copy Line Up', kbd: 'Shift+Alt+↑', disabled: true },
        { label: 'Copy Line Down', kbd: 'Shift+Alt+↓', disabled: true },
        { label: 'Move Line Up', kbd: 'Alt+↑', disabled: true },
        { label: 'Move Line Down', kbd: 'Alt+↓', disabled: true },
      ],
    },
    view: {
      title: 'View',
      items: [
        { label: 'Command Palette…', kbd: 'Ctrl+Shift+P', action: () => { close(); onOpenPalette?.('commands') } },
        { label: 'Go to File…', kbd: 'Ctrl+P', action: () => { close(); onOpenPalette?.('files') } },
        { type: 'sep' },
        { label: 'Explorer', kbd: 'Ctrl+Shift+E', action: () => { close(); setSidebarVisible(true); setSidebarView('explorer') } },
        { label: 'Search', kbd: 'Ctrl+Shift+F', action: () => { close(); setSidebarVisible(true); setSidebarView('search') } },
        { label: 'Source Control', kbd: 'Ctrl+Shift+G', action: () => { close(); setSidebarVisible(true); setSidebarView('git') } },
        { label: 'Org Teams', action: () => { close(); setSidebarVisible(true); setSidebarView('teams') } },
        { label: 'Testing Hub', action: () => { close(); setSidebarVisible(true); setSidebarView('testing') } },
        { label: 'MCP Servers', action: () => { close(); setSidebarVisible(true); setSidebarView('mcp') } },
        { label: 'Settings', kbd: 'Ctrl+,', action: () => { close(); setSidebarVisible(true); setSidebarView('settings') } },
        { type: 'sep' },
        { label: sidebarVisible ? 'Hide Primary Side Bar' : 'Show Primary Side Bar', kbd: 'Ctrl+B', action: () => { close(); setSidebarVisible(!sidebarVisible) } },
        { label: agentPaneVisible ? 'Hide Aura Agent' : 'Show Aura Agent', kbd: 'Ctrl+L', action: () => { close(); setAgentPaneVisible(!agentPaneVisible) } },
        { label: bottomPanelVisible ? 'Hide Panel' : 'Show Panel', kbd: 'Ctrl+J', action: () => { close(); setBottomPanelVisible(!bottomPanelVisible) } },
        { type: 'sep' },
        { label: theme === 'dark' ? 'Color Theme: Light' : 'Color Theme: Dark', action: () => { close(); setTheme(theme === 'dark' ? 'light' : 'dark') } },
        { type: 'sep' },
        { label: 'Appearance', type: 'label' },
        { label: 'Zoom In', kbd: 'Ctrl+=', action: () => { close(); document.body.style.zoom = String(Math.min(1.4, (Number(document.body.style.zoom) || 1) + 0.1)) } },
        { label: 'Zoom Out', kbd: 'Ctrl+-', action: () => { close(); document.body.style.zoom = String(Math.max(0.7, (Number(document.body.style.zoom) || 1) - 0.1)) } },
        { label: 'Reset Zoom', kbd: 'Ctrl+0', action: () => { close(); document.body.style.zoom = '1' } },
      ],
    },
    go: {
      title: 'Go',
      items: [
        { label: 'Go to File…', kbd: 'Ctrl+P', action: () => { close(); onOpenPalette?.('files') } },
        { label: 'Go to Symbol in Workspace…', kbd: 'Ctrl+T', action: () => { close(); onOpenPalette?.('files') } },
        { type: 'sep' },
        { label: 'Back', kbd: 'Alt+←', disabled: true },
        { label: 'Forward', kbd: 'Alt+→', disabled: true },
        { type: 'sep' },
        ...openTabs.slice(0, 8).map((t, i) => ({
          label: t.name + (t.dirty ? ' •' : ''),
          kbd: i < 9 ? `Ctrl+${i + 1}` : undefined,
          action: () => { close(); store.setActiveTab(t.id) },
        })),
      ],
    },
    run: {
      title: 'Run',
      items: [
        { label: 'Focus Aura Agent', kbd: 'Ctrl+L', action: () => { close(); setAgentPaneVisible(true) } },
        { type: 'sep' },
        { label: 'Agent Mode', kbd: chatMode === 'agent' ? '✓' : undefined, action: () => { close(); setChatMode('agent'); setAgentPaneVisible(true) } },
        { label: 'Plan Mode', kbd: chatMode === 'plan' ? '✓' : undefined, action: () => { close(); setChatMode('plan'); setAgentPaneVisible(true) } },
        { label: 'Ask Mode', kbd: chatMode === 'ask' ? '✓' : undefined, action: () => { close(); setChatMode('ask'); setAgentPaneVisible(true) } },
        { type: 'sep' },
        { label: 'Active Team', type: 'label' },
        ...ORG_TEAMS.map(t => ({
          label: `${t.label}${teamRole === t.id ? '  ✓' : ''}`,
          action: () => switchTeam(t.id),
        })),
        { type: 'sep' },
        { label: 'Open Testing Hub', action: () => { close(); setSidebarVisible(true); setSidebarView('testing'); setTeamRole('testing') } },
      ],
    },
    terminal: {
      title: 'Terminal',
      items: [
        { label: 'New Terminal', kbd: 'Ctrl+Shift+`', action: () => { close(); useStore.getState().addTerminal(/Win/i.test(navigator.userAgent) ? 'powershell' : 'bash') } },
        { label: 'Toggle Terminal', kbd: 'Ctrl+`', action: () => { close(); setBottomPanelVisible(!bottomPanelVisible); setBottomTab('terminal') } },
        { type: 'sep' },
        { label: 'Problems', action: () => { close(); setBottomPanelVisible(true); setBottomTab('problems') } },
      ],
    },
    help: {
      title: 'Help',
      items: [
        { label: 'Command Palette…', kbd: 'Ctrl+Shift+P', action: () => { close(); onOpenPalette?.('commands') } },
        { label: 'Keyboard Shortcuts Reference', action: () => {
          close()
          alert(
            'Aura shortcuts\n\n' +
            'Ctrl+P          Go to File\n' +
            'Ctrl+Shift+P    Command Palette\n' +
            'Ctrl+O          Open Folder\n' +
            'Ctrl+S          Save\n' +
            'Ctrl+B          Toggle Sidebar\n' +
            'Ctrl+J          Toggle Panel\n' +
            'Ctrl+L          Aura Agent\n' +
            'Ctrl+`          Terminal\n' +
            'Ctrl+K          Inline Edit (editor)\n'
          )
        } },
        { type: 'sep' },
        { label: 'Documentation', action: () => { close(); window.open('http://127.0.0.1:8600/api/docs', '_blank') } },
        { type: 'sep' },
        { label: `Organization: ${orgName || '—'}`, disabled: true },
        { label: 'About Aura', action: () => {
          close()
          alert('Aura — AI Coding IDE\nOrg-wide teammate for Testing, Engineering, Platform, Hardware, and more.\n\nBuddy agent framework')
        } },
      ],
    },
  }

  const order: MenuKey[] = ['file', 'edit', 'selection', 'view', 'go', 'run', 'terminal', 'help']

  return (
    <div className="menubar" ref={rootRef} role="menubar">
      {order.map(key => {
        const m = menus[key]
        const isOpen = open === key
        return (
          <div
            key={key}
            className={`menubar__item${isOpen ? ' menubar__item--open' : ''}`}
            onMouseEnter={() => { if (open) setOpen(key) }}
          >
            <button
              type="button"
              className={`menubar__btn${isOpen ? ' menubar__btn--open' : ''}`}
              role="menuitem"
              aria-haspopup="true"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : key)}
            >
              {m.title}
            </button>
            {isOpen && (
              <div className="menubar__dropdown" role="menu">
                {m.items.map((item, i) => (
                  <MenuRow key={`${key}-${i}`} item={item} />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function MenuRow({ item }: { item: MenuEntry }) {
  const [subOpen, setSubOpen] = useState(false)

  if (item.type === 'sep') return <div className="menubar__sep" role="separator" />
  if (item.type === 'label') {
    return <div className="menubar__label">{item.label}</div>
  }

  if (item.submenu) {
    return (
      <div
        className={`menubar__row menubar__row--sub${item.disabled ? ' menubar__row--disabled' : ''}`}
        onMouseEnter={() => setSubOpen(true)}
        onMouseLeave={() => setSubOpen(false)}
      >
        <span className="menubar__row-label">{item.label}</span>
        <span className="menubar__row-kbd">›</span>
        {subOpen && (
          <div className="menubar__submenu" role="menu">
            {item.submenu.map((s, i) => (
              <MenuRow key={i} item={s} />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <button
      type="button"
      className={`menubar__row${item.disabled ? ' menubar__row--disabled' : ''}`}
      disabled={item.disabled}
      role="menuitem"
      onClick={() => item.action?.()}
    >
      <span className="menubar__row-label">{item.label}</span>
      {item.kbd && <span className="menubar__row-kbd">{item.kbd}</span>}
    </button>
  )
}
