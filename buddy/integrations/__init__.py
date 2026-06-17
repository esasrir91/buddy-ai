"""Buddy AI integrations with third-party orchestration frameworks.

This package provides optional, dependency-light adapters that let Buddy
components interoperate with the LangChain and LangGraph ecosystems:

- :mod:`buddy.integrations.langchain` — use Buddy models, agents, and tools
  inside LangChain (and pull LangChain tools into Buddy).
- :mod:`buddy.integrations.langgraph` — drop Buddy agents and teams into a
  LangGraph ``StateGraph`` as nodes, with helpers for routing edges.

The third-party packages are imported lazily, so importing
``buddy.integrations`` never requires ``langchain`` or ``langgraph`` to be
installed. Each submodule raises a clear, actionable error if the relevant
package is missing.
"""

from __future__ import annotations

__all__ = ["langchain", "langgraph"]


def __getattr__(name: str):  # pragma: no cover - thin lazy import shim
    if name in __all__:
        import importlib

        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
