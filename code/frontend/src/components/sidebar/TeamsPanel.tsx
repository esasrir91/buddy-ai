import React from 'react'
import { useStore } from '../../store'
import { ORG_TEAMS, teamWorkflows } from '../../teams'
import type { TeamRole } from '../../types'
import { updateSettings } from '../../api'

export default function TeamsPanel() {
  const { teamRole, setTeamRole, setAgentPaneVisible, setInputDraft } = useStore()

  const select = (role: TeamRole) => {
    setTeamRole(role)
    updateSettings({ team_role: role }).catch(() => {})
    setAgentPaneVisible(true)
  }

  const runWorkflow = (prompt: string) => {
    setAgentPaneVisible(true)
    setInputDraft(prompt)
  }

  const active = ORG_TEAMS.find(t => t.id === teamRole) ?? ORG_TEAMS[0]
  const workflows = teamWorkflows(teamRole)

  return (
    <>
      <div className="sidebar__header">
        <span>Org Teams</span>
      </div>
      <div className="sidebar__body" style={{ padding: '8px 10px' }}>
        <p className="teams-intro">
          Aura supports the whole org — pick your team to shape the agent, workflows, and guidance.
        </p>

        <div className="teams-grid">
          {ORG_TEAMS.map(t => (
            <button
              key={t.id}
              className={`team-card${teamRole === t.id ? ' team-card--active' : ''}`}
              style={{ ['--team-color' as string]: t.color }}
              onClick={() => select(t.id)}
              title={t.description}
            >
              <span className="team-card__badge" style={{ background: t.color }}>{t.short}</span>
              <span className="team-card__label">{t.label}</span>
              <span className="team-card__desc">{t.description}</span>
            </button>
          ))}
        </div>

        <div className="teams-section">
          <div className="teams-section__title">Active · {active.label}</div>
          <p className="teams-section__sub">{active.description}</p>
          <div className="workflow-list">
            {workflows.map(w => (
              <button key={w.id} className="workflow-item" onClick={() => runWorkflow(w.prompt)}>
                <span className="workflow-item__label">{w.label}</span>
                <span className="workflow-item__go">→</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
