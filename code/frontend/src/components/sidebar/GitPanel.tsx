import React, { useEffect, useState, useCallback } from 'react'
import {
  gitStatus, gitStage, gitUnstage, gitCommit,
  gitDiscard, gitDiff, gitLog, gitCommitMsg, gitBranches, gitCheckout,
} from '../../api'
import { useStore } from '../../store'

interface GitFile { path: string; status: string; staged: boolean }

export default function GitPanel() {
  const { setGitInfo } = useStore()
  const [files, setFiles] = useState<GitFile[]>([])
  const [branch, setBranch] = useState('')
  const [commitMsg, setCommitMsg] = useState('')
  const [diffText, setDiffText] = useState('')
  const [logText, setLogText] = useState('')
  const [view, setView] = useState<'changes' | 'diff' | 'log'>('changes')
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  const refresh = useCallback(async () => {
    try {
      const s = await gitStatus()
      setBranch(s.branch ?? '')
      setFiles(s.files ?? [])
      setGitInfo(s.branch ?? '', (s.files ?? []).length)
    } catch {}
  }, [])

  useEffect(() => { refresh() }, [])

  useEffect(() => {
    if (view === 'diff') gitDiff(false).then(d => setDiffText(d.output)).catch(() => {})
    if (view === 'log') gitLog(30).then(l => setLogText(l.output)).catch(() => {})
  }, [view])

  const staged = files.filter(f => f.staged)
  const unstaged = files.filter(f => !f.staged)

  const doCommit = async () => {
    if (!commitMsg.trim()) return
    setLoading(true)
    try {
      await gitCommit(commitMsg)
      setCommitMsg('')
      setMsg('Committed')
      await refresh()
    } catch (e: any) {
      setMsg(String(e.message ?? e))
    } finally {
      setLoading(false)
    }
  }

  const autoMsg = async () => {
    setLoading(true)
    try {
      const { message } = await gitCommitMsg()
      setCommitMsg(message)
    } finally {
      setLoading(false)
    }
  }

  const statusColor = (s: string) => {
    if (s.startsWith('A') || s === '??' ) return 'var(--ok)'
    if (s.startsWith('M')) return 'var(--warn)'
    if (s.startsWith('D')) return 'var(--err)'
    return 'var(--info)'
  }

  return (
    <>
      <div className="sidebar__header">
        <span>Source Control</span>
        <div className="sidebar__header-actions">
          <button className="icon-btn" title="Refresh" onClick={refresh}>↻</button>
        </div>
      </div>
      <div className="sidebar__body">
        {/* branch */}
        <div style={{ padding: '6px 10px', fontSize: 12, color: 'var(--text-dim)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>⎇</span>
          <span style={{ fontWeight: 600 }}>{branch || '(no branch)'}</span>
        </div>

        {/* view tabs */}
        <div style={{ display: 'flex', gap: 2, padding: '4px 6px', borderBottom: '1px solid var(--border)' }}>
          {(['changes', 'diff', 'log'] as const).map(v => (
            <button
              key={v} onClick={() => setView(v)}
              className={`btn btn--xs${view === v ? ' btn--primary' : ' btn--ghost'}`}
            >{v}</button>
          ))}
        </div>

        {view === 'changes' && (
          <>
            {staged.length > 0 && (
              <>
                <div className="git-section-title">Staged ({staged.length})</div>
                {staged.map(f => (
                  <div className="git-file" key={f.path}>
                    <span className="git-file__status" style={{ color: statusColor(f.status) }}>{f.status}</span>
                    <span className="git-file__path">{f.path}</span>
                    <div className="git-file__actions">
                      <button className="icon-btn" title="Unstage" onClick={() => gitUnstage([f.path]).then(refresh)}>−</button>
                    </div>
                  </div>
                ))}
              </>
            )}
            {unstaged.length > 0 && (
              <>
                <div className="git-section-title">Changes ({unstaged.length})</div>
                {unstaged.map(f => (
                  <div className="git-file" key={f.path}>
                    <span className="git-file__status" style={{ color: statusColor(f.status) }}>{f.status}</span>
                    <span className="git-file__path">{f.path}</span>
                    <div className="git-file__actions">
                      <button className="icon-btn" title="Stage" onClick={() => gitStage([f.path]).then(refresh)}>+</button>
                      <button className="icon-btn" title="Discard" style={{ color: 'var(--err)' }} onClick={() => { if (confirm(`Discard ${f.path}?`)) gitDiscard([f.path]).then(refresh) }}>✕</button>
                    </div>
                  </div>
                ))}
                <div style={{ padding: '6px 10px' }}>
                  <button className="btn btn--sm" style={{ width: '100%' }} onClick={() => gitStage(['.']).then(refresh)}>Stage All</button>
                </div>
              </>
            )}
            {files.length === 0 && <div className="empty-state"><p>No changes</p></div>}

            {/* commit box */}
            <div style={{ padding: '8px 10px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', gap: 4 }}>
                <input
                  className="input" style={{ flex: 1, fontSize: 12 }}
                  placeholder="Commit message…"
                  value={commitMsg}
                  onChange={e => setCommitMsg(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && doCommit()}
                />
                <button className="btn btn--sm btn--ghost" title="AI commit message" onClick={autoMsg} disabled={loading}>✨</button>
              </div>
              <button className="btn btn--sm btn--primary" onClick={doCommit} disabled={loading || !commitMsg.trim()}>
                {loading ? '…' : 'Commit'}
              </button>
              {msg && <div style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>{msg}</div>}
            </div>
          </>
        )}

        {view === 'diff' && (
          <pre style={{ padding: 8, fontSize: 11.5, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', flex: 1, overflow: 'auto' }}>
            {diffText || 'No diff'}
          </pre>
        )}

        {view === 'log' && (
          <pre style={{ padding: 8, fontSize: 11.5, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', flex: 1, overflow: 'auto' }}>
            {logText || 'No log'}
          </pre>
        )}
      </div>
    </>
  )
}
