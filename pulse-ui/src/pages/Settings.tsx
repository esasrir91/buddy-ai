import { useState, useEffect } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { updateEmployee, getLLMSettings, saveLLMSettings, testLLMConnection } from '../api/pulse'
import { LLM_PROVIDERS, type LLMProvider, type LLMSettingsState } from '../types/pulse'
import {
  Settings as SettingsIcon,
  Save,
  Cpu,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Key,
} from 'lucide-react'
import clsx from 'clsx'

export default function Settings() {
  return (
    <div className="p-6 space-y-6 animate-fade-in max-w-2xl">
      <div className="flex items-center gap-3">
        <SettingsIcon size={20} className="text-slate-400" />
        <h1 className="text-xl font-bold text-white">Settings</h1>
      </div>

      <LLMSettingsCard />
      <ProfileSettingsCard />
    </div>
  )
}

// ===========================================================================
// LLM Settings card
// ===========================================================================

function LLMSettingsCard() {
  const [current, setCurrent] = useState<LLMSettingsState | null>(null)
  const [provider, setProvider] = useState<LLMProvider>('openai')
  const [modelId, setModelId] = useState('gpt-4o')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const providerMeta = LLM_PROVIDERS.find((p) => p.id === provider)!

  // Load current settings from backend
  useEffect(() => {
    getLLMSettings()
      .then((s) => {
        setCurrent(s)
        setProvider(s.provider as LLMProvider)
        setModelId(s.model_id)
        setBaseUrl(s.base_url ?? '')
      })
      .catch(() => {/* server may not be running yet */})
  }, [])

  // When provider changes, reset model to first option
  const handleProviderChange = (p: LLMProvider) => {
    setProvider(p)
    const meta = LLM_PROVIDERS.find((x) => x.id === p)
    if (meta) setModelId(meta.models[0].id)
    setApiKey('')
    setTestResult(null)
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    setError('')
    try {
      const res = await testLLMConnection({
        provider,
        model_id: modelId,
        api_key: apiKey || undefined,
        base_url: baseUrl || undefined,
      })
      setTestResult({
        success: res.success,
        message: res.success
          ? `Connected! Response: "${res.response ?? 'OK'}"`
          : res.error ?? 'Connection failed',
      })
    } catch (e) {
      setTestResult({ success: false, message: String(e) })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      await saveLLMSettings({
        provider,
        model_id: modelId,
        api_key: apiKey || undefined,
        base_url: baseUrl || undefined,
      })
      setSaved(true)
      setApiKey('')   // clear from UI after save
      setTimeout(() => setSaved(false), 3000)
      // Refresh masked state
      getLLMSettings().then(setCurrent).catch(() => {})
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
          <Cpu size={15} className="text-blue-400" />
        </div>
        <div>
          <h2 className="font-semibold text-white">AI Model &amp; API Keys</h2>
          <p className="text-xs text-slate-500 mt-0.5">Configure which LLM powers your PULSE employee.</p>
        </div>
        {current?.key_set && (
          <div className="ml-auto flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 border border-green-500/20 rounded-full">
            <CheckCircle2 size={11} className="text-green-400" />
            <span className="text-[11px] text-green-400 font-medium">Active</span>
          </div>
        )}
      </div>

      {/* Provider tabs */}
      <div>
        <label className="block text-xs text-slate-400 mb-2">Provider</label>
        <div className="flex flex-wrap gap-2">
          {LLM_PROVIDERS.map((p) => (
            <button
              key={p.id}
              onClick={() => handleProviderChange(p.id)}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                provider === p.id
                  ? 'bg-blue-600/20 border-blue-600/50 text-blue-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white hover:border-slate-600',
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Model selector */}
      <div>
        <label className="block text-xs text-slate-400 mb-1.5">Model</label>
        <select
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        >
          {providerMeta.models.map((m) => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
          <option value="__custom__">Custom model ID…</option>
        </select>
        {modelId === '__custom__' && (
          <input
            type="text"
            placeholder="Enter model ID (e.g. gpt-4o-2024-11-20)"
            onChange={(e) => setModelId(e.target.value)}
            className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        )}
      </div>

      {/* API Key */}
      {providerMeta.needs_key && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs text-slate-400 flex items-center gap-1.5">
              <Key size={11} />
              API Key
              <span className="text-slate-600">({providerMeta.env_var})</span>
            </label>
            {current?.key_set && !apiKey && (
              <span className="text-[10px] text-green-400 font-medium">Key already set</span>
            )}
          </div>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                current?.key_set
                  ? `Current: ${current.key_masked} — paste new key to rotate`
                  : `Paste your ${providerMeta.label} API key…`
              }
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
            <button
              type="button"
              onClick={() => setShowKey((s) => !s)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <p className="text-[10px] text-slate-600 mt-1">
            Stored in this server's environment for the current session.{' '}
            <a
              href={getKeyLink(provider)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-400 inline-flex items-center gap-0.5"
            >
              Get a key <ExternalLink size={9} />
            </a>
          </p>
        </div>
      )}

      {/* Base URL (Ollama / custom) */}
      {(provider === 'ollama' || providerMeta.id === 'openai') && (
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">
            Base URL
            {provider === 'ollama' ? ' (default: http://localhost:11434)' : ' (leave blank for default)'}
          </label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={provider === 'ollama' ? 'http://localhost:11434' : 'https://api.openai.com/v1'}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      )}

      {/* Test result banner */}
      {testResult && (
        <div
          className={clsx(
            'flex items-start gap-2 p-3 rounded-lg text-sm border',
            testResult.success
              ? 'bg-green-500/10 border-green-500/20 text-green-300'
              : 'bg-red-500/10 border-red-500/20 text-red-300',
          )}
        >
          {testResult.success
            ? <CheckCircle2 size={15} className="flex-shrink-0 mt-0.5" />
            : <XCircle size={15} className="flex-shrink-0 mt-0.5" />}
          <span className="leading-relaxed">{testResult.message}</span>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">{error}</p>
      )}

      {/* Buttons */}
      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={handleTest}
          disabled={testing || saving}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded-xl text-slate-200 text-sm font-medium transition-colors"
        >
          {testing ? <Loader2 size={14} className="animate-spin" /> : <Cpu size={14} />}
          {testing ? 'Testing…' : 'Test Connection'}
        </button>

        <button
          onClick={handleSave}
          disabled={saving || testing}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium transition-colors"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {saving ? 'Saving…' : saved ? 'Saved!' : 'Save & Apply'}
        </button>
      </div>

      {/* Environment variable hint */}
      {providerMeta.needs_key && (
        <div className="p-3 bg-slate-800/60 border border-slate-700/50 rounded-xl text-xs text-slate-500">
          <p className="font-medium text-slate-400 mb-1">Alternative: set via environment</p>
          <code className="text-slate-300">{providerMeta.env_var}=sk-...</code>
          <span className="mx-2 text-slate-700">·</span>
          <code className="text-slate-300">buddy pulse start</code>
        </div>
      )}
    </div>
  )
}

function getKeyLink(provider: LLMProvider): string {
  const links: Record<LLMProvider, string> = {
    openai:    'https://platform.openai.com/api-keys',
    anthropic: 'https://console.anthropic.com/settings/keys',
    google:    'https://aistudio.google.com/apikey',
    groq:      'https://console.groq.com/keys',
    ollama:    'https://ollama.com/download',
  }
  return links[provider]
}

// ===========================================================================
// Profile settings card
// ===========================================================================

function ProfileSettingsCard() {
  const { employeeId, employee } = usePulseStore()
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState({
    full_name: employee?.profile.full_name ?? '',
    role:      employee?.profile.role ?? '',
    bio:       employee?.profile.bio ?? '',
    email:     employee?.profile.email ?? '',
    slack_handle: employee?.profile.slack_handle ?? '',
    timezone:  employee?.profile.timezone ?? 'UTC',
  })

  const handleSave = async () => {
    if (!employeeId) return
    setSaving(true)
    try {
      await updateEmployee(employeeId, form)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally { setSaving(false) }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
      <h2 className="font-semibold text-white">Employee Profile</h2>
      <Field label="Full Name" value={form.full_name} onChange={(v) => setForm((p) => ({ ...p, full_name: v }))} />
      <Field label="Role" value={form.role} onChange={(v) => setForm((p) => ({ ...p, role: v }))} />
      <Field label="Bio" value={form.bio} onChange={(v) => setForm((p) => ({ ...p, bio: v }))} textarea />
      <Field label="Email" value={form.email} onChange={(v) => setForm((p) => ({ ...p, email: v }))} placeholder="name@company.com" />
      <Field label="Slack Handle" value={form.slack_handle} onChange={(v) => setForm((p) => ({ ...p, slack_handle: v }))} placeholder="@name" />
      <Field label="Timezone" value={form.timezone} onChange={(v) => setForm((p) => ({ ...p, timezone: v }))} placeholder="Asia/Kolkata" />

      <button
        onClick={handleSave}
        disabled={saving}
        className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded-xl text-white text-sm font-medium transition-colors"
      >
        <Save size={14} />
        {saving ? 'Saving…' : saved ? 'Saved!' : 'Save Changes'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared field component
// ---------------------------------------------------------------------------

function Field({
  label, value, onChange, placeholder, textarea = false,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  textarea?: boolean
}) {
  const cls =
    'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors'
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1.5">{label}</label>
      {textarea ? (
        <textarea
          rows={3}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`${cls} resize-none`}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={cls}
        />
      )}
    </div>
  )
}
