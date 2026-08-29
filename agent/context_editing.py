"""Context editing utilities for managing an agent's conversation history.

Provides helpers to keep long-running conversations within context-window
limits by editing the *agent-level* message list (``List[Message]``) before
it is forwarded to the model.  A lower-level variant that operates on raw
provider-format dicts (``List[Dict]``) is also re-exported here for use
inside model implementations.

Strategies
----------
* **Message truncation** — drop the oldest non-system messages.
* **Tool result clearing** — replace old tool-call outputs with a short
  placeholder, preserving conversation structure without the bulk.
* **Thinking block clearing** — strip accumulated ``thinking`` / extended-
  thinking blocks from earlier assistant turns.
* **Image clearing** — replace base64 image blocks older than the last
  *n* images with a text placeholder.

Usage::

    from buddy.agent.context_editing import ContextEditingConfig, moderate_editing

    agent = Agent(
        model=Claude(id="claude-opus-5"),
        context_editing=moderate_editing(),
    )

References
----------
* https://platform.claude.com/docs/en/build-with-claude/context-editing
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from buddy.models.message import Message


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLEARED_TOOL_RESULT_PLACEHOLDER = "[tool result cleared to save context]"
_CLEARED_THINKING_PLACEHOLDER = ""
_DEFAULT_IMAGE_PLACEHOLDER = "[image removed to save context]"


# ---------------------------------------------------------------------------
# Message-object helpers  (operate on List[Message] — the agent layer)
# ---------------------------------------------------------------------------


def truncate_agent_messages(
    messages: List[Message],
    max_messages: int,
    keep_system: bool = True,
) -> Tuple[List[Message], int]:
    """Drop the oldest non-system messages to stay within *max_messages*.

    Args:
        messages: Agent-level message list (``List[Message]``).
        max_messages: Maximum number of messages to keep.
        keep_system: Always preserve system-role messages.

    Returns:
        ``(truncated_messages, dropped_count)``
    """
    if len(messages) <= max_messages:
        return messages, 0

    if keep_system:
        system = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]
        budget = max(0, max_messages - len(system))
        if len(non_system) <= budget:
            return messages, 0
        dropped = len(non_system) - budget
        return system + non_system[dropped:], dropped
    else:
        dropped = len(messages) - max_messages
        return messages[dropped:], dropped


def clear_agent_tool_results(
    messages: List[Message],
    keep_last_n: int = 0,
    placeholder: str = _CLEARED_TOOL_RESULT_PLACEHOLDER,
) -> Tuple[List[Message], int]:
    """Replace old tool-call outputs with *placeholder* to save tokens.

    Handles both OpenAI-style (``role="tool"`` messages) and Anthropic-style
    (``role="user"`` messages with ``tool_result`` content blocks).

    Args:
        messages: Agent-level message list.
        keep_last_n: Keep the last *n* tool results verbatim.
        placeholder: Replacement text for cleared results.

    Returns:
        ``(edited_messages, cleared_count)``
    """
    msgs = list(messages)
    cleared = 0

    # Collect (index, block_index_or_None) for all tool results
    positions: List[Tuple[int, Optional[int]]] = []

    for i, msg in enumerate(msgs):
        if msg.role == "tool":
            positions.append((i, None))
        elif isinstance(msg.content, list):
            for j, block in enumerate(msg.content):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    positions.append((i, j))

    to_clear = positions[: max(0, len(positions) - keep_last_n)]

    for msg_idx, block_idx in to_clear:
        msg = msgs[msg_idx]
        if block_idx is None:
            if msg.content != placeholder:
                msgs[msg_idx] = msg.model_copy(update={"content": placeholder})
                cleared += 1
        else:
            content = list(msg.content)  # type: ignore[arg-type]
            block = content[block_idx]
            current = block.get("content")
            if current != placeholder:
                new_block = {**block}
                if isinstance(current, list):
                    new_block["content"] = [{"type": "text", "text": placeholder}]
                else:
                    new_block["content"] = placeholder
                content[block_idx] = new_block
                msgs[msg_idx] = msg.model_copy(update={"content": content})
                cleared += 1

    return msgs, cleared


def clear_agent_thinking_blocks(
    messages: List[Message],
    keep_last_n: int = 0,
    clear_redacted: bool = True,
) -> Tuple[List[Message], int]:
    """Strip old thinking blocks from assistant messages.

    Args:
        messages: Agent-level message list.
        keep_last_n: Keep thinking blocks in the last *n* assistant turns.
        clear_redacted: Also remove ``redacted_thinking`` blocks.

    Returns:
        ``(edited_messages, cleared_count)``
    """
    msgs = list(messages)
    cleared = 0

    thinking_positions: List[Tuple[int, List[int]]] = []
    for i, msg in enumerate(msgs):
        if msg.role != "assistant" or not isinstance(msg.content, list):
            continue
        block_idxs = [
            j
            for j, b in enumerate(msg.content)
            if isinstance(b, dict)
            and b.get("type") in ("thinking", "redacted_thinking")
            and (b.get("type") != "redacted_thinking" or clear_redacted)
        ]
        if block_idxs:
            thinking_positions.append((i, block_idxs))

    to_clear = thinking_positions[: max(0, len(thinking_positions) - keep_last_n)]

    for msg_idx, block_idxs in to_clear:
        content = list(msgs[msg_idx].content)  # type: ignore[arg-type]
        for bidx in sorted(block_idxs, reverse=True):
            block = content[bidx]
            if block.get("type") == "thinking":
                content[bidx] = {**block, "thinking": _CLEARED_THINKING_PLACEHOLDER}
                cleared += 1
            elif block.get("type") == "redacted_thinking":
                content.pop(bidx)
                cleared += 1
        msgs[msg_idx] = msgs[msg_idx].model_copy(update={"content": content})

    return msgs, cleared


def clear_agent_images(
    messages: List[Message],
    keep_last_n: int = 0,
    placeholder: str = _DEFAULT_IMAGE_PLACEHOLDER,
) -> Tuple[List[Message], int]:
    """Replace old base64 image blocks with a lightweight text placeholder.

    Args:
        messages: Agent-level message list.
        keep_last_n: Keep the last *n* image blocks verbatim.
        placeholder: Text to substitute for cleared images.

    Returns:
        ``(edited_messages, replaced_count)``
    """
    msgs = list(messages)

    all_images: List[Tuple[int, int]] = []
    for i, msg in enumerate(msgs):
        if isinstance(msg.content, list):
            for j, block in enumerate(msg.content):
                if isinstance(block, dict) and block.get("type") == "image":
                    all_images.append((i, j))

    to_replace = all_images[: max(0, len(all_images) - keep_last_n)]
    for msg_idx, blk_idx in to_replace:
        content = list(msgs[msg_idx].content)  # type: ignore[arg-type]
        content[blk_idx] = {"type": "text", "text": placeholder}
        msgs[msg_idx] = msgs[msg_idx].model_copy(update={"content": content})

    return msgs, len(to_replace)


# ---------------------------------------------------------------------------
# ContextEditingConfig
# ---------------------------------------------------------------------------


@dataclass
class ContextEditingConfig:
    """Declarative configuration for automatic context editing on an agent.

    Attach to ``Agent(context_editing=...)`` to have Buddy automatically
    trim the conversation history before each model call.

    Attributes:
        clear_tool_results_keep_last: Clear tool-result content, keeping
            only the last *n* results verbatim.  ``None`` disables this.
        clear_thinking_keep_last: Clear accumulated thinking blocks,
            keeping the last *n* assistant turns' thinking intact.
            ``None`` disables this.
        clear_redacted_thinking: Also drop ``redacted_thinking`` blocks.
        max_messages: Truncate to at most this many messages (oldest
            non-system messages are dropped first).  ``None`` disables.
        keep_system_on_truncation: Always keep system messages when
            truncating.
        image_placeholder: Replace old base64 image blocks with this text.
            ``None`` disables image clearing.
        keep_last_n_images: Number of recent image blocks to keep verbatim.
    """

    clear_tool_results_keep_last: Optional[int] = None
    clear_thinking_keep_last: Optional[int] = None
    clear_redacted_thinking: bool = True
    max_messages: Optional[int] = None
    keep_system_on_truncation: bool = True
    image_placeholder: Optional[str] = None
    keep_last_n_images: int = 0

    def apply(self, messages: List[Message]) -> Tuple[List[Message], Dict[str, int]]:
        """Apply all configured edits in-order to *messages*.

        Args:
            messages: Agent-level ``List[Message]`` to edit.

        Returns:
            ``(edited_messages, stats)`` where *stats* maps each edit type
            to the number of changes made.
        """
        stats: Dict[str, int] = {}
        msgs = list(messages)

        if self.clear_tool_results_keep_last is not None:
            msgs, n = clear_agent_tool_results(
                msgs, keep_last_n=self.clear_tool_results_keep_last
            )
            stats["tool_results_cleared"] = n

        if self.clear_thinking_keep_last is not None:
            msgs, n = clear_agent_thinking_blocks(
                msgs,
                keep_last_n=self.clear_thinking_keep_last,
                clear_redacted=self.clear_redacted_thinking,
            )
            stats["thinking_blocks_cleared"] = n

        if self.image_placeholder is not None:
            msgs, n = clear_agent_images(
                msgs,
                keep_last_n=self.keep_last_n_images,
                placeholder=self.image_placeholder,
            )
            stats["images_replaced"] = n

        if self.max_messages is not None:
            msgs, n = truncate_agent_messages(
                msgs,
                max_messages=self.max_messages,
                keep_system=self.keep_system_on_truncation,
            )
            stats["messages_dropped"] = n

        return msgs, stats


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def light_editing() -> ContextEditingConfig:
    """Minimal editing: clear old thinking blocks only."""
    return ContextEditingConfig(clear_thinking_keep_last=2)


def moderate_editing() -> ContextEditingConfig:
    """Clear old thinking blocks and old tool results."""
    return ContextEditingConfig(
        clear_thinking_keep_last=2,
        clear_tool_results_keep_last=3,
    )


def aggressive_editing(max_messages: int = 50) -> ContextEditingConfig:
    """Clear thinking, tool results, images, and truncate history."""
    return ContextEditingConfig(
        clear_thinking_keep_last=1,
        clear_tool_results_keep_last=1,
        image_placeholder=_DEFAULT_IMAGE_PLACEHOLDER,
        keep_last_n_images=2,
        max_messages=max_messages,
    )


# ---------------------------------------------------------------------------
# Raw-dict helpers (re-exported for use inside model implementations)
# ---------------------------------------------------------------------------
# These operate on List[Dict[str, Any]] (provider-formatted messages) and are
# kept here so model-layer code that needs them does not have to reach into
# agent/.  They are unchanged from the original implementation.

from copy import deepcopy as _deepcopy
from typing import Callable as _Callable


def clear_tool_results(
    messages: List[Dict[str, Any]],
    keep_last_n: int = 0,
    placeholder: str = _CLEARED_TOOL_RESULT_PLACEHOLDER,
    deep_copy: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """Clear old tool results from a raw provider-format message list."""
    msgs = _deepcopy(messages) if deep_copy else messages
    cleared = 0
    positions: List[Tuple[int, Optional[int]]] = []

    for i, msg in enumerate(msgs):
        role = msg.get("role", "")
        content = msg.get("content")
        if role == "tool":
            positions.append((i, None))
        elif isinstance(content, list):
            for j, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    positions.append((i, j))

    to_clear = positions[: max(0, len(positions) - keep_last_n)]
    for msg_idx, block_idx in to_clear:
        msg = msgs[msg_idx]
        if block_idx is None:
            if msg.get("content") != placeholder:
                msg["content"] = placeholder
                cleared += 1
        else:
            block = msg["content"][block_idx]
            content_val = block.get("content")
            if content_val != placeholder:
                if isinstance(content_val, list):
                    block["content"] = [{"type": "text", "text": placeholder}]
                else:
                    block["content"] = placeholder
                cleared += 1

    return msgs, cleared


def clear_thinking_blocks(
    messages: List[Dict[str, Any]],
    keep_last_n: int = 0,
    clear_redacted: bool = True,
    deep_copy: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """Clear thinking blocks from a raw provider-format message list."""
    msgs = _deepcopy(messages) if deep_copy else messages
    cleared = 0
    thinking_positions: List[Tuple[int, List[int]]] = []

    for i, msg in enumerate(msgs):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        block_idxs = [
            j
            for j, block in enumerate(content)
            if isinstance(block, dict)
            and block.get("type") in ("thinking", "redacted_thinking")
            and (block.get("type") != "redacted_thinking" or clear_redacted)
        ]
        if block_idxs:
            thinking_positions.append((i, block_idxs))

    to_clear = thinking_positions[: max(0, len(thinking_positions) - keep_last_n)]
    for msg_idx, block_idxs in to_clear:
        content = msgs[msg_idx]["content"]
        for bidx in sorted(block_idxs, reverse=True):
            block = content[bidx]
            if block.get("type") == "thinking":
                if block.get("thinking") != _CLEARED_THINKING_PLACEHOLDER:
                    block["thinking"] = _CLEARED_THINKING_PLACEHOLDER
                    cleared += 1
            elif block.get("type") == "redacted_thinking":
                content.pop(bidx)
                cleared += 1

    return msgs, cleared


def truncate_messages(
    messages: List[Dict[str, Any]],
    max_messages: int,
    keep_system: bool = True,
    deep_copy: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """Truncate a raw provider-format message list to *max_messages*."""
    msgs = _deepcopy(messages) if deep_copy else list(messages)
    if len(msgs) <= max_messages:
        return msgs, 0
    if keep_system:
        system = [m for m in msgs if m.get("role") == "system"]
        non_system = [m for m in msgs if m.get("role") != "system"]
        budget = max(0, max_messages - len(system))
        if len(non_system) <= budget:
            return msgs, 0
        dropped = len(non_system) - budget
        return system + non_system[dropped:], dropped
    dropped = len(msgs) - max_messages
    return msgs[dropped:], dropped


def replace_content_blocks(
    messages: List[Dict[str, Any]],
    predicate: _Callable[[Dict[str, Any]], bool],
    replacement: Dict[str, Any],
    deep_copy: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """Replace matching content blocks in a raw provider-format message list."""
    msgs = _deepcopy(messages) if deep_copy else messages
    replaced = 0
    for msg in msgs:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for i, block in enumerate(content):
            if isinstance(block, dict) and predicate(block):
                content[i] = replacement
                replaced += 1
    return msgs, replaced
