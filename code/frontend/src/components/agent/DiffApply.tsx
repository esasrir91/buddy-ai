import React, { useState } from 'react'
import type { FileDiff } from '../../types'

interface Props {
  msgId: string
  diff: FileDiff
  onApply: (msgId: string, diffId: string, diff: FileDiff) => void
  onReject: (msgId: string, diffId: string) => void
}

export default function DiffApply({ msgId, diff, onApply, onReject }: Props) {
  const [expanded, setExpanded] = useState(true)
  const fileName = diff.path.split(/[\\/]/).pop() ?? diff.path

  const statusLabel = diff.applied === true ? '✓ Applied' :
    diff.applied === false ? '✕ Rejected' :
    'Pending'

  const statusColor = diff.applied === true ? 'var(--ok)' :
    diff.applied === false ? 'var(--err)' :
    'var(--warn)'

  // Simple line diff display
  const oldLines = diff.oldContent.split('\n')
  const newLines = diff.newContent.split('\n')

  return (
    <div className="diff-card">
      <div className="diff-card__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ cursor: 'pointer' }} onClick={() => setExpanded(v => !v)}>
            {expanded ? '▼' : '▶'}
          </span>
          <span className="diff-card__path">📄 {fileName}</span>
          <span style={{ fontSize: 11, color: statusColor, fontWeight: 600 }}>{statusLabel}</span>
        </div>
        {diff.applied == null && (
          <div className="diff-card__actions">
            <button className="btn btn--xs btn--accept" onClick={() => onApply(msgId, diff.id, diff)}>✓ Apply</button>
            <button className="btn btn--xs btn--danger" onClick={() => onReject(msgId, diff.id)}>✕ Reject</button>
          </div>
        )}
      </div>
      {expanded && (
        <div className="diff-card__body">
          {/* Show unified diff */}
          {renderDiff(oldLines, newLines)}
        </div>
      )}
    </div>
  )
}

function renderDiff(oldLines: string[], newLines: string[]) {
  // Build a simple LCS-based diff display
  const maxLines = 40
  const truncated = oldLines.length > maxLines || newLines.length > maxLines

  const rows: React.ReactNode[] = []
  const minLen = Math.min(oldLines.length, newLines.length, maxLines)

  for (let i = 0; i < minLen; i++) {
    if (oldLines[i] !== newLines[i]) {
      rows.push(
        <div className="diff-line diff-line--del" key={`d${i}`}>
          <span className="diff-line__num">{i + 1}</span>
          <span>- {oldLines[i]}</span>
        </div>
      )
      rows.push(
        <div className="diff-line diff-line--add" key={`a${i}`}>
          <span className="diff-line__num">{i + 1}</span>
          <span>+ {newLines[i]}</span>
        </div>
      )
    } else {
      rows.push(
        <div className="diff-line diff-line--ctx" key={`c${i}`}>
          <span className="diff-line__num">{i + 1}</span>
          <span>  {oldLines[i]}</span>
        </div>
      )
    }
  }

  for (let i = minLen; i < Math.min(newLines.length, maxLines); i++) {
    rows.push(
      <div className="diff-line diff-line--add" key={`na${i}`}>
        <span className="diff-line__num">{i + 1}</span>
        <span>+ {newLines[i]}</span>
      </div>
    )
  }

  for (let i = minLen; i < Math.min(oldLines.length, maxLines); i++) {
    rows.push(
      <div className="diff-line diff-line--del" key={`od${i}`}>
        <span className="diff-line__num">{i + 1}</span>
        <span>- {oldLines[i]}</span>
      </div>
    )
  }

  if (truncated) {
    rows.push(
      <div key="trunc" style={{ padding: '4px 8px', fontSize: 11, color: 'var(--text-faint)' }}>
        … (truncated for display)
      </div>
    )
  }

  return <>{rows}</>
}
