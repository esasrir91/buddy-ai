"""
PULSE FastAPI Router — REST + WebSocket endpoints for the PULSE web UI.

All routes are prefixed with /api/pulse and mounted onto PulseApp.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from buddy.pulse.employee import PulseEmployee
from buddy.pulse.identity import EmployeeProfile, SeniorityLevel, WorkMode, WorkStyle
from buddy.pulse.kt import KTSession, KTSourceType
from buddy.pulse.meeting import MeetingPlatform
from buddy.pulse.work import TaskPriority

router = APIRouter(prefix="/api/pulse", tags=["PULSE"])

# ---------------------------------------------------------------------------
# Employee persistence — survives server restarts
# ---------------------------------------------------------------------------
import os
import pathlib

_PULSE_DATA_DIR = pathlib.Path(os.environ.get("PULSE_DATA_DIR", pathlib.Path.home() / ".pulse_data"))
_EMPLOYEES_FILE = _PULSE_DATA_DIR / "employees.json"


def _save_employees() -> None:
    """Persist all employee profiles, KT summaries, and tasks to disk."""
    _PULSE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = {}
    for eid, emp in _employees.items():
        p = emp.employee_profile
        # KT summaries
        kt_data = [s.model_dump(mode="json") for s in emp.kt_manager.all_summaries()]
        # Tasks
        task_data = [t.model_dump(mode="json") for t in emp.task_manager.list_tasks()]
        records[eid] = {
            "profile": {
                "full_name": p.full_name,
                "role": p.role,
                "department": p.department,
                "team": p.team,
                "skills": p.skills,
                "timezone": p.timezone,
                "reporting_to": p.reporting_to,
                "company_name": p.company_name,
                "bio": p.bio,
            },
            "kt_summaries": kt_data,
            "tasks": task_data,
        }
    _EMPLOYEES_FILE.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")


def _load_employees() -> None:
    """Restore persisted employees, KT summaries, and tasks on startup."""
    if not _EMPLOYEES_FILE.exists():
        return
    try:
        records = json.loads(_EMPLOYEES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    for eid, data in records.items():
        if eid in _employees:
            continue
        try:
            # Support both old format (flat profile) and new format (nested)
            profile_data = data.get("profile", data)
            model = _build_model(_llm_config["provider"], _llm_config["model_id"], None)
            profile = EmployeeProfile(**{k: v for k, v in profile_data.items() if v is not None})
            emp = PulseEmployee(employee_profile=profile, model=model)

            # Restore KT summaries
            from buddy.pulse.kt import KTSummary
            for s_data in data.get("kt_summaries", []):
                try:
                    summary = KTSummary(**s_data)
                    emp.kt_manager.commit_summary(summary)
                    emp._store_kt_in_memory(summary)
                except Exception:
                    pass

            # Restore tasks
            from buddy.pulse.work import WorkItem
            for t_data in data.get("tasks", []):
                try:
                    task = WorkItem(**t_data)
                    emp.task_manager._tasks[task.task_id] = task
                except Exception:
                    pass

            _employees[eid] = emp
        except Exception:
            pass


# ---------------------------------------------------------------------------
# In-memory employee registry
# ---------------------------------------------------------------------------
_employees: Dict[str, PulseEmployee] = {}
_kt_sessions: Dict[str, KTSession] = {}

# ---------------------------------------------------------------------------
# Activity log — every autonomous action PULSE takes is recorded here
# ---------------------------------------------------------------------------
from datetime import datetime
from collections import deque

class ActivityEvent:
    def __init__(self, employee_id: str, event_type: str, title: str, detail: str = "") -> None:
        self.employee_id = employee_id
        self.event_type = event_type   # task_started | task_done | kt_learned | standup | suggestion | message
        self.title = title
        self.detail = detail
        self.ts = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {"employee_id": self.employee_id, "event_type": self.event_type,
                "title": self.title, "detail": self.detail, "ts": self.ts}

# Per-employee capped activity log (last 200 events)
_activity_log: Dict[str, deque] = {}   # employee_id -> deque[ActivityEvent]

# Notifications queue — proactive messages from PULSE to the user
_notifications: Dict[str, deque] = {}  # employee_id -> deque[dict]


def _log(employee_id: str, event_type: str, title: str, detail: str = "") -> None:
    if employee_id not in _activity_log:
        _activity_log[employee_id] = deque(maxlen=200)
    _activity_log[employee_id].appendleft(ActivityEvent(employee_id, event_type, title, detail))


def _notify(employee_id: str, message: str, notif_type: str = "info") -> None:
    if employee_id not in _notifications:
        _notifications[employee_id] = deque(maxlen=50)
    _notifications[employee_id].appendleft({
        "id": str(uuid4())[:8],
        "message": message,
        "type": notif_type,
        "ts": datetime.utcnow().isoformat(),
        "read": False,
    })


# ---------------------------------------------------------------------------
# Autonomous task worker — PULSE picks up and executes tasks automatically
# ---------------------------------------------------------------------------
_auto_work_enabled: bool = True
_TASK_POLL_INTERVAL: int = 30
_auto_work_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]


def _build_kt_block(emp: "PulseEmployee", max_summaries: int = 3, max_chars: int = 800) -> str:
    kt_summaries = emp.kt_manager.all_summaries()
    if not kt_summaries:
        return ""
    return "KNOWLEDGE BASE:\n" + "\n\n".join(
        f"[{s.session_name}] {s.mental_model[:max_chars]}"
        for s in kt_summaries[-max_summaries:]
    ) + "\n\n---\n"


async def _autonomous_worker() -> None:
    """
    Background loop — PULSE autonomously works tasks, generates daily standups,
    suggests new tasks when idle, and sends proactive notifications.
    """
    await asyncio.sleep(5)
    loop = asyncio.get_event_loop()
    last_standup_date: Dict[str, str] = {}   # employee_id -> date str
    last_suggest_date: Dict[str, str] = {}   # employee_id -> date str

    while True:
        if _auto_work_enabled and _employees:
            today = datetime.utcnow().strftime("%Y-%m-%d")

            for employee_id, emp in list(_employees.items()):
                from buddy.pulse.work import TaskStatus

                # ── 1. Work on the next todo task ──────────────────────────
                pending = emp.task_manager.list_tasks(TaskStatus.TODO)
                if pending:
                    task = pending[0]
                    try:
                        task.status = TaskStatus.IN_PROGRESS
                        task.updated_at = datetime.utcnow()
                        _save_employees()
                        _log(employee_id, "task_started", f"Started: {task.title}")

                        kt_block = _build_kt_block(emp)
                        prompt = (
                            f"You are {emp.employee_profile.full_name}, a {emp.employee_profile.role} "
                            f"at {emp.employee_profile.company_name or 'the company'}.\n\n"
                            f"{kt_block}"
                            f"TASK ASSIGNED TO YOU:\n"
                            f"Title: {task.title}\n"
                            f"Description: {task.description or 'No additional description.'}\n"
                            f"Priority: {task.priority.value}\n\n"
                            f"Complete this task as a professional employee. Produce actual, detailed work output. "
                            f"End with a one-line summary on a new line starting with 'SUMMARY:'."
                        )

                        response = await asyncio.wait_for(
                            loop.run_in_executor(None, lambda p=prompt: emp.run(p, stream=False)),
                            timeout=90.0,
                        )
                        output = response.content if hasattr(response, "content") else str(response)
                        lines = output.strip().split("\n")
                        summary_line = next(
                            (l.replace("SUMMARY:", "").strip() for l in lines if l.startswith("SUMMARY:")),
                            task.title,
                        )
                        task.add_note(f"[AUTO] {output.strip()}")
                        task.status = TaskStatus.DONE
                        task.completed_at = datetime.utcnow()
                        task.updated_at = task.completed_at
                        _save_employees()
                        _log(employee_id, "task_done", f"Completed: {task.title}", summary_line)
                        _notify(employee_id,
                                f"I finished '{task.title}'. {summary_line}",
                                "success")

                    except asyncio.TimeoutError:
                        task.add_note("[AUTO] Timed out. Will retry.")
                        task.status = TaskStatus.TODO
                        task.updated_at = datetime.utcnow()
                        _save_employees()
                        _log(employee_id, "task_error", f"Timeout on: {task.title}")

                    except Exception as exc:
                        task.add_note(f"[AUTO] Error: {exc}")
                        task.status = TaskStatus.TODO
                        task.updated_at = datetime.utcnow()
                        _save_employees()
                        _log(employee_id, "task_error", f"Error on: {task.title}", str(exc))

                # ── 2. Daily standup (once per day, after any work is done) ─
                elif last_standup_date.get(employee_id) != today:
                    try:
                        kt_block = _build_kt_block(emp, max_summaries=2, max_chars=400)
                        done_tasks = emp.task_manager.list_tasks(TaskStatus.DONE)[-5:]
                        todo_tasks = emp.task_manager.list_tasks(TaskStatus.TODO)[:3]
                        task_ctx = ""
                        if done_tasks:
                            task_ctx += "Recently completed:\n" + "\n".join(f"- {t.title}" for t in done_tasks) + "\n"
                        if todo_tasks:
                            task_ctx += "Upcoming:\n" + "\n".join(f"- {t.title}" for t in todo_tasks) + "\n"

                        prompt = (
                            f"You are {emp.employee_profile.full_name}, a {emp.employee_profile.role}.\n\n"
                            f"{kt_block}"
                            f"{task_ctx}\n"
                            f"Write a brief (3-5 bullet) daily standup update in first person. "
                            f"Cover: what you did, what you'll work on next, and any observations. "
                            f"Be concise and professional."
                        )
                        response = await asyncio.wait_for(
                            loop.run_in_executor(None, lambda p=prompt: emp.run(p, stream=False)),
                            timeout=60.0,
                        )
                        standup = response.content if hasattr(response, "content") else str(response)
                        last_standup_date[employee_id] = today
                        _log(employee_id, "standup", "Daily standup", standup.strip())
                        _notify(employee_id, standup.strip(), "standup")
                    except Exception:
                        pass

                # ── 3. Suggest tasks when idle (once per day) ───────────────
                if last_suggest_date.get(employee_id) != today:
                    try:
                        kt_block = _build_kt_block(emp, max_summaries=2, max_chars=500)
                        all_tasks = emp.task_manager.list_tasks()
                        existing = "\n".join(f"- {t.title}" for t in all_tasks[:10]) if all_tasks else "None"
                        prompt = (
                            f"You are {emp.employee_profile.full_name}, a {emp.employee_profile.role} "
                            f"at {emp.employee_profile.company_name or 'the company'}.\n\n"
                            f"{kt_block}"
                            f"Current tasks:\n{existing}\n\n"
                            f"Based on your role, skills ({', '.join(emp.employee_profile.skills[:5])}), "
                            f"and knowledge, suggest exactly 3 high-value tasks you could work on proactively. "
                            f"Return ONLY a JSON array: "
                            f'[{{"title":"...","description":"...","priority":"medium"}},...]\n'
                            f"No other text."
                        )
                        response = await asyncio.wait_for(
                            loop.run_in_executor(None, lambda p=prompt: emp.run(p, stream=False)),
                            timeout=60.0,
                        )
                        raw = response.content if hasattr(response, "content") else str(response)
                        import re as _re
                        m = _re.search(r'\[.*\]', raw, _re.S)
                        if m:
                            suggestions = json.loads(m.group())
                            for s in suggestions[:3]:
                                if isinstance(s, dict) and s.get("title"):
                                    _notify(
                                        employee_id,
                                        f"Task suggestion: {s['title']} — {s.get('description', '')}",
                                        "suggestion",
                                    )
                            titles = ", ".join(s.get("title", "") for s in suggestions[:3] if isinstance(s, dict))
                            _log(employee_id, "suggestion", "Suggested tasks", titles)
                        last_suggest_date[employee_id] = today
                    except Exception:
                        pass

        await asyncio.sleep(_TASK_POLL_INTERVAL)


def start_auto_worker() -> None:
    global _auto_work_task
    loop = asyncio.get_event_loop()
    _auto_work_task = loop.create_task(_autonomous_worker())


def _get_employee(employee_id: str) -> PulseEmployee:
    emp = _employees.get(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found")
    return emp


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateEmployeeRequest(BaseModel):
    full_name: str
    role: str
    department: str = "Engineering"
    team: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    timezone: str = "UTC"
    reporting_to: Optional[str] = None
    company_name: Optional[str] = None
    bio: Optional[str] = None
    model_id: str = "gpt-4o"
    model_provider: str = "openai"


class UpdateEmployeeRequest(BaseModel):
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    reporting_to: Optional[str] = None
    company_name: Optional[str] = None


class OnboardRequest(BaseModel):
    company_docs: List[str] = Field(default_factory=list)
    team_members: List[Dict[str, str]] = Field(default_factory=list)


class AsyncKTRequest(BaseModel):
    source: str = Field(..., description="File path, URL, or raw text content")
    source_type: str = "document"
    session_name: str
    knowledge_giver: str
    confidence_threshold: float = 0.82


class LiveKTCreateRequest(BaseModel):
    session_name: str
    knowledge_giver: str
    source_type: str = "human_chat"
    confidence_threshold: float = 0.82
    max_rounds: int = 12


class HumanExplainsRequest(BaseModel):
    text: str


class HumanAnswersRequest(BaseModel):
    answers: Dict[str, str]


class HumanCorrectsRequest(BaseModel):
    correction: str


class MeetingRequest(BaseModel):
    transcript: str
    participants: List[str] = Field(default_factory=list)
    platform: str = "other"
    title: Optional[str] = None


class TaskRequest(BaseModel):
    description: str
    title: Optional[str] = None
    priority: str = "medium"
    deadline: Optional[str] = None
    assigned_by: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str


class FeedbackRequest(BaseModel):
    content: str
    given_by: str
    category: str = "other"
    sentiment: str = "neutral"


# ---------------------------------------------------------------------------
# Employee management
# ---------------------------------------------------------------------------

@router.post("/employees")
async def create_employee(req: CreateEmployeeRequest) -> Dict[str, Any]:
    """Create a new PULSE employee and register it."""
    try:
        model = _build_model(req.model_provider, req.model_id, None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Model init failed: {e}")

    profile = EmployeeProfile(
        full_name=req.full_name,
        role=req.role,
        department=req.department,
        team=req.team,
        skills=req.skills,
        timezone=req.timezone,
        reporting_to=req.reporting_to,
        company_name=req.company_name,
        bio=req.bio,
    )
    employee_id = str(uuid4())[:8]
    emp = PulseEmployee(employee_profile=profile, model=model)
    _employees[employee_id] = emp
    _save_employees()
    return {"employee_id": employee_id, "profile": profile.model_dump()}


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    return {
        "employee_id": employee_id,
        "profile": emp.employee_profile.model_dump(),
        "memory_summary": emp.professional_memory.professional_summary(),
        "task_summary": emp.task_manager.task_summary(),
        "kt_domains": emp.professional_memory.get_kt_domains(),
    }


@router.put("/employees/{employee_id}")
async def update_employee(employee_id: str, req: UpdateEmployeeRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    if req.bio is not None:
        emp.employee_profile.bio = req.bio
    if req.skills is not None:
        emp.employee_profile.skills = req.skills
    if req.reporting_to is not None:
        emp.employee_profile.reporting_to = req.reporting_to
    if req.company_name is not None:
        emp.employee_profile.company_name = req.company_name
    _save_employees()
    return {"employee_id": employee_id, "updated": True}


@router.post("/employees/{employee_id}/onboard")
async def onboard_employee(employee_id: str, req: OnboardRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    result = emp.run_onboarding(
        company_docs=req.company_docs,
        team_members=req.team_members,
    )
    return result


# ---------------------------------------------------------------------------
# KT — async source mode
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/kt/async")
async def kt_async(employee_id: str, req: AsyncKTRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    try:
        source_type = KTSourceType(req.source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source_type: {req.source_type!r}")

    loop = asyncio.get_event_loop()
    try:
        summary = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: emp.take_kt(
                    source=req.source,
                    source_type=source_type,
                    session_name=req.session_name,
                    knowledge_giver=req.knowledge_giver,
                    confidence_threshold=req.confidence_threshold,
                ),
            ),
            timeout=180.0,  # PDF crawl + LLM can take up to 3 min
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="KT processing timed out. Try with a smaller document.")
    _save_employees()
    return summary.model_dump(mode="json")


# ---------------------------------------------------------------------------
# KT — live human mode
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/kt/live")
async def kt_live_create(employee_id: str, req: LiveKTCreateRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    try:
        source_type = KTSourceType(req.source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source_type: {req.source_type!r}")

    session = emp.start_live_kt(
        session_name=req.session_name,
        knowledge_giver=req.knowledge_giver,
        source_type=source_type,
        confidence_threshold=req.confidence_threshold,
        max_rounds=req.max_rounds,
    )
    _kt_sessions[session.session_id] = session
    return {"session_id": session.session_id, "state": session.state.model_dump()}


@router.post("/{employee_id}/kt/{session_id}/explain")
async def kt_human_explains(employee_id: str, session_id: str, req: HumanExplainsRequest) -> Dict[str, Any]:
    _get_employee(employee_id)
    session = _kt_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"KT session '{session_id}' not found")
    turn = session.human_explains(req.text)
    return turn.model_dump()


@router.post("/{employee_id}/kt/{session_id}/answer")
async def kt_human_answers(employee_id: str, session_id: str, req: HumanAnswersRequest) -> Dict[str, Any]:
    _get_employee(employee_id)
    session = _kt_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"KT session '{session_id}' not found")
    turn = session.human_answers(req.answers)
    return turn.model_dump()


@router.post("/{employee_id}/kt/{session_id}/correct")
async def kt_human_corrects(employee_id: str, session_id: str, req: HumanCorrectsRequest) -> Dict[str, Any]:
    _get_employee(employee_id)
    session = _kt_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"KT session '{session_id}' not found")
    turn = session.human_corrects(req.correction)
    return turn.model_dump()


@router.post("/{employee_id}/kt/{session_id}/commit")
async def kt_commit(employee_id: str, session_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    session = _kt_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"KT session '{session_id}' not found")
    loop = asyncio.get_event_loop()
    summary = await asyncio.wait_for(
        loop.run_in_executor(None, lambda: emp.finalize_kt_session(session)),
        timeout=120.0,
    )
    _save_employees()
    return summary.model_dump(mode="json")


@router.get("/{employee_id}/kt")
async def list_kt_sessions(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    summaries = emp.kt_manager.all_summaries()
    return {"sessions": [s.model_dump(mode="json") for s in summaries]}


@router.get("/{employee_id}/kt/{session_id}")
async def get_kt_session(employee_id: str, session_id: str) -> Dict[str, Any]:
    _get_employee(employee_id)
    session = _kt_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"KT session '{session_id}' not found")
    return {
        "session_id": session_id,
        "state": session.state.model_dump(),
        "summary": emp.kt_manager._summaries.get(session_id, {}).model_dump()  # type: ignore[attr-defined]
        if session_id in (emp := _get_employee(employee_id)).kt_manager._summaries else None,
    }


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/meetings")
async def process_meeting(employee_id: str, req: MeetingRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    try:
        platform = MeetingPlatform(req.platform)
    except ValueError:
        platform = MeetingPlatform.OTHER
    loop = asyncio.get_event_loop()
    try:
        notes = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: emp.attend_meeting(
                    transcript=req.transcript,
                    participants=req.participants or None,
                    platform=platform,
                    title=req.title,
                ),
            ),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Meeting processing timed out. Please try again.")
    _save_employees()
    return notes.model_dump(mode="json")


@router.get("/{employee_id}/meetings")
async def list_meetings(employee_id: str) -> Dict[str, Any]:
    return {"meetings": [], "note": "Persistent meeting storage not yet wired — coming soon."}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/tasks")
async def assign_task(employee_id: str, req: TaskRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    task = emp.receive_task(
        description=req.description,
        title=req.title,
        priority=req.priority,
        deadline=req.deadline,
        assigned_by=req.assigned_by,
        tags=req.tags,
    )
    _save_employees()
    return task.model_dump(mode="json")


@router.get("/{employee_id}/tasks")
async def list_tasks(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    return {"tasks": [t.model_dump(mode="json") for t in emp.task_manager.list_tasks()]}


@router.put("/{employee_id}/tasks/{task_id}")
async def update_task(employee_id: str, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    task = emp.task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    if "status" in updates:
        from buddy.pulse.work import TaskStatus
        new_status = TaskStatus(updates["status"])
        task.status = new_status
        # Generate completion note in background thread (non-blocking)
        if new_status == TaskStatus.DONE and not any("✅" in n for n in task.progress_notes):
            async def _add_completion_note() -> None:
                try:
                    prompt = (
                        f"You are {emp.employee_profile.full_name} ({emp.employee_profile.role}).\n"
                        f"You just completed the following task:\n\n"
                        f"Title: {task.title}\n"
                        f"Description: {task.description or 'No description'}\n\n"
                        f"Write a brief (2-4 sentences) first-person completion note summarising "
                        f"what you did, the outcome, and any relevant observations."
                    )
                    loop = asyncio.get_event_loop()
                    resp = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: emp.run(prompt, stream=False)),
                        timeout=60.0,
                    )
                    note = resp.content if hasattr(resp, "content") else str(resp)
                    task.add_note(f"✅ {note.strip()}")
                except Exception:
                    task.add_note("✅ Task marked as done.")
                finally:
                    _save_employees()
            asyncio.create_task(_add_completion_note())
    if "note" in updates:
        task.add_note(updates["note"])
    _save_employees()
    return task.model_dump(mode="json")


@router.get("/{employee_id}/tasks/{task_id}/status-update")
async def task_status_update(employee_id: str, task_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    loop = asyncio.get_event_loop()
    try:
        update = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: emp.report_status(task_id=task_id)),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        from buddy.pulse.work import StatusUpdate
        update = StatusUpdate(
            employee_name=emp.employee_profile.full_name,
            update_type="task_update",
            task_id=task_id,
            message="Status report timed out. Please try again.",
        )
    return update.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/chat")
async def chat(employee_id: str, req: ChatRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)

    # Inject KT knowledge into context (same logic as WebSocket stream)
    kt_summaries = emp.kt_manager.all_summaries()
    if kt_summaries:
        knowledge_block = "\n\n".join(
            f"[KT: {s.session_name} | confidence {s.confidence_score:.0%}]\n"
            f"{s.mental_model[:1500]}\n"
            f"Key concepts: {', '.join(s.key_concepts)}"
            for s in kt_summaries[-5:]
        )
        augmented = (
            f"KNOWLEDGE BASE (from your KT sessions):\n"
            f"{knowledge_block}\n\n"
            f"---\n"
            f"User message: {req.message}\n\n"
            f"Answer using your knowledge above when relevant. "
            f"Speak in first person as a knowledgeable employee."
        )
    else:
        augmented = req.message

    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: emp.run(augmented, stream=False)),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        return {"response": "Sorry, response timed out. Please try again.", "employee": emp.employee_profile.full_name}

    content = response.content if hasattr(response, "content") else str(response)
    return {"response": content, "employee": emp.employee_profile.full_name}


@router.websocket("/{employee_id}/chat/stream")
async def chat_stream(websocket: WebSocket, employee_id: str) -> None:
    await websocket.accept()
    emp = _employees.get(employee_id)
    if not emp:
        await websocket.send_json({"error": f"Employee '{employee_id}' not found"})
        await websocket.close()
        return
    loop = asyncio.get_event_loop()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")

            # Inject KT knowledge (cap at 5 most recent to avoid token limits)
            kt_summaries = emp.kt_manager.all_summaries()
            if kt_summaries:
                knowledge_block = "\n\n".join(
                    f"[KT: {s.session_name} | confidence {s.confidence_score:.0%}]\n"
                    f"{s.mental_model[:1500]}\n"
                    f"Key concepts: {', '.join(s.key_concepts)}"
                    for s in kt_summaries[-5:]  # most recent 5 only
                )
                augmented = (
                    f"KNOWLEDGE BASE (from your KT sessions):\n"
                    f"{knowledge_block}\n\n"
                    f"---\n"
                    f"User message: {message}\n\n"
                    f"Answer using your knowledge above when relevant. "
                    f"Speak in first person as a knowledgeable employee."
                )
            else:
                augmented = message

            # Run the synchronous LLM call in a thread so it doesn't block
            # the async event loop (which would freeze the WebSocket)
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda msg=augmented: emp.run(msg, stream=False)),
                    timeout=60.0,
                )
                content = response.content if hasattr(response, "content") else str(response)
            except asyncio.TimeoutError:
                await websocket.send_json({"chunk": "Sorry, the response timed out. Please try again.", "done": False})
                await websocket.send_json({"chunk": "", "done": True})
                continue
            except Exception as e:
                await websocket.send_json({"chunk": f"Error: {e}", "done": False})
                await websocket.send_json({"chunk": "", "done": True})
                continue

            # Stream back word-by-word for a smooth typing effect
            words = content.split(" ")
            for i, word in enumerate(words):
                chunk = word + ("" if i == len(words) - 1 else " ")
                await websocket.send_json({"chunk": chunk, "done": False})
                await asyncio.sleep(0.008)

            await websocket.send_json({"chunk": "", "done": True})
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Knowledge explorer
# ---------------------------------------------------------------------------

@router.get("/{employee_id}/knowledge/search")
async def knowledge_search(employee_id: str, q: str = "") -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    results = emp.kt_manager.search_knowledge(q)
    return {"query": q, "results": [r.model_dump() for r in results]}


@router.get("/{employee_id}/knowledge/summary")
async def knowledge_summary(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    return {
        "domains": emp.professional_memory.get_kt_domains(),
        "kt_sessions": [s.model_dump() for s in emp.kt_manager.all_summaries()],
        "memory_summary": emp.professional_memory.professional_summary(),
    }


# ---------------------------------------------------------------------------
# EOD summary
# ---------------------------------------------------------------------------

@router.get("/{employee_id}/eod-summary")
async def eod_summary(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    update = emp.report_status()
    return update.model_dump()


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/feedback")
async def receive_feedback(employee_id: str, req: FeedbackRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    entry = emp.receive_feedback(
        content=req.content,
        given_by=req.given_by,
        category=req.category,
        sentiment=req.sentiment,
    )
    return entry.model_dump()


# ---------------------------------------------------------------------------
# LLM settings
# ---------------------------------------------------------------------------

# Provider → env var name
_PROVIDER_ENV_KEYS: Dict[str, str] = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude":    "ANTHROPIC_API_KEY",
    "google":    "GOOGLE_API_KEY",
    "gemini":    "GOOGLE_API_KEY",
    "groq":      "GROQ_API_KEY",
    "ollama":    "",   # no key needed
}

# Active LLM config (single global for the server process)
_llm_config: Dict[str, str] = {
    "provider": "openai",
    "model_id": "gpt-4o",
}


class LLMSettingsRequest(BaseModel):
    provider: str
    model_id: str
    api_key: Optional[str] = None  # None means "keep existing"
    base_url: Optional[str] = None  # For Ollama / custom endpoints


# ---------------------------------------------------------------------------
# Auto-work settings
# ---------------------------------------------------------------------------

@router.get("/settings/auto-work")
async def get_auto_work_settings() -> Dict[str, Any]:
    return {"enabled": _auto_work_enabled, "poll_interval_seconds": _TASK_POLL_INTERVAL}


@router.post("/settings/auto-work")
async def set_auto_work_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    global _auto_work_enabled, _TASK_POLL_INTERVAL
    if "enabled" in body:
        _auto_work_enabled = bool(body["enabled"])
    if "poll_interval_seconds" in body:
        _TASK_POLL_INTERVAL = max(10, min(int(body["poll_interval_seconds"]), 3600))
    return {"enabled": _auto_work_enabled, "poll_interval_seconds": _TASK_POLL_INTERVAL}


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

@router.get("/{employee_id}/activity")
async def get_activity(employee_id: str, limit: int = 50) -> Dict[str, Any]:
    _get_employee(employee_id)
    events = list(_activity_log.get(employee_id, deque()))[:limit]
    return {"events": [e.to_dict() for e in events]}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.get("/{employee_id}/notifications")
async def get_notifications(employee_id: str) -> Dict[str, Any]:
    _get_employee(employee_id)
    notifs = list(_notifications.get(employee_id, deque()))
    return {"notifications": notifs, "unread": sum(1 for n in notifs if not n["read"])}


@router.post("/{employee_id}/notifications/{notif_id}/read")
async def mark_notification_read(employee_id: str, notif_id: str) -> Dict[str, Any]:
    _get_employee(employee_id)
    for n in _notifications.get(employee_id, deque()):
        if n["id"] == notif_id:
            n["read"] = True
    return {"ok": True}


@router.post("/{employee_id}/notifications/read-all")
async def mark_all_read(employee_id: str) -> Dict[str, Any]:
    _get_employee(employee_id)
    for n in _notifications.get(employee_id, deque()):
        n["read"] = True
    return {"ok": True}


# ---------------------------------------------------------------------------
# Daily standup (on-demand trigger)
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/standup")
async def generate_standup(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    from buddy.pulse.work import TaskStatus
    done_tasks = emp.task_manager.list_tasks(TaskStatus.DONE)[-5:]
    todo_tasks = emp.task_manager.list_tasks(TaskStatus.TODO)[:3]
    task_ctx = ""
    if done_tasks:
        task_ctx += "Recently completed:\n" + "\n".join(f"- {t.title}" for t in done_tasks) + "\n"
    if todo_tasks:
        task_ctx += "Upcoming:\n" + "\n".join(f"- {t.title}" for t in todo_tasks) + "\n"
    kt_block = _build_kt_block(emp, max_summaries=2, max_chars=400)
    prompt = (
        f"You are {emp.employee_profile.full_name}, a {emp.employee_profile.role}.\n\n"
        f"{kt_block}"
        f"{task_ctx}\n"
        f"Write a concise daily standup (3-5 bullets) in first person covering: "
        f"what you did, what you'll work on next, and any blockers or observations."
    )
    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: emp.run(prompt, stream=False)),
            timeout=60.0,
        )
        standup = response.content if hasattr(response, "content") else str(response)
    except asyncio.TimeoutError:
        standup = "Standup generation timed out."
    _log(employee_id, "standup", "Daily standup", standup.strip())
    _notify(employee_id, standup.strip(), "standup")
    return {"standup": standup.strip(), "ts": datetime.utcnow().isoformat()}


# ---------------------------------------------------------------------------
# Task suggestions — PULSE proactively suggests what it should work on
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/suggest-tasks")
async def suggest_tasks(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    all_tasks = emp.task_manager.list_tasks()
    existing = "\n".join(f"- {t.title}" for t in all_tasks[:10]) if all_tasks else "None"
    kt_block = _build_kt_block(emp, max_summaries=2, max_chars=500)
    prompt = (
        f"You are {emp.employee_profile.full_name}, a {emp.employee_profile.role} "
        f"at {emp.employee_profile.company_name or 'the company'}.\n\n"
        f"{kt_block}"
        f"Current tasks:\n{existing}\n\n"
        f"Based on your role, skills ({', '.join(emp.employee_profile.skills[:5])}), and knowledge, "
        f"suggest exactly 3 high-value tasks you should work on proactively. "
        f'Return ONLY a JSON array: [{{"title":"...","description":"...","priority":"medium"}},...]\nNo other text.'
    )
    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: emp.run(prompt, stream=False)),
            timeout=60.0,
        )
        raw = response.content if hasattr(response, "content") else str(response)
        import re as _re
        m = _re.search(r'\[.*\]', raw, _re.S)
        suggestions = json.loads(m.group()) if m else []
    except Exception:
        suggestions = []
    return {"suggestions": suggestions[:3]}


@router.get("/settings/llm")
async def get_llm_settings() -> Dict[str, Any]:
    """Return current LLM configuration (key is masked)."""
    import os
    provider = _llm_config.get("provider", "openai")
    env_var  = _PROVIDER_ENV_KEYS.get(provider.lower(), "")
    raw_key  = os.environ.get(env_var, "") if env_var else ""
    masked   = ("*" * 8 + raw_key[-4:]) if len(raw_key) > 4 else ("*" * len(raw_key) if raw_key else "")
    return {
        "provider":    provider,
        "model_id":    _llm_config.get("model_id", "gpt-4o"),
        "env_var":     env_var,
        "key_set":     bool(raw_key),
        "key_masked":  masked,
        "base_url":    _llm_config.get("base_url", ""),
    }


@router.post("/settings/llm")
async def save_llm_settings(req: LLMSettingsRequest) -> Dict[str, Any]:
    """
    Persist LLM provider/model/key for this server process.

    - Updates the OS environment so that model libraries pick up the key.
    - Re-wires the model on all registered employees.
    """
    import os
    _llm_config["provider"] = req.provider
    _llm_config["model_id"]  = req.model_id
    if req.base_url is not None:
        _llm_config["base_url"] = req.base_url

    # Inject API key into env so all model SDKs find it
    env_var = _PROVIDER_ENV_KEYS.get(req.provider.lower(), "")
    if req.api_key and env_var:
        os.environ[env_var] = req.api_key

    # Re-wire existing employees to the new model
    errors: List[str] = []
    for emp_id, emp in _employees.items():
        try:
            emp.model = _build_model(req.provider, req.model_id, req.base_url)
        except Exception as exc:
            errors.append(f"{emp_id}: {exc}")

    return {
        "saved":    True,
        "provider": req.provider,
        "model_id": req.model_id,
        "env_var":  env_var,
        "key_set":  bool(req.api_key or (env_var and os.environ.get(env_var))),
        "rewired":  len(_employees),
        "errors":   errors,
    }


@router.post("/settings/llm/test")
async def test_llm_connection(req: LLMSettingsRequest) -> Dict[str, Any]:
    """
    Attempt to instantiate the model and send a tiny ping message.
    Returns success/failure without persisting anything.
    """
    import os
    env_var = _PROVIDER_ENV_KEYS.get(req.provider.lower(), "")
    if req.api_key and env_var:
        os.environ[env_var] = req.api_key

    try:
        model = _build_model(req.provider, req.model_id, req.base_url)
        # Minimal call — just create a throwaway employee and run a ping
        from buddy.pulse.identity import EmployeeProfile
        test_profile = EmployeeProfile(
            full_name="Test",
            role="Test",
            department="Test",
            skills=[],
            timezone="UTC",
        )
        test_emp = PulseEmployee(employee_profile=test_profile, model=model)
        resp = test_emp.run("Reply with exactly: OK", stream=False)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return {"success": True, "response": content[:120]}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_model(provider: str, model_id: str, base_url: Optional[str] = None) -> Any:
    provider_lower = provider.lower()
    if provider_lower == "openai":
        from buddy.models.openai import OpenAIChat
        kwargs: Dict[str, Any] = {"id": model_id}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAIChat(**kwargs)
    if provider_lower in ("anthropic", "claude"):
        from buddy.models.anthropic import Claude
        return Claude(id=model_id)
    if provider_lower in ("google", "gemini"):
        from buddy.models.google import Gemini
        return Gemini(id=model_id)
    if provider_lower in ("groq",):
        from buddy.models.groq import Groq
        return Groq(id=model_id)
    if provider_lower in ("ollama",):
        from buddy.models.ollama import Ollama
        kwargs = {"id": model_id}
        if base_url:
            kwargs["base_url"] = base_url
        return Ollama(**kwargs)
    # Default fallback
    from buddy.models.openai import OpenAIChat
    return OpenAIChat(id=model_id)
