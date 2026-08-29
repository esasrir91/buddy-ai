import React, { useState } from 'react'
import type { ToolCall } from '../../types'

interface Props { toolCall: ToolCall }

export default function ToolCallChip({ toolCall }: Props) {
  const [expanded, setExpanded] = useState(false)

  const dotClass = `tool-chip__dot tool-chip__dot--${toolCall.status}`
  const chipClass = `tool-chip tool-chip--${toolCall.status}`

  const argPreview = Object.entries(toolCall.args ?? {})
    .slice(0, 2)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ')

  const statusIcon = toolCall.status === 'running' ? '⟳' :
    toolCall.status === 'done' ? '✓' : '✕'

  return (
    <div>
      <div className={chipClass} onClick={() => setExpanded(v => !v)}>
        <span className={dotClass} />
        <span style={{ color: 'var(--text-faint)', fontSize: 10 }}>{statusIcon}</span>
        <span className="tool-chip__name">{toolCall.name}</span>
        <span className="tool-chip__args">{argPreview}</span>
        <span style={{ marginLeft: 'auto', color: 'var(--text-faint)', fontSize: 10 }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>
      {expanded && (
        <div className="tool-detail">
          <div style={{ marginBottom: 4, color: 'var(--text-faint)', fontSize: 10 }}>INPUT</div>
          {JSON.stringify(toolCall.args, null, 2)}
          {toolCall.result && (
            <>
              <div style={{ margin: '6px 0 4px', color: 'var(--text-faint)', fontSize: 10 }}>OUTPUT</div>
              {toolCall.result.slice(0, 2000)}
              {toolCall.result.length > 2000 && '…'}
            </>
          )}
        </div>
      )}
    </div>
  )
}
