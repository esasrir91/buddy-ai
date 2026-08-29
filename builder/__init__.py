"""Buddy Builder - a no-code, drag-and-drop platform for building Buddy agents,
teams, workflows and full agent apps.

The builder is a thin *visual layer* over the Buddy framework. Everything a user
drags onto the canvas is serialized into a versioned :class:`GraphSpec` JSON
document, which the :mod:`buddy.builder.compiler` turns into live Buddy objects
(:class:`~buddy.agent.Agent`, :class:`~buddy.team.Team`,
:class:`~buddy.workflow.Workflow`).

Sub-packages
------------
- ``spec``     : the GraphSpec schema (the single source of truth)
- ``registry`` : auto-introspection of every Buddy building block into a catalog
- ``compiler`` : GraphSpec -> Buddy objects
- ``runner``   : execute a compiled graph and stream events
- ``server``   : FastAPI backend (catalog, project CRUD, compile, run)
"""

from buddy.builder.spec.schema import (
    Capability,
    Edge,
    EvalSpec,
    GraphSpec,
    Node,
    Trigger,
)

__all__ = [
    "GraphSpec",
    "Node",
    "Edge",
    "Capability",
    "Trigger",
    "EvalSpec",
]
