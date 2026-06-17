import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Flame, Loader2, CheckCircle2, XCircle, Ban, MessageSquare, ArrowLeft,
} from 'lucide-react'
import clsx from 'clsx'
import { cancelTrainingJob } from '../api/train'
import { useTrainProgress } from '../hooks/useTrainProgress'

export default function TrainMonitor() {
  const { jobId } = useParams<{ jobId: string }>()
  const {
    status, progress, phase, message, events, done, error, connected,
  } = useTrainProgress(jobId ?? null)

  const isSuccess = status === 'completed'
  const isFailed = status === 'failed' || status === 'cancelled'

  const handleCancel = async () => {
    if (!jobId || !confirm('Cancel this training job?')) return
    await cancelTrainingJob(jobId).catch(() => {})
  }

  useEffect(() => {
    if (isSuccess && jobId) {
      // optional auto-navigate after short delay — user can stay to read logs
    }
  }, [isSuccess, jobId])

  if (!jobId) {
    return (
      <div className="p-6 text-slate-400">No job ID provided.</div>
    )
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in max-w-2xl">
      <div>
        <Link to="/train" className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1">
          <ArrowLeft size={12} /> Fire Studio
        </Link>
        <div className="flex items-center gap-2 mt-2">
          <Flame size={20} className="text-orange-400" />
          <h1 className="text-xl font-bold text-white">Training Fire</h1>
          {!done && (
            <span className="flex items-center gap-1 text-[10px] text-slate-500">
              <span className={clsx('w-1.5 h-1.5 rounded-full', connected ? 'bg-green-400' : 'bg-slate-600')} />
              {connected ? 'live' : 'polling'}
            </span>
          )}
        </div>
      </div>

      {/* Progress card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <StatusBadge status={status} />
          <span className="text-2xl font-bold text-white">{Math.round(progress * 100)}%</span>
        </div>

        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all duration-700',
              isSuccess ? 'bg-green-500' : isFailed ? 'bg-red-500' : 'bg-orange-500',
            )}
            style={{ width: `${Math.max(progress * 100, done ? 100 : 2)}%` }}
          />
        </div>

        <p className="text-sm text-slate-300">{message}</p>
        {phase && <p className="text-xs text-slate-500 uppercase tracking-wider">{phase}</p>}
        {error && <p className="text-sm text-red-400">{error}</p>}

        {!done && (
          <button
            onClick={handleCancel}
            className="text-xs text-slate-500 hover:text-red-400 flex items-center gap-1"
          >
            <Ban size={12} /> Cancel job
          </button>
        )}

        {isSuccess && (
          <div className="flex gap-2 pt-2">
            <Link
              to="/train/playground"
              className="flex items-center gap-2 px-4 py-2.5 bg-orange-600 hover:bg-orange-500 rounded-xl text-white text-sm font-medium"
            >
              <MessageSquare size={15} />
              Open Playground
            </Link>
            <Link
              to="/train"
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl text-slate-300 text-sm"
            >
              Back to Studio
            </Link>
          </div>
        )}
      </div>

      {/* Event log */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 mb-2">Training log</h2>
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 max-h-80 overflow-y-auto font-mono text-xs space-y-1">
          {events.length === 0 && !done && (
            <p className="text-slate-600 flex items-center gap-2">
              <Loader2 size={12} className="animate-spin" /> Waiting for events…
            </p>
          )}
          {events.map((ev, i) => (
            <div key={i} className="text-slate-400">
              <span className="text-slate-600">{new Date(ev.ts).toLocaleTimeString()}</span>
              {' '}
              <span className="text-orange-400/80">[{ev.phase}]</span>
              {' '}
              {ev.message}
              {ev.logs?.loss != null && (
                <span className="text-blue-400/80"> loss={ev.logs.loss.toFixed(4)}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'completed') {
    return (
      <span className="flex items-center gap-1.5 text-sm text-green-400">
        <CheckCircle2 size={16} /> Completed
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className="flex items-center gap-1.5 text-sm text-red-400">
        <XCircle size={16} /> Failed
      </span>
    )
  }
  if (status === 'cancelled') {
    return (
      <span className="flex items-center gap-1.5 text-sm text-slate-400">
        <Ban size={16} /> Cancelled
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1.5 text-sm text-orange-400">
      <Loader2 size={16} className="animate-spin" /> {status.replace(/_/g, ' ')}
    </span>
  )
}
