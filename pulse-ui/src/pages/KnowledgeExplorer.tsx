import { useState } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { searchKnowledge, listKTSessions } from '../api/pulse'
import type { KTSummary } from '../types/pulse'
import { Search, BookOpen, CheckCircle2 } from 'lucide-react'

export default function KnowledgeExplorer() {
  const { employeeId } = usePulseStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<KTSummary[]>([])
  const [allSessions, setAllSessions] = useState<KTSummary[]>([])
  const [loaded, setLoaded] = useState(false)
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState<KTSummary | null>(null)

  const loadAll = async () => {
    if (!employeeId) return
    setLoaded(false)
    const res = await listKTSessions(employeeId)
    setAllSessions(res.sessions)
    setLoaded(true)
  }

  useState(() => { loadAll() })

  const handleSearch = async () => {
    if (!employeeId || !query.trim()) return
    setSearching(true)
    try {
      const res = await searchKnowledge(employeeId, query)
      setResults(res.results)
    } finally { setSearching(false) }
  }

  const displayed = query ? results : allSessions

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-white">Knowledge Explorer</h1>
        <p className="text-slate-400 text-sm">Search across everything PULSE has learned.</p>
      </div>

      {/* Search */}
      <div className="flex gap-2 max-w-2xl">
        <div className="flex-1 relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search topics, concepts, sessions…"
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <button onClick={handleSearch} disabled={searching}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium transition-colors">
          {searching ? 'Searching…' : 'Search'}
        </button>
      </div>

      <div className="flex gap-5">
        {/* List */}
        <div className="flex-1 space-y-2">
          {displayed.length === 0 && loaded && (
            <div className="text-center py-12">
              <BookOpen size={36} className="text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">No KT sessions yet. Run a KT to see knowledge here.</p>
            </div>
          )}
          {displayed.map((s) => (
            <button
              key={s.session_id}
              onClick={() => setSelected(s)}
              className={`w-full text-left p-4 rounded-xl border transition-colors ${
                selected?.session_id === s.session_id
                  ? 'border-blue-600/50 bg-blue-600/10'
                  : 'border-slate-800 bg-slate-900 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-white">{s.session_name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{s.domain} · {s.knowledge_giver}</p>
                </div>
                <span className="text-xs font-bold text-green-400 flex-shrink-0">
                  {Math.round(s.confidence_score * 100)}%
                </span>
              </div>
              {s.key_concepts.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {s.key_concepts.slice(0, 4).map((c) => (
                    <span key={c} className="px-1.5 py-0.5 bg-slate-800 text-slate-400 text-[10px] rounded">{c}</span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div className="w-80 flex-shrink-0 bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3 animate-slide-up self-start sticky top-0">
            <h3 className="font-semibold text-white">{selected.session_name}</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">{selected.domain}</span>
              <span className="text-xs text-slate-700">·</span>
              <span className="text-xs font-bold text-green-400">{Math.round(selected.confidence_score * 100)}% confident</span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{selected.mental_model}</p>
            {selected.key_concepts.length > 0 && (
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1.5">Key Concepts</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.key_concepts.map((c) => (
                    <span key={c} className="flex items-center gap-1 px-2 py-0.5 bg-green-500/10 border border-green-500/20 rounded text-xs text-green-400">
                      <CheckCircle2 size={10} /> {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {selected.open_questions.length > 0 && (
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1.5">Open Questions</p>
                {selected.open_questions.map((q, i) => (
                  <p key={i} className="text-xs text-amber-300 mb-1">{q}</p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
