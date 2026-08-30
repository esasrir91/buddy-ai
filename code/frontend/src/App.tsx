import React, { useEffect, useRef, useCallback } from 'react'
import { useStore } from './store'
import TitleBar from './components/TitleBar'
import ActivityBar from './components/ActivityBar'
import Sidebar from './components/sidebar/Sidebar'
import EditorArea from './components/editor/EditorArea'
import AgentPane from './components/agent/AgentPane'
import BottomPanel from './components/panel/BottomPanel'
import StatusBar from './components/StatusBar'
import CommandPalette from './components/CommandPalette'
import Onboarding from './components/Onboarding'
import AuraLogo from './components/AuraLogo'
import { getWorkspace, getProfile, gitStatus } from './api'
import type { TeamRole } from './types'

export default function App() {
  const {
    theme,
    sidebarVisible, sidebarWidth, setSidebarWidth,
    agentPaneVisible, agentPaneWidth, setAgentPaneWidth,
    bottomPanelVisible, bottomPanelHeight, setBottomPanelHeight,
    setWorkspace, setGitInfo, setBottomPanelVisible,
    onboardingComplete, setOrgProfile, setTeamRole,
  } = useStore()

  const [showPalette, setShowPalette] = React.useState(false)
  const [paletteMode, setPaletteMode] = React.useState<'files' | 'commands'>('files')

  const openPalette = useCallback((mode: 'files' | 'commands' = 'files') => {
    setPaletteMode(mode)
    setShowPalette(true)
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  // Load profile first — gates onboarding vs workbench
  useEffect(() => {
    getProfile()
      .then((p) => {
        const role = (p.team_role || 'testing') as TeamRole
        setTeamRole(role)
        setOrgProfile({
          orgName: p.org_name || '',
          userName: p.user_name || '',
          userTitle: p.user_title || '',
          focusAreas: p.focus_areas || [],
          teamRole: role,
          onboardingComplete: !!p.onboarding_complete,
        })
      })
      .catch(() => {
        setOrgProfile({ onboardingComplete: false })
      })

    getWorkspace()
      .then(({ path }) => setWorkspace(path))
      .catch(() => {})
    gitStatus()
      .then((s) => {
        const dirty = (s.files ?? []).filter((f: any) => !f.staged).length
        setGitInfo(s.branch ?? '', dirty)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!onboardingComplete) return
    const handler = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      const key = e.key.toLowerCase()
      if (mod && e.shiftKey && key === 'p') { e.preventDefault(); openPalette('commands'); return }
      if (mod && key === 'p' && !e.shiftKey) { e.preventDefault(); openPalette('files'); return }
      if (mod && key === 'o') {
        e.preventDefault()
        const path = window.prompt('Open folder:', useStore.getState().workspace || '')
        if (!path) return
        import('./api').then(({ setWorkspace: apiSet, getWorkspace }) => {
          apiSet(path).then(() => getWorkspace()).then(({ path: resolved }) => {
            useStore.getState().setWorkspace(resolved)
          }).catch((err: any) => alert(`Cannot open: ${err.message}`))
        })
        return
      }
      if (mod && key === 's') {
        e.preventDefault()
        const st = useStore.getState()
        const tab = st.openTabs.find(t => t.id === st.activeTabId)
        if (!tab) return
        import('./api').then(({ fsWrite }) => {
          fsWrite(tab.path, tab.content)
            .then(() => st.markTabDirty(tab.id, false))
            .catch((err: any) => alert(`Save failed: ${err.message}`))
        })
        return
      }
      if (mod && key === 'b') { e.preventDefault(); useStore.getState().setSidebarVisible(!useStore.getState().sidebarVisible); return }
      if (mod && key === 'j') { e.preventDefault(); useStore.getState().setBottomPanelVisible(!useStore.getState().bottomPanelVisible); return }
      if (mod && key === 'l') { e.preventDefault(); useStore.getState().setAgentPaneVisible(true); return }
      if (mod && key === ',') { e.preventDefault(); useStore.getState().setSidebarVisible(true); useStore.getState().setSidebarView('settings'); return }
      if (mod && e.shiftKey && key === '`') {
        e.preventDefault()
        const shell = /Win/i.test(navigator.userAgent) ? 'powershell' : 'bash'
        useStore.getState().addTerminal(shell)
        return
      }
      if (mod && key === '`') { e.preventDefault(); setBottomPanelVisible(true); useStore.getState().setBottomTab('terminal'); return }
      if (e.key === 'Escape') setShowPalette(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onboardingComplete, openPalette, setBottomPanelVisible])

  const sidebarDragging = useRef(false)
  const sidebarStartX = useRef(0)
  const sidebarStartW = useRef(0)

  const onSidebarDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    sidebarDragging.current = true
    sidebarStartX.current = e.clientX
    sidebarStartW.current = sidebarWidth
    const onMove = (e: MouseEvent) => {
      if (!sidebarDragging.current) return
      setSidebarWidth(sidebarStartW.current + e.clientX - sidebarStartX.current)
    }
    const onUp = () => {
      sidebarDragging.current = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [sidebarWidth, setSidebarWidth])

  const agentDragging = useRef(false)
  const agentStartX = useRef(0)
  const agentStartW = useRef(0)

  const onAgentDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    agentDragging.current = true
    agentStartX.current = e.clientX
    agentStartW.current = agentPaneWidth
    const onMove = (e: MouseEvent) => {
      if (!agentDragging.current) return
      setAgentPaneWidth(agentStartW.current - (e.clientX - agentStartX.current))
    }
    const onUp = () => {
      agentDragging.current = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [agentPaneWidth, setAgentPaneWidth])

  const btmDragging = useRef(false)
  const btmStartY = useRef(0)
  const btmStartH = useRef(0)

  const onBtmDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    btmDragging.current = true
    btmStartY.current = e.clientY
    btmStartH.current = bottomPanelHeight
    const onMove = (e: MouseEvent) => {
      if (!btmDragging.current) return
      setBottomPanelHeight(btmStartH.current - (e.clientY - btmStartY.current))
    }
    const onUp = () => {
      btmDragging.current = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [bottomPanelHeight, setBottomPanelHeight])

  // Boot splash while profile loads
  if (onboardingComplete === null) {
    return (
      <div className="onboard onboard--in" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="onboard__aurora" />
        <div style={{ position: 'relative', zIndex: 2, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <AuraLogo size={56} />
          <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-.4px' }}>Aura</div>
          <div style={{ color: '#64748b', fontSize: 13 }}>Preparing your workspace…</div>
        </div>
      </div>
    )
  }

  if (!onboardingComplete) {
    return <Onboarding />
  }

  return (
    <div className="aura-root">
      <TitleBar onOpenPalette={openPalette} />

      <div className="workbench">
        <ActivityBar onOpenPalette={() => openPalette('files')} />

        {sidebarVisible && (
          <>
            <Sidebar style={{ width: sidebarWidth }} />
            <div
              className="resize-handle resize-handle--vertical"
              onMouseDown={onSidebarDragStart}
            />
          </>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, overflow: 'hidden' }}>
          <EditorArea />
          {bottomPanelVisible && (
            <>
              <div className="resize-handle resize-handle--horizontal" onMouseDown={onBtmDragStart} />
              <BottomPanel style={{ height: bottomPanelHeight }} />
            </>
          )}
        </div>

        {agentPaneVisible && (
          <>
            <div className="resize-handle resize-handle--vertical" onMouseDown={onAgentDragStart} />
            <AgentPane style={{ width: agentPaneWidth }} />
          </>
        )}
      </div>

      <StatusBar />

      {showPalette && (
        <CommandPalette
          mode={paletteMode}
          onClose={() => setShowPalette(false)}
        />
      )}
    </div>
  )
}
