import React, { useEffect, useState, useRef } from 'react'
import { fsList } from '../../api'
import { useStore } from '../../store'

interface Props {
  query: string
  onSelect: (path: string) => void
  onClose: () => void
}

export default function AtMentionMenu({ query, onSelect, onClose }: Props) {
  const { workspaceTree } = useStore()
  const [results, setResults] = useState<string[]>([])
  const [selected, setSelected] = useState(0)

  // Flatten tree to get all file paths
  const allFiles = React.useMemo(() => {
    const collect = (nodes: any[], out: string[] = []): string[] => {
      for (const n of nodes) {
        if (n.type === 'file') out.push(n.path)
        if (n.children) collect(n.children, out)
      }
      return out
    }
    return collect(workspaceTree)
  }, [workspaceTree])

  useEffect(() => {
    const q = query.toLowerCase()
    const filtered = allFiles
      .filter(p => p.toLowerCase().includes(q))
      .slice(0, 10)
    setResults(filtered)
    setSelected(0)
  }, [query, allFiles])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, results.length - 1)) }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)) }
      if (e.key === 'Enter') { e.preventDefault(); if (results[selected]) onSelect(results[selected]) }
      if (e.key === 'Escape') { e.preventDefault(); onClose() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [results, selected, onSelect, onClose])

  if (results.length === 0) return null

  return (
    <div className="at-menu">
      {results.map((path, i) => (
        <div
          key={path}
          className={`at-item${i === selected ? ' at-item--active' : ''}`}
          onClick={() => onSelect(path)}
          onMouseEnter={() => setSelected(i)}
        >
          <span className="at-item__icon">📄</span>
          <span className="at-item__label">{path.split(/[\\/]/).pop()}</span>
          <span className="at-item__detail">{path}</span>
        </div>
      ))}
    </div>
  )
}
