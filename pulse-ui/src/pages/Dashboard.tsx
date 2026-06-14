import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Video, CheckSquare, MessageSquare, TrendingUp, Clock, Zap, RefreshCw, Lightbulb, Calendar } from 'lucide-react'
import { usePulseStore } from '../hooks/usePulseStore'
import { getEmployee, listTasks, getActivity, generateStandup, suggestTasks, assignTask } from '../api/pulse'
import type { WorkItem, Employee, ActivityEvent } from '../types/pulse'
import clsx from 'clsx'

const EVENT_ICONS: Record<string, string> = {
  task_started: '▶',
  task_done: '✓',
  task_error: '✗',
  kt_learned: '📚',
  standup: '📋',
  suggestion: '💡',
  message: '💬',
}

const EVENT_COLORS: Record<string, string> = {
  task_started: 'text-blue-400',
  task_done: 'text-green-400',
  task_error: 'text-red-400',
  kt_learned: 'text-purple-400',
  standup: 'text-amber-400',
  suggestion: 'text-cyan-400',
  message: 'text-slate-400',
}

export default function Dashboard() {
  const { employeeId, employee: cached, setEmployee } = usePulseStore()
  const [employee, setEmp] = useState<Employee | null>(cached)
  const [tasks, setTasks] = useState<WorkItem[]>([])
  const [activity, setActivity] = useState<ActivityEvent[]>([])
  const [standup, setStandup] = useState<string | null>(null)
  const [generatingStandup, setGeneratingStandup] = useState(false)
  const [suggestions, setSuggestions] = useState<Array<{ title: string; description: string; priority: string }>>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [addingTask, setAddingTask] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = async () => {
    if (!employeeId) return
    const [e, t, a] = await Promise.all([
      getEmployee(employeeId),
      listTasks(employeeId),
      getActivity(employeeId, 30),
    ])
    setEmp(e); setEmployee(employeeId, e)
    setTasks(t.tasks)
    setActivity(a.events)
  }

  useEffect(() => {
    load()
    // Poll activity every 10s when tasks are running
    pollRef.current = setInterval(() => {
      if (!employeeId) return
      Promise.all([listTasks(employeeId), getActivity(employeeId, 30)]).then(([t, a]) => {
        setTasks(t.tasks); setActivity(a.events)
      }).catch(() => {})
    }, 10000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [employeeId])

  const handleStandup = async () => {
    if (!employeeId) return
    setGeneratingStandup(true)
    try {
      const r = await generateStandup(employeeId)
      setStandup(r.standup)
    } finally { setGeneratingStandup(false) }
  }

  const handleSuggest = async () => {
    if (!employeeId) return
    setLoadingSuggestions(true)
    try {
      const r = await suggestTasks(employeeId)
      setSuggestions(r.suggestions)
    } finally { setLoadingSuggestions(false) }
  }

  const handleAddSuggestion = async (s: { title: string; description: string; priority: string }) => {
    if (!employeeId) return
    setAddingTask(s.title)
    try {
      await assignTask(employeeId, { title: s.title, description: s.description, priority: s.priority })
      setSuggestions((prev) => prev.filter((x) => x.title !== s.title))
      const t = await listTasks(employeeId)
      setTasks(t.tasks)
    } finally { setAddingTask(null) }
  }

  if (!employee) return <div className="p-8 text-slate-500">Loading…</div>

  const p = employee.profile
  const activeTasks = tasks.filter((t) => t.status === 'in_progress')
  const todoTasks = tasks.filter((t) => t.status === 'todo')
  const blockedTasks = tasks.filter((t) => t.status === 'blocked')
  const doneTasks = tasks.filter((t) => t.status === 'done')

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xl flex-shrink-0">
          {p.full_name.charAt(0)}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">{p.full_name}</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {p.role} · {p.department}{p.team ? ` / ${p.team}` : ''}
          </p>
          {p.company_name && <p className="text-slate-500 text-xs mt-0.5">{p.company_name}</p>}
        </div>
        <div className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-green-400 font-medium">
            {activeTasks.length > 0 ? `Working on ${activeTasks.length} task${activeTasks.length > 1 ? 's' : ''}` : 'Available'}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="KT Sessions" value={employee.memory_summary.kt_sessions_completed} icon={BookOpen} colorClass="text-blue-400 bg-blue-600/20" />
        <StatCard label="Tasks Done" value={doneTasks.length} icon={CheckSquare} colorClass="text-green-400 bg-green-600/20" />
        <StatCard label="In Progress" value={activeTasks.length} icon={Zap} colorClass="text-amber-400 bg-amber-600/20" />
        <StatCard label="Queued" value={todoTasks.length} icon={TrendingUp} colorClass="text-indigo-400 bg-indigo-600/20" />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Activity feed — col 1 */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300">Activity Feed</h2>
            <button onClick={load} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors">
              <RefreshCw size={13} />
            </button>
          </div>
          {activity.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-slate-600 text-sm">No activity yet.</p>
              <p className="text-slate-700 text-xs mt-1">PULSE will log every action it takes here.</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
              {activity.map((e, i) => (
                <div key={i} className="flex items-start gap-2.5 py-2 border-b border-slate-800/50 last:border-0">
                  <span className={clsx('text-xs font-mono mt-0.5 w-4 text-center flex-shrink-0', EVENT_COLORS[e.event_type] ?? 'text-slate-500')}>
                    {EVENT_ICONS[e.event_type] ?? '•'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-200 truncate">{e.title}</p>
                    {e.detail && (
                      <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{e.detail}</p>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-600 flex-shrink-0 mt-0.5">
                    {new Date(e.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right column — quick actions + active tasks */}
        <div className="space-y-4">
          {/* Quick actions */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">Quick Actions</h2>
            <div className="space-y-1">
              <QuickAction to="/kt" icon={BookOpen} label="Give KT" description="Teach PULSE something new" colorClass="bg-blue-600/20 text-blue-400" />
              <QuickAction to="/meetings" icon={Video} label="Upload Meeting" description="Process transcript" colorClass="bg-purple-600/20 text-purple-400" />
              <QuickAction to="/tasks" icon={CheckSquare} label="Task Board" description="View all tasks" colorClass="bg-amber-600/20 text-amber-400" />
              <QuickAction to="/chat" icon={MessageSquare} label="Chat" description="Ask anything" colorClass="bg-green-600/20 text-green-400" />
            </div>
          </div>

          {/* Active tasks */}
          {activeTasks.length > 0 && (
            <div className="bg-slate-900 border border-blue-600/20 rounded-2xl p-4">
              <h2 className="text-sm font-semibold text-blue-300 mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                Currently Working On
              </h2>
              <div className="space-y-2">
                {activeTasks.slice(0, 3).map((t) => (
                  <div key={t.task_id} className="p-2.5 bg-blue-600/10 border border-blue-600/20 rounded-lg">
                    <p className="text-sm text-white">{t.title}</p>
                    {t.deadline && (
                      <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1">
                        <Clock size={10} /> Due {t.deadline}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {blockedTasks.length > 0 && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
              <p className="text-xs text-red-400 font-medium">{blockedTasks.length} blocked task{blockedTasks.length !== 1 ? 's' : ''}</p>
              <Link to="/tasks" className="text-[11px] text-red-400/70 hover:text-red-300">View on board →</Link>
            </div>
          )}
        </div>
      </div>

      {/* Standup + Suggestions row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Daily standup */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Calendar size={14} className="text-amber-400" /> Daily Standup
            </h2>
            <button
              onClick={handleStandup}
              disabled={generatingStandup}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 text-xs rounded-lg transition-colors disabled:opacity-50"
            >
              {generatingStandup ? <RefreshCw size={12} className="animate-spin" /> : null}
              {generatingStandup ? 'Generating…' : 'Generate'}
            </button>
          </div>
          {standup ? (
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{standup}</p>
          ) : (
            <p className="text-sm text-slate-600 py-4 text-center">
              Click Generate to get PULSE's daily standup report.
            </p>
          )}
        </div>

        {/* Task suggestions */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Lightbulb size={14} className="text-cyan-400" /> PULSE Suggests
            </h2>
            <button
              onClick={handleSuggest}
              disabled={loadingSuggestions}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs rounded-lg transition-colors disabled:opacity-50"
            >
              {loadingSuggestions ? <RefreshCw size={12} className="animate-spin" /> : null}
              {loadingSuggestions ? 'Thinking…' : 'Ask PULSE'}
            </button>
          </div>
          {suggestions.length > 0 ? (
            <div className="space-y-2">
              {suggestions.map((s, i) => (
                <div key={i} className="flex items-start gap-2 p-2.5 bg-slate-800/50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200">{s.title}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{s.description}</p>
                  </div>
                  <button
                    onClick={() => handleAddSuggestion(s)}
                    disabled={addingTask === s.title}
                    className="flex-shrink-0 px-2 py-1 text-[11px] bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 rounded transition-colors disabled:opacity-50"
                  >
                    {addingTask === s.title ? '…' : '+ Add'}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600 py-4 text-center">
              PULSE will suggest proactive tasks based on its role and knowledge.
            </p>
          )}
        </div>
      </div>

      {/* Knowledge domains */}
      {employee.kt_domains.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Knowledge Domains</h2>
          <div className="flex flex-wrap gap-2">
            {employee.kt_domains.map((domain) => (
              <span key={domain} className="px-2.5 py-1 bg-blue-600/15 border border-blue-600/25 text-blue-300 text-xs rounded-lg">
                {domain}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, icon: Icon, colorClass }: {
  label: string; value: number; icon: React.ElementType; colorClass: string
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${colorClass.split(' ')[1]}`}>
        <Icon size={16} className={colorClass.split(' ')[0]} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
    </div>
  )
}

function QuickAction({ to, icon: Icon, label, description, colorClass }: {
  to: string; icon: React.ElementType; label: string; description: string; colorClass: string
}) {
  return (
    <Link to={to} className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-800 transition-colors group">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${colorClass}`}>
        <Icon size={15} />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-200 group-hover:text-white">{label}</p>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
    </Link>
  )
}
