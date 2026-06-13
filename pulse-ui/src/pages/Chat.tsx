import { useEffect, useRef, useState } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { usePulseChat } from '../hooks/usePulseChat'
import { Send, Loader2, MessageSquare } from 'lucide-react'

export default function Chat() {
  const { employeeId, employee } = usePulseStore()
  const employeeName = employee?.profile.full_name ?? 'PULSE'
  const chat = usePulseChat(employeeId ?? '')
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat.messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || !employeeId) return
    setInput('')

    if (chat.isConnected) {
      chat.sendMessage(text)
    } else {
      // Fallback: REST
      chat.sendMessage(text)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
          {employeeName.charAt(0)}
        </div>
        <div>
          <p className="text-sm font-semibold text-white">{employeeName}</p>
          <p className="text-[11px] text-slate-500 flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${chat.isConnected ? 'bg-green-400' : 'bg-slate-600'}`} />
            {chat.isConnected ? 'Connected' : 'Ready'}
          </p>
        </div>
        <div className="ml-auto">
          <MessageSquare size={16} className="text-slate-600" />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chat.messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-14 h-14 rounded-full bg-blue-600/20 border border-blue-600/30 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-blue-400">{employeeName.charAt(0)}</span>
              </div>
              <p className="text-slate-400 font-medium">Hi, I'm {employeeName}!</p>
              <p className="text-sm text-slate-500 mt-1">Ask me anything about my work, knowledge, or tasks.</p>
            </div>
          </div>
        )}

        {chat.messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''} animate-slide-up`}>
            <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${
              msg.role === 'user' ? 'bg-slate-700 text-slate-300' : 'bg-blue-600 text-white'}`}>
              {msg.role === 'user' ? 'You' : employeeName.charAt(0)}
            </div>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-slate-800 text-slate-200 rounded-tr-sm'
                : 'bg-blue-600/15 border border-blue-600/25 text-slate-100 rounded-tl-sm'}`}>
              {msg.role === 'assistant' && (
                <p className="text-[10px] text-blue-400 font-medium mb-1">{employeeName}</p>
              )}
              <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.streaming && <span className="inline-block w-1.5 h-4 bg-blue-400 ml-1 animate-pulse" />}
            </div>
          </div>
        ))}

        {chat.isStreaming && chat.messages[chat.messages.length - 1]?.role !== 'assistant' && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center text-xs font-bold text-white">
              {employeeName.charAt(0)}
            </div>
            <div className="flex items-center gap-2 px-4 py-3 bg-blue-600/15 border border-blue-600/25 rounded-2xl rounded-tl-sm">
              <Loader2 size={14} className="animate-spin text-blue-400" />
              <span className="text-sm text-slate-400">Thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-4 border-t border-slate-800 pt-3">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${employeeName}…`}
            rows={2}
            className="flex-1 resize-none bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || chat.isStreaming}
            className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 flex items-center justify-center transition-colors"
          >
            <Send size={16} className="text-white" />
          </button>
        </div>
      </div>
    </div>
  )
}
