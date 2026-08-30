import React from 'react'
import { useStore } from '../../store'
import { teamWorkflows } from '../../teams'
import { updateSettings } from '../../api'

const PHASES = [
  {
    id: 'generate',
    title: 'Generate',
    color: '#059669',
    items: ['gen-unit', 'gen-e2e'],
    blurb: 'Create unit, API, and e2e coverage that matches your project.',
  },
  {
    id: 'review',
    title: 'Review',
    color: '#2563eb',
    items: ['review-suite', 'regression'],
    blurb: 'Find gaps, flaky tests, weak assertions, and risk hotspots.',
  },
  {
    id: 'execute',
    title: 'Execute',
    color: '#d97706',
    items: ['execute', 'report'],
    blurb: 'Run suites, triage failures, and produce a go/no-go report.',
  },
] as const

export default function TestingPanel() {
  const {
    teamRole, setTeamRole, setAgentPaneVisible, setInputDraft,
    setBottomPanelVisible, setBottomTab,
  } = useStore()

  const workflows = teamWorkflows('testing')
  const byId = Object.fromEntries(workflows.map(w => [w.id, w]))

  const ensureTesting = () => {
    if (teamRole !== 'testing') {
      setTeamRole('testing')
      updateSettings({ team_role: 'testing' }).catch(() => {})
    }
    setAgentPaneVisible(true)
  }

  const run = (prompt: string) => {
    ensureTesting()
    setInputDraft(prompt)
  }

  return (
    <>
      <div className="sidebar__header">
        <span>Testing Hub</span>
      </div>
      <div className="sidebar__body" style={{ padding: '10px 12px' }}>
        <div className="test-hero">
          <div className="test-hero__title">Full testing lifecycle</div>
          <p className="test-hero__sub">
            Generation → Review → Execution. Aura runs as your QA teammate across unit, API, e2e, regression, and reports.
          </p>
          <button
            className="btn btn--sm btn--primary"
            onClick={() => {
              ensureTesting()
              setBottomPanelVisible(true)
              setBottomTab('terminal')
            }}
          >
            Open terminal for execution
          </button>
        </div>

        {PHASES.map(phase => (
          <div key={phase.id} className="test-phase">
            <div className="test-phase__head">
              <span className="test-phase__dot" style={{ background: phase.color }} />
              <span className="test-phase__title">{phase.title}</span>
            </div>
            <p className="test-phase__blurb">{phase.blurb}</p>
            <div className="workflow-list">
              {phase.items.map(id => {
                const w = byId[id]
                if (!w) return null
                return (
                  <button key={id} className="workflow-item" onClick={() => run(w.prompt)}>
                    <span className="workflow-item__label">{w.label}</span>
                    <span className="workflow-item__go">→</span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
