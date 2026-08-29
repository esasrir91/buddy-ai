"""Backward-compatibility shim.

The canonical implementation has moved to :mod:`buddy.agent.context_editing`
where it belongs architecturally — context editing manages the *agent's*
conversation history, not the model's inference parameters.

All public names are re-exported here so that existing code that imports
from ``buddy.models.context_editing`` continues to work unchanged.
"""

from buddy.agent.context_editing import (  # noqa: F401
    ContextEditingConfig,
    aggressive_editing,
    clear_agent_images,
    clear_agent_thinking_blocks,
    clear_agent_tool_results,
    clear_thinking_blocks,
    clear_tool_results,
    light_editing,
    moderate_editing,
    replace_content_blocks,
    truncate_agent_messages,
    truncate_messages,
)

__all__ = [
    "ContextEditingConfig",
    "light_editing",
    "moderate_editing",
    "aggressive_editing",
    "truncate_agent_messages",
    "clear_agent_tool_results",
    "clear_agent_thinking_blocks",
    "clear_agent_images",
    # Raw dict helpers (for model-layer use)
    "clear_tool_results",
    "clear_thinking_blocks",
    "truncate_messages",
    "replace_content_blocks",
]
