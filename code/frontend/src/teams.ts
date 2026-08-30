import type { TeamMeta, TeamRole, TeamWorkflow } from './types'

export const ORG_TEAMS: TeamMeta[] = [
  { id: 'engineering', label: 'Engineering', short: 'Dev', description: 'Build features, refactor, debug, and ship code.', color: '#6366f1', icon: 'code' },
  { id: 'testing', label: 'Testing / QA', short: 'QA', description: 'Generate, review, and execute tests across the stack.', color: '#059669', icon: 'test' },
  { id: 'platform', label: 'Platform / DevOps', short: 'Ops', description: 'CI/CD, infra, reliability, observability, and releases.', color: '#d97706', icon: 'platform' },
  { id: 'hardware', label: 'Hardware / Embedded', short: 'HW', description: 'Firmware, boards, protocols, bring-up, and validation.', color: '#dc2626', icon: 'chip' },
  { id: 'security', label: 'Security', short: 'Sec', description: 'Threat modeling, reviews, hardening, and incident response.', color: '#7c3aed', icon: 'shield' },
  { id: 'product', label: 'Product', short: 'PM', description: 'Specs, acceptance criteria, roadmaps, and stakeholder docs.', color: '#2563eb', icon: 'product' },
  { id: 'data', label: 'Data / ML', short: 'Data', description: 'Pipelines, models, evaluation, and analytics.', color: '#0891b2', icon: 'data' },
  { id: 'general', label: 'General', short: 'All', description: 'Cross-team helper for individuals and any org role.', color: '#64748b', icon: 'org' },
]

export const TEAM_WORKFLOWS: Record<TeamRole, TeamWorkflow[]> = {
  engineering: [
    { id: 'impl', label: 'Implement from spec', prompt: 'Implement the described feature following existing project patterns. Read relevant files first, then edit, then verify.' },
    { id: 'debug', label: 'Debug failure', prompt: 'Investigate the current failure. Reproduce if possible, find root cause, fix, and verify.' },
    { id: 'refactor', label: 'Safe refactor', prompt: 'Refactor the selected/active code for clarity without changing behavior. Run checks after.' },
    { id: 'review', label: 'Code review', prompt: 'Review recent changes for bugs, edge cases, readability, and missing tests. List findings by severity.' },
  ],
  testing: [
    { id: 'gen-unit', label: 'Generate unit tests', prompt: 'Generate thorough unit tests for the active/mentioned code. Cover edge cases and failure paths. Match the project\'s test style.' },
    { id: 'gen-e2e', label: 'Generate e2e / API tests', prompt: 'Design and generate end-to-end or API tests for the critical user/API flows. Include setup, assertions, and teardown.' },
    { id: 'review-suite', label: 'Review test suite', prompt: 'Review the existing tests for coverage gaps, flakiness, weak assertions, and missing negative cases. Prioritize by risk.' },
    { id: 'execute', label: 'Execute & triage', prompt: 'Run the relevant test suite for this change/project. Summarize pass/fail, triage failures, and propose fixes.' },
    { id: 'regression', label: 'Regression plan', prompt: 'Create a risk-based regression plan for this change: what to test, why, and suggested automation.' },
    { id: 'report', label: 'Test report', prompt: 'Produce a concise QA report: scope, executed suites, results, defects, residual risks, and go/no-go.' },
  ],
  platform: [
    { id: 'pipeline', label: 'Fix / add CI pipeline', prompt: 'Inspect CI config and improve or fix the pipeline. Keep it fast, cacheable, and fail-fast on quality gates.' },
    { id: 'deploy', label: 'Deployment checklist', prompt: 'Create a safe deployment and rollback checklist for the current service/environment.' },
    { id: 'obs', label: 'Observability', prompt: 'Propose metrics, logs, and alerts for this service. Include SLO sketches and runbook stubs.' },
    { id: 'incident', label: 'Incident draft', prompt: 'Draft an incident response outline: detect, mitigate, communicate, root-cause, and follow-ups.' },
  ],
  hardware: [
    { id: 'bringup', label: 'Bring-up plan', prompt: 'Create a board/firmware bring-up plan with ordered checks, tools needed, and pass/fail criteria.' },
    { id: 'driver', label: 'Driver / peripheral', prompt: 'Implement or review the driver for the target peripheral. Include init sequence, registers, and validation steps.' },
    { id: 'protocol', label: 'Protocol debug', prompt: 'Debug the communication issue (UART/SPI/I2C/CAN/USB). Suggest capture points and likely root causes.' },
    { id: 'hil', label: 'HIL test plan', prompt: 'Write a hardware-in-the-loop validation plan with fixtures, stimuli, measurements, and safety notes.' },
  ],
  security: [
    { id: 'threat', label: 'Threat model', prompt: 'Produce a lightweight threat model for this feature/system: assets, actors, entry points, and mitigations.' },
    { id: 'review-sec', label: 'Secure review', prompt: 'Security-review the active/mentioned code for common vulnerabilities and secrets exposure. Severity-ranked findings.' },
    { id: 'deps', label: 'Dependency risk', prompt: 'Assess dependency and supply-chain risk in this project and recommend concrete upgrades or pins.' },
    { id: 'harden', label: 'Hardening steps', prompt: 'List practical hardening steps for this service (auth, headers, secrets, least privilege, logging).' },
  ],
  product: [
    { id: 'prd', label: 'Draft PRD', prompt: 'Draft a concise PRD: problem, users, goals, non-goals, requirements, acceptance criteria, and metrics.' },
    { id: 'stories', label: 'User stories', prompt: 'Break this initiative into user stories with clear acceptance criteria suitable for Eng and QA.' },
    { id: 'release', label: 'Release notes', prompt: 'Write customer-facing release notes and an internal checklist for Eng/QA/Support.' },
    { id: 'prioritize', label: 'Prioritize backlog', prompt: 'Help prioritize the described backlog using impact, effort, and risk. Explain tradeoffs briefly.' },
  ],
  data: [
    { id: 'pipeline', label: 'Pipeline design', prompt: 'Design or improve the data pipeline for this use case. Include schema, failure handling, and validation.' },
    { id: 'eval', label: 'Model evaluation', prompt: 'Define an evaluation plan with metrics, datasets, baselines, and go/no-go thresholds.' },
    { id: 'query', label: 'Analytics query', prompt: 'Write correct, efficient queries/analysis for the stated question. Document assumptions.' },
    { id: 'dq', label: 'Data quality checks', prompt: 'Propose data quality checks and monitoring for this dataset/pipeline.' },
  ],
  general: [
    { id: 'plan', label: 'Make a plan', prompt: 'Create a clear step-by-step plan for this goal across the relevant teams.' },
    { id: 'summarize', label: 'Summarize status', prompt: 'Summarize current project status for leadership: progress, risks, blockers, next actions.' },
    { id: 'handoff', label: 'Cross-team handoff', prompt: 'Write a handoff note between teams with context, owners, acceptance criteria, and open questions.' },
    { id: 'howto', label: 'How should we approach?', prompt: 'Recommend the best approach for this org task and which team roles should be involved.' },
  ],
}

export function teamMeta(role: TeamRole): TeamMeta {
  return ORG_TEAMS.find(t => t.id === role) ?? ORG_TEAMS[0]
}

export function teamWorkflows(role: TeamRole): TeamWorkflow[] {
  return TEAM_WORKFLOWS[role] ?? TEAM_WORKFLOWS.general
}
