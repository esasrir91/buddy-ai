import React, { useEffect, useRef, useCallback } from 'react'
import { useStore } from './store'
import ActivityBar from './components/ActivityBar'
import Sidebar from './components/sidebar/Sidebar'
import EditorArea from './components/editor/EditorArea'
import AgentPane from './components/agent/AgentPane'
import BottomPanel from './components/panel/BottomPanel'
import StatusBar from './components/StatusBar'
import CommandPalette from './components/CommandPalette'
import { getWorkspace, getSettings, gitStatus } from './api'

export default function App() {
  const {
    theme,
    sidebarVisible, sidebarWidth, setSidebarWidth,
    agentPaneVisible, agentPaneWidth, setAgentPaneWidth,
    bottomPanelVisible, bottomPanelHeight, setBottomPanelHeight,
    setWorkspace, setWorkspaceTree, setGitInfo,
    setBottomPanelVisible,
  } = useStore()

  const [showPalette, setShowPalette] = React.useState(false)

  // apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  // load workspace on mount
  useEffect(() => {
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

  // global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      if (mod && e.key === 'p' && !e.shiftKey) { e.preventDefault(); setShowPalette(true) }
      if (e.key === 'Escape') setShowPalette(false)
      if (mod && e.key === '`') { e.preventDefault(); setBottomPanelVisible(true) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── resizable sidebar ────────────────────────────────────────────
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
    const onUp = () => { sidebarDragging.current = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [sidebarWidth, setSidebarWidth])

  // ── resizable agent pane ─────────────────────────────────────────
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
    const onUp = () => { agentDragging.current = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [agentPaneWidth, setAgentPaneWidth])

  // ── resizable bottom panel ───────────────────────────────────────
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
    const onUp = () => { btmDragging.current = false; window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [bottomPanelHeight, setBottomPanelHeight])

  return (
    <div className="aura-root">
      <div className="workbench">
        {/* Activity bar */}
        <ActivityBar onOpenPalette={() => setShowPalette(true)} />

        {/* Sidebar */}
        {sidebarVisible && (
          <>
            <Sidebar style={{ width: sidebarWidth }} />
            <div
              className="resize-handle resize-handle--vertical"
              onMouseDown={onSidebarDragStart}
            />
          </>
        )}

        {/* Editor + bottom panel (column) */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, overflow: 'hidden' }}>
          <EditorArea />
          {bottomPanelVisible && (
            <>
              <div className="resize-handle resize-handle--horizontal" onMouseDown={onBtmDragStart} />
              <BottomPanel style={{ height: bottomPanelHeight }} />
            </>
          )}
        </div>

        {/* Agent pane */}
        {agentPaneVisible && (
          <>
            <div className="resize-handle resize-handle--vertical" onMouseDown={onAgentDragStart} />
            <AgentPane style={{ width: agentPaneWidth }} />
          </>
        )}
      </div>

      <StatusBar />

      {showPalette && <CommandPalette onClose={() => setShowPalette(false)} />}
    </div>
  )
}
