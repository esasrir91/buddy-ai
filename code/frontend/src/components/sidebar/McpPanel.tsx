import React, { useEffect, useState } from 'react'
import { getMcpServers, addMcpServer, removeMcpServer, toggleMcpServer } from '../../api'
import type { McpServer } from '../../types'

export default function McpPanel() {
  const [servers, setServers] = useState<McpServer[]>([])
  const [loading, setLoading] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCmd, setNewCmd] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [transport, setTransport] = useState<'stdio' | 'sse' | 'streamable-http'>('stdio')

  const refresh = async () => {
    try {
      const data = await getMcpServers()
      setServers((data.servers ?? []) as McpServer[])
    } catch {}
  }

  useEffect(() => { refresh() }, [])

  const doAdd = async () => {
    if (!newName.trim()) return
    setLoading(true)
    try {
      const payload: any = { name: newName, enabled: true, transport }
      if (transport === 'stdio') payload.command = newCmd
      else payload.url = newUrl
      await addMcpServer(payload)
      setShowAdd(false)
      setNewName(''); setNewCmd(''); setNewUrl('')
      await refresh()
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="sidebar__header">
        <span>MCP Servers</span>
        <div className="sidebar__header-actions">
          <button className="icon-btn" title="Add server" onClick={() => setShowAdd(v => !v)}>+</button>
          <button className="icon-btn" title="Refresh" onClick={refresh}>↻</button>
        </div>
      </div>
      <div className="sidebar__body">
        {showAdd && (
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input className="input" placeholder="Server name" value={newName} onChange={e => setNewName(e.target.value)} style={{ fontSize: 12 }} />
            <select className="select" value={transport} onChange={e => setTransport(e.target.value as any)} style={{ fontSize: 12 }}>
              <option value="stdio">stdio</option>
              <option value="sse">SSE</option>
              <option value="streamable-http">HTTP</option>
            </select>
            {transport === 'stdio'
              ? <input className="input input--mono" placeholder="Command (e.g. npx -y @modelcontextprotocol/server-github)" value={newCmd} onChange={e => setNewCmd(e.target.value)} style={{ fontSize: 11.5 }} />
              : <input className="input input--mono" placeholder="URL" value={newUrl} onChange={e => setNewUrl(e.target.value)} style={{ fontSize: 11.5 }} />
            }
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn--sm btn--primary" onClick={doAdd} disabled={loading}>Add</button>
              <button className="btn btn--sm btn--ghost" onClick={() => setShowAdd(false)}>Cancel</button>
            </div>
          </div>
        )}

        {servers.length === 0 && (
          <div className="empty-state">
            <p>No MCP servers configured.</p>
            <p>Add a server to give the agent extra tools.</p>
          </div>
        )}

        {servers.map(srv => (
          <div key={srv.name} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: srv.enabled ? 'var(--ok)' : 'var(--text-faint)', flexShrink: 0 }} />
              <span style={{ fontWeight: 600, fontSize: 12.5, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{srv.name}</span>
              <button className="icon-btn" title={srv.enabled ? 'Disable' : 'Enable'} onClick={() => toggleMcpServer(srv.name, !srv.enabled).then(refresh)}>
                {srv.enabled ? '⏸' : '▶'}
              </button>
              <button className="icon-btn" style={{ color: 'var(--err)' }} title="Remove" onClick={() => { if (confirm(`Remove ${srv.name}?`)) removeMcpServer(srv.name).then(refresh) }}>✕</button>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {srv.command || srv.url || ''}
            </div>
            {srv.tools && srv.tools.length > 0 && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {srv.tools.length} tool{srv.tools.length !== 1 ? 's' : ''}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  )
}
