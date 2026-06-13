import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, BookOpen, Zap, Upload } from 'lucide-react'
import { usePulseStore } from '../hooks/usePulseStore'
import { runAsyncKT, createLiveKTSession } from '../api/pulse'
import type { KTSummary } from '../types/pulse'

export default function KTCenter() {
  const { employeeId, employee } = usePulseStore()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'async' | 'live'>('live')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<KTSummary | null>(null)
  const [error, setError] = useState('')

  // Async KT form
  const [asyncForm, setAsyncForm] = useState({
    source: '',
    source_type: 'document',
    session_name: '',
    knowledge_giver: '',
  })

  // Live KT form
  const [liveForm, setLiveForm] = useState({
    session_name: '',
    knowledge_giver: '',
  })

  const handleAsyncKT = async () => {
    if (!employeeId) return
    setLoading(true); setError(''); setResult(null)
    try {
      const summary = await runAsyncKT(employeeId, asyncForm)
      setResult(summary)
    } catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  const handleStartLiveKT = async () => {
    if (!employeeId) return
    setLoading(true); setError('')
    try {
      const res = await createLiveKTSession(employeeId, {
        session_name: liveForm.session_name,
        knowledge_giver: liveForm.knowledge_giver,
      })
      navigate(`/kt/live/${res.session_id}`)
    } catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-white">KT Center</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          {employee?.profile.full_name} can learn from documents or live human sessions.
        </p>
      </div>

      {/* Tab selector */}
      <div className="flex gap-1 p-1 bg-slate-900 border border-slate-800 rounded-xl w-fit">
        {(['live', 'async'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {t === 'live' ? <><Zap size={14} /> Live KT</> : <><Upload size={14} /> From Document</>}
          </button>
        ))}
      </div>

      {/* Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-2xl space-y-4">
        {tab === 'live' ? (
          <>
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Zap size={16} className="text-blue-400" />
              Start Live KT Session
            </h2>
            <p className="text-sm text-slate-400">
              A human explains a topic and {employee?.profile.full_name ?? 'PULSE'} asks targeted questions until it's confident.
            </p>
            <Field label="Session Name" value={liveForm.session_name} onChange={(v) => setLiveForm((p) => ({ ...p, session_name: v }))} placeholder="e.g. Auth Service Architecture" />
            <Field label="Knowledge Giver" value={liveForm.knowledge_giver} onChange={(v) => setLiveForm((p) => ({ ...p, knowledge_giver: v }))} placeholder="Name of the person explaining" />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              onClick={handleStartLiveKT}
              disabled={loading || !liveForm.session_name || !liveForm.knowledge_giver}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium transition-colors"
            >
              <Plus size={15} />
              {loading ? 'Starting…' : 'Start Live KT'}
            </button>
          </>
        ) : (
          <>
            <h2 className="font-semibold text-white flex items-center gap-2">
              <BookOpen size={16} className="text-blue-400" />
              Document / URL KT
            </h2>
            <Field label="Session Name" value={asyncForm.session_name} onChange={(v) => setAsyncForm((p) => ({ ...p, session_name: v }))} placeholder="e.g. Payments Architecture KT" />
            <Field label="Knowledge Giver" value={asyncForm.knowledge_giver} onChange={(v) => setAsyncForm((p) => ({ ...p, knowledge_giver: v }))} placeholder="Who created this document?" />
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Source Type</label>
              <select
                value={asyncForm.source_type}
                onChange={(e) => setAsyncForm((p) => ({ ...p, source_type: e.target.value }))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                <option value="document">Document (file path)</option>
                <option value="url">URL</option>
                <option value="audio_transcript">Audio Transcript</option>
                <option value="wiki_page">Wiki Page</option>
                <option value="codebase">Codebase</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Source (path, URL, or paste text)</label>
              <textarea
                rows={4}
                value={asyncForm.source}
                onChange={(e) => setAsyncForm((p) => ({ ...p, source: e.target.value }))}
                placeholder="Paste content, a file path, or URL…"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              onClick={handleAsyncKT}
              disabled={loading || !asyncForm.source || !asyncForm.session_name}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium transition-colors"
            >
              <BookOpen size={15} />
              {loading ? 'Processing KT…' : 'Run KT'}
            </button>
          </>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className="bg-slate-900 border border-green-600/30 rounded-2xl p-5 max-w-2xl animate-slide-up">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-green-400" />
            <h3 className="font-semibold text-white">KT Complete — {result.session_name}</h3>
            <span className="ml-auto text-sm font-bold text-green-400">{Math.round(result.confidence_score * 100)}%</span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed mb-3">{result.mental_model}</p>
          {result.key_concepts.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.key_concepts.map((c) => (
                <span key={c} className="px-2 py-0.5 bg-blue-600/15 text-blue-300 text-xs rounded-md">{c}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1.5">{label}</label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500" />
    </div>
  )
}
