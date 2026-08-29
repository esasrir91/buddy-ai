import React from 'react'
import { useStore } from '../../store'
import Explorer from './Explorer'
import SearchPanel from './SearchPanel'
import GitPanel from './GitPanel'
import McpPanel from './McpPanel'
import SettingsPanel from './SettingsPanel'

interface Props {
  style?: React.CSSProperties
}

export default function Sidebar({ style }: Props) {
  const { sidebarView } = useStore()

  return (
    <div className="sidebar" style={style}>
      {sidebarView === 'explorer' && <Explorer />}
      {sidebarView === 'search' && <SearchPanel />}
      {sidebarView === 'git' && <GitPanel />}
      {sidebarView === 'mcp' && <McpPanel />}
      {sidebarView === 'settings' && <SettingsPanel />}
      {sidebarView === null && null}
    </div>
  )
}
