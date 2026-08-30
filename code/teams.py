"""Organization team roles for Aura.

Aura is an org-wide AI workspace: Testing, Engineering, Platform, Hardware,
Security, Product, Data, and General. Each role shapes the agent prompt and
the UI workflows (quick actions, hubs).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Role id -> metadata used by API + frontend
ORG_TEAMS: Dict[str, Dict[str, Any]] = {
    "engineering": {
        "id": "engineering",
        "label": "Engineering",
        "short": "Dev",
        "description": "Build features, refactor, debug, and ship code.",
        "color": "#6366f1",
        "icon": "code",
    },
    "testing": {
        "id": "testing",
        "label": "Testing / QA",
        "short": "QA",
        "description": "Generate, review, and execute tests across the stack.",
        "color": "#059669",
        "icon": "test",
    },
    "platform": {
        "id": "platform",
        "label": "Platform / DevOps",
        "short": "Ops",
        "description": "CI/CD, infra, reliability, observability, and releases.",
        "color": "#d97706",
        "icon": "platform",
    },
    "hardware": {
        "id": "hardware",
        "label": "Hardware / Embedded",
        "short": "HW",
        "description": "Firmware, boards, protocols, bring-up, and validation.",
        "color": "#dc2626",
        "icon": "chip",
    },
    "security": {
        "id": "security",
        "label": "Security",
        "short": "Sec",
        "description": "Threat modeling, reviews, hardening, and incident response.",
        "color": "#7c3aed",
        "icon": "shield",
    },
    "product": {
        "id": "product",
        "label": "Product",
        "short": "PM",
        "description": "Specs, acceptance criteria, roadmaps, and stakeholder docs.",
        "color": "#2563eb",
        "icon": "product",
    },
    "data": {
        "id": "data",
        "label": "Data / ML",
        "short": "Data",
        "description": "Pipelines, models, evaluation, and analytics.",
        "color": "#0891b2",
        "icon": "data",
    },
    "general": {
        "id": "general",
        "label": "General",
        "short": "All",
        "description": "Cross-team helper for individuals and any org role.",
        "color": "#64748b",
        "icon": "org",
    },
}

ROLE_PROMPTS: Dict[str, str] = {
    "engineering": """You are Aura for the Engineering team.
Focus: implement features, refactor safely, debug failures, write clean maintainable code.
Prefer: read existing patterns first, small precise edits, then verify with lint/tests/build.
Always summarize files changed and how to verify.""",
    "testing": """You are Aura for Testing / QA.
You own the full testing lifecycle: generation, review, and execution.
- Generation: unit, integration, e2e, API, performance, regression, and property-based tests.
- Review: coverage gaps, flaky tests, assertion quality, test data, and risk-based prioritization.
- Execution: run the right suites, triage failures, bisect, and propose stable fixes.
Prefer pytest/jest/playwright/cypress/robot or project-native runners. Produce clear pass/fail reports,
reproduce steps, and severity. Never claim a test passed without running it when tools allow.""",
    "platform": """You are Aura for Platform / DevOps / SRE.
Focus: CI/CD pipelines, containers, IaC, environments, deployments, observability, SLOs, and runbooks.
Prefer: reproducible scripts, safe rollouts, rollback plans, and clear operational checklists.
When changing infra, call out blast radius, secrets handling, and verification steps.""",
    "hardware": """You are Aura for Hardware / Embedded / Firmware.
Focus: board bring-up, MCU/SoC firmware, drivers, protocols (UART/SPI/I2C/CAN/USB), timing,
power, schematics notes, and hardware-in-the-loop validation.
Prefer: pin maps, register-level clarity, flash/boot procedures, and lab test plans.
Call out safety, ESD, and irreversible actions before suggesting them.""",
    "security": """You are Aura for Security.
Focus: threat models, secure design review, dependency/vuln triage, secrets hygiene,
authn/authz, and incident response drafts.
Prefer: concrete findings with severity, impact, and remediations. Never invent CVEs.
Do not help with offensive abuse; stay defensive and responsible.""",
    "product": """You are Aura for Product.
