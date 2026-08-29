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
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import buddy.models as _models  # noqa: F401  init order

from fastapi import Body, FastAPI, HTTPException, Query
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


class _State:
    """Runtime state: current workspace + cached agent (rebuilt on change)."""

    def __init__(self) -> None:
        self.workspace: Path = Path(os.getenv("BUDDY_CODE_WORKSPACE", Path.cwd())).resolve()
        self.settings: CodeSettings = load_settings()
        self.settings.apply_to_env()
        self._agent = None
        self._agent_signature: Optional[str] = None
        self.diagnostics: List[Dict[str, Any]] = []

    def signature(self) -> str:
        s = self.settings
        return f"{self.workspace}|{s.model_type}|{s.model_id}|{s.enable_shell}|{','.join(s.enabled_tools)}"

    def agent(self):
        sig = self.signature()
        if self._agent is None or sig != self._agent_signature:
            self._agent = build_code_agent(self.settings, str(self.workspace))
            self._agent_signature = sig
        return self._agent

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


class ChatRequest(BaseModel):
    message: str
    mode: str = "code"  # "code" | "pulse" | "ca" | "valuation" | "civil"
    profile: Optional[Dict[str, Any]] = None
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
    app = FastAPI(title="Varam AI", version="1.0", docs_url="/api/docs")
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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----------------------------------------------------------------- meta
    @app.get("/api/health")
    def health():
        return {"status": "ok", "workspace": str(state.workspace)}

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
    @app.post("/api/chat")
    def chat(req: ChatRequest):
        if req.mode == "pulse":
            entitlements_gate.require("pulse")
        elif req.mode in PACK_FEATURE:
            entitlements_gate.require(PACK_FEATURE[req.mode])

        # Build a rich message from the context object (Cursor-style injection).
        message = _enrich_message(req.message, req.context, state.workspace)

        def stream():
            yield _sse({"type": "started"})
            try:
                if req.mode == "pulse":
                    agent = state.pulse_agent(req.profile)
                elif req.mode in PACK_FEATURE:
                    agent = state.vertical_agent(req.mode)
                else:
                    agent = state.agent()
            except Exception as e:
                yield _sse({"type": "error", "content": f"Failed to build agent: {e}"})
                yield "data: [DONE]\n\n"
                return
            try:
                for event in agent.run(message, stream=True):
                    payload = _normalize_event(event)
                    if payload:
                        yield _sse(payload)
            except Exception as e:
                yield _sse({"type": "error", "content": str(e)})
            yield _sse({"type": "completed"})
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

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
        return _git(state.workspace, ["status", "--short", "--branch"])

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
        if tool is not None:
            tool_name = getattr(tool, "tool_name", None) or getattr(tool, "name", None)
            args = getattr(tool, "tool_args", None)
            if tool_name is None and isinstance(tool, dict):
                tool_name = tool.get("tool_name") or tool.get("name")
                args = tool.get("tool_args")
        phase = "completed" if "completed" in name else "started"
        return {"type": "tool", "phase": phase, "tool": tool_name or "tool", "args": _safe_args(args)}

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
    for name in (".varamrules", ".cursorrules"):
        p = workspace / name
        if p.exists():
            try:
                return p.read_text(encoding="utf-8", errors="ignore")[:8000]
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

    print(f"\n  Varam AI  →  {url}")
    print(f"  API docs  →  {url}/api/docs\n")

    if reload:
        uvicorn.run("buddy.code.server.app:create_app", host=host, port=port, reload=True, factory=True)
    else:
        uvicorn.run(create_app(), host=host, port=port)


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
        window = webview.create_window(
            title="Varam AI",
            url=url,
            width=1400,
            height=900,
            min_size=(900, 600),
            background_color="#0c0c14",
            text_select=True,
        )
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
