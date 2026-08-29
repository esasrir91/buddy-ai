import React, { useState } from 'react'
import type { ChatMessage as ChatMsg, FileDiff, AskPayload, PlanPayload } from '../../types'
import ToolCallChip from './ToolCallChip'
import DiffApply from './DiffApply'
import PlanView from './PlanView'
import AskView from './AskView'

interface Props {
  msg: ChatMsg
  onApplyDiff: (msgId: string, diffId: string, diff: FileDiff) => void
  onRejectDiff: (msgId: string, diffId: string) => void
  onAnswerAsk: (msgId: string, answers: Record<string, any>) => void
  onConfirmPlan: (msgId: string, confirmed: boolean) => void
}

function renderMarkdown(text: string): string {
  // simple markdown renderer
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(.+)$(?!<\/?(h\d|ul|li|pre|p))/gm, (_, l) => l)
}

export default function ChatMessage({ msg, onApplyDiff, onRejectDiff, onAnswerAsk, onConfirmPlan }: Props) {
  const isUser = msg.role === 'user'
  const ts = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className={`chat-msg chat-msg--${msg.role}`}>
      {isUser ? (
        <>
          <div className="chat-msg__meta"><span>You</span><span>{ts}</span></div>
          <div className="chat-msg__bubble">{msg.content}</div>
        </>
      ) : (
        <>
          <div className="chat-msg__meta">
            <span style={{ color: 'var(--accent-ai)' }}>✨ Aura</span>
            <span>{ts}</span>
          </div>

          {/* tool calls */}
          {msg.toolCalls && msg.toolCalls.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {msg.toolCalls.map(tc => (
                <ToolCallChip key={tc.id} toolCall={tc} />
              ))}
            </div>
          )}

          {/* file diffs */}
          {msg.fileDiffs && msg.fileDiffs.map(diff => (
            <DiffApply
              key={diff.id}
              msgId={msg.id}
              diff={diff}
              onApply={onApplyDiff}
              onReject={onRejectDiff}
            />
          ))}

          {/* plan */}
          {msg.planPayload && (
            <PlanView
              msgId={msg.id}
              plan={msg.planPayload}
              onConfirm={onConfirmPlan}
            />
          )}

          {/* ask question */}
          {msg.askPayload && !msg.askPayload.answered && (
            <AskView
              msgId={msg.id}
              ask={msg.askPayload}
              onAnswer={onAnswerAsk}
            />
          )}
          {msg.askPayload?.answered && (
            <div style={{ fontSize: 12, color: 'var(--text-faint)', fontStyle: 'italic' }}>✓ Answered</div>
          )}

          {/* main content */}
          {msg.content && msg.content !== '⟳' && (
            <div
              className="chat-msg__bubble"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
            />
          )}
          {msg.streaming && !msg.content && (
            <div className="chat-msg__bubble" style={{ color: 'var(--text-faint)', fontStyle: 'italic' }}>
              <span className="spinner">⟳</span> thinking…
            </div>
          )}
        </>
      )}
    </div>
  )
}
