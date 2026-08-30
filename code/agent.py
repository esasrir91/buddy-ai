"""Build the Buddy Code agent from settings + a workspace path.

Resolves the active model class from the auto-introspection catalog (shared with
the Builder), wires the workspace coding tools plus any catalog tools the user
enabled, and applies a strong agentic-coding system prompt.
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any, List, Optional

from buddy.code.settings import CodeSettings, PROVIDER_ENV_KEYS
from buddy.code.tools import WorkspaceTools

_CATEGORY_PACKAGE = {
    "model": "buddy.models",
    "tool": "buddy.tools",
}

CODING_SYSTEM_PROMPT = """You are Aura, an org-wide AI teammate embedded in the user's workspace.
You support Engineering, Testing/QA, Platform, Hardware, Security, Product, Data, and General work.
You have Cursor-class capabilities: read files, search with Glob/Grep, write/edit/delete files,
run shell commands, manage todos, and launch sub-agents.

Operating principles:
- Read first: use Read and Grep to understand context before editing.
- Edit precisely: use StrReplace for targeted edits, Write for new/rewritten files.
  Preserve the project's indentation and style.
- Verify: after changes, run the relevant test/build/lint/hardware-check command with Shell
  when applicable, and fix issues you introduced.
- Communicate: after completing a task, give a concise summary of what changed, how to verify,
  and residual risks. Always show the file paths you modified.
- Stay autonomous: work through the task step-by-step without stopping to ask
  unless truly blocked. Use AskQuestion only when user input is essential.
- In Plan mode: use CreatePlan to lay out a plan before executing. In Ask mode:
  answer without making changes.
