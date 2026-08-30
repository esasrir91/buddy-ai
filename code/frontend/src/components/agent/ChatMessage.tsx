import React, { useState, useRef } from 'react'
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
  onEdit: (msgId: string) => void
  onSaveEdit: (msgId: string, content: string) => void
  onCancelEdit: (msgId: string) => void
  onDelete: (msgId: string) => void
  onRetry: (msgId: string) => void
}

function renderMarkdown(text: string): string {
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

export default function ChatMessage({
  msg, onApplyDiff, onRejectDiff, onAnswerAsk, onConfirmPlan,
  onEdit, onSaveEdit, onCancelEdit, onDelete, onRetry,
}: Props) {
  const isUser = msg.role === 'user'
  const ts = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const [hovered, setHovered] = useState(false)
  const [editDraft, setEditDraft] = useState(msg.content)
  const editRef = useRef<HTMLTextAreaElement>(null)

  const handleEditClick = () => {
    setEditDraft(msg.content)
    onEdit(msg.id)
    setTimeout(() => editRef.current?.focus(), 50)
  }

  return (
    <div
      className={`chat-msg chat-msg--${msg.role}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {isUser ? (
        <>
          <div className="chat-msg__meta">
            <span>You</span>
            <span>{ts}</span>
            {hovered && !msg.editing && (
              <div className="chat-msg__actions">
                <button className="msg-action-btn" onClick={handleEditClick} title="Edit">✎</button>
                <button className="msg-action-btn msg-action-btn--danger" onClick={() => onDelete(msg.id)} title="Delete">✕</button>
              </div>
            )}
          </div>
          {msg.editing ? (
            <div className="chat-msg__edit">
              <textarea
                ref={editRef}
                value={editDraft}
                onChange={e => setEditDraft(e.target.value)}
                rows={3}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSaveEdit(msg.id, editDraft) }
                  if (e.key === 'Escape') onCancelEdit(msg.id)
                }}
              />
              <div className="chat-msg__edit-actions">
                <button className="btn btn--xs btn--primary" onClick={() => onSaveEdit(msg.id, editDraft)}>Send</button>
                <button className="btn btn--xs btn--ghost" onClick={() => onCancelEdit(msg.id)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="chat-msg__bubble">{msg.content}</div>
          )}
        </>
      ) : (
        <>
          <div className="chat-msg__meta">
            <span style={{ color: 'var(--accent-ai)' }}>✨ Aura</span>
            <span>{ts}</span>
            {hovered && !msg.streaming && (
              <div className="chat-msg__actions">
                <button className="msg-action-btn" onClick={() => onRetry(msg.id)} title="Regenerate">↺</button>
                <button className="msg-action-btn msg-action-btn--danger" onClick={() => onDelete(msg.id)} title="Delete">✕</button>
              </div>
            )}
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
