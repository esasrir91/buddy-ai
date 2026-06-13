import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Video, CheckSquare, MessageSquare, TrendingUp, Clock } from 'lucide-react'
import { usePulseStore } from '../hooks/usePulseStore'
import { getEmployee, listTasks } from '../api/pulse'
import type { WorkItem, Employee } from '../types/pulse'

export default function Dashboard() {
  const { employeeId, employee: cached, setEmployee } = usePulseStore()
  const [employee, setEmp] = useState<Employee | null>(cached)
  const [tasks, setTasks] = useState<WorkItem[]>([])

  useEffect(() => {
    if (!employeeId) return
    getEmployee(employeeId).then((e) => { setEmp(e); setEmployee(employeeId, e) })
    listTasks(employeeId).then((r) => setTasks(r.tasks))
  }, [employeeId])

  if (!employee) return <div className="p-8 text-slate-500">Loading…</div>

  const p = employee.profile
  const activeTasks = tasks.filter((t) => t.status === 'in_progress')
  const blockedTasks = tasks.filter((t) => t.status === 'blocked')

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xl flex-shrink-0">
          {p.full_name.charAt(0)}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Good to see you, {p.full_name.split(' ')[0]}!</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {p.role} · {p.department}{p.team ? ` / ${p.team}` : ''}
          </p>
          {p.reporting_to && (
            <p className="text-slate-500 text-xs mt-0.5">Reports to {p.reporting_to}</p>
          )}
        </div>
        <div className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 pulse-dot" />
          <span className="text-xs text-green-400 font-medium">Available</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="KT Sessions" value={employee.memory_summary.kt_sessions_completed} icon={BookOpen} color="blue" />
        <StatCard label="KT Domains" value={employee.memory_summary.kt_domains.length} icon={TrendingUp} color="indigo" />
        <StatCard label="Active Tasks" value={activeTasks.length} icon={CheckSquare} color="amber" />
        <StatCard label="Colleagues" value={employee.memory_summary.colleagues_known} icon={MessageSquare} color="green" />
      </div>

      {/* Two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Quick actions */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Quick Actions</h2>
          <div className="space-y-2">
            <QuickAction to="/kt" icon={BookOpen} label="Start a KT Session" description="Learn from a document or human" color="bg-blue-600/20 text-blue-400" />
            <QuickAction to="/meetings" icon={Video} label="Process Meeting" description="Upload a transcript and extract actions" color="bg-purple-600/20 text-purple-400" />
            <QuickAction to="/tasks" icon={CheckSquare} label="View Task Board" description="See your current work items" color="bg-amber-600/20 text-amber-400" />
            <QuickAction to="/chat" icon={MessageSquare} label="Chat with PULSE" description="Ask anything in real-time" color="bg-green-600/20 text-green-400" />
          </div>
        </div>

        {/* Active tasks */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300">Active Tasks</h2>
            <Link to="/tasks" className="text-xs text-blue-400 hover:text-blue-300">View all →</Link>
          </div>
          {activeTasks.length === 0 ? (
            <p className="text-sm text-slate-600 py-4 text-center">No active tasks</p>
          ) : (
            <div className="space-y-2">
              {activeTasks.slice(0, 4).map((t) => (
                <div key={t.task_id} className="flex items-start gap-2.5 p-2.5 bg-slate-800/50 rounded-lg">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${t.priority === 'critical' ? 'bg-red-400' : t.priority === 'high' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                  <div className="min-w-0">
                    <p className="text-sm text-white truncate">{t.title}</p>
                    {t.deadline && (
                      <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1">
                        <Clock size={10} />
                        Due {t.deadline}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          {blockedTasks.length > 0 && (
            <div className="mt-3 p-2.5 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-xs text-red-400 font-medium">⚠️ {blockedTasks.length} blocked task{blockedTasks.length !== 1 ? 's' : ''}</p>
            </div>
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

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 bg-${color}-600/20`}>
        <Icon size={16} className={`text-${color}-400`} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
    </div>
  )
}

function QuickAction({ to, icon: Icon, label, description, color }: { to: string; icon: React.ElementType; label: string; description: string; color: string }) {
  return (
    <Link to={to} className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800 transition-colors group">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon size={15} />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-200 group-hover:text-white">{label}</p>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
    </Link>
  )
}
