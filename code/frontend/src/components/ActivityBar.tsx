import React from 'react'
import { useStore } from '../store'
import type { SidebarView } from '../types'
import AuraLogo from './AuraLogo'

interface ActivityBtnProps {
  icon: React.ReactNode
  label: string
  view?: SidebarView
  active?: boolean
  badge?: number
  onClick?: () => void
}

function ActivityBtn({ icon, label, view, active, badge, onClick }: ActivityBtnProps) {
  const { setSidebarView } = useStore()
  return (
    <button
      className={`activity-btn${active ? ' activity-btn--active' : ''}`}
      title={label}
      onClick={onClick ?? (view ? () => setSidebarView(view) : undefined)}
    >
      {icon}
      {badge != null && badge > 0 && <span className="badge">{badge > 99 ? '99+' : badge}</span>}
    </button>
  )
}

interface Props {
  onOpenPalette?: () => void
}

export default function ActivityBar({ onOpenPalette }: Props) {
  const {
    sidebarView, sidebarVisible, theme, setTheme,
    agentPaneVisible, setAgentPaneVisible,
    diagnostics,
  } = useStore()

  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length

  return (
    <div className="activity-bar">
      <div className="activity-bar__top">
        <div style={{ marginBottom: 6, marginTop: 2 }} title="Aura">
          <AuraLogo size={28} />
        </div>

        {/* Explorer */}
        <ActivityBtn
          icon={<ExplorerIcon />}
          label="Explorer"
          view="explorer"
          active={sidebarVisible && sidebarView === 'explorer'}
        />

        {/* Search */}
        <ActivityBtn
          icon={<SearchIcon />}
          label="Search"
          view="search"
          active={sidebarVisible && sidebarView === 'search'}
        />

        {/* Source Control */}
        <ActivityBtn
          icon={<GitIcon />}
          label="Source Control"
          view="git"
          active={sidebarVisible && sidebarView === 'git'}
        />

        <div className="activity-sep" />

        {/* Org Teams */}
        <ActivityBtn
          icon={<TeamsIcon />}
          label="Org Teams"
          view="teams"
          active={sidebarVisible && sidebarView === 'teams'}
        />

        {/* Testing Hub */}
        <ActivityBtn
          icon={<TestIcon />}
          label="Testing Hub"
          view="testing"
          active={sidebarVisible && sidebarView === 'testing'}
        />

        {/* MCP Servers */}
        <ActivityBtn
          icon={<McpIcon />}
          label="MCP Servers"
          view="mcp"
          active={sidebarVisible && sidebarView === 'mcp'}
        />

        {/* Aura Agent (Composer) */}
        <ActivityBtn
          icon={<AgentIcon />}
          label="Aura Agent"
          active={agentPaneVisible}
          onClick={() => setAgentPaneVisible(!agentPaneVisible)}
        />
      </div>

      <div className="activity-bar__bottom">
        {/* Problems badge */}
        <ActivityBtn
          icon={<ProblemsIcon />}
          label="Problems"
          view="explorer"
          badge={errCount + warnCount}
          onClick={() => useStore.getState().setBottomTab('problems')}
        />

        {/* Settings */}
        <ActivityBtn
          icon={<SettingsIcon />}
          label="Settings"
          view="settings"
          active={sidebarVisible && sidebarView === 'settings'}
        />

        {/* Theme toggle */}
        <ActivityBtn
          icon={theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          label={theme === 'dark' ? 'Light theme' : 'Dark theme'}
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        />
      </div>
    </div>
  )
}

/* ── SVG Icons ──────────────────────────────────────────────────────────── */

const iconProps = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

function ExplorerIcon() {
  return (
    <svg {...iconProps}>
      <path d="M3 3h18v4H3z" />
      <path d="M3 7v14h18V7" />
      <path d="M8 11h8M8 15h5" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="11" cy="11" r="7" />
      <line x1="16.5" y1="16.5" x2="21" y2="21" />
    </svg>
  )
}

function GitIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="6" cy="6" r="2" />
      <circle cx="18" cy="6" r="2" />
      <circle cx="6" cy="18" r="2" />
      <path d="M6 8v8" />
      <path d="M18 8v2a4 4 0 01-4 4H6" />
    </svg>
  )
}

function McpIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="2" />
      <circle cx="4" cy="6" r="2" />
      <circle cx="20" cy="6" r="2" />
      <circle cx="4" cy="18" r="2" />
      <circle cx="20" cy="18" r="2" />
      <path d="M6 6l4 5M18 6l-4 5M6 18l4-5M18 18l-4-5" />
    </svg>
  )
}

function TeamsIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="9" cy="8" r="3" />
      <circle cx="16" cy="9" r="2.5" />
      <path d="M3 19c0-3 2.5-5 6-5s6 2 6 5" />
      <path d="M14 19c.3-1.8 1.5-3 3.5-3 2 0 3.5 1 3.5 3" />
    </svg>
  )
}

function TestIcon() {
  return (
    <svg {...iconProps}>
      <path d="M9 3h6" />
      <path d="M10 3v5l-4 8a3 3 0 002.6 4.5h6.8A3 3 0 0018 16l-4-8V3" />
      <path d="M9.5 14h5" />
    </svg>
  )
}

function AgentIcon() {
  return (
    <svg {...iconProps}>
      <path d="M12 2a5 5 0 015 5c0 2-1 3.5-2.5 4.5L16 20H8l1.5-8.5C8 10.5 7 9 7 7a5 5 0 015-5z" />
      <path d="M9 20v1a3 3 0 006 0v-1" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg {...iconProps} strokeWidth={1.6}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  )
}

function ProblemsIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <circle cx="12" cy="16" r=".5" fill="currentColor" />
    </svg>
  )
}

function SunIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg {...iconProps}>
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  )
}
