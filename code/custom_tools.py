"""LLM-generated custom tools for Aura.

Users describe a tool in natural language; an LLM writes a Python function (with
type hints + a Google-style docstring so Buddy can expose it as a tool), which is
validated and saved to ``~/.buddy/aura_tools/<name>.py``. The Aura agent then
loads these automatically, so users extend their assistant just by asking.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_TOOLS_DIR = Path(os.getenv("BUDDY_AURA_TOOLS", Path.home() / ".buddy" / "aura_tools"))

GENERATION_PROMPT = """You are a Python tool generator for an AI coding assistant.
Write EXACTLY ONE self-contained Python function that implements the user's request.

STRICT rules:
- Output ONLY raw Python code. No markdown fences, no prose, no examples.
- The function MUST have full type hints on every parameter and the return type.
- Return type MUST be `str` (serialize results to a string / JSON string).
- Include a Google-style docstring: a one-line summary, then an `Args:` section
  documenting every parameter, then a `Returns:` section.
- Put any imports INSIDE the function body.
- Do not call the function or add top-level code. No classes. No global state.
- Handle errors gracefully and return an error string instead of raising.

User request:
{request}
"""

_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _ensure_dir() -> Path:
    _TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    return _TOOLS_DIR


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # remove ```python ... ``` wrapper
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def _extract_function_name(code: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


def validate_tool_code(code: str) -> Dict[str, Any]:
    """Validate generated code defines exactly one importable function.

    Returns ``{"ok": bool, "name": str|None, "error": str|None}``.
    """
    code = _strip_fences(code)
    name = _extract_function_name(code)
    if not name:
        return {"ok": False, "name": None, "error": "No top-level function found in generated code."}
    if not _NAME_RE.match(name):
        return {"ok": False, "name": name, "error": f"Invalid function name '{name}'."}
    namespace: Dict[str, Any] = {}
    try:
        exec(compile(code, f"<aura_tool:{name}>", "exec"), namespace)  # noqa: S102 - user-authored tool
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "name": name, "error": f"Code failed to execute: {exc}"}
    if not callable(namespace.get(name)):
        return {"ok": False, "name": name, "error": f"'{name}' is not callable."}
    return {"ok": True, "name": name, "error": None, "code": code}


def generate_tool_code(prompt: str, settings) -> Dict[str, Any]:
    """Use the configured model to generate tool code from a description."""
    from buddy.agent import Agent
    from buddy.code.agent import build_model

    settings.apply_to_env()
    model = build_model(settings)
    gen = Agent(model=model, instructions=[GENERATION_PROMPT.format(request=prompt)], markdown=False)
    resp = gen.run("Generate the tool now.")
    code = getattr(resp, "content", None) or str(resp)
    result = validate_tool_code(code)
    return result


def save_custom_tool(name: str, code: str, description: str = "") -> Dict[str, Any]:
    """Validate and persist a custom tool to disk."""
    result = validate_tool_code(code)
    if not result["ok"]:
        return result
    real_name = result["name"]
    _ensure_dir()
    header = (
        f"# Aura custom tool\n"
        f"# name: {real_name}\n"
        f"# description: {description}\n"
        f"# created: {datetime.now(timezone.utc).isoformat()}\n\n"
    )
    (_TOOLS_DIR / f"{real_name}.py").write_text(header + result["code"] + "\n", encoding="utf-8")
    return {"ok": True, "name": real_name, "error": None}


def delete_custom_tool(name: str) -> bool:
    path = _TOOLS_DIR / f"{name}.py"
    if path.exists():
        path.unlink()
        return True
    return False


def list_custom_tools() -> List[Dict[str, Any]]:
    if not _TOOLS_DIR.exists():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(_TOOLS_DIR.glob("*.py")):
        meta: Dict[str, Any] = {"name": path.stem, "description": ""}
        try:
            for line in path.read_text(encoding="utf-8").splitlines()[:6]:
                if line.startswith("# description:"):
                    meta["description"] = line.split(":", 1)[1].strip()
        except Exception:
            pass
        out.append(meta)
    return out


def load_custom_tools() -> List[Callable]:
    """Import every saved custom tool and return the callables."""
    if not _TOOLS_DIR.exists():
        return []
    fns: List[Callable] = []
    for path in sorted(_TOOLS_DIR.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(f"aura_tool_{path.stem}", path)
            if not spec or not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            fn = getattr(module, path.stem, None)
            if callable(fn):
                fns.append(fn)
        except Exception:
            continue
    return fns


__all__ = [
    "generate_tool_code",
    "validate_tool_code",
    "save_custom_tool",
    "delete_custom_tool",
    "list_custom_tools",
    "load_custom_tools",
]
