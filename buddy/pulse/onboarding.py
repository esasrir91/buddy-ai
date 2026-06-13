"""
PULSE Onboarding Workflow — automates the first-day experience for a PULSE employee.

OnboardingWorkflow is a Workflow v1 subclass that orchestrates:
  1. Ingest company documents (KT)
  2. Register team members
  3. Load initial task list
  4. Send introduction message
  5. Return structured OnboardingResult
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional

from buddy.run.response import RunResponse
from buddy.workflow.workflow import Workflow

from buddy.pulse.identity import ColleagueRecord
from buddy.pulse.kt import KTSourceType
from buddy.pulse.work import TaskPriority, WorkItem


@dataclass
class OnboardingConfig:
    """Configuration for a PULSE onboarding run."""

    company_name: str = ""
    company_docs: List[str] = field(default_factory=list)
    team_members: List[ColleagueRecord] = field(default_factory=list)
    initial_tasks: List[WorkItem] = field(default_factory=list)
    send_introduction_to: Optional[str] = None
    introduction_channel: str = "general"


@dataclass
class OnboardingResult:
    """Output of a completed PULSE onboarding run."""

    employee_name: str
    kt_sessions: List[str] = field(default_factory=list)
    kt_failed: List[str] = field(default_factory=list)
    colleagues_added: List[str] = field(default_factory=list)
    tasks_loaded: List[str] = field(default_factory=list)
    introduction_sent: bool = False
    introduction_message: str = ""
    onboarded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def is_successful(self) -> bool:
        return len(self.kt_sessions) > 0 or len(self.colleagues_added) > 0

    def summary(self) -> str:
        lines = [
            f"Onboarding complete for {self.employee_name}",
            f"  ✅ KT sessions: {len(self.kt_sessions)}",
            f"  👥 Colleagues added: {len(self.colleagues_added)}",
            f"  📋 Tasks loaded: {len(self.tasks_loaded)}",
        ]
        if self.kt_failed:
            lines.append(f"  ⚠️  KT failures: {len(self.kt_failed)}")
        if self.introduction_sent:
            lines.append("  💬 Introduction sent")
        return "\n".join(lines)


class OnboardingWorkflow(Workflow):
    """
    Automates onboarding a PULSE virtual employee.

    Usage:
        from buddy.pulse import PulseEmployee, EmployeeProfile
        from buddy.pulse.onboarding import OnboardingWorkflow, OnboardingConfig
        from buddy.pulse.identity import ColleagueRecord

        employee = PulseEmployee(
            employee_profile=EmployeeProfile(full_name="Priya", role="Backend Engineer"),
            model=OpenAIChat(id="gpt-4o"),
        )

        config = OnboardingConfig(
            company_name="Acme Corp",
            company_docs=["docs/architecture.pdf"],
            team_members=[ColleagueRecord(full_name="Arjun Nair", role="Tech Lead")],
        )

        workflow = OnboardingWorkflow(employee=employee)
        for chunk in workflow.run(config):
            print(chunk.content, end="", flush=True)
    """

    name: str = "PULSE Onboarding Workflow"
    description: str = "Automates the first-day onboarding experience for a PULSE virtual employee"

    def __init__(self, employee: "PulseEmployee", **kwargs) -> None:  # type: ignore[name-defined]
        super().__init__(**kwargs)
        self.employee = employee

    def run(  # type: ignore[override]
        self,
        config: Optional[OnboardingConfig] = None,
        **kwargs,
    ) -> Iterator[RunResponse]:
        if config is None:
            config = OnboardingConfig()

        result = OnboardingResult(employee_name=self.employee.employee_profile.full_name)

        # ---- Step 1: KT from company documents ----
        if config.company_docs:
            yield RunResponse(content=f"📚 Starting KT from {len(config.company_docs)} document(s)...\n")
            for doc_path in config.company_docs:
                try:
                    summary = self.employee.take_kt(
                        source=doc_path,
                        source_type=KTSourceType.DOCUMENT,
                        session_name=f"Onboarding — {doc_path.split('/')[-1]}",
                        knowledge_giver=config.company_name or "Company",
                    )
                    result.kt_sessions.append(summary.session_name)
                    yield RunResponse(
                        content=f"  ✅ KT complete: {summary.session_name} (confidence: {summary.confidence_score:.0%})\n"
                    )
                except Exception as e:
                    result.kt_failed.append(f"{doc_path}: {e}")
                    yield RunResponse(content=f"  ⚠️  KT failed for {doc_path}: {e}\n")

        # ---- Step 2: Meet the team ----
        if config.team_members:
            yield RunResponse(content=f"\n👥 Learning about {len(config.team_members)} team member(s)...\n")
            for member in config.team_members:
                from buddy.pulse.memory import ColleagueMemoryEntry
                entry = ColleagueMemoryEntry(
                    colleague_name=member.full_name,
                    role=member.role,
                    interactions=["Met during onboarding"],
                )
                self.employee.professional_memory.remember_colleague(entry)
                result.colleagues_added.append(member.full_name)
                yield RunResponse(content=f"  ✅ Colleague added: {member.full_name} ({member.role})\n")

        # ---- Step 3: Load initial tasks ----
        if config.initial_tasks:
            yield RunResponse(content=f"\n📋 Loading {len(config.initial_tasks)} initial task(s)...\n")
            for task in config.initial_tasks:
                self.employee.task_manager.assign(task)
                result.tasks_loaded.append(task.title)
                yield RunResponse(content=f"  ✅ Task loaded: {task.title}\n")

        # ---- Step 4: Send introduction ----
        intro = self.employee.introduce_yourself()
        result.introduction_message = intro
        if config.send_introduction_to:
            yield RunResponse(content=f"\n💬 Sending introduction to #{config.introduction_channel}...\n")
            from buddy.pulse.comms import CommChannel
            msg = self.employee.communication_hub.send_slack_message(
                channel_or_user=config.introduction_channel,
                message=intro,
            )
            result.introduction_sent = msg.sent
        else:
            yield RunResponse(content=f"\n💬 Introduction ready:\n{intro}\n")

        # ---- Done ----
        yield RunResponse(content=f"\n\n{'=' * 50}\n{result.summary()}\n")


# Resolve forward reference
from buddy.pulse.employee import PulseEmployee  # noqa: E402
OnboardingWorkflow.__annotations__["employee"] = PulseEmployee
