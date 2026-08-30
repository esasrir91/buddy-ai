"""FastAPI backend for Buddy Code (the Cursor-like coding app).

Endpoints
---------
GET  /api/health
GET  /api/settings                 - current settings (API keys redacted) + workspace
PUT  /api/settings                 - update settings (partial; masked keys preserved)
GET  /api/models                   - available models (from the auto-introspection catalog)
GET  /api/tools                    - available tools (from the catalog)
GET  /api/workspace                - current workspace path
POST /api/workspace                - set the workspace path
GET  /api/fs/list?path=            - list immediate children of a directory
GET  /api/fs/file?path=            - read a file
PUT  /api/fs/file                  - write a file
POST /api/chat                     - run the coding agent, streaming events (SSE)

Serves the built frontend (if present at ``buddy/code/server/static``) at ``/``.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import buddy.models as _models  # noqa: F401  init order

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from buddy.code import entitlements as entitlements_gate
from buddy.code.agent import build_code_agent
from buddy.code.custom_tools import (
    delete_custom_tool,
    generate_tool_code,
    list_custom_tools,
    save_custom_tool,
)
from buddy.code.offline import offline_status
from buddy.code.settings import (
    PROVIDER_ENV_KEYS,
    CodeSettings,
    load_settings,
    merge_settings_update,
    save_settings,
)
from buddy.code.training import TrainingManager, available_models, training_deps_ok
from buddy.code.tools import _IGNORE_DIRS  # noqa: F401 (also used in _search_workspace)

_STATIC_DIR = Path(__file__).parent / "static"
_AURA_DIR = Path.home() / ".aura"
_RECENT_PATH = _AURA_DIR / "recent.json"


def _load_last_workspace() -> Path:
    """Return last opened workspace, falling back to home dir."""
    try:
        if _RECENT_PATH.exists():
            data = json.loads(_RECENT_PATH.read_text(encoding="utf-8"))
            recent = data.get("recent", [])
            if recent:
                p = Path(recent[0])
                if p.is_dir():
                    return p
    except Exception:
        pass
    return Path.home()


def _save_recent_workspace(path: Path) -> None:
    """Persist opened folder to recent list (max 10)."""
    try:
        _AURA_DIR.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}
        if _RECENT_PATH.exists():
            try:
                data = json.loads(_RECENT_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        recent: List[str] = [str(path)] + [
            p for p in data.get("recent", []) if p != str(path)
        ]
        data["recent"] = recent[:10]
        _RECENT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── File-backed session store ─────────────────────────────────────────────

def _sessions_dir(workspace: Path) -> Path:
    d = workspace / ".aura" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_path(workspace: Path, session_id: str) -> Path:
    return _sessions_dir(workspace) / f"{session_id}.json"


def _load_session(workspace: Path, session_id: str) -> Optional[Dict[str, Any]]:
    p = _session_path(workspace, session_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_session(workspace: Path, data: Dict[str, Any]) -> None:
    p = _session_path(workspace, data["id"])
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _list_sessions(workspace: Path) -> List[Dict[str, Any]]:
    d = _sessions_dir(workspace)
    sessions = []
    for f in d.glob("*.json"):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({"id": s["id"], "title": s.get("title", "Chat"), "updated": s.get("updated", 0)})
        except Exception:
            pass
    return sorted(sessions, key=lambda x: x["updated"], reverse=True)


def _delete_session(workspace: Path, session_id: str) -> None:
    p = _session_path(workspace, session_id)
    if p.exists():
        p.unlink()


class _State:
    """Runtime state: current workspace + cached agent (rebuilt on change)."""

    def __init__(self) -> None:
        env_ws = os.getenv("BUDDY_CODE_WORKSPACE")
        if env_ws:
            self.workspace: Path = Path(env_ws).resolve()
        else:
            # Load last workspace from ~/.aura/recent.json, fall back to home dir
            self.workspace = _load_last_workspace()
        self.settings: CodeSettings = load_settings()
        self.settings.apply_to_env()
        self._agent = None
        self._agent_signature: Optional[str] = None
        self.diagnostics: List[Dict[str, Any]] = []

    def signature(self) -> str:
        s = self.settings
        return (
            f"{self.workspace}|{s.model_type}|{s.model_id}|{s.enable_shell}"
            f"|{s.workspace_tools}|{s.base_url}|{getattr(s, 'team_role', '')}|{','.join(s.enabled_tools)}"
        )

    def agent(self):
        sig = self.signature()
        if self._agent is None or sig != self._agent_signature:
            self._agent = build_code_agent(self.settings, str(self.workspace))
            self._agent_signature = sig
        return self._agent

    def invalidate(self):
        self._agent = None
        self._agent_signature = None

    def pulse_agent(self, profile: Optional[Dict[str, Any]] = None):
        from buddy.code.pulse import build_pulse_employee

        return build_pulse_employee(self.settings, str(self.workspace), profile)

    def vertical_agent(self, pack: str):
        """Build a domain-pack copilot (ca/valuation/civil) reusing the user's
        model + API keys + workspace from Aura settings."""
        from buddy.verticals.base import VerticalSettings

        s = self.settings
        vs = VerticalSettings(
            pack=pack,
            model_type=s.model_type,
            model_id=s.model_id,
            temperature=s.temperature if s.temperature is not None else 0.2,
            api_keys=dict(s.api_keys),
            workspace=str(self.workspace),
            instructions=s.instructions,
        )
        if pack == "ca":
            from buddy.verticals.ca import build_ca_agent
            return build_ca_agent(vs)
        if pack == "valuation":
            from buddy.verticals.valuation import build_valuation_agent
            return build_valuation_agent(vs)
        if pack == "civil":
            from buddy.verticals.civil import build_civil_agent
            return build_civil_agent(vs)
        raise ValueError(f"Unknown vertical pack '{pack}'")

    def invalidate(self) -> None:
        self._agent = None


class SettingsUpdate(BaseModel):
    model_config = {"extra": "allow"}


class WorkspaceUpdate(BaseModel):
    path: str


class ChatContext(BaseModel):
    """Rich context attached to every chat message (Cursor-style context injection)."""
    active_file: Optional[str] = None          # path of the file open in editor
    active_file_content: Optional[str] = None  # content (or selection)
    selection: Optional[str] = None            # selected text if any
    selection_start: Optional[int] = None      # start line
    selection_end: Optional[int] = None        # end line
    mentioned_files: List[str] = []            # @file mentions
    images: List[str] = []                     # base64 data URLs
    notepad: Optional[str] = None             # active notepad text
    rules: Optional[str] = None               # project rules (.varamrules)
    diagnostics: Optional[str] = None         # linter/error context


class ProfileUpdate(BaseModel):
    org_name: Optional[str] = None
    user_name: Optional[str] = None
    user_title: Optional[str] = None
    team_role: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    onboarding_complete: Optional[bool] = None


class ChatRequest(BaseModel):
    message: str
    mode: str = "agent"  # "agent" | "plan" | "ask" | "agent_free" | "pulse" | …
    session_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    workspace_tools: Optional[bool] = None  # override per-message; None = use settings
    team_role: Optional[str] = None         # engineering | testing | platform | …
    context: Optional[ChatContext] = None


class InlineEditRequest(BaseModel):
    file_path: str
    selection: str
    instruction: str
    start_line: int = 1


class CompletionRequest(BaseModel):
    file_path: str
    content_before: str   # text before cursor
    content_after: str    # text after cursor
    language: str = ""


# Vertical chat modes -> the licensing feature that gates them.
PACK_FEATURE = {"ca": "pack_ca", "valuation": "pack_valuation", "civil": "pack_civil"}


class ActivateRequest(BaseModel):
    token: str
    public_key: Optional[str] = None


class GenerateToolRequest(BaseModel):
    prompt: str


class SaveToolRequest(BaseModel):
    name: str
    code: str
    description: str = ""


class UseOfflineRequest(BaseModel):
    model_id: Optional[str] = None


class TrainRequest(BaseModel):
    base_model: str
    dataset_path: str
    output_dir: str
    epochs: int = 3


class ObserverConfigUpdate(BaseModel):
    model_config = {"extra": "allow"}


class ObserverPauseRequest(BaseModel):
    paused: bool = True


class FileWrite(BaseModel):
    path: str
    content: str


def create_app() -> FastAPI:
    _load_env()
    app = FastAPI(title="Aura", version="1.0", docs_url="/api/docs")
    state = _State()
    training = TrainingManager()

    from buddy.code.observer import ScreenObserver

    observer = ScreenObserver(settings_provider=lambda: state.settings)
    # Auto-resume if the user had it enabled in a previous session.
    if observer.config.enabled:
        observer.start()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----------------------------------------------------------------- meta
    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "workspace": str(state.workspace),
            "terminal": True,
        }

    @app.get("/api/settings")
    def get_settings():
        return {
            "settings": json.loads(state.settings.redacted().model_dump_json()),
            "workspace": str(state.workspace),
            "providers": PROVIDER_ENV_KEYS,
        }

    @app.put("/api/settings")
    def update_settings(update: Dict[str, Any] = Body(...)):
        state.settings = merge_settings_update(state.settings, dict(update))
        save_settings(state.settings)
        state.invalidate()
        return {"ok": True, "settings": json.loads(state.settings.redacted().model_dump_json())}

    # -------------------------------------------------------------- account
    @app.get("/api/account")
    def account():
        return entitlements_gate.get().status()

    @app.post("/api/account/activate")
    def account_activate(req: ActivateRequest):
        entitlements_gate.get().set_token(req.token, req.public_key or "")
        entitlements_gate.reload()
        return entitlements_gate.get().status()

    @app.get("/api/models")
    def models():
        return _catalog_by_category("model")

    @app.get("/api/tools")
    def tools():
        return _catalog_by_category("tool")

    @app.get("/api/teams")
    def teams(role: Optional[str] = None):
        """Org team roles + workflows for the Aura workspace."""
        from buddy.code.teams import team_payload, normalize_team
        active = normalize_team(role or getattr(state.settings, "team_role", None))
        return team_payload(active)

    @app.get("/api/profile")
    def get_profile():
        s = state.settings
        from buddy.code.teams import normalize_team, ORG_TEAMS
        team = normalize_team(getattr(s, "team_role", None))
        return {
            "org_name": getattr(s, "org_name", "") or "",
            "user_name": getattr(s, "user_name", "") or "",
            "user_title": getattr(s, "user_title", "") or "",
            "team_role": team,
            "focus_areas": list(getattr(s, "focus_areas", None) or []),
            "onboarding_complete": bool(getattr(s, "onboarding_complete", False)),
            "workspace": str(state.workspace),
            "team": ORG_TEAMS.get(team, ORG_TEAMS["general"]),
        }

    def _apply_profile(body: ProfileUpdate):
        from buddy.code.settings import merge_settings_update, save_settings
        from buddy.code.teams import normalize_team
        update: Dict[str, Any] = {}
        if body.org_name is not None:
            update["org_name"] = str(body.org_name or "").strip()[:120]
        if body.user_name is not None:
            update["user_name"] = str(body.user_name or "").strip()[:80]
        if body.user_title is not None:
            update["user_title"] = str(body.user_title or "").strip()[:80]
        if body.team_role is not None:
            update["team_role"] = normalize_team(body.team_role)
        if body.focus_areas is not None:
            update["focus_areas"] = [str(a)[:60] for a in (body.focus_areas or [])][:12]
        if body.onboarding_complete is not None:
            update["onboarding_complete"] = bool(body.onboarding_complete)
        if update:
            state.settings = save_settings(merge_settings_update(state.settings, update))
            state.invalidate()
        return get_profile()

    @app.put("/api/profile")
    def put_profile(body: ProfileUpdate):
        return _apply_profile(body)

    @app.post("/api/profile")
    def post_profile(body: ProfileUpdate):
        return _apply_profile(body)

    # ------------------------------------------------------------ workspace
    @app.get("/api/workspace")
    def get_workspace():
        return {"path": str(state.workspace)}

    @app.post("/api/workspace")
    def set_workspace(update: WorkspaceUpdate):
        p = Path(update.path).expanduser().resolve()
        if not p.is_dir():
            raise HTTPException(status_code=400, detail="Not a directory")
        state.workspace = p
        state.invalidate()
        _save_recent_workspace(p)
        return {"ok": True, "path": str(p)}

    # ------------------------------------------------------------------- fs
    @app.get("/api/fs/list")
    def fs_list(path: str = Query(".")):
        target = _safe_join(state.workspace, path)
        if not target.is_dir():
            raise HTTPException(status_code=404, detail="Not a directory")
        children: List[Dict[str, Any]] = []
        try:
            for entry in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                if entry.name in _IGNORE_DIRS:
                    continue
                children.append(
                    {
                        "name": entry.name,
                        "path": str(entry.relative_to(state.workspace)).replace("\\", "/"),
                        "type": "dir" if entry.is_dir() else "file",
                    }
                )
        except PermissionError:
            pass
        return {"path": path, "children": children}

    @app.get("/api/fs/file")
    def fs_read(path: str = Query(...)):
        target = _safe_join(state.workspace, path)
        if not target.is_file():
            raise HTTPException(status_code=404, detail="Not a file")
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"path": path, "content": content}

    @app.put("/api/fs/file")
    def fs_write(body: FileWrite):
        target = _safe_join(state.workspace, body.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body.content, encoding="utf-8")
        return {"ok": True}

    # ----------------------------------------------------------------- chat
    # Active abort controllers per session
    _abort_flags: Dict[str, threading.Event] = {}

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        if req.mode == "pulse":
            entitlements_gate.require("pulse")
        elif req.mode in PACK_FEATURE:
            entitlements_gate.require(PACK_FEATURE[req.mode])

        session_id = req.session_id or str(uuid.uuid4())
        message = _enrich_message(req.message, req.context, state.workspace)

        # Ensure session exists on disk; create if new
        sess = _load_session(state.workspace, session_id)
        if sess is None:
            sess = {"id": session_id, "title": req.message[:60], "updated": time.time(), "messages": []}
        # Append user message to transcript
        sess["messages"].append({"role": "user", "content": req.message, "ts": time.time()})
        sess["updated"] = time.time()
        if sess.get("title", "New chat") == "New chat":
            sess["title"] = req.message[:60]
        _save_session(state.workspace, sess)

        # Per-session event queue and abort flag
        ev_q: queue.Queue = queue.Queue()
        abort_flag = threading.Event()
        _abort_flags[session_id] = abort_flag

        # Collect streamed assistant text for saving
        assistant_chunks: list = []
        assistant_tools: list = []

        def run_agent():
            try:
                if req.mode == "pulse":
                    agent = state.pulse_agent(req.profile)
                elif req.mode in PACK_FEATURE:
                    agent = state.vertical_agent(req.mode)
                else:
                    # Build agent respecting workspace_tools, team role, and mode settings
                    settings_copy = state.settings.model_copy(deep=True)
                    if req.mode == "agent_free":
                        settings_copy.workspace_tools = False
                    elif req.workspace_tools is not None:
                        settings_copy.workspace_tools = req.workspace_tools
                    team_role = req.team_role or getattr(settings_copy, "team_role", None)
                    if team_role:
                        settings_copy.team_role = team_role
                    from buddy.code.agent import build_code_agent
                    agent = build_code_agent(
                        settings_copy,
                        str(state.workspace),
                        session_id=session_id,
                        event_queue=ev_q,
                        team_role=team_role,
                    )
                    for tool in getattr(agent, 'tools', []):
                        if hasattr(tool, '_mode') and req.mode in ('agent', 'plan', 'ask'):
                            tool._mode = req.mode
                for event in agent.run(message, stream=True):
                    if abort_flag.is_set():
                        break
                    payload = _normalize_event(event)
                    if payload:
                        # Track assistant text for persistence
                        if payload.get("type") == "content":
                            assistant_chunks.append(payload.get("content", ""))
                        elif payload.get("type") == "tool" and payload.get("phase") == "completed":
                            assistant_tools.append(payload.get("tool", ""))
                        ev_q.put(payload)
            except Exception as e:
                ev_q.put({"type": "error", "content": str(e)})
            finally:
                ev_q.put(None)  # sentinel

        t = threading.Thread(target=run_agent, daemon=True)
        t.start()

        def stream():
            yield _sse({"type": "started", "session_id": session_id})
            while True:
                try:
                    ev = ev_q.get(timeout=60)
                    if ev is None:
                        break
                    yield _sse(ev)
                except queue.Empty:
                    if not t.is_alive():
                        break
            _abort_flags.pop(session_id, None)
            # Persist assistant turn
            try:
                s2 = _load_session(state.workspace, session_id) or sess
                text = "".join(assistant_chunks)
                s2["messages"].append({
                    "role": "assistant",
                    "content": text,
                    "tools": assistant_tools,
                    "ts": time.time(),
                })
                s2["updated"] = time.time()
                _save_session(state.workspace, s2)
            except Exception:
                pass
            yield _sse({"type": "completed"})
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/chat/cancel")
    def chat_cancel(body: Dict[str, Any] = Body(default={})):
        sid = body.get("session_id")
        if sid and sid in _abort_flags:
            _abort_flags[sid].set()
            return {"ok": True}
        # Cancel all active if no session_id
        for flag in _abort_flags.values():
            flag.set()
        return {"ok": True}

    @app.post("/api/chat/answer")
    def chat_answer(body: Dict[str, Any] = Body(...)):
        """Answer an AskQuestion pause."""
        sid = body.get("session_id")
        answers = body.get("answers", {})
        if not sid:
            raise HTTPException(status_code=400, detail="session_id required")
        try:
            from buddy.code.server._events import post_answer
            post_answer(sid, answers)
        except Exception:
            pass
        return {"ok": True}

    @app.post("/api/chat/plan-confirm")
    def chat_plan_confirm(body: Dict[str, Any] = Body(...)):
        """Confirm or cancel a CreatePlan pause."""
        sid = body.get("session_id")
        confirmed = body.get("confirmed", False)
        if not sid:
            raise HTTPException(status_code=400, detail="session_id required")
        try:
            from buddy.code.server._events import post_answer
            post_answer(sid, {"plan_confirmed": confirmed})
        except Exception:
            pass
        return {"ok": True}

    # ----------------------------------------------------------- inline edit
    @app.post("/api/inline-edit")
    def inline_edit(req: InlineEditRequest):
        """AI edit of a code selection — drives the Cmd+K inline widget."""
        from buddy.code.agent import CODING_SYSTEM_PROMPT

        prompt = (
            f"You are an AI code editor. Apply the following instruction to the given code "
            f"and return ONLY the replacement code — no prose, no markdown fences.\n\n"
            f"Instruction: {req.instruction}\n\n"
            f"Current code (lines {req.start_line}+):\n{req.selection}\n\n"
            f"Replacement code:"
        )

        def stream():
            yield _sse({"type": "started"})
            try:
                from buddy.code.agent import _resolve_class, _accepts
                cls = _resolve_class(state.settings.model_type)
                kwargs: Dict[str, Any] = {"id": state.settings.model_id}
                provider = state.settings.model_type.split(".")[1] if "." in state.settings.model_type else ""
                api_key = state.settings.api_keys.get(provider)
                if api_key and _accepts(cls, "api_key"):
                    kwargs["api_key"] = api_key
                model = cls(**kwargs)
                from buddy.agent import Agent
                agent = Agent(name="inline-edit", model=model, markdown=False)
                for event in agent.run(prompt, stream=True):
                    payload = _normalize_event(event)
                    if payload:
                        yield _sse(payload)
            except Exception as e:
                yield _sse({"type": "error", "content": str(e)})
            yield _sse({"type": "completed"})
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    # ---------------------------------------------------------- completions
    @app.post("/api/completions")
    def completions(req: CompletionRequest):
        """AI tab completion — ghost text in Monaco."""
        prompt = (
            f"Complete the following {req.language} code. Output ONLY the completion text "
            f"to insert after the cursor — no commentary, no repeating existing text.\n\n"
            f"<prefix>\n{req.content_before[-800:]}\n</prefix>\n"
            f"<suffix>\n{req.content_after[:200]}\n</suffix>\n\nCompletion:"
        )
        try:
            from buddy.code.agent import _resolve_class, _accepts
            cls = _resolve_class(state.settings.model_type)
            kwargs: Dict[str, Any] = {"id": state.settings.model_id}
            provider = state.settings.model_type.split(".")[1] if "." in state.settings.model_type else ""
            api_key = state.settings.api_keys.get(provider)
            if api_key and _accepts(cls, "api_key"):
                kwargs["api_key"] = api_key
            model = cls(**kwargs)
            from buddy.agent import Agent
            agent = Agent(name="completion", model=model, markdown=False)
            result = agent.run(prompt)
            text = getattr(result, "content", str(result)) if result else ""
            return {"completion": (text or "").strip()}
        except Exception as e:
            return JSONResponse(status_code=500, content={"completion": "", "error": str(e)})

    # --------------------------------------------------------------- git
    @app.get("/api/git/status")
    def git_status():
        """Git status of the workspace."""
        raw = _git(state.workspace, ["status", "--short", "--branch"])
        output = raw.get("output", "")
        # Parse branch from first line  (## main...origin/main [ahead 1])
        lines = output.splitlines()
        branch = ""
        files = []
        for line in lines:
            if line.startswith("## "):
                branch = line[3:].split("...")[0].split(" ")[0]
            elif len(line) >= 3:
                status = line[:2].strip()
                path = line[3:].strip()
                staged = line[0] not in (" ", "?", "!")
                files.append({"path": path, "status": status, "staged": staged})
        raw["branch"] = branch
        raw["files"] = files
        return raw

    @app.get("/api/git/log")
    def git_log(limit: int = Query(20)):
        return _git(state.workspace, ["log", f"--max-count={limit}", "--oneline", "--decorate"])

    @app.get("/api/git/diff")
    def git_diff(staged: bool = Query(False), path: Optional[str] = Query(None)):
        args = ["diff"] + (["--cached"] if staged else []) + (["--", path] if path else [])
        return _git(state.workspace, args)

    @app.post("/api/git/stage")
    def git_stage(body: Dict[str, Any] = Body(...)):
        paths = body.get("paths", ["."])
        return _git(state.workspace, ["add", "--"] + list(paths))

    @app.post("/api/git/unstage")
    def git_unstage(body: Dict[str, Any] = Body(...)):
        paths = body.get("paths", ["."])
        return _git(state.workspace, ["restore", "--staged", "--"] + list(paths))

    @app.post("/api/git/commit")
    def git_commit(body: Dict[str, Any] = Body(...)):
        msg = body.get("message", "")
        if not msg:
            raise HTTPException(status_code=400, detail="commit message required")
        return _git(state.workspace, ["commit", "-m", msg])

    @app.post("/api/git/discard")
    def git_discard(body: Dict[str, Any] = Body(...)):
        paths = body.get("paths", [])
        if not paths:
            raise HTTPException(status_code=400, detail="paths required")
        return _git(state.workspace, ["checkout", "--"] + list(paths))

    @app.get("/api/git/branches")
    def git_branches():
        return _git(state.workspace, ["branch", "-a", "--format=%(refname:short)"])

    @app.post("/api/git/checkout")
    def git_checkout(body: Dict[str, Any] = Body(...)):
        branch = body.get("branch", "")
        if not branch:
            raise HTTPException(status_code=400, detail="branch required")
        return _git(state.workspace, ["checkout", branch])

    @app.post("/api/git/commit-message")
    def git_commit_message():
        """AI-generated commit message from current diff."""
        diff_result = _git(state.workspace, ["diff", "--cached"])
        if not diff_result.get("ok"):
            diff_result = _git(state.workspace, ["diff"])
        diff_text = diff_result.get("output", "")[:4000]
        if not diff_text.strip():
            return {"message": ""}
        try:
            from buddy.code.agent import _resolve_class, _accepts
            from buddy.agent import Agent
            cls = _resolve_class(state.settings.model_type)
            kwargs: Dict[str, Any] = {"id": state.settings.model_id}
            provider = state.settings.model_type.split(".")[1] if "." in state.settings.model_type else ""
            api_key = state.settings.api_keys.get(provider)
            if api_key and _accepts(cls, "api_key"):
                kwargs["api_key"] = api_key
            model = cls(**kwargs)
            agent = Agent(name="git-msg", model=model, markdown=False)
            result = agent.run(
                f"Write a concise git commit message (50 chars subject, optional body) for this diff. "
                f"Return only the commit message, nothing else.\n\n{diff_text}"
            )
            text = getattr(result, "content", str(result)) if result else ""
            return {"message": text.strip()}
        except Exception as e:
            return {"message": "", "error": str(e)}

    # --------------------------------------------------------- project rules
    @app.get("/api/rules")
    def get_rules():
        """Read .varamrules or .cursorrules from workspace root."""
        return {"rules": _load_rules(state.workspace)}

    @app.put("/api/rules")
    def save_rules(body: Dict[str, Any] = Body(...)):
        text = body.get("content", "")
        rules_path = state.workspace / ".varamrules"
        rules_path.write_text(text, encoding="utf-8")
        return {"ok": True}

    # ---------------------------------------------------------- diagnostics
    @app.post("/api/diagnostics")
    def post_diagnostics(body: Dict[str, Any] = Body(...)):
        """Receive Monaco editor markers (linter errors) — stored for agent context."""
        state.diagnostics = body.get("markers", [])
        return {"ok": True, "count": len(state.diagnostics)}

    @app.get("/api/diagnostics")
    def get_diagnostics():
        return {"markers": getattr(state, "diagnostics", [])}

    # ----------------------------------------------------------- terminal run
    @app.post("/api/run")
    def terminal_run(body: Dict[str, Any] = Body(...)):
        """Run a shell command in the workspace (mirrors WorkspaceTools.run_command)."""
        if not state.settings.enable_shell:
            raise HTTPException(status_code=403, detail="Shell execution is disabled in settings.")
        command = body.get("command", "")
        if not command.strip():
            raise HTTPException(status_code=400, detail="command required")
        try:
            r = subprocess.run(
                command, shell=True, cwd=str(state.workspace),
                capture_output=True, text=True, timeout=60,
            )
            return {"stdout": r.stdout, "stderr": r.stderr, "code": r.returncode, "cwd": str(state.workspace)}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Command timed out (60s)", "code": -1, "cwd": str(state.workspace)}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "code": -1, "cwd": str(state.workspace)}

    # -------------------------------------------------------- codebase search
    @app.get("/api/search")
    def codebase_search(q: str = Query(...), max_results: int = Query(30)):
        """Fast text search across the workspace (ripgrep if available, fallback walk)."""
        return _search_workspace(state.workspace, q, max_results)

    # ------------------------------------------------------- sessions (file-backed)

    @app.get("/api/sessions")
    def list_sessions():
        return {"sessions": _list_sessions(state.workspace)}

    @app.post("/api/sessions")
    def create_session():
        sid = str(uuid.uuid4())
        data: Dict[str, Any] = {"id": sid, "title": "New chat", "updated": time.time(), "messages": []}
        _save_session(state.workspace, data)
        return {"id": sid}

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str):
        data = _load_session(state.workspace, session_id)
        if not data:
            raise HTTPException(status_code=404, detail="Session not found")
        return data

    @app.patch("/api/sessions/{session_id}")
    def rename_session(session_id: str, body: Dict[str, Any] = Body(...)):
        data = _load_session(state.workspace, session_id)
        if not data:
            raise HTTPException(status_code=404, detail="Session not found")
        if "title" in body:
            data["title"] = body["title"]
        data["updated"] = time.time()
        _save_session(state.workspace, data)
        return {"ok": True}

    @app.delete("/api/sessions/{session_id}")
    def delete_session(session_id: str):
        _delete_session(state.workspace, session_id)
        return {"ok": True}

    @app.put("/api/sessions/{session_id}/messages")
    def replace_messages(session_id: str, body: Dict[str, Any] = Body(...)):
        """Replace transcript (for edit/delete message). Body: {messages: [...]}"""
        data = _load_session(state.workspace, session_id)
        if not data:
            raise HTTPException(status_code=404, detail="Session not found")
        data["messages"] = body.get("messages", [])
        data["updated"] = time.time()
        _save_session(state.workspace, data)
        return {"ok": True}

    @app.get("/api/recents")
    def list_recents():
        try:
            if _RECENT_PATH.exists():
                data = json.loads(_RECENT_PATH.read_text(encoding="utf-8"))
                return {"recent": [p for p in data.get("recent", []) if Path(p).is_dir()]}
        except Exception:
            pass
        return {"recent": []}

    # ----------------------------------------- WebSocket PTY terminal
    # NOTE: WebSocket must be imported at module top (future annotations).

    def _resolve_shell(shell: str | None = None):
        """Return (appname, cmdline, display_name) for the interactive shell."""
        import platform
        import shutil

        system = platform.system()
        requested = (shell or "").strip().lower()

        if system == "Windows":
            windir = os.environ.get("SystemRoot", r"C:\Windows")
            if requested in ("pwsh", "powershell-core"):
                path = shutil.which("pwsh.exe") or shutil.which("pwsh")
                if path:
                    return path, "-NoLogo -NoExit", "pwsh"
            if requested == "cmd":
                path = (
                    shutil.which("cmd.exe")
                    or os.path.join(windir, "System32", "cmd.exe")
                )
                return path, "/K", "cmd"

            # Default: Windows PowerShell
            ps = (
                shutil.which("powershell.exe")
                or shutil.which("powershell")
                or os.path.join(
                    windir, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
                )
            )
            if os.path.exists(ps) or shutil.which("powershell"):
                return ps, "-NoLogo -NoExit", "powershell"
            cmd = shutil.which("cmd.exe") or os.path.join(windir, "System32", "cmd.exe")
            return cmd, "/K", "cmd"

        if requested in ("zsh", "fish", "sh", "bash"):
            path = shutil.which(requested) or f"/bin/{requested}"
            return path, None, requested
        for name in ("bash", "zsh", "sh"):
            path = shutil.which(name)
            if path:
                return path, None, name
        return "/bin/sh", None, "sh"

    @app.websocket("/ws/terminal")
    async def ws_terminal(websocket: WebSocket):
        await websocket.accept()
        import asyncio
        import platform
        import queue
        import threading

        cwd = str(state.workspace) if state.workspace else os.getcwd()
        if not os.path.isdir(cwd):
            cwd = os.getcwd()

        shell_q = websocket.query_params.get("shell")
        appname, cmdline, shell_name = _resolve_shell(shell_q)
        cols = max(20, min(int(websocket.query_params.get("cols") or 80), 500))
        rows = max(5, min(int(websocket.query_params.get("rows") or 24), 200))

        await websocket.send_json({
            "type": "ready",
            "shell": shell_name,
            "cwd": cwd,
            "pty": True,
        })

        # ── Windows: force WinPTY (ConPTY is unreliable on many hosts) ──
        if platform.system() == "Windows":
            try:
                from winpty import PTY, Backend  # type: ignore
            except ImportError:
                await websocket.send_json({
                    "type": "output",
                    "data": (
                        "\r\n\x1b[33m[Terminal needs pywinpty]\x1b[0m\r\n"
                        "  pip install pywinpty\r\n"
                    ),
                })
                await websocket.close()
                return

            try:
                pty = PTY(cols, rows, backend=Backend.WinPTY)
            except Exception:
                pty = PTY(cols, rows)

            ok = pty.spawn(appname, cmdline=cmdline, cwd=cwd)
            if not ok:
                await websocket.send_json({
                    "type": "output",
                    "data": f"\r\n\x1b[31mFailed to spawn {shell_name}\x1b[0m\r\n",
                })
                await websocket.close()
                return

            out_q: queue.Queue = queue.Queue()
            stop = threading.Event()

            def reader_thread():
                while not stop.is_set():
                    try:
                        data = pty.read(blocking=False)
                    except Exception as exc:
                        out_q.put(("err", str(exc)))
                        break
                    if data:
                        out_q.put(("data", data))
                    else:
                        if not pty.isalive():
                            out_q.put(("dead", None))
                            break
                        time.sleep(0.015)

            threading.Thread(target=reader_thread, daemon=True).start()

            async def pump_ws():
                while not stop.is_set():
                    try:
                        kind, payload = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: out_q.get(timeout=0.2)
                        )
                    except Exception:
                        continue
                    if kind == "data":
                        await websocket.send_json({"type": "output", "data": payload})
                    else:
                        break

            pump_task = asyncio.ensure_future(pump_ws())
            try:
                while True:
                    msg = await websocket.receive_json()
                    msg_type = msg.get("type", "")
                    if msg_type == "input":
                        data = msg.get("data", "")
                        if data:
                            try:
                                pty.write(data)
                            except Exception:
                                break
                    elif msg_type == "resize":
                        try:
                            c = max(20, int(msg.get("cols") or cols))
                            r = max(5, int(msg.get("rows") or rows))
                            pty.set_size(c, r)
                        except Exception:
                            pass
            except (WebSocketDisconnect, Exception):
                pass
            finally:
                stop.set()
                pump_task.cancel()
                try:
                    if pty.isalive():
                        pty.write("exit\r\n")
                except Exception:
                    pass
            return

        # ── Unix PTY ─────────────────────────────────────────────────────
        import pty as unix_pty
        import fcntl
        import struct
        import termios
        import select

        master, slave = unix_pty.openpty()
        try:
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except Exception:
            pass

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        args = [appname]
        if shell_name in ("bash", "zsh"):
            args.append("-l")

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        os.close(slave)

        async def pump_unix():
            loop = asyncio.get_event_loop()
            try:
                while True:
                    ready = await loop.run_in_executor(
                        None, lambda: select.select([master], [], [], 0.05)
                    )
                    if ready[0]:
                        try:
                            data = os.read(master, 4096)
                        except OSError:
                            break
                        if not data:
                            break
                        await websocket.send_json({
                            "type": "output",
                            "data": data.decode(errors="replace"),
                        })
                    if proc.returncode is not None:
                        break
            except Exception:
                pass

        read_task = asyncio.ensure_future(pump_unix())
        try:
            while True:
                msg = await websocket.receive_json()
                msg_type = msg.get("type", "")
                if msg_type == "input":
                    data = msg.get("data", "")
                    if data:
                        try:
                            os.write(master, data.encode())
                        except OSError:
                            break
                elif msg_type == "resize":
                    try:
                        c = max(20, int(msg.get("cols") or cols))
                        r = max(5, int(msg.get("rows") or rows))
                        fcntl.ioctl(
                            master,
                            termios.TIOCSWINSZ,
                            struct.pack("HHHH", r, c, 0, 0),
                        )
                    except Exception:
                        pass
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            read_task.cancel()
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                os.close(master)
            except Exception:
                pass

    # ---------------------------------------------------------- MCP servers config
    _mcp_config_path = lambda: state.workspace / ".aura" / "mcp.json"

    def _load_mcp_config() -> Dict[str, Any]:
        p = _mcp_config_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"servers": {}}

    def _save_mcp_config(cfg: Dict[str, Any]) -> None:
        p = _mcp_config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    @app.get("/api/mcp/servers")
    def mcp_list():
        cfg = _load_mcp_config()
        servers = [
            {"name": k, **v}
            for k, v in cfg.get("servers", {}).items()
        ]
        return {"servers": servers}

    @app.post("/api/mcp/servers")
    def mcp_add(body: Dict[str, Any] = Body(...)):
        name = body.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="name required")
        cfg = _load_mcp_config()
        if "servers" not in cfg:
            cfg["servers"] = {}
        cfg["servers"][name] = {k: v for k, v in body.items() if k != "name"}
        _save_mcp_config(cfg)
        state.invalidate()
        return {"ok": True}

    @app.delete("/api/mcp/servers/{name}")
    def mcp_remove(name: str):
        cfg = _load_mcp_config()
        cfg.get("servers", {}).pop(name, None)
        _save_mcp_config(cfg)
        state.invalidate()
        return {"ok": True}

    @app.put("/api/mcp/servers/{name}")
    def mcp_update(name: str, body: Dict[str, Any] = Body(...)):
        cfg = _load_mcp_config()
        if name in cfg.get("servers", {}):
            cfg["servers"][name].update(body)
            _save_mcp_config(cfg)
        return {"ok": True}

    # ------------------------------------------------------- diagnostics
    @app.post("/api/diagnostics")
    def set_diagnostics(body: Dict[str, Any] = Body(...)):
        from buddy.code.server._diagnostics import set_diagnostics as _set
        _set(body.get("markers", []))
        return {"ok": True}

    @app.get("/api/diagnostics")
    def get_diagnostics_endpoint():
        from buddy.code.server._diagnostics import get_diagnostics
        return {"markers": get_diagnostics()}

    # -------------------------------------------------------------- offline
    @app.get("/api/offline/status")
    def offline():
        return offline_status()

    @app.post("/api/offline/use")
    def use_offline(req: UseOfflineRequest):
        from buddy.code.offline import DEFAULT_OFFLINE_MODEL, OLLAMA_MODEL_TYPE

        state.settings.model_type = OLLAMA_MODEL_TYPE
        state.settings.model_id = req.model_id or DEFAULT_OFFLINE_MODEL
        save_settings(state.settings)
        state.invalidate()
        return {"ok": True, "model_type": state.settings.model_type, "model_id": state.settings.model_id}

    # --------------------------------------------------------- custom tools
    @app.get("/api/tools/custom")
    def custom_tools():
        return list_custom_tools()

    @app.post("/api/tools/generate")
    def gen_tool(req: GenerateToolRequest):
        entitlements_gate.require("tool_studio")
        try:
            return generate_tool_code(req.prompt, state.settings)
        except Exception as e:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})

    @app.post("/api/tools/custom")
    def add_tool(req: SaveToolRequest):
        entitlements_gate.enforce_quota("custom_tools")
        result = save_custom_tool(req.name, req.code, req.description)
        if result["ok"]:
            state.invalidate()
        return result

    @app.delete("/api/tools/custom/{name}")
    def remove_tool(name: str):
        ok = delete_custom_tool(name)
        state.invalidate()
        return {"ok": ok}

    # --------------------------------------------------------------- pulse
    @app.get("/api/pulse/profile")
    def get_pulse_profile():
        from buddy.code.pulse import _DEFAULT_PROFILE

        return state.settings.model_dump().get("pulse_profile") or _DEFAULT_PROFILE

    # ------------------------------------------------------------ training
    @app.get("/api/train/models")
    def train_models():
        return {"models": available_models(), "deps_ok": training_deps_ok()}

    @app.post("/api/train/start")
    def train_start(req: TrainRequest):
        entitlements_gate.require("training")
        entitlements_gate.enforce_quota("train_runs")
        return training.start(req.base_model, req.dataset_path, req.output_dir, req.epochs)

    @app.get("/api/train/status")
    def train_status():
        return training.job.to_dict() if training.job else {"status": "idle"}

    # ------------------------------------------------------------ observer
    @app.get("/api/observer/status")
    def observer_status():
        return observer.status()

    @app.get("/api/observer/config")
    def observer_get_config():
        return observer.config.model_dump()

    @app.put("/api/observer/config")
    def observer_set_config(patch: ObserverConfigUpdate):
        return observer.update_config(patch.model_dump()).model_dump()

    @app.post("/api/observer/start")
    def observer_start():
        entitlements_gate.require("observer")
        return observer.start()

    @app.post("/api/observer/stop")
    def observer_stop():
        return observer.stop()

    @app.post("/api/observer/pause")
    def observer_pause(req: ObserverPauseRequest):
        return observer.pause(req.paused)

    @app.get("/api/observer/journal")
    def observer_journal(limit: int = Query(200), q: Optional[str] = Query(None)):
        from buddy.code.observer import read_journal

        return read_journal(limit=limit, query=q)

    @app.get("/api/observer/insights")
    def observer_insights():
        from buddy.code.observer import insights

        return insights()

    @app.delete("/api/observer/journal")
    def observer_clear():
        from buddy.code.observer import clear_journal

        return {"ok": clear_journal()}

    # ------------------------------------------------------------- frontend
    if _STATIC_DIR.exists():
        if (_STATIC_DIR / "assets").exists():
            app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(_STATIC_DIR / "index.html")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            target = _STATIC_DIR / full_path
            if target.exists() and target.is_file():
                return FileResponse(target)
            return FileResponse(_STATIC_DIR / "index.html")

    return app


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _sse(obj: Dict[str, Any]) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _safe_join(base: Path, path: str) -> Path:
    p = (base / path).resolve()
    if base != p and base not in p.parents:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    return p


def _normalize_event(event: Any) -> Optional[Dict[str, Any]]:
    """Map a Buddy run event to a UI event (content / tool / error)."""
    name = type(event).__name__.lower()

    # Streamed text content.
    for attr in ("content", "delta", "text"):
        val = getattr(event, attr, None)
        if isinstance(val, str) and val:
            return {"type": "content", "content": val}

    if "tool" in name:
        tool = getattr(event, "tool", None)
        tool_name = None
        args = None
        result = None
        if tool is not None:
            tool_name = getattr(tool, "tool_name", None) or getattr(tool, "name", None)
            args = getattr(tool, "tool_args", None)
            # Grab result from completed events
            result = getattr(tool, "tool_result", None) or getattr(tool, "result", None)
            if tool_name is None and isinstance(tool, dict):
                tool_name = tool.get("tool_name") or tool.get("name")
                args = tool.get("tool_args")
                result = tool.get("tool_result") or tool.get("result")
        phase = "completed" if "completed" in name else "started"
        payload: Dict[str, Any] = {
            "type": "tool",
            "phase": phase,
            "tool": tool_name or "tool",
            "args": _safe_args(args),
        }
        if result is not None:
            payload["result"] = str(result)[:2000]
        return payload

    return None


def _safe_args(args: Any) -> Any:
    try:
        json.dumps(args)
        return args
    except Exception:
        return str(args)[:300] if args is not None else None


def _git(workspace: Path, args: List[str]) -> Dict[str, Any]:
    """Run a git command in the workspace and return structured output."""
    try:
        r = subprocess.run(
            ["git"] + args, cwd=str(workspace),
            capture_output=True, text=True, timeout=15,
        )
        return {"ok": r.returncode == 0, "output": r.stdout + r.stderr, "code": r.returncode}
    except FileNotFoundError:
        return {"ok": False, "output": "git not found", "code": -1}
    except Exception as e:
        return {"ok": False, "output": str(e), "code": -1}


def _load_rules(workspace: Path) -> str:
    for name in (".aurarules", ".varamrules", ".cursorrules"):
        p = workspace / name
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="ignore")[:8000]
            except Exception:
                pass
    # Also try .aura/rules
    aura_rules = workspace / ".aura" / "rules.md"
    if aura_rules.exists():
        try:
            return aura_rules.read_text(encoding="utf-8", errors="ignore")[:8000]
        except Exception:
            pass
    return ""


def _enrich_message(message: str, ctx: Optional[Any], workspace: Path) -> str:
    """Prepend context to the user message so the agent sees the full picture."""
    if ctx is None:
        return message
    parts: List[str] = []
    # Project rules
    rules = ctx.rules or _load_rules(workspace)
    if rules:
        parts.append(f"<project_rules>\n{rules}\n</project_rules>")
    # Active file / selection
    if ctx.active_file:
        if ctx.selection:
            lines = ""
            if ctx.selection_start is not None:
                lines = f" (lines {ctx.selection_start}–{ctx.selection_end})"
            parts.append(f"<selection file='{ctx.active_file}'{lines}>\n{ctx.selection}\n</selection>")
        elif ctx.active_file_content:
            parts.append(f"<file path='{ctx.active_file}'>\n{ctx.active_file_content[:6000]}\n</file>")
    # @mentioned files
    for fp in ctx.mentioned_files or []:
        try:
            full = (workspace / fp).resolve()
            if workspace in full.parents or full == workspace:
                content = full.read_text(encoding="utf-8", errors="ignore")[:4000]
                parts.append(f"<file path='{fp}'>\n{content}\n</file>")
        except Exception:
            pass
    # Diagnostics / linter errors
    if ctx.diagnostics:
        parts.append(f"<diagnostics>\n{ctx.diagnostics}\n</diagnostics>")
    # Notepad
    if ctx.notepad:
        parts.append(f"<notepad>\n{ctx.notepad}\n</notepad>")
    if parts:
        return "\n".join(parts) + "\n\n" + message
    return message


def _search_workspace(workspace: Path, query: str, max_results: int = 30) -> Dict[str, Any]:
    """Search workspace with ripgrep if available, else fallback os.walk."""
    results: List[Dict[str, Any]] = []
    try:
        r = subprocess.run(
            ["rg", "--json", "-i", "-m", "3", "--max-count", str(max_results),
             "--glob", "!node_modules", "--glob", "!.git",
             query, str(workspace)],
            capture_output=True, text=True, timeout=10,
        )
        for line in r.stdout.splitlines():
            try:
                obj = json.loads(line)
                if obj.get("type") == "match":
                    data = obj["data"]
                    results.append({
                        "file": str(Path(data["path"]["text"]).relative_to(workspace)).replace("\\", "/"),
                        "line": data["line_number"],
                        "text": data["lines"]["text"].rstrip(),
                    })
            except Exception:
                continue
        if results:
            return {"results": results[:max_results], "engine": "ripgrep"}
    except FileNotFoundError:
        pass
    # Fallback: walk
    q = query.lower()
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for fname in files:
            if len(results) >= max_results:
                break
            fp = Path(root) / fname
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if q in line.lower():
                        results.append({
                            "file": str(fp.relative_to(workspace)).replace("\\", "/"),
                            "line": i, "text": line.rstrip(),
                        })
                        if len(results) >= max_results:
                            break
            except Exception:
                continue
    return {"results": results, "engine": "walk"}


def _catalog_by_category(category: str) -> List[Dict[str, Any]]:
    from buddy.builder.registry import build_catalog

    out: List[Dict[str, Any]] = []
    for nt in build_catalog().node_types:
        if nt.category != category:
            continue
        provider = nt.type.split(".")[1] if nt.type.count(".") >= 2 else ""
        out.append({"type": nt.type, "label": nt.label, "provider": provider, "description": nt.description})
    out.sort(key=lambda x: (x["provider"], x["label"]))
    return out


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for candidate in (os.getenv("BUDDY_CODE_ENV"), Path.cwd() / ".env"):
        if candidate and Path(candidate).exists():
            load_dotenv(candidate, override=False)


def serve(
    host: str = "127.0.0.1",
    port: int = 8600,
    reload: bool = False,
    desktop: bool = False,
    browser: bool = False,
) -> None:
    import threading
    import uvicorn

    url = f"http://{host}:{port}"

    if desktop:
        _launch_desktop_window(url, host, port, reload)
        return

    if browser:
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print(f"\n  Aura  ->  {url}")
    print(f"  API docs  ->  {url}/api/docs\n")

    if reload:
        uvicorn.run("buddy.code.server.app:create_app", host=host, port=port, reload=True, factory=True)
    else:
        uvicorn.run(create_app(), host=host, port=port)


def _resolve_aura_icon() -> str | None:
    """Return absolute path to Aura.ico if present."""
    from pathlib import Path as _P
    here = _P(__file__).resolve()
    candidates = [
        here.parents[2] / "Aura.ico",                 # repo root
        here.parents[2] / "assets" / "aura.ico",
        here.parents[1] / "static" / "favicon.ico",   # code/server/static
        _P.home() / ".buddy" / "aura.ico",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return None


def _apply_windows_hwnd_icon(icon_path: str, title: str = "Aura") -> None:
    """Force title-bar + taskbar icons via Win32 (covers EdgeChromium cases)."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_SETICON = 0x0080
    ICON_SMALL, ICON_BIG = 0, 1
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x0010
    LR_DEFAULTSIZE = 0x0040

    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        return

    # Load both sizes
    hicon_big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
    hicon_small = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    if not hicon_big:
        hicon_big = user32.LoadImageW(0, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
    if hicon_big:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
    if hicon_small:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)


