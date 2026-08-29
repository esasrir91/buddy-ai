"""Pulse integration for Aura.

Pulse is Buddy's "virtual employee" - an agent with a professional identity and
persistent professional memory. In Aura we expose it as a teammate that also has
the workspace coding tools, so it can act like an onboarded engineer on the
project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from buddy.code.settings import CodeSettings
from buddy.code.tools import WorkspaceTools

_DEFAULT_PROFILE: Dict[str, Any] = {
    "full_name": "Varam AI",
    "role": "Senior Software Engineer",
    "department": "engineering",
    "team": "Platform",
    "seniority": "senior",
    "skills": ["python", "typescript", "system design", "testing"],
    "bio": "An AI teammate that helps build, review, and ship software.",
}


def build_pulse_employee(settings: CodeSettings, workspace: str, profile: Optional[Dict[str, Any]] = None):
    """Create a PulseEmployee (an Agent with professional identity) wired with the
    workspace coding tools."""
    from buddy.code.agent import build_model
    from buddy.pulse import EmployeeProfile, PulseEmployee

    settings.apply_to_env()
    data = {**_DEFAULT_PROFILE, **(profile or {})}
    try:
        emp_profile = EmployeeProfile(**data)
    except Exception:
        # Be lenient about unknown/extra fields from the UI.
        emp_profile = EmployeeProfile(full_name=data.get("full_name", "Varam AI"), role=data.get("role", "Engineer"))

    tools = [WorkspaceTools(base_path=workspace, enable_shell=settings.enable_shell)]
    agent_kwargs = {"model": build_model(settings), "tools": tools, "markdown": True}

    try:
        return PulseEmployee(employee_profile=emp_profile, agent_kwargs=agent_kwargs)
    except TypeError:
        # Fallback for differing signatures across versions.
        return PulseEmployee(employee_profile=emp_profile)


__all__ = ["build_pulse_employee"]
