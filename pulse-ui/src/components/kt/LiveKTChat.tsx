import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import type { KTTurn } from '../../types/pulse'
import clsx from 'clsx'

export interface ChatEntry {
  id: string
  role: 'human' | 'pulse'
  text: string
  turn?: KTTurn
}

interface Props {
  entries: ChatEntry[]
  employeeName: string
  isLoading: boolean
  onHumanSend: (text: string) => void
  placeholder?: string
}

export function LiveKTChat({ entries, employeeName, isLoading, onHumanSend, placeholder }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    onHumanSend(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (entries.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 flex items-center justify-center p-8 text-center">
          <div>
            <div className="w-14 h-14 rounded-full bg-blue-600/20 border border-blue-600/30 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-blue-400">
                {employeeName.charAt(0)}
              </span>
            </div>
            <p className="text-slate-300 font-medium mb-1">Ready to learn</p>
            <p className="text-sm text-slate-500">
              {employeeName} is listening. Start explaining the topic below.
            </p>
          </div>
        </div>
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          onKeyDown={handleKeyDown}
          isLoading={isLoading}
          placeholder={placeholder}
          ref={textareaRef}
        />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={clsx(
              'flex gap-3 animate-slide-up',
              entry.role === 'human' ? 'flex-row-reverse' : 'flex-row',
            )}
          >
            {/* Avatar */}
            <div
              className={clsx(
                'w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold',
                entry.role === 'human'
                  ? 'bg-slate-700 text-slate-300'
                  : 'bg-blue-600 text-white',
              )}
            >
              {entry.role === 'human' ? 'You' : employeeName.charAt(0)}
            </div>

            {/* Bubble */}
            <div
              className={clsx(
                'max-w-[75%] rounded-2xl px-4 py-3 text-sm',
                entry.role === 'human'
                  ? 'bg-slate-800 text-slate-200 rounded-tr-sm'
                  : 'bg-blue-600/15 border border-blue-600/25 text-slate-100 rounded-tl-sm',
              )}
            >
              {entry.role === 'pulse' && (
                <p className="text-[10px] text-blue-400 font-medium mb-1">{employeeName}</p>
              )}
              <p className="leading-relaxed whitespace-pre-wrap">{entry.text}</p>

              {/* Questions list */}
              {entry.turn && entry.turn.questions.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {entry.turn.questions.map((q, i) => (
                    <div key={i} className="flex items-start gap-1.5">
                      <span className="text-blue-400 font-bold text-xs mt-0.5 flex-shrink-0">
                        {i + 1}.
                      </span>
                      <p className="text-xs text-slate-300">{q}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Confidence chip */}
              {entry.turn && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-1 flex-1 bg-slate-800 rounded-full">
                    <div
                      className="h-1 rounded-full bg-blue-400 transition-all duration-500"
                      style={{ width: `${Math.round(entry.turn.confidence_score * 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-slate-500">
                    {Math.round(entry.turn.confidence_score * 100)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center text-xs font-bold text-white">
              {employeeName.charAt(0)}
            </div>
            <div className="flex items-center gap-2 px-4 py-3 bg-blue-600/15 border border-blue-600/25 rounded-2xl rounded-tl-sm">
              <Loader2 size={14} className="animate-spin text-blue-400" />
              <span className="text-sm text-slate-400">{employeeName} is thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        onKeyDown={handleKeyDown}
        isLoading={isLoading}
        placeholder={placeholder}
        ref={textareaRef}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Chat input sub-component
// ---------------------------------------------------------------------------

interface InputProps {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
  isLoading: boolean
  placeholder?: string
}

import React from 'react'

const ChatInput = React.forwardRef<HTMLTextAreaElement, InputProps>(
  ({ value, onChange, onSend, onKeyDown, isLoading, placeholder }, ref) => (
    <div className="px-4 pb-4 border-t border-slate-800 pt-3">
      <div className="flex gap-2 items-end">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder ?? 'Explain or answer… (Enter to send, Shift+Enter for new line)'}
          rows={2}
          className="flex-1 resize-none bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
        <button
          onClick={onSend}
          disabled={!value.trim() || isLoading}
          className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors flex-shrink-0"
        >
          <Send size={16} className="text-white" />
        </button>
      </div>
      <p className="text-[10px] text-slate-600 mt-1 text-right">
        Enter ↵ to send
      </p>
    </div>
  ),
)
ChatInput.displayName = 'ChatInput'
