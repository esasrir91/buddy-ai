import React, { useState, useCallback } from 'react'
import { search as apiSearch, fsRead } from '../../api'
import { useStore } from '../../store'

interface Result {
  path: string
  line: number
  text: string
}

export default function SearchPanel() {
  const { openTab, openTabs } = useStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const doSearch = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const data = await apiSearch(query)
      setResults(data.results ?? [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query])

  // Group results by file
  const grouped: Record<string, Result[]> = {}
  for (const r of results) {
    if (!grouped[r.path]) grouped[r.path] = []
    grouped[r.path].push(r)
  }

  const openResult = async (r: Result) => {
    const existing = openTabs.find(t => t.path === r.path)
    if (existing) {
      useStore.getState().setActiveTab(existing.id)
      return
    }
    try {
      const { content } = await fsRead(r.path)
      openTab(r.path, content)
    } catch {
      openTab(r.path, '')
    }
  }

  // highlight match in text
  const highlight = (text: string, q: string) => {
    if (!q) return text
    const idx = text.toLowerCase().indexOf(q.toLowerCase())
    if (idx === -1) return text
    return (
      <>
        {text.slice(0, idx)}
        <span className="search-result-item__match">{text.slice(idx, idx + q.length)}</span>
        {text.slice(idx + q.length)}
      </>
    )
  }

  return (
    <>
      <div className="sidebar__header">
        <span>Search</span>
      </div>
      <div className="sidebar__body">
        <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              className="input"
              style={{ flex: 1, fontSize: 12.5 }}
              placeholder="Search workspace…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doSearch()}
            />
            <button className="btn btn--sm" onClick={doSearch} disabled={loading}>
              {loading ? '…' : '🔍'}
            </button>
          </div>
        </div>
        {searched && results.length === 0 && !loading && (
          <div className="empty-state"><p>No results for "{query}"</p></div>
        )}
        {Object.entries(grouped).map(([file, items]) => (
          <div key={file}>
            <div className="search-result-file" title={file}>{file.split(/[\\/]/).pop()}</div>
            {items.map((r, i) => (
              <div key={i} className="search-result-item" onClick={() => openResult(r)}>
                <span className="search-result-item__line">{r.line}</span>
                <span className="search-result-item__text">{highlight(r.text, query)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  )
}
