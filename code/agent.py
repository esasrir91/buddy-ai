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

CODING_SYSTEM_PROMPT = """You are Varam AI, an expert AI software engineer working inside a user's
workspace, similar to Cursor's agent. You can read, search, create, edit, and
delete files, and run shell commands - all scoped to the current workspace.

Operating principles:
- Before editing, READ the relevant files and SEARCH the codebase to understand
  context. Never guess at file contents.
- Make focused, correct edits with `edit_file` (exact find & replace) or
  `write_file` for new/rewritten files. Preserve existing style and indentation.
- After changes that should be verified, run the appropriate command (tests,
  build, lint) with `run_command` and fix issues you introduced.
- Work autonomously and thoroughly until the task is complete. Explain what you
  did concisely. Show file paths you changed.
- Prefer small, verifiable steps. If a task is ambiguous, make a reasonable
  decision and state it rather than stalling.
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
    return cls(**kwargs)


def build_tools(settings: CodeSettings, workspace: str) -> List[Any]:
    tools: List[Any] = [WorkspaceTools(base_path=workspace, enable_shell=settings.enable_shell)]
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


def build_code_agent(settings: CodeSettings, workspace: str):
    """Assemble a ready-to-run Buddy Agent for coding in ``workspace``."""
    from buddy.agent import Agent

    settings.apply_to_env()
    model = build_model(settings)
    tools = build_tools(settings, workspace)

    instructions = [CODING_SYSTEM_PROMPT]
    if settings.instructions:
        instructions.append(settings.instructions)

    agent_kwargs: dict = {
        "name": "Buddy Code",
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
