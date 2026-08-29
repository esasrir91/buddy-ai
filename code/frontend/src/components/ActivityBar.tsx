import React from 'react'
import { useStore } from '../store'
import type { SidebarView } from '../types'

interface ActivityBtnProps {
  icon: string
  label: string
  view?: SidebarView
  active?: boolean
  badge?: number
  onClick?: () => void
  title?: string
}

function ActivityBtn({ icon, label, view, active, badge, onClick, title }: ActivityBtnProps) {
  const { setSidebarView } = useStore()
  return (
    <button
      className={`activity-btn${active ? ' activity-btn--active' : ''}`}
      title={title ?? label}
      onClick={onClick ?? (view ? () => setSidebarView(view) : undefined)}
    >
      <span>{icon}</span>
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

  const views: Array<{ icon: string; label: string; view: SidebarView }> = [
    { icon: '📁', label: 'Explorer', view: 'explorer' },
    { icon: '🔍', label: 'Search', view: 'search' },
    { icon: '⎇', label: 'Source Control', view: 'git' },
    { icon: '🔌', label: 'MCP Servers', view: 'mcp' },
  ]

  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length

  return (
    <div className="activity-bar">
      <div className="activity-bar__top">
        {/* Aura logo */}
        <div style={{ marginBottom: 8, marginTop: 4, opacity: .9 }}>
          <AuraLogo />
        </div>

        {views.map(v => (
          <ActivityBtn
            key={v.view}
            icon={v.icon}
            label={v.label}
            view={v.view}
            active={sidebarVisible && sidebarView === v.view}
          />
        ))}

        <ActivityBtn
          icon="🤖"
          label="Aura Agent"
          active={agentPaneVisible}
          onClick={() => setAgentPaneVisible(!agentPaneVisible)}
        />
      </div>

      <div className="activity-bar__bottom">
        <ActivityBtn
          icon="⚙️"
          label="Settings"
          view="settings"
          active={sidebarVisible && sidebarView === 'settings'}
        />
        <ActivityBtn
          icon={theme === 'dark' ? '☀️' : '🌙'}
          label="Toggle theme"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        />
      </div>
    </div>
  )
}

function AuraLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="14" fill="url(#ag)" />
      <path d="M10 22 L16 10 L22 22" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <path d="M12 18 L20 18" stroke="white" strokeWidth="2" strokeLinecap="round" />
      <defs>
        <linearGradient id="ag" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7c3aed" />
          <stop offset="1" stopColor="#a855f7" />
        </linearGradient>
      </defs>
    </svg>
  )
}
