import React, { useEffect, useMemo, useState } from 'react'
import { useStore } from '../store'
import { saveProfile, setWorkspace as apiSetWorkspace, getWorkspace, updateSettings } from '../api'
import { ORG_TEAMS, teamMeta } from '../teams'
import type { TeamRole } from '../types'
import AuraLogo from './AuraLogo'

type Step = 'welcome' | 'identity' | 'team' | 'focus' | 'workspace' | 'ready'

const FOCUS_OPTIONS: Record<TeamRole, string[]> = {
  engineering: ['Feature delivery', 'Bug fixing', 'Code review', 'Architecture', 'Refactoring'],
  testing: ['Test generation', 'Test review', 'Test execution', 'Regression', 'Automation', 'QA reports'],
  platform: ['CI/CD', 'Infrastructure', 'Observability', 'Releases', 'Incidents'],
  hardware: ['Bring-up', 'Firmware', 'Protocol debug', 'HIL validation', 'Drivers'],
  security: ['Threat modeling', 'Secure review', 'Hardening', 'Dependencies'],
  product: ['PRDs', 'User stories', 'Prioritization', 'Release notes'],
  data: ['Pipelines', 'Evaluation', 'Analytics', 'Data quality'],
  general: ['Planning', 'Cross-team handoff', 'Status updates', 'Research'],
}

const STEPS: Step[] = ['welcome', 'identity', 'team', 'focus', 'workspace', 'ready']

