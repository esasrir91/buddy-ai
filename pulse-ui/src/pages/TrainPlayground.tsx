import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Flame, Send, Loader2, Zap, ArrowLeft } from 'lucide-react'
import { getTrainedModels, testTrainedModel } from '../api/train'
import type { TrainedModel } from '../types/train'

interface ChatMsg {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export default function TrainPlayground() {
  const [searchParams] = useSearchParams()
  const initialModel = searchParams.get('model') ?? 'fire'

  const [models, setModels] = useState<TrainedModel[]>([])
  const [selected, setSelected] = useState(initialModel)
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getTrainedModels()
      .then((r) => {
        setModels(r.models)
        if (r.models.length && !r.models.find((m) => m.name === selected)) {
          setSelected(r.models[0].name)
        }
      })
      .catch((e) => setError(String(e)))
  }, [])

  const handleSend = async () => {
    const text = prompt.trim()
    if (!text || loading) return
    setPrompt('')
    setError('')
    const userMsg: ChatMsg = { id: crypto.randomUUID(), role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)
    try {
      const res = await testTrainedModel(selected, { prompt: text, max_length: 200, temperature: 0.7 })
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: res.response },
      ])
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 flex flex-col h-full max-w-2xl animate-fade-in">
      <div className="mb-4">
        <Link to="/train" className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1">
          <ArrowLeft size={12} /> Fire Studio
        </Link>
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-2">
            <Flame size={20} className="text-orange-400" />
            <h1 className="text-xl font-bold text-white">Playground</h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
              local · free
            </span>
          </div>
          {models.length > 0 && (
            <select
              value={selected}
              onChange={(e) => { setSelected(e.target.value); setMessages([]) }}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white"
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {models.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-slate-900 border border-slate-800 rounded-2xl">
          <Flame size={36} className="text-slate-600 mb-3" />
          <p className="text-slate-300 font-medium">No trained models yet</p>
          <p className="text-sm text-slate-500 mt-1 mb-4">Train Fire first, then test it here.</p>
          <Link to="/train/new" className="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded-xl text-white text-sm">
            Train Fire
          </Link>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-[300px]">
            {messages.length === 0 && (
              <div className="text-center py-12 text-slate-600 text-sm">
                <Zap size={24} className="mx-auto mb-2 opacity-50" />
                Chat with <strong className="text-slate-400">{selected}</strong> — runs entirely on your machine.
              </div>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm ${
                    m.role === 'user'
                      ? 'bg-orange-600/20 text-orange-100 border border-orange-500/20'
                      : 'bg-slate-800 text-slate-200 border border-slate-700'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-slate-500 text-sm">
                <Loader2 size={14} className="animate-spin" /> Generating locally…
              </div>
            )}
          </div>

          {error && <p className="text-sm text-red-400 mb-2">{error}</p>}

          <div className="flex gap-2">
            <input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder={`Message ${selected}…`}
              disabled={loading}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-orange-500"
            />
            <button
              onClick={handleSend}
              disabled={loading || !prompt.trim()}
              className="px-4 py-3 bg-orange-600 hover:bg-orange-500 disabled:opacity-40 rounded-xl text-white transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </>
      )}
    </div>
  )
}
