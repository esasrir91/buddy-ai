import { useState } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { processMeeting } from '../api/pulse'
import type { MeetingNotes } from '../types/pulse'
import { Video, CheckCircle2, AlertCircle } from 'lucide-react'

export default function MeetingRoom() {
  const { employeeId } = usePulseStore()
  const [transcript, setTranscript] = useState('')
  const [title, setTitle] = useState('')
  const [platform, setPlatform] = useState('zoom')
  const [loading, setLoading] = useState(false)
  const [notes, setNotes] = useState<MeetingNotes | null>(null)
  const [error, setError] = useState('')

  const handleProcess = async () => {
    if (!employeeId || !transcript.trim()) return
    setLoading(true); setError(''); setNotes(null)
    try {
      const result = await processMeeting(employeeId, { transcript, title: title || undefined, platform })
      setNotes(result)
    } catch (e) { setError(String(e)) }
    finally { setLoading(false) }
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Video size={20} className="text-purple-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Meeting Room</h1>
          <p className="text-slate-400 text-sm">Paste a meeting transcript to extract decisions and action items.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Input */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs text-slate-400 mb-1.5">Meeting Title</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Sprint Planning"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Platform</label>
              <select value={platform} onChange={(e) => setPlatform(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
                <option value="zoom">Zoom</option>
                <option value="microsoft_teams">MS Teams</option>
                <option value="google_meet">Google Meet</option>
                <option value="in_person">In Person</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">Transcript</label>
            <textarea rows={14} value={transcript} onChange={(e) => setTranscript(e.target.value)}
              placeholder={"Alice: Let's review the sprint goals...\nBob: I'll take the API refactor.\nAlice: Great, due by Friday?"}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none font-mono" />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button onClick={handleProcess} disabled={loading || !transcript.trim()}
            className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium transition-colors">
            <Video size={14} />
            {loading ? 'Processing…' : 'Process Meeting'}
          </button>
        </div>

        {/* Output */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          {!notes ? (
            <div className="h-full flex items-center justify-center py-16 text-center">
              <div>
                <Video size={40} className="text-slate-700 mx-auto mb-3" />
                <p className="text-sm text-slate-500">Meeting notes will appear here</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4 animate-slide-up">
              <h2 className="font-semibold text-white">{notes.title ?? 'Meeting Notes'}</h2>
              <p className="text-sm text-slate-300 leading-relaxed">{notes.summary}</p>

              {notes.key_decisions.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">Decisions</p>
                  <ul className="space-y-1">
                    {notes.key_decisions.map((d, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <CheckCircle2 size={14} className="text-green-400 mt-0.5 flex-shrink-0" />
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {notes.action_items.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">Action Items</p>
                  <div className="space-y-2">
                    {notes.action_items.map((a) => (
                      <div key={a.action_id} className="flex items-start gap-2.5 p-2.5 bg-slate-800 rounded-lg">
                        <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${a.priority === 'high' || a.priority === 'critical' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                        <div>
                          <p className="text-sm text-slate-200">{a.description}</p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {a.owner && `@${a.owner}`}{a.due_date && ` · due ${a.due_date}`}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {notes.open_questions.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-2">Open Questions</p>
                  {notes.open_questions.map((q, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-amber-300 mb-1">
                      <AlertCircle size={13} className="mt-0.5 flex-shrink-0" />
                      {q}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
