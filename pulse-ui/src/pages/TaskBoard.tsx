import { useState, useEffect, useRef } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { assignTask, listTasks, updateTask, getTaskStatusUpdate } from '../api/pulse'
import type { WorkItem, StatusUpdate } from '../types/pulse'
import { Plus, RefreshCw, Zap, ZapOff } from 'lucide-react'
import clsx from 'clsx'

const STATUS_COLS: WorkItem['status'][] = ['todo', 'in_progress', 'blocked', 'in_review', 'done']

const STATUS_LABELS: Record<WorkItem['status'], string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  in_review: 'In Review',
  done: 'Done',
  cancelled: 'Cancelled',
}

const STATUS_COLORS: Record<string, string> = {
  todo: 'bg-slate-700 text-slate-300',
  in_progress: 'bg-blue-600/20 text-blue-300',
  blocked: 'bg-red-600/20 text-red-400',
  in_review: 'bg-purple-600/20 text-purple-300',
  done: 'bg-green-600/20 text-green-400',
  cancelled: 'bg-slate-800 text-slate-500',
}

const PRIORITY_DOT: Record<string, string> = {
  low: 'bg-slate-500',
  medium: 'bg-blue-400',
  high: 'bg-amber-400',
  critical: 'bg-red-500',
}

export default function TaskBoard() {
  const { employeeId } = usePulseStore()
  const [tasks, setTasks] = useState<WorkItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ title: '', description: '', priority: 'medium', deadline: '' })
  const [statusUpdate, setStatusUpdate] = useState<StatusUpdate | null>(null)
  const [autoWork, setAutoWork] = useState(true)
  const [togglingAuto, setTogglingAuto] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = async () => {
    if (!employeeId) return
    setLoading(true)
    try { setTasks((await listTasks(employeeId)).tasks) }
    finally { setLoading(false) }
  }

  // Fetch auto-work setting from backend on mount
  useEffect(() => {
    fetch('/api/pulse/settings/auto-work')
      .then((r) => r.json())
      .then((d) => setAutoWork(d.enabled))
      .catch(() => {})
  }, [])

  // Poll every 15s when tasks are active so auto-completions appear in real time
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => {
      if (tasks.some((t) => t.status === 'in_progress' || t.status === 'todo')) {
        refresh()
      }
    }, 15000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [tasks, employeeId])

  useEffect(() => { refresh() }, [employeeId])

  const toggleAutoWork = async () => {
    setTogglingAuto(true)
    try {
      const res = await fetch('/api/pulse/settings/auto-work', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !autoWork }),
      })
      const data = await res.json()
      setAutoWork(data.enabled)
    } catch { /* ignore */ }
    finally { setTogglingAuto(false) }
  }

  const handleAdd = async () => {
    if (!employeeId || !addForm.title) return
    const task = await assignTask(employeeId, {
      title: addForm.title,
      description: addForm.description,
      priority: addForm.priority,
      deadline: addForm.deadline || undefined,
    })
    setTasks((prev) => [...prev, task])
    setAddForm({ title: '', description: '', priority: 'medium', deadline: '' })
    setShowAdd(false)
  }

  const moveTask = async (taskId: string, newStatus: WorkItem['status']) => {
    if (!employeeId) return
    const updated = await updateTask(employeeId, taskId, { status: newStatus })
    setTasks((prev) => prev.map((t) => t.task_id === taskId ? updated : t))
    if (newStatus === 'done') {
      setTimeout(async () => {
        try {
          const refreshed = (await listTasks(employeeId)).tasks
          setTasks(refreshed)
        } catch { /* ignore */ }
      }, 8000)
    }
  }

  const getUpdate = async (taskId: string) => {
    if (!employeeId) return
    const update = await getTaskStatusUpdate(employeeId, taskId)
    setStatusUpdate(update)
  }

  const todoCount = tasks.filter((t) => t.status === 'todo').length
  const inProgressCount = tasks.filter((t) => t.status === 'in_progress').length

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Task Board</h1>
          <p className="text-slate-400 text-sm">{tasks.length} tasks assigned</p>
        </div>
        <div className="flex gap-2 items-center">
          {/* Auto-work toggle */}
          <button
            onClick={toggleAutoWork}
            disabled={togglingAuto}
            title={autoWork
              ? 'Auto-work ON — PULSE works on tasks automatically. Click to pause.'
              : 'Auto-work OFF — tasks need manual moves. Click to enable.'}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all',
              autoWork
                ? 'bg-green-600/20 text-green-400 border border-green-600/30 hover:bg-green-600/30'
                : 'bg-slate-800 text-slate-500 border border-slate-700 hover:bg-slate-700',
              togglingAuto && 'opacity-50 cursor-wait'
            )}
          >
            {autoWork ? <Zap size={14} /> : <ZapOff size={14} />}
            {autoWork ? 'Auto' : 'Manual'}
          </button>
          <button onClick={refresh} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-medium transition-colors"
          >
            <Plus size={15} /> New Task
          </button>
        </div>
      </div>

      {/* Auto-work status banner */}
      {autoWork && (todoCount > 0 || inProgressCount > 0) && (
        <div className="flex items-center gap-2 px-4 py-2 bg-green-600/10 border border-green-600/20 rounded-xl text-sm text-green-400">
          <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          PULSE is autonomously working on tasks —
          {inProgressCount > 0 ? ` ${inProgressCount} in progress` : ''}
          {todoCount > 0 ? `, ${todoCount} queued` : ''}.
          Board refreshes every 15s.
        </div>
      )}
      {!autoWork && (
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/60 border border-slate-700 rounded-xl text-sm text-slate-500">
          <ZapOff size={13} />
          Auto-work is paused. Enable it to let PULSE work on tasks automatically.
        </div>
      )}

      {/* Add task form */}
      {showAdd && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 max-w-lg space-y-3 animate-slide-up">
          <input
            value={addForm.title}
            onChange={(e) => setAddForm((p) => ({ ...p, title: e.target.value }))}
            placeholder="Task title *"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <textarea
            value={addForm.description}
            onChange={(e) => setAddForm((p) => ({ ...p, description: e.target.value }))}
            placeholder="Description (the more detail, the better PULSE can work on it)…"
            rows={3}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
          />
          <div className="flex gap-3">
            <select
              value={addForm.priority}
              onChange={(e) => setAddForm((p) => ({ ...p, priority: e.target.value }))}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="low">Low priority</option>
              <option value="medium">Medium priority</option>
              <option value="high">High priority</option>
              <option value="critical">Critical</option>
            </select>
            <input
              type="date"
              value={addForm.deadline}
              onChange={(e) => setAddForm((p) => ({ ...p, deadline: e.target.value }))}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!addForm.title}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-lg text-white text-sm font-medium transition-colors"
            >
              Add Task
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 text-sm transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Kanban board */}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {STATUS_COLS.map((status) => {
          const col = tasks.filter((t) => t.status === status)
          return (
            <div key={status} className="flex-shrink-0 w-60">
              <div className="flex items-center gap-2 mb-3">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[status]}`}>
                  {STATUS_LABELS[status]}
                </span>
                <span className="text-xs text-slate-600">{col.length}</span>
              </div>
              <div className="space-y-2">
                {col.map((task) => (
                  <TaskCard
                    key={task.task_id}
                    task={task}
                    onMove={moveTask}
                    onGetUpdate={getUpdate}
                    autoWork={autoWork}
                  />
                ))}
                {col.length === 0 && (
                  <div className="h-16 border border-dashed border-slate-800 rounded-xl flex items-center justify-center">
                    <span className="text-xs text-slate-700">Empty</span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Status update modal */}
      {statusUpdate && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setStatusUpdate(null)}
        >
          <div
            className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-lg w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-semibold text-white mb-2">{statusUpdate.task_title}</h3>
            <p className="text-sm text-slate-300 leading-relaxed">{statusUpdate.message}</p>
            {statusUpdate.blockers.length > 0 && (
              <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-xs text-red-400 font-medium mb-1">Blockers</p>
                {statusUpdate.blockers.map((b, i) => (
                  <p key={i} className="text-xs text-slate-300">{b}</p>
                ))}
              </div>
            )}
            <button
              onClick={() => setStatusUpdate(null)}
              className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 text-sm"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function TaskCard({ task, onMove, onGetUpdate, autoWork }: {
  task: WorkItem
  onMove: (id: string, status: WorkItem['status']) => void
  onGetUpdate: (id: string) => void
  autoWork: boolean
}) {
  const NEXT: Partial<Record<WorkItem['status'], WorkItem['status'][]>> = {
    todo: ['in_progress', 'cancelled'],
    in_progress: ['in_review', 'blocked', 'done'],
    blocked: ['in_progress', 'cancelled'],
    in_review: ['done', 'in_progress'],
  }

  // Prefer [FILE] note for the workspace filename, then [AUTO] for preview, then ✅
  const fileNote = task.progress_notes?.find((n) => n.startsWith('[FILE]'))?.replace(/^\[FILE\]\s*/, '')
  const autoNote = task.progress_notes?.find((n) => n.startsWith('[AUTO]'))?.replace(/^\[AUTO\]\s*/, '')
  const completionNote = task.progress_notes?.find((n) => n.startsWith('✅'))?.replace(/^✅\s*/, '')
  const workPreview = autoNote || completionNote

  return (
    <div className={clsx(
      'bg-slate-900 border rounded-xl p-3 space-y-2 transition-colors group',
      task.status === 'in_progress' && autoWork
        ? 'border-blue-600/40 shadow-sm shadow-blue-600/10'
        : 'border-slate-800 hover:border-slate-700'
    )}>
      <div className="flex items-start gap-2">
        <div className={clsx('w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0', PRIORITY_DOT[task.priority])} />
        <p className="text-sm text-slate-200 leading-snug flex-1">{task.title}</p>
        {/* Pulsing dot while PULSE is actively working */}
        {task.status === 'in_progress' && autoWork && (
          <span
            className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse mt-1.5"
            title="PULSE is working on this"
          />
        )}
      </div>

      {task.deadline && (
        <p className="text-[10px] text-slate-600 pl-3.5">{task.deadline}</p>
      )}

      {/* Work output shown on done tasks */}
      {task.status === 'done' && (
        <div className="pl-3.5 mt-1 space-y-1.5">
          {fileNote && (
            <a
              href={`/workspace/${encodeURIComponent(fileNote)}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <span>📄</span>
              <span className="font-mono underline">{fileNote}</span>
            </a>
          )}
          {workPreview && (
            <p className="text-[11px] text-green-400/80 leading-relaxed border-l-2 border-green-600/30 pl-2 whitespace-pre-wrap">
              {workPreview.length > 300 ? workPreview.slice(0, 300) + '…' : workPreview}
            </p>
          )}
        </div>
      )}

      <div className="flex items-center gap-1 pl-3.5 opacity-0 group-hover:opacity-100 transition-opacity">
        {(NEXT[task.status] ?? []).map((s) => (
          <button
            key={s}
            onClick={() => onMove(task.task_id, s)}
            className="text-[10px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors"
          >
            → {s.replace('_', ' ')}
          </button>
        ))}
        <button
          onClick={() => onGetUpdate(task.task_id)}
          className="text-[10px] px-2 py-0.5 bg-blue-600/20 hover:bg-blue-600/30 rounded text-blue-400 transition-colors ml-auto"
        >
          Status
        </button>
      </div>
    </div>
  )
}