def _launch_desktop_window(url: str, host: str, port: int, reload: bool) -> None:
    """Start the FastAPI server in a background thread, then open a pywebview window."""
    import threading
    import time
    import uvicorn

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait until the server is actually accepting connections.
    import socket
    for _ in range(40):
        try:
            with socket.create_connection((host if host != "0.0.0.0" else "127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.25)

    try:
        import webview  # pywebview

        # Windows taskbar / jump-list identity (keeps icon grouping correct)
        try:
            import ctypes as _ct
            _ct.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.aura.ide")
        except Exception:
            pass

        # Detect screen dimensions for a good default size
        import ctypes, sys as _sys
        try:
            if _sys.platform == "win32":
                user32 = ctypes.windll.user32
                sw = user32.GetSystemMetrics(0)
                sh = user32.GetSystemMetrics(1)
                w = min(int(sw * 0.9), 1600)
                h = min(int(sh * 0.9), 1000)
            else:
                w, h = 1440, 900
        except Exception:
            w, h = 1440, 900

        icon_path = _resolve_aura_icon()

        window = webview.create_window(
            title="Aura",
            url=url,
            width=w,
            height=h,
            min_size=(960, 640),
            background_color="#11111b",
            text_select=True,
        )

        def _on_shown():
            if icon_path and _sys.platform == "win32":
                try:
                    _apply_windows_hwnd_icon(icon_path, "Aura")
                except Exception:
                    pass

        try:
            window.events.shown += _on_shown
        except Exception:
            pass

        # Icon belongs on start() for winforms/GTK/QT backends
        if icon_path:
            webview.start(debug=False, icon=icon_path)
        else:
            webview.start(debug=False)
    except ImportError:
        # pywebview not installed — fall back to browser
        import webbrowser
        print(f"\n  pywebview not installed. Opening in browser: {url}")
        print("  Install for native window:  pip install pywebview\n")
        webbrowser.open(url)
        # Keep the server alive.
        server_thread.join()


__all__ = ["create_app", "serve"]