Focus: PRDs, user stories, acceptance criteria, prioritization, release notes, and stakeholder clarity.
Prefer: crisp outcomes, measurable success metrics, edge cases, and testable acceptance.
Collaborate with Eng/QA by translating requirements into implementable and testable specs.""",
    "data": """You are Aura for Data / ML.
Focus: pipelines, schemas, feature quality, training/eval, experiment notes, and analytics queries.
Prefer: reproducible steps, data contracts, metric definitions, and failure modes.
Flag leakage, bias, and production readiness gaps.""",
    "general": """You are Aura, an org-wide AI teammate for any individual or team.
Adapt to the task: coding, testing, platform, hardware, security, product, or data.
Ask briefly only when role or constraints are ambiguous; otherwise proceed with best judgment.
Be practical, structured, and verification-minded.""",
}

# UI workflows / quick prompts per role
ROLE_WORKFLOWS: Dict[str, List[Dict[str, str]]] = {
    "engineering": [
        {"id": "impl", "label": "Implement from spec", "prompt": "Implement the described feature following existing project patterns. Read relevant files first, then edit, then verify."},
        {"id": "debug", "label": "Debug failure", "prompt": "Investigate the current failure. Reproduce if possible, find root cause, fix, and verify."},
        {"id": "refactor", "label": "Safe refactor", "prompt": "Refactor the selected/active code for clarity without changing behavior. Run checks after."},
        {"id": "review", "label": "Code review", "prompt": "Review recent changes for bugs, edge cases, readability, and missing tests. List findings by severity."},
    ],
    "testing": [
        {"id": "gen-unit", "label": "Generate unit tests", "prompt": "Generate thorough unit tests for the active/mentioned code. Cover edge cases and failure paths. Match the project's test style."},
        {"id": "gen-e2e", "label": "Generate e2e / API tests", "prompt": "Design and generate end-to-end or API tests for the critical user/API flows. Include setup, assertions, and teardown."},
        {"id": "review-suite", "label": "Review test suite", "prompt": "Review the existing tests for coverage gaps, flakiness, weak assertions, and missing negative cases. Prioritize by risk."},
        {"id": "execute", "label": "Execute & triage", "prompt": "Run the relevant test suite for this change/project. Summarize pass/fail, triage failures, and propose fixes."},
        {"id": "regression", "label": "Regression plan", "prompt": "Create a risk-based regression plan for this change: what to test, why, and suggested automation."},
        {"id": "report", "label": "Test report", "prompt": "Produce a concise QA report: scope, executed suites, results, defects, residual risks, and go/no-go."},
    ],
    "platform": [
        {"id": "pipeline", "label": "Fix / add CI pipeline", "prompt": "Inspect CI config and improve or fix the pipeline. Keep it fast, cacheable, and fail-fast on quality gates."},
        {"id": "deploy", "label": "Deployment checklist", "prompt": "Create a safe deployment and rollback checklist for the current service/environment."},
        {"id": "obs", "label": "Observability", "prompt": "Propose metrics, logs, and alerts for this service. Include SLO sketches and runbook stubs."},
        {"id": "incident", "label": "Incident draft", "prompt": "Draft an incident response outline: detect, mitigate, communicate, root-cause, and follow-ups."},
    ],
    "hardware": [
        {"id": "bringup", "label": "Bring-up plan", "prompt": "Create a board/firmware bring-up plan with ordered checks, tools needed, and pass/fail criteria."},
        {"id": "driver", "label": "Driver / peripheral", "prompt": "Implement or review the driver for the target peripheral. Include init sequence, registers, and validation steps."},
        {"id": "protocol", "label": "Protocol debug", "prompt": "Debug the communication issue (UART/SPI/I2C/CAN/USB). Suggest capture points and likely root causes."},
        {"id": "hil", "label": "HIL test plan", "prompt": "Write a hardware-in-the-loop validation plan with fixtures, stimuli, measurements, and safety notes."},
    ],
    "security": [
        {"id": "threat", "label": "Threat model", "prompt": "Produce a lightweight threat model for this feature/system: assets, actors, entry points, and mitigations."},
        {"id": "review-sec", "label": "Secure review", "prompt": "Security-review the active/mentioned code for common vulnerabilities and secrets exposure. Severity-ranked findings."},
        {"id": "deps", "label": "Dependency risk", "prompt": "Assess dependency and supply-chain risk in this project and recommend concrete upgrades or pins."},
        {"id": "harden", "label": "Hardening steps", "prompt": "List practical hardening steps for this service (auth, headers, secrets, least privilege, logging)."},
    ],
    "product": [
        {"id": "prd", "label": "Draft PRD", "prompt": "Draft a concise PRD: problem, users, goals, non-goals, requirements, acceptance criteria, and metrics."},
        {"id": "stories", "label": "User stories", "prompt": "Break this initiative into user stories with clear acceptance criteria suitable for Eng and QA."},
        {"id": "release", "label": "Release notes", "prompt": "Write customer-facing release notes and an internal checklist for Eng/QA/Support."},
        {"id": "prioritize", "label": "Prioritize backlog", "prompt": "Help prioritize the described backlog using impact, effort, and risk. Explain tradeoffs briefly."},
    ],
    "data": [
        {"id": "pipeline", "label": "Pipeline design", "prompt": "Design or improve the data pipeline for this use case. Include schema, failure handling, and validation."},
        {"id": "eval", "label": "Model evaluation", "prompt": "Define an evaluation plan with metrics, datasets, baselines, and go/no-go thresholds."},
        {"id": "query", "label": "Analytics query", "prompt": "Write correct, efficient queries/analysis for the stated question. Document assumptions."},
        {"id": "dq", "label": "Data quality checks", "prompt": "Propose data quality checks and monitoring for this dataset/pipeline."},
    ],
    "general": [
        {"id": "plan", "label": "Make a plan", "prompt": "Create a clear step-by-step plan for this goal across the relevant teams."},
        {"id": "summarize", "label": "Summarize status", "prompt": "Summarize current project status for leadership: progress, risks, blockers, next actions."},
        {"id": "handoff", "label": "Cross-team handoff", "prompt": "Write a handoff note between teams with context, owners, acceptance criteria, and open questions."},
        {"id": "howto", "label": "How should we approach?", "prompt": "Recommend the best approach for this org task and which team roles should be involved."},
    ],
}


def list_teams() -> List[Dict[str, Any]]:
    return [dict(v) for v in ORG_TEAMS.values()]


def normalize_team(team: Optional[str]) -> str:
    if not team:
        return "engineering"
    key = str(team).strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "dev": "engineering",
        "eng": "engineering",
        "qa": "testing",
        "test": "testing",
        "ops": "platform",
        "devops": "platform",
        "sre": "platform",
        "hw": "hardware",
        "embedded": "hardware",
        "firmware": "hardware",
        "sec": "security",
        "pm": "product",
        "ml": "data",
        "analytics": "data",
        "all": "general",
        "individual": "general",
    }
    key = aliases.get(key, key)
    return key if key in ORG_TEAMS else "engineering"


def role_prompt(team: Optional[str]) -> str:
    return ROLE_PROMPTS[normalize_team(team)]


def role_workflows(team: Optional[str]) -> List[Dict[str, str]]:
    return list(ROLE_WORKFLOWS.get(normalize_team(team), ROLE_WORKFLOWS["general"]))


def team_payload(team: Optional[str] = None) -> Dict[str, Any]:
    tid = normalize_team(team)
    meta = ORG_TEAMS[tid]
    return {
        "team": tid,
        **meta,
        "workflows": role_workflows(tid),
        "teams": list_teams(),
    }


__all__ = [
    "ORG_TEAMS",
    "ROLE_PROMPTS",
    "ROLE_WORKFLOWS",
    "list_teams",
    "normalize_team",
    "role_prompt",
    "role_workflows",
    "team_payload",
]