- Adapt to the active org team role instructions below.
"""


def _resolve_class(type_key: str) -> type:
    category = type_key.split(".", 1)[0]
    package = _CATEGORY_PACKAGE.get(category)
    if not package:
        raise ValueError(f"Unknown type '{type_key}'")
    rest = type_key.split(".", 1)[1]
    dotted = f"{package}.{rest}"
    module_path, _, name = dotted.rpartition(".")
    mod = importlib.import_module(module_path)
    cls = getattr(mod, name, None)
    if cls is None:
        raise ValueError(f"Could not import '{dotted}'")
    return cls


def _accepts(cls: type, key: str) -> bool:
    try:
        params = inspect.signature(cls.__init__).parameters
    except (TypeError, ValueError):
        return True
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return True
    return key in params


def build_model(settings: CodeSettings):
    cls = _resolve_class(settings.model_type)
    kwargs: dict = {"id": settings.model_id}
    # Skip temperature for models that reject it (Claude 4.7+/5, OpenAI reasoning).
    wants_temp = settings.temperature is not None and _accepts(cls, "temperature")
    if wants_temp:
        supports = getattr(cls, "supports_temperature", None)
        if supports is None or supports(settings.model_id):
            kwargs["temperature"] = settings.temperature
    # Inject the API key explicitly too (belt and suspenders alongside env).
    provider = settings.model_type.split(".")[1] if "." in settings.model_type else ""
    api_key = settings.api_keys.get(provider)
    if api_key and _accepts(cls, "api_key"):
        kwargs["api_key"] = api_key
    # OpenAI-compatible base URL
    if settings.base_url and _accepts(cls, "base_url"):
        kwargs["base_url"] = settings.base_url
    # Timeout
    if settings.timeout is not None and _accepts(cls, "timeout"):
        kwargs["timeout"] = settings.timeout
    # httpx client with proxy / ssl / retries
    needs_client = settings.http_proxy or not settings.verify_ssl or settings.max_retries != 2
    if needs_client and _accepts(cls, "http_client"):
        try:
            import httpx
            transport = httpx.HTTPTransport(
                proxy=settings.http_proxy or None,
                verify=settings.verify_ssl,
                retries=settings.max_retries,
            )
            kwargs["http_client"] = httpx.Client(transport=transport)
        except ImportError:
            pass
    return cls(**kwargs)


def build_tools(settings: CodeSettings, workspace: str, session_id: str = None, event_queue=None) -> List[Any]:
    # Agent-free mode: skip all workspace file tools
    if not settings.workspace_tools or not workspace:
        tools: List[Any] = []
    else:
        # Prefer CursorTools over the legacy WorkspaceTools
        try:
            from buddy.tools.cursor import CursorTools
            tools = [CursorTools(
                base_path=workspace,
                enable_shell=settings.enable_shell,
                session_id=session_id,
                event_queue=event_queue,
            )]
        except Exception:
            tools = [WorkspaceTools(base_path=workspace, enable_shell=settings.enable_shell)]

    for tool_type in settings.enabled_tools:
        try:
            cls = _resolve_class(tool_type)
            tools.append(cls())
        except Exception:
            continue  # skip tools that need config/keys we don't have

    # LLM-generated custom tools the user added are always available.
    try:
        from buddy.code.custom_tools import load_custom_tools
        tools.extend(load_custom_tools())
    except Exception:
        pass

    # If the Observer has learned anything, let the agent recall it.
    tools.append(recall_activity)
    return tools


def recall_activity(query: str = "", limit: int = 30) -> str:
    """Recall what the user has recently been working on, learned by Varam AI's Observer.

    Use this to answer questions like "what was I working on?", "what errors have I
    been hitting?", or to get context about the user's recent activity before helping.

    Args:
        query (str): Optional keyword to filter activity (e.g. "error", a filename, a tool).
        limit (int): Max number of recent activity notes to return.

    Returns:
        str: A chronological list of recent activity summaries, or a note if none exist.
    """
    try:
        from buddy.code.observer import read_journal

        entries = read_journal(limit=limit, query=query or None)
        if not entries:
            return "No observed activity recorded (the Observer may be off or just enabled)."
        lines = [f"- {e.get('ts', '')[:19]} [{(e.get('app') or '')[:30]}] {e.get('summary', '')}" for e in entries]
        return "Recent activity:\n" + "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"Could not read activity journal: {exc}"


AGENT_FREE_PROMPT = """You are Aura, a helpful AI assistant for organizations and individuals.
You can think deeply, answer questions, write and explain code, do research, make plans,
and complete complex tasks autonomously across engineering, testing, platform, hardware,
security, product, and data work.
You do NOT have access to the user's local files or project codebase in this mode.
Respond thoroughly and directly. Use markdown formatting."""


def build_code_agent(
    settings: CodeSettings,
    workspace: str,
    session_id: str = None,
    event_queue=None,
    team_role: str = None,
):
    """Assemble a ready-to-run Buddy Agent for the active org team role."""
    from buddy.agent import Agent
    from buddy.code.teams import normalize_team, role_prompt

    settings.apply_to_env()
    model = build_model(settings)
    tools = build_tools(settings, workspace, session_id=session_id, event_queue=event_queue)

    team = normalize_team(team_role or getattr(settings, "team_role", None) or "engineering")

    # Agent-free mode: simpler prompt + still apply team specialty
    base_prompt = CODING_SYSTEM_PROMPT if settings.workspace_tools else AGENT_FREE_PROMPT
    instructions = [base_prompt, role_prompt(team)]

    org = (getattr(settings, "org_name", None) or "").strip()
    uname = (getattr(settings, "user_name", None) or "").strip()
    title = (getattr(settings, "user_title", None) or "").strip()
    focuses = list(getattr(settings, "focus_areas", None) or [])
    identity_bits = []
    if org:
        identity_bits.append(f"Organization: {org}")
    if uname:
        identity_bits.append(f"User: {uname}" + (f" ({title})" if title else ""))
    elif title:
        identity_bits.append(f"Role title: {title}")
    if focuses:
        identity_bits.append("Focus areas: " + ", ".join(focuses))
    if identity_bits:
        instructions.append(
            "Org context for this session:\n- " + "\n- ".join(identity_bits)
            + "\nTailor language, priorities, and examples to this org and team."
        )

    if settings.instructions:
        instructions.append(settings.instructions)

    agent_kwargs: dict = {
        "name": f"Aura ({team})",
        "model": model,
        "tools": tools,
        "instructions": instructions,
        "markdown": True,
        "add_history_to_messages": True,
        "num_history_runs": 5,
    }
    if _accepts(Agent, "reasoning") and settings.reasoning:
        agent_kwargs["reasoning"] = True
    if _accepts(Agent, "tool_call_limit"):
        agent_kwargs["tool_call_limit"] = settings.max_tool_calls

    return Agent(**agent_kwargs)


__all__ = ["build_code_agent", "build_model", "build_tools", "recall_activity", "CODING_SYSTEM_PROMPT"]