export default function Onboarding() {
  const {
    setOrgProfile, setTeamRole, setWorkspace, setSidebarView, setAgentPaneVisible,
  } = useStore()

  const [step, setStep] = useState<Step>('welcome')
  const [orgName, setOrgName] = useState('')
  const [userName, setUserName] = useState('')
  const [userTitle, setUserTitle] = useState('')
  const [team, setTeam] = useState<TeamRole>('testing')
  const [focus, setFocus] = useState<string[]>(['Test generation', 'Test execution'])
  const [folder, setFolder] = useState('')
  const [saving, setSaving] = useState(false)
  const [entered, setEntered] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    const t = requestAnimationFrame(() => setEntered(true))
    return () => cancelAnimationFrame(t)
  }, [])

  useEffect(() => {
    setFocus(FOCUS_OPTIONS[team].slice(0, 2))
  }, [team])

  const stepIndex = STEPS.indexOf(step)
  const meta = teamMeta(team)
  const canNext = useMemo(() => {
    if (step === 'identity') return orgName.trim().length >= 2 && userName.trim().length >= 1
    if (step === 'team') return !!team
    return true
  }, [step, orgName, userName, team])

  const next = () => {
    if (!canNext) return
    const i = STEPS.indexOf(step)
    if (i < STEPS.length - 1) setStep(STEPS[i + 1])
  }
  const back = () => {
    const i = STEPS.indexOf(step)
    if (i > 0) setStep(STEPS[i - 1])
  }

  const toggleFocus = (item: string) => {
    setFocus(prev => prev.includes(item) ? prev.filter(x => x !== item) : [...prev, item].slice(0, 6))
  }

  const finish = async () => {
    setSaving(true)
    setErr('')
    try {
      if (folder.trim()) {
        await apiSetWorkspace(folder.trim())
        const { path } = await getWorkspace()
        setWorkspace(path)
      }
      await saveProfile({
        org_name: orgName.trim(),
        user_name: userName.trim(),
        user_title: userTitle.trim(),
        team_role: team,
        focus_areas: focus,
        onboarding_complete: true,
      })
      await updateSettings({ team_role: team }).catch(() => {})
      setTeamRole(team)
      setOrgProfile({
        orgName: orgName.trim(),
        userName: userName.trim(),
        userTitle: userTitle.trim(),
        focusAreas: focus,
        teamRole: team,
        onboardingComplete: true,
      })
      setSidebarView(team === 'testing' ? 'testing' : 'teams')
      setAgentPaneVisible(true)
    } catch (e: any) {
      setErr(e?.message || 'Could not save profile')
      setSaving(false)
    }
  }

  return (
    <div className={`onboard ${entered ? 'onboard--in' : ''}`}>
      <div className="onboard__aurora" aria-hidden />
      <div className="onboard__grid" aria-hidden />
      <div className="onboard__orb onboard__orb--a" aria-hidden />
      <div className="onboard__orb onboard__orb--b" aria-hidden />
      <div className="onboard__orb onboard__orb--c" aria-hidden />

      <header className="onboard__top">
        <div className="onboard__brand">
          <AuraLogo size={32} />
          <span>Aura</span>
        </div>
        <div className="onboard__progress" aria-label="Onboarding progress">
          {STEPS.map((s, i) => (
            <span
              key={s}
              className={`onboard__dot${i <= stepIndex ? ' onboard__dot--on' : ''}${i === stepIndex ? ' onboard__dot--cur' : ''}`}
            />
          ))}
        </div>
      </header>

      <main className="onboard__stage">
        <div key={step} className="onboard__card">
          {step === 'welcome' && (
            <section className="onboard__panel">
              <p className="onboard__eyebrow">Organization workspace</p>
              <h1 className="onboard__title">
                One AI teammate for<br />
                <span className="onboard__gradient">your entire org</span>
              </h1>
              <p className="onboard__lead">
                Tell Aura who you are. We’ll tune testing, engineering, platform, hardware,
                security, product, and data workflows to your team.
              </p>
              <div className="onboard__pills">
                {['Testing', 'Dev', 'Platform', 'Hardware', 'Security', 'Product', 'Data'].map(t => (
                  <span key={t} className="onboard__pill">{t}</span>
                ))}
              </div>
            </section>
          )}

          {step === 'identity' && (
            <section className="onboard__panel">
              <p className="onboard__eyebrow">Step 1 · Identity</p>
              <h2 className="onboard__h2">Who are you working with?</h2>
              <p className="onboard__lead">Org and name shape how Aura speaks and prioritizes.</p>
              <div className="onboard__fields">
                <label className="onboard__field">
                  <span>Organization</span>
                  <input
                    className="onboard__input"
                    value={orgName}
                    onChange={e => setOrgName(e.target.value)}
                    placeholder="Acme Systems"
                    autoFocus
                  />
                </label>
                <div className="onboard__row">
                  <label className="onboard__field">
                    <span>Your name</span>
                    <input
                      className="onboard__input"
                      value={userName}
                      onChange={e => setUserName(e.target.value)}
                      placeholder="Alex Rivera"
                    />
                  </label>
                  <label className="onboard__field">
                    <span>Title (optional)</span>
                    <input
                      className="onboard__input"
                      value={userTitle}
                      onChange={e => setUserTitle(e.target.value)}
                      placeholder="QA Lead"
                    />
                  </label>
                </div>
              </div>
            </section>
          )}

          {step === 'team' && (
            <section className="onboard__panel">
              <p className="onboard__eyebrow">Step 2 · Team</p>
              <h2 className="onboard__h2">Which team should Aura join?</h2>
              <p className="onboard__lead">This sets prompts, hubs, and default workflows. You can switch anytime.</p>
              <div className="onboard__teams">
                {ORG_TEAMS.map(t => (
                  <button
                    key={t.id}
                    type="button"
                    className={`onboard__team${team === t.id ? ' onboard__team--on' : ''}`}
                    style={{ ['--tc' as string]: t.color }}
                    onClick={() => setTeam(t.id)}
                  >
                    <span className="onboard__team-badge">{t.short}</span>
                    <span className="onboard__team-label">{t.label}</span>
                    <span className="onboard__team-desc">{t.description}</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {step === 'focus' && (
            <section className="onboard__panel">
              <p className="onboard__eyebrow">Step 3 · Focus</p>
              <h2 className="onboard__h2">What should Aura prioritize?</h2>
              <p className="onboard__lead">Pick up to six focus areas for {meta.label}.</p>
              <div className="onboard__focus">
                {FOCUS_OPTIONS[team].map(item => (
                  <button
                    key={item}
                    type="button"
                    className={`onboard__chip${focus.includes(item) ? ' onboard__chip--on' : ''}`}
                    style={{ ['--tc' as string]: meta.color }}
                    onClick={() => toggleFocus(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </section>
          )}

          {step === 'workspace' && (
            <section className="onboard__panel">
              <p className="onboard__eyebrow">Step 4 · Workspace</p>
              <h2 className="onboard__h2">Open a project folder?</h2>
              <p className="onboard__lead">Optional — you can open one later from File → Open Folder.</p>
              <label className="onboard__field">
                <span>Folder path</span>
                <input
                  className="onboard__input"
                  value={folder}
                  onChange={e => setFolder(e.target.value)}
                  placeholder="C:\\Projects\\my-app"
                  autoFocus
                />
              </label>
              <button type="button" className="onboard__skip" onClick={next}>
                Skip for now
              </button>
            </section>
          )}

          {step === 'ready' && (
            <section className="onboard__panel onboard__panel--ready">
              <div className="onboard__ready-glow" style={{ ['--tc' as string]: meta.color }} />
              <p className="onboard__eyebrow">You’re set</p>
              <h2 className="onboard__h2">
                Welcome{userName ? `, ${userName.split(' ')[0]}` : ''}
              </h2>
              <p className="onboard__lead">
                Aura will open as <strong>{meta.label}</strong>
                {orgName ? <> for <strong>{orgName}</strong></> : null}.
              </p>
              <div className="onboard__summary">
                <div><span>Org</span><b>{orgName || '—'}</b></div>
                <div><span>Team</span><b style={{ color: meta.color }}>{meta.label}</b></div>
                <div><span>Focus</span><b>{focus.slice(0, 3).join(' · ') || '—'}</b></div>
              </div>
              {err && <p className="onboard__err">{err}</p>}
            </section>
          )}
        </div>
      </main>

      <footer className="onboard__foot">
        {step !== 'welcome' && step !== 'ready' && (
          <button type="button" className="onboard__btn onboard__btn--ghost" onClick={back}>
            Back
          </button>
        )}
        <div className="onboard__foot-spacer" />
        {step !== 'ready' ? (
          <button
            type="button"
            className="onboard__btn onboard__btn--primary"
            disabled={!canNext}
            onClick={next}
          >
            {step === 'welcome' ? 'Get started' : 'Continue'}
          </button>
        ) : (
          <button
            type="button"
            className="onboard__btn onboard__btn--primary onboard__btn--enter"
            disabled={saving}
            onClick={finish}
            style={{ ['--tc' as string]: meta.color }}
          >
            {saving ? 'Opening Aura…' : 'Enter Aura'}
          </button>
        )}
      </footer>
    </div>
  )
}

