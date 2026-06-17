import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Flame, Upload, ChevronRight, ChevronLeft, Loader2,
  FileText, Settings2, Rocket, AlertTriangle, FolderOpen,
} from 'lucide-react'
import clsx from 'clsx'
import {
  getAvailableBaseModels,
  getSystemInfo,
  previewDataset,
  startTrainingJob,
  uploadDataset,
} from '../api/train'
import type { BaseModelInfo, DatasetPreview, SystemInfo } from '../types/train'

const STEPS = ['Dataset', 'Base model', 'Settings', 'Launch'] as const
const DEFAULT_NAME = 'fire'

export default function TrainWizard() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState(0)
  const [system, setSystem] = useState<SystemInfo | null>(null)
  const [baseModels, setBaseModels] = useState<BaseModelInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Step 1 — dataset
  const [files, setFiles] = useState<File[]>([])
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [preview, setPreview] = useState<DatasetPreview | null>(null)
  const [uploading, setUploading] = useState(false)

  // Step 2 — model
  const [baseModel, setBaseModel] = useState('distilgpt2')
  const [localOnly, setLocalOnly] = useState(true)

  // Step 3 — settings
  const [name, setName] = useState(DEFAULT_NAME)
  const [description, setDescription] = useState('Fire — free local language model')
  const [epochs, setEpochs] = useState(3)
  const [batchSize, setBatchSize] = useState(4)
  const [learningRate, setLearningRate] = useState('5e-5')
  const [maxLength, setMaxLength] = useState(512)
  const [force, setForce] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    Promise.all([getSystemInfo(), getAvailableBaseModels()])
      .then(([sys, models]) => {
        setSystem(sys)
        setBaseModels(models.local_free)
        setBaseModel(models.default)
      })
      .catch((e) => setError(String(e)))
  }, [])

  const handleFiles = (list: FileList | null) => {
    if (!list?.length) return
    setFiles(Array.from(list))
    setDatasetId(null)
    setPreview(null)
  }

  const handleUpload = async () => {
    if (!files.length) return
    setUploading(true)
    setError('')
    try {
      const res = await uploadDataset(files)
      setDatasetId(res.dataset_id)
      const prev = await previewDataset(res.dataset_id)
      setPreview(prev)
      if (!prev.ready) throw new Error('No readable text found in uploaded files')
    } catch (e) {
      setError(String(e))
    } finally {
      setUploading(false)
    }
  }

  const handleLaunch = async () => {
    if (!datasetId) return
    setLoading(true)
    setError('')
    try {
      const { job } = await startTrainingJob({
        name: name.trim(),
        dataset_id: datasetId,
        base_model: baseModel,
        description,
        epochs,
        batch_size: batchSize,
        learning_rate: parseFloat(learningRate),
        max_length: maxLength,
        force,
      })
      navigate(`/train/jobs/${job.id}`)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const canNext = () => {
    if (step === 0) return preview?.ready === true
    if (step === 1) return !!baseModel
    if (step === 2) return name.trim().length > 0
    return true
  }

  const displayedModels = localOnly
    ? baseModels
    : baseModels // gated hidden when localOnly — keep simple

  return (
    <div className="p-6 space-y-6 animate-fade-in max-w-2xl">
      <div>
        <Link to="/train" className="text-xs text-slate-500 hover:text-slate-300">← Fire Studio</Link>
        <div className="flex items-center gap-2 mt-2">
          <Flame size={20} className="text-orange-400" />
          <h1 className="text-xl font-bold text-white">Train Fire</h1>
        </div>
        <p className="text-slate-400 text-sm mt-0.5">Fine-tune a free local model on your data.</p>
      </div>

      {/* Step indicator */}
      <div className="flex gap-1">
        {STEPS.map((label, i) => (
          <div key={label} className="flex-1">
            <div
              className={clsx(
                'h-1 rounded-full transition-colors',
                i <= step ? 'bg-orange-500' : 'bg-slate-800',
              )}
            />
            <p className={clsx('text-[10px] mt-1', i === step ? 'text-orange-400' : 'text-slate-600')}>
              {label}
            </p>
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5">
        {/* Step 0: Dataset */}
        {step === 0 && (
          <>
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Upload size={16} className="text-orange-400" /> Upload training data
            </h2>
            <p className="text-sm text-slate-400">
              PDF, TXT, DOCX, CSV, MD, and more. Upload files or an entire folder.
            </p>

            <input
              ref={fileRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <input
              id="folder-upload"
              type="file"
              multiple
              // @ts-expect-error webkitdirectory is non-standard but widely supported
              webkitdirectory=""
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />

            <div className="flex gap-2">
              <button
                onClick={() => fileRef.current?.click()}
                className="flex-1 flex items-center justify-center gap-2 py-8 border-2 border-dashed border-slate-700 hover:border-orange-500/50 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
              >
                <FileText size={18} />
                Select files
              </button>
              <button
                onClick={() => document.getElementById('folder-upload')?.click()}
                className="flex-1 flex items-center justify-center gap-2 py-8 border-2 border-dashed border-slate-700 hover:border-orange-500/50 rounded-xl text-slate-400 hover:text-slate-200 transition-colors"
              >
                <FolderOpen size={18} />
                Select folder
              </button>
            </div>

            {files.length > 0 && (
              <div className="text-sm text-slate-400">
                {files.length} file{files.length !== 1 ? 's' : ''} selected
                {!datasetId && (
                  <button
                    onClick={handleUpload}
                    disabled={uploading}
                    className="ml-3 text-orange-400 hover:text-orange-300 font-medium"
                  >
                    {uploading ? 'Processing…' : 'Process & preview →'}
                  </button>
                )}
              </div>
            )}

            {uploading && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 size={16} className="animate-spin" /> Reading files…
              </div>
            )}

            {preview?.ready && (
              <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl space-y-2">
                <p className="text-sm text-green-400 font-medium">Dataset ready</p>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                  <span>{String(preview.stats.processed_files ?? 0)} files processed</span>
                  <span>{preview.sample_count} text chunks</span>
                  <span>{Number(preview.stats.total_characters ?? 0).toLocaleString()} characters</span>
                </div>
                {preview.preview[0] && (
                  <p className="text-xs text-slate-500 font-mono line-clamp-2 mt-2">
                    Sample: {preview.preview[0]}
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {/* Step 1: Base model */}
        {step === 1 && (
          <>
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Flame size={16} className="text-orange-400" /> Choose base model
            </h2>
            <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={localOnly}
                onChange={(e) => setLocalOnly(e.target.checked)}
                className="rounded border-slate-600"
              />
              Local & free only (no HuggingFace gate, no API cost)
            </label>
            <div className="space-y-2">
              {displayedModels.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setBaseModel(m.id)}
                  className={clsx(
                    'w-full text-left p-3 rounded-xl border transition-colors',
                    baseModel === m.id
                      ? 'border-orange-500/50 bg-orange-500/10'
                      : 'border-slate-800 hover:border-slate-700',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">{m.id}</span>
                    {m.recommended && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">
                        recommended
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 font-mono">{m.hf_id}</p>
                </button>
              ))}
            </div>
            {system && !system.cuda_available && baseModel === 'phi-2' && (
              <p className="text-xs text-amber-400">
                No GPU detected — phi-2 will train on CPU (slower). Consider distilgpt2 for faster training.
              </p>
            )}
          </>
        )}

        {/* Step 2: Settings */}
        {step === 2 && (
          <>
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Settings2 size={16} className="text-orange-400" /> Training settings
            </h2>
            <Field label="Model name" value={name} onChange={setName} placeholder="fire" />
            <Field label="Description" value={description} onChange={setDescription} />
            <div className="grid grid-cols-2 gap-3">
              <Field label="Epochs" value={String(epochs)} onChange={(v) => setEpochs(Number(v) || 3)} type="number" />
              <Field label="Batch size" value={String(batchSize)} onChange={(v) => setBatchSize(Number(v) || 4)} type="number" />
            </div>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              {showAdvanced ? 'Hide' : 'Show'} advanced settings
            </button>
            {showAdvanced && (
              <div className="space-y-3 pt-1">
                <Field label="Learning rate" value={learningRate} onChange={setLearningRate} />
                <Field label="Max sequence length" value={String(maxLength)} onChange={(v) => setMaxLength(Number(v) || 512)} type="number" />
                <label className="flex items-center gap-2 text-sm text-slate-400">
                  <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
                  Overwrite existing model with same name
                </label>
              </div>
            )}
          </>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <>
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Rocket size={16} className="text-orange-400" /> Review & launch
            </h2>
            <dl className="space-y-2 text-sm">
              {[
                ['Model name', name],
                ['Base model', baseModel],
                ['Epochs', String(epochs)],
                ['Device', system?.cuda_available ? 'GPU' : 'CPU'],
                ['Cost', 'Free — runs locally'],
                ['Data chunks', preview ? String(preview.sample_count) : '—'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-1.5 border-b border-slate-800/50">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="text-slate-200 font-medium">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="text-xs text-slate-500">
              Training may take 5–30+ minutes depending on data size and hardware. You can leave this page open to watch progress.
            </p>
          </>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30"
        >
          <ChevronLeft size={16} /> Back
        </button>
        {step < STEPS.length - 1 ? (
          <button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canNext()}
            className="flex items-center gap-1 px-5 py-2.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium"
          >
            Next <ChevronRight size={16} />
          </button>
        ) : (
          <button
            onClick={handleLaunch}
            disabled={loading || !datasetId}
            className="flex items-center gap-2 px-5 py-2.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Rocket size={16} />}
            {loading ? 'Starting…' : 'Launch training'}
          </button>
        )}
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
      />
    </div>
  )
}
