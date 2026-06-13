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
# In-memory employee registry (replace with DB-backed store in production)
# ---------------------------------------------------------------------------
_employees: Dict[str, PulseEmployee] = {}
_kt_sessions: Dict[str, KTSession] = {}


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

    summary = emp.take_kt(
        source=req.source,
        source_type=source_type,
        session_name=req.session_name,
        knowledge_giver=req.knowledge_giver,
        confidence_threshold=req.confidence_threshold,
    )
    return summary.model_dump()


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
    summary = emp.finalize_kt_session(session)
    return summary.model_dump()


@router.get("/{employee_id}/kt")
async def list_kt_sessions(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    summaries = emp.kt_manager.all_summaries()
    return {"sessions": [s.model_dump() for s in summaries]}


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
    notes = emp.attend_meeting(
        transcript=req.transcript,
        participants=req.participants or None,
        platform=platform,
        title=req.title,
    )
    return notes.model_dump()


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
    return task.model_dump()


@router.get("/{employee_id}/tasks")
async def list_tasks(employee_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    return {"tasks": [t.model_dump() for t in emp.task_manager.list_tasks()]}


@router.put("/{employee_id}/tasks/{task_id}")
async def update_task(employee_id: str, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    task = emp.task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    if "status" in updates:
        from buddy.pulse.work import TaskStatus
        task.status = TaskStatus(updates["status"])
    if "note" in updates:
        task.add_note(updates["note"])
    return task.model_dump()


@router.get("/{employee_id}/tasks/{task_id}/status-update")
async def task_status_update(employee_id: str, task_id: str) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    update = emp.report_status(task_id=task_id)
    return update.model_dump()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/{employee_id}/chat")
async def chat(employee_id: str, req: ChatRequest) -> Dict[str, Any]:
    emp = _get_employee(employee_id)
    response = emp.run(req.message, stream=False)
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
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            for chunk in emp.run(message, stream=True):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    await websocket.send_json({"chunk": content, "done": False})
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
