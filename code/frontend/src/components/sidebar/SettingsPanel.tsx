import React, { useEffect, useState } from 'react'
import { getSettings, updateSettings, getModels, getRules, setRules } from '../../api'
import { useStore } from '../../store'

export default function SettingsPanel() {
  const { theme, setTheme } = useStore()
  const [settings, setSettings] = useState<Record<string, any>>({})
  const [providers, setProviders] = useState<Record<string, string>>({})
  const [models, setModels] = useState<any[]>([])
  const [rules, setRulesState] = useState('')
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState('')
  const [tab, setTab] = useState<'model' | 'keys' | 'rules' | 'agent'>('model')

  useEffect(() => {
    getSettings().then(({ settings: s, providers: p }) => {
      setSettings(s); setProviders(p)
    }).catch(() => {})
    getModels().then(ms => setModels(ms as any[])).catch(() => {})
    getRules().then(r => setRulesState(r.content ?? '')).catch(() => {})
  }, [])

  const save = async (patch: Record<string, any>) => {
    setLoading(true)
    try {
      await updateSettings(patch)
      setSaved('Saved'); setTimeout(() => setSaved(''), 2000)
    } finally { setLoading(false) }
  }

  return (
    <>
      <div className="sidebar__header"><span>Settings</span></div>
      <div className="sidebar__body" style={{ padding: '0 0 60px' }}>
        <div style={{ display: 'flex', gap: 2, padding: '6px 8px', borderBottom: '1px solid var(--border)' }}>
          {(['model', 'keys', 'rules', 'agent'] as const).map(t => (
            <button key={t} className={`btn btn--xs${tab === t ? ' btn--primary' : ' btn--ghost'}`} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>

        <div style={{ padding: '12px 12px' }}>
          {tab === 'model' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="field">
                <label>Model ID</label>
                <input
                  className="input" value={settings.model_id ?? ''}
                  onChange={e => setSettings(s => ({ ...s, model_id: e.target.value }))}
                />
              </div>
              <div className="field">
                <label>Max tool calls</label>
                <input
                  className="input" type="number"
                  value={settings.max_tool_calls ?? 50}
                  onChange={e => setSettings(s => ({ ...s, max_tool_calls: +e.target.value }))}
                />
              </div>
              <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <label style={{ marginBottom: 0 }}>Enable shell</label>
                <input type="checkbox" checked={settings.enable_shell ?? true}
                  onChange={e => setSettings(s => ({ ...s, enable_shell: e.target.checked }))}
                />
              </div>
              <button className="btn btn--primary btn--sm" onClick={() => save(settings)} disabled={loading}>
                {loading ? '…' : 'Save'}
              </button>
            </div>
          )}

          {tab === 'keys' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {Object.entries(providers).map(([prov, envKey]) => (
                <div className="field" key={prov}>
                  <label>{prov}</label>
                  <input
                    className="input input--mono" type="password"
                    placeholder={`${envKey}…`}
                    value={(settings.api_keys ?? {})[prov] ?? ''}
                    onChange={e => setSettings(s => ({ ...s, api_keys: { ...(s.api_keys ?? {}), [prov]: e.target.value } }))}
                  />
                </div>
              ))}
              <button className="btn btn--primary btn--sm" onClick={() => save({ api_keys: settings.api_keys })} disabled={loading}>
                {loading ? '…' : 'Save keys'}
              </button>
            </div>
          )}

          {tab === 'rules' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <p style={{ fontSize: 12, color: 'var(--text-dim)', lineHeight: 1.5 }}>Rules are injected into every chat message. Supports Markdown.</p>
              <textarea
                className="input input--mono"
                style={{ minHeight: 200, resize: 'vertical', fontSize: 12 }}
                value={rules}
                onChange={e => setRulesState(e.target.value)}
                placeholder="You are Aura, a helpful coding assistant…"
              />
              <button className="btn btn--primary btn--sm" onClick={() => setRules(rules).then(() => { setSaved('Saved'); setTimeout(() => setSaved(''), 2000) })} disabled={loading}>
                {loading ? '…' : 'Save rules'}
              </button>
            </div>
          )}

          {tab === 'agent' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="field">
                <label>System instructions</label>
                <textarea
                  className="input input--mono"
                  style={{ minHeight: 120, resize: 'vertical', fontSize: 12 }}
                  value={settings.instructions ?? ''}
                  onChange={e => setSettings(s => ({ ...s, instructions: e.target.value }))}
                  placeholder="Additional system instructions…"
                />
              </div>
              <div className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <label style={{ marginBottom: 0 }}>Reasoning</label>
                <input type="checkbox" checked={settings.reasoning ?? false}
                  onChange={e => setSettings(s => ({ ...s, reasoning: e.target.checked }))}
                />
              </div>
              <button className="btn btn--primary btn--sm" onClick={() => save(settings)} disabled={loading}>
                {loading ? '…' : 'Save'}
              </button>
            </div>
          )}

          {saved && <div style={{ marginTop: 8, color: 'var(--ok)', fontSize: 12 }}>✓ {saved}</div>}
        </div>

        {/* theme toggle */}
        <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>Theme</span>
            <button className="btn btn--sm btn--ghost" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
