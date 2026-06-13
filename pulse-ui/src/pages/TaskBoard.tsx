import { useState, useEffect } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { assignTask, listTasks, updateTask, getTaskStatusUpdate } from '../api/pulse'
import type { WorkItem, StatusUpdate } from '../types/pulse'
import { Plus, RefreshCw } from 'lucide-react'
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

  const refresh = async () => {
    if (!employeeId) return
    setLoading(true)
    try { setTasks((await listTasks(employeeId)).tasks) }
    finally { setLoading(false) }
  }

  useEffect(() => { refresh() }, [employeeId])

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
  }

  const getUpdate = async (taskId: string) => {
    if (!employeeId) return
    const update = await getTaskStatusUpdate(employeeId, taskId)
    setStatusUpdate(update)
  }

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Task Board</h1>
          <p className="text-slate-400 text-sm">{tasks.length} tasks assigned</p>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-medium transition-colors">
            <Plus size={15} /> New Task
          </button>
        </div>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 max-w-lg space-y-3 animate-slide-up">
          <input value={addForm.title} onChange={(e) => setAddForm((p) => ({ ...p, title: e.target.value }))} placeholder="Task title *"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500" />
          <textarea value={addForm.description} onChange={(e) => setAddForm((p) => ({ ...p, description: e.target.value }))} placeholder="Description…" rows={2}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none" />
          <div className="flex gap-3">
            <select value={addForm.priority} onChange={(e) => setAddForm((p) => ({ ...p, priority: e.target.value }))}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
              <option value="low">Low priority</option>
              <option value="medium">Medium priority</option>
              <option value="high">High priority</option>
              <option value="critical">Critical</option>
            </select>
            <input type="date" value={addForm.deadline} onChange={(e) => setAddForm((p) => ({ ...p, deadline: e.target.value }))}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} disabled={!addForm.title}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-lg text-white text-sm font-medium transition-colors">
              Add Task
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 text-sm transition-colors">
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
                  <TaskCard key={task.task_id} task={task} onMove={moveTask} onGetUpdate={getUpdate} />
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setStatusUpdate(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-white mb-2">{statusUpdate.task_title}</h3>
            <p className="text-sm text-slate-300 leading-relaxed">{statusUpdate.message}</p>
            {statusUpdate.blockers.length > 0 && (
              <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-xs text-red-400 font-medium mb-1">Blockers</p>
                {statusUpdate.blockers.map((b, i) => <p key={i} className="text-xs text-slate-300">{b}</p>)}
              </div>
            )}
            <button onClick={() => setStatusUpdate(null)} className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 text-sm">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}

function TaskCard({ task, onMove, onGetUpdate }: {
  task: WorkItem
  onMove: (id: string, status: WorkItem['status']) => void
  onGetUpdate: (id: string) => void
}) {
  const NEXT: Partial<Record<WorkItem['status'], WorkItem['status'][]>> = {
    todo: ['in_progress', 'cancelled'],
    in_progress: ['in_review', 'blocked', 'done'],
    blocked: ['in_progress', 'cancelled'],
    in_review: ['done', 'in_progress'],
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2 hover:border-slate-700 transition-colors group">
      <div className="flex items-start gap-2">
        <div className={clsx('w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0', PRIORITY_DOT[task.priority])} />
        <p className="text-sm text-slate-200 leading-snug">{task.title}</p>
      </div>
      {task.deadline && <p className="text-[10px] text-slate-600 pl-3.5">{task.deadline}</p>}
      <div className="flex items-center gap-1 pl-3.5 opacity-0 group-hover:opacity-100 transition-opacity">
        {(NEXT[task.status] ?? []).map((s) => (
          <button key={s} onClick={() => onMove(task.task_id, s)}
            className="text-[10px] px-2 py-0.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-400 hover:text-white transition-colors">
            → {s.replace('_', ' ')}
          </button>
        ))}
        <button onClick={() => onGetUpdate(task.task_id)}
          className="text-[10px] px-2 py-0.5 bg-blue-600/20 hover:bg-blue-600/30 rounded text-blue-400 transition-colors ml-auto">
          Status
        </button>
      </div>
    </div>
  )
}
