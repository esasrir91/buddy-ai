import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Cpu, ArrowRight, ArrowLeft, Check } from 'lucide-react'
import { createEmployee, getEmployee } from '../api/pulse'
import { usePulseStore } from '../hooks/usePulseStore'
import clsx from 'clsx'

const STEPS = ['Identity', 'Company & Role', 'Skills', 'Ready!']

export default function OnboardingWizard() {
  const navigate = useNavigate()
  const setEmployee = usePulseStore((s) => s.setEmployee)
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    full_name: '',
    role: '',
    department: 'Engineering',
    team: '',
    company_name: '',
    reporting_to: '',
    timezone: 'UTC',
    bio: '',
    skills_raw: '',
    model_id: 'gpt-4o',
    model_provider: 'openai',
  })

  const update = (k: keyof typeof form, v: string) => setForm((p) => ({ ...p, [k]: v }))

  const handleCreate = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await createEmployee({
        full_name: form.full_name,
        role: form.role,
        department: form.department,
        skills: form.skills_raw.split(',').map((s) => s.trim()).filter(Boolean),
        timezone: form.timezone,
        reporting_to: form.reporting_to || undefined,
        company_name: form.company_name || undefined,
        bio: form.bio || undefined,
        model_id: form.model_id,
        model_provider: form.model_provider,
      })
      const emp = await getEmployee(res.employee_id)
      setEmployee(res.employee_id, emp)
      navigate('/dashboard')
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-950">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center mx-auto mb-4 pulse-dot">
            <Cpu size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create Your PULSE Employee</h1>
          <p className="text-slate-400 mt-1 text-sm">The heartbeat of your team starts here.</p>
        </div>

        {/* Steps */}
        <div className="flex items-center justify-between mb-8">
          {STEPS.map((label, i) => (
            <div key={i} className="flex-1 flex items-center">
              <div className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors',
                i < step ? 'bg-green-500 text-white'
                  : i === step ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-500',
              )}>
                {i < step ? <Check size={12} /> : i + 1}
              </div>
              <span className={clsx(
                'ml-1.5 text-xs hidden sm:block',
                i === step ? 'text-white' : 'text-slate-500',
              )}>
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={clsx(
                  'flex-1 h-px mx-2',
                  i < step ? 'bg-green-500' : 'bg-slate-800',
                )} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          {step === 0 && (
            <>
              <h2 className="text-lg font-semibold text-white">Identity</h2>
              <Field label="Full Name *" value={form.full_name} onChange={(v) => update('full_name', v)} placeholder="e.g. Priya Sharma" />
              <Field label="Timezone" value={form.timezone} onChange={(v) => update('timezone', v)} placeholder="e.g. Asia/Kolkata" />
            </>
          )}
          {step === 1 && (
            <>
              <h2 className="text-lg font-semibold text-white">Company & Role</h2>
              <Field label="Job Role *" value={form.role} onChange={(v) => update('role', v)} placeholder="e.g. Senior Backend Engineer" />
              <Field label="Department" value={form.department} onChange={(v) => update('department', v)} placeholder="Engineering" />
              <Field label="Team" value={form.team} onChange={(v) => update('team', v)} placeholder="e.g. Payments Platform" />
              <Field label="Company Name" value={form.company_name} onChange={(v) => update('company_name', v)} placeholder="e.g. Acme Corp" />
              <Field label="Reports To" value={form.reporting_to} onChange={(v) => update('reporting_to', v)} placeholder="e.g. Arjun Nair" />
            </>
          )}
          {step === 2 && (
            <>
              <h2 className="text-lg font-semibold text-white">Skills & Model</h2>
              <Field
                label="Skills (comma-separated)"
                value={form.skills_raw}
                onChange={(v) => update('skills_raw', v)}
                placeholder="Python, FastAPI, PostgreSQL, Redis"
              />
              <Field label="Bio" value={form.bio} onChange={(v) => update('bio', v)} placeholder="Short professional bio..." textarea />
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">AI Model</label>
                <select
                  value={form.model_id}
                  onChange={(e) => update('model_id', e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="gpt-4o">GPT-4o (OpenAI)</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo (OpenAI)</option>
                  <option value="claude-opus-4-5">Claude Opus (Anthropic)</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro (Google)</option>
                </select>
              </div>
            </>
          )}
          {step === 3 && (
            <div className="text-center py-4">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mx-auto mb-4 text-white font-bold text-2xl">
                {form.full_name.charAt(0) || '?'}
              </div>
              <h2 className="text-xl font-bold text-white mb-1">{form.full_name}</h2>
              <p className="text-slate-400 text-sm">{form.role}</p>
              {form.company_name && <p className="text-slate-500 text-xs mt-1">at {form.company_name}</p>}
              <p className="text-slate-600 text-xs mt-3">
                {form.skills_raw ? `Skills: ${form.skills_raw}` : 'No skills listed yet'}
              </p>
              {error && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
                  {error}
                </div>
              )}
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 pt-2">
            {step > 0 && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm transition-colors"
              >
                <ArrowLeft size={14} /> Back
              </button>
            )}
            <button
              onClick={step < STEPS.length - 1 ? () => setStep((s) => s + 1) : handleCreate}
              disabled={loading || (step === 0 && !form.full_name) || (step === 1 && !form.role)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors"
            >
              {loading ? 'Creating…' : step < STEPS.length - 1 ? (
                <><span>Next</span><ArrowRight size={14} /></>
              ) : (
                <><span>Launch PULSE</span><Cpu size={14} /></>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({
  label, value, onChange, placeholder, textarea = false,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  textarea?: boolean
}) {
  const cls = 'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors'
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1.5">{label}</label>
      {textarea ? (
        <textarea rows={3} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={`${cls} resize-none`} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={cls} />
      )}
    </div>
  )
}
