import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Flame, Plus, Cpu, HardDrive, Loader2, Trash2, MessageSquare,
  AlertTriangle, CheckCircle2, Zap,
} from 'lucide-react'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'
import { deleteTrainedModel, getSystemInfo, getTrainedModels, listTrainingJobs } from '../api/train'
import type { SystemInfo, TrainedModel, TrainingJob } from '../types/train'

export default function TrainDashboard() {
  const [system, setSystem] = useState<SystemInfo | null>(null)
  const [models, setModels] = useState<TrainedModel[]>([])
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [sys, m, j] = await Promise.all([
        getSystemInfo(),
        getTrainedModels(),
        listTrainingJobs(),
      ])
      setSystem(sys)
      setModels(m.models)
      setJobs(j.jobs)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete model "${name}"? This cannot be undone.`)) return
    setDeleting(name)
    try {
      await deleteTrainedModel(name)
      await load()
    } catch (e) {
      setError(String(e))
    } finally {
      setDeleting(null)
    }
  }

  const fireModel = models.find((m) => m.name === 'fire')
  const activeJob = jobs.find((j) => !['completed', 'failed', 'cancelled'].includes(j.status))

  return (
    <div className="p-6 space-y-6 animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Flame size={22} className="text-orange-400" />
            <h1 className="text-xl font-bold text-white">Fire</h1>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
              Local · Free
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Train and run your own language model — no API keys, no per-message cost.
          </p>
        </div>
        <Link
          to="/train/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-orange-600 hover:bg-orange-500 rounded-xl text-white text-sm font-medium transition-colors shrink-0"
        >
          <Plus size={16} />
          Train Fire
        </Link>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* System status */}
      {system && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <StatusCard
            icon={Cpu}
            label="Device"
            value={system.cuda_available ? `GPU — ${system.cuda_device}` : 'CPU (local)'}
            ok={system.training_available}
          />
          <StatusCard
            icon={HardDrive}
            label="Training"
            value={system.training_available ? 'Ready' : 'Deps missing'}
            ok={system.training_available}
            hint={!system.training_available ? system.install_hint : undefined}
          />
          <StatusCard
            icon={Zap}
            label="Cost"
            value="Free — runs offline"
            ok
          />
        </div>
      )}

      {/* Active job banner */}
      {activeJob && (
        <Link
          to={`/train/jobs/${activeJob.id}`}
          className="block p-4 bg-orange-500/10 border border-orange-500/30 rounded-2xl hover:bg-orange-500/15 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-300">Training in progress</p>
              <p className="text-xs text-slate-400 mt-0.5">{activeJob.message}</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold text-white">{Math.round(activeJob.progress * 100)}%</p>
              <p className="text-[10px] text-slate-500 uppercase">{activeJob.status}</p>
            </div>
          </div>
          <div className="mt-3 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-orange-500 rounded-full transition-all duration-500"
              style={{ width: `${activeJob.progress * 100}%` }}
            />
          </div>
        </Link>
      )}

      {/* Fire model highlight */}
      {fireModel ? (
        <div className="bg-slate-900 border border-orange-500/30 rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center">
                <Flame size={20} className="text-white" />
              </div>
              <div>
                <p className="font-semibold text-white">fire</p>
                <p className="text-xs text-slate-400">{fireModel.description ?? 'Your local model'}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/train/playground"
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm text-slate-200 transition-colors"
              >
                <MessageSquare size={14} />
                Playground
              </Link>
              <CheckCircle2 size={18} className="text-green-400" />
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            {fireModel.base_model && <span>Base: {fireModel.base_model}</span>}
            {fireModel.created_at && <span>Created: {new Date(fireModel.created_at).toLocaleDateString()}</span>}
            {fireModel.total_characters != null && (
              <span>{fireModel.total_characters.toLocaleString()} chars trained</span>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
          <Flame size={32} className="text-slate-600 mx-auto mb-3" />
          <p className="text-slate-300 font-medium">Fire isn&apos;t trained yet</p>
          <p className="text-sm text-slate-500 mt-1 mb-4">Upload your documents and train your free local model.</p>
          <Link
            to="/train/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-600 hover:bg-orange-500 rounded-xl text-white text-sm font-medium"
          >
            <Plus size={15} />
            Start training
          </Link>
        </div>
      )}

      {/* All models */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">All trained models</h2>
        {loading ? (
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Loader2 size={16} className="animate-spin" /> Loading…
          </div>
        ) : models.length === 0 ? (
          <p className="text-sm text-slate-600">No models yet.</p>
        ) : (
          <div className="space-y-2">
            {models.map((m) => (
              <div
                key={m.name}
                className="flex items-center justify-between p-4 bg-slate-900 border border-slate-800 rounded-xl"
              >
                <div>
                  <p className="text-sm font-medium text-white">{m.name}</p>
                  <p className="text-xs text-slate-500">{m.description ?? 'No description'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/train/playground?model=${encodeURIComponent(m.name)}`}
                    className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                  >
                    Test
                  </Link>
                  <button
                    onClick={() => handleDelete(m.name)}
                    disabled={deleting === m.name}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                  >
                    {deleting === m.name ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatusCard({
  icon: Icon,
  label,
  value,
  ok,
  hint,
}: {
  icon: LucideIcon
  label: string
  value: string
  ok: boolean
  hint?: string
}) {
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className={clsx(ok ? 'text-blue-400' : 'text-amber-400')} />
        <span className="text-[10px] uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      <p className="text-sm font-medium text-white truncate" title={value}>{value}</p>
      {hint && <p className="text-[10px] text-slate-500 mt-1">{hint}</p>}
    </div>
  )
}
