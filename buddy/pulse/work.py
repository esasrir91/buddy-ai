"""
PULSE Work Engine — task management and calendar for virtual employees.

WorkItem        : A single task assigned to the PULSE employee.
TaskManager     : Manages the employee's task list.
WorkCalendar    : Tracks meetings and availability.
StatusUpdate    : A formatted status report for a task or end-of-day.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    RESEARCH = "research"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    MEETING_PREP = "meeting_prep"
    OTHER = "other"


# ---------------------------------------------------------------------------
# WorkItem
# ---------------------------------------------------------------------------

class WorkItem(BaseModel):
    """A task assigned to or created by a PULSE employee."""

    task_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    title: str
    description: str = ""
    task_type: TaskType = TaskType.OTHER
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO

    assigned_by: Optional[str] = None
    assigned_to: Optional[str] = None
    deadline: Optional[str] = Field(default=None, description="ISO date string YYYY-MM-DD")
    estimated_hours: Optional[float] = None
    tags: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    progress_notes: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)

    def start(self) -> None:
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        self.status = TaskStatus.DONE
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def block(self, reason: str) -> None:
        self.status = TaskStatus.BLOCKED
        self.blockers.append(reason)
        self.updated_at = datetime.utcnow()

    def add_note(self, note: str) -> None:
        self.progress_notes.append(note)
        self.updated_at = datetime.utcnow()

    def format_brief(self) -> str:
        deadline_str = f" (due {self.deadline})" if self.deadline else ""
        blocker_str = f" 🚫 Blocker: {self.blockers[-1]}" if self.blockers else ""
        return f"[{self.priority.value.upper()}] {self.title} — {self.status.value}{deadline_str}{blocker_str}"


# ---------------------------------------------------------------------------
# StatusUpdate
# ---------------------------------------------------------------------------

class StatusUpdate(BaseModel):
    """A formatted status update produced by the PULSE employee."""

    update_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    employee_name: str
    update_type: str = "task_update"
    task_id: Optional[str] = None
    task_title: Optional[str] = None

    what_i_did: List[str] = Field(default_factory=list)
    what_i_will_do: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    percentage_complete: Optional[float] = None

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = ""

    def format_standup(self) -> str:
        """Returns a standup-style formatted status update."""
        lines = [f"**{self.employee_name} — Status Update**"]
        if self.task_title:
            lines.append(f"Task: {self.task_title}")
        lines.append("")
        if self.what_i_did:
            lines.append("✅ **Yesterday / Done:**")
            for item in self.what_i_did:
                lines.append(f"  - {item}")
        if self.what_i_will_do:
            lines.append("📋 **Today / Next:**")
            for item in self.what_i_will_do:
                lines.append(f"  - {item}")
        if self.blockers:
            lines.append("🚫 **Blockers:**")
            for blocker in self.blockers:
                lines.append(f"  - {blocker}")
        if self.percentage_complete is not None:
            lines.append(f"\nProgress: {self.percentage_complete:.0f}%")
        if self.message:
            lines.append(f"\n{self.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CalendarEvent
# ---------------------------------------------------------------------------

class CalendarEvent(BaseModel):
    """A meeting or event on the PULSE employee's calendar."""

    event_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    title: str
    start_time: datetime
    end_time: datetime
    participants: List[str] = Field(default_factory=list)
    platform: Optional[str] = None
    agenda: Optional[str] = None
    meeting_notes_id: Optional[str] = None


# ---------------------------------------------------------------------------
# TaskManager
# ---------------------------------------------------------------------------

class TaskManager:
    """Manages a PULSE employee's task list."""

    def __init__(self, employee_name: str) -> None:
        self.employee_name = employee_name
        self._tasks: Dict[str, WorkItem] = {}

    def assign(self, task: WorkItem) -> WorkItem:
        """Register a new task."""
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> Optional[WorkItem]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[WorkItem]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (t.priority.value, t.created_at), reverse=True)

    def active_tasks(self) -> List[WorkItem]:
        return self.list_tasks(TaskStatus.IN_PROGRESS)

    def pending_tasks(self) -> List[WorkItem]:
        return self.list_tasks(TaskStatus.TODO)

    def blocked_tasks(self) -> List[WorkItem]:
        return self.list_tasks(TaskStatus.BLOCKED)

    def task_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {s.value: 0 for s in TaskStatus}
        for task in self._tasks.values():
            summary[task.status.value] += 1
        return summary

    def build_eod_context(self) -> str:
        """Returns a text summary of task state for EOD report generation."""
        active = self.active_tasks()
        pending = self.pending_tasks()
        blocked = self.blocked_tasks()
        lines = ["Current task state:"]
        if active:
            lines.append(f"In progress ({len(active)}):")
            for t in active:
                lines.append(f"  - {t.format_brief()}")
        if pending:
            lines.append(f"Pending ({len(pending)}):")
            for t in pending[:5]:
                lines.append(f"  - {t.format_brief()}")
        if blocked:
            lines.append(f"Blocked ({len(blocked)}):")
            for t in blocked:
                lines.append(f"  - {t.format_brief()}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# WorkCalendar
# ---------------------------------------------------------------------------

class WorkCalendar:
    """Tracks the PULSE employee's upcoming meetings and events."""

    def __init__(self) -> None:
        self._events: Dict[str, CalendarEvent] = {}

    def schedule(self, event: CalendarEvent) -> CalendarEvent:
        self._events[event.event_id] = event
        return event

    def upcoming(self, limit: int = 5) -> List[CalendarEvent]:
        now = datetime.utcnow()
        future = [e for e in self._events.values() if e.start_time >= now]
        return sorted(future, key=lambda e: e.start_time)[:limit]

    def today(self) -> List[CalendarEvent]:
        now = datetime.utcnow()
        return [
            e for e in self._events.values()
            if e.start_time.date() == now.date()
        ]
