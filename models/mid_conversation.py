"""Mid-conversation system messages and tool changes.

Allows updating system instructions and tool availability **mid-conversation**
without invalidating the prompt-cache prefix, by injecting ``{"role": "system"}``
messages at specific points in the conversation history.

Supported features
------------------
* **Mid-conversation system messages**: Append a system-role message at any
  point in the conversation.  Works on Claude Fable 5, Claude Mythos 5,
  Claude Opus 4.8, Claude Opus 5 (no beta header required).

* **Mid-conversation tool changes** (beta): Add or remove specific tools at a
  conversation checkpoint using ``tool_addition`` / ``tool_removal`` content
  blocks.  Requires the beta header ``mid-conversation-tool-changes-2026-07-01``
  and a model in the supported set.

* **Mid-conversation effort/thinking changes**: Adjust the reasoning intensity
  (effort level or thinking budget) between turns using a system message hint
  recognized by Buddy.  Works with any model via the :class:`EffortConfig` and
  :class:`ThinkingConfig` present in ``buddy.models``.

For other LLM providers that don't support a native system-role message in the
conversation, a ``user``-role fallback message is automatically substituted so
the instruction is still communicated, albeit at a lower priority.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Supported models
# ---------------------------------------------------------------------------

_MID_CONV_SYSTEM_MODELS = {
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    "claude-opus-5",
    "claude-opus-4-8",
}

_MID_CONV_TOOL_CHANGES_BETA = "mid-conversation-tool-changes-2026-07-01"

_MID_CONV_TOOL_CHANGE_MODELS = {
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-5",
    "claude-opus-4-8",
}


def supports_mid_conversation_system(model_id: str) -> bool:
    """Return True when *model_id* natively supports mid-conversation system messages."""
    for prefix in _MID_CONV_SYSTEM_MODELS:
        if model_id.startswith(prefix):
            return True
    return False


def supports_mid_conversation_tool_changes(model_id: str) -> bool:
    """Return True when *model_id* supports mid-conversation tool changes (beta)."""
    for prefix in _MID_CONV_TOOL_CHANGE_MODELS:
        if model_id.startswith(prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# Building mid-conversation system messages
# ---------------------------------------------------------------------------


def make_system_message(
    text: str,
    model_id: str = "",
    fallback_role: str = "user",
) -> Dict[str, Any]:
    """Create a mid-conversation system message dict.

    For models that support native system-role messages in the conversation,
    returns ``{"role": "system", "content": text}``.  For all other providers,
    returns a user-role message with a clearly delimited instruction block so
    the model still treats it as an instruction update.

    Args:
        text: The new system instruction text.
        model_id: Target model ID.  Used to decide native vs. fallback.
        fallback_role: Role to use for non-native providers (``"user"``).

    Returns:
        A message dict ready to be appended to the conversation.
    """
    if supports_mid_conversation_system(model_id) or not model_id:
        return {"role": "system", "content": text}

    # Fallback: wrap in a clearly labelled user block
    wrapped = (
        "<system_instruction_update>\n"
        f"{text}\n"
        "</system_instruction_update>"
    )
    return {"role": fallback_role, "content": wrapped}


def inject_system_message(
    messages: List[Dict[str, Any]],
    text: str,
    model_id: str = "",
    position: int = -1,
    deep_copy: bool = True,
) -> List[Dict[str, Any]]:
    """Inject a mid-conversation system message into *messages*.

    Args:
        messages: Existing conversation history.
        text: New system instruction text.
        model_id: Target model ID.
        position: Index at which to insert (``-1`` appends before the last
            user message so the instruction precedes the next user turn, which
            is the recommended placement).
        deep_copy: Make a deep copy of *messages* before mutating.

    Returns:
        Updated message list.
    """
    msgs = deepcopy(messages) if deep_copy else list(messages)
    msg = make_system_message(text, model_id=model_id)

    if position == -1:
        msgs.append(msg)
    else:
        msgs.insert(position, msg)

    return msgs


# ---------------------------------------------------------------------------
# Mid-conversation tool changes
# ---------------------------------------------------------------------------


def make_tool_addition_block(tool_name: str) -> Dict[str, Any]:
    """Return a ``tool_addition`` content block for tool *tool_name*."""
    return {
        "type": "tool_addition",
        "tool": {"type": "tool_reference", "name": tool_name},
    }


def make_tool_removal_block(tool_name: str) -> Dict[str, Any]:
    """Return a ``tool_removal`` content block for tool *tool_name*."""
    return {
        "type": "tool_removal",
        "tool": {"type": "tool_reference", "name": tool_name},
    }


def make_tool_change_message(
    add: Optional[List[str]] = None,
    remove: Optional[List[str]] = None,
    system_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a mid-conversation tool-change system message.

    Combines ``tool_addition``, ``tool_removal``, and optional text blocks
    into a single ``{"role": "system"}`` message.

    Args:
        add: Tool names to add (re-offer) at this point.
        remove: Tool names to remove (withdraw) at this point.
        system_text: Optional text instruction to include alongside the
            tool changes.

    Returns:
        A system-role message dict with the appropriate content blocks.
    """
    content: List[Dict[str, Any]] = []

    for name in (add or []):
        content.append(make_tool_addition_block(name))

    for name in (remove or []):
        content.append(make_tool_removal_block(name))

    if system_text:
        content.append({"type": "text", "text": system_text})

    return {"role": "system", "content": content}


def inject_tool_changes(
    messages: List[Dict[str, Any]],
    add: Optional[List[str]] = None,
    remove: Optional[List[str]] = None,
    system_text: Optional[str] = None,
    position: int = -1,
    deep_copy: bool = True,
) -> List[Dict[str, Any]]:
    """Inject a mid-conversation tool-change message into *messages*.

    Args:
        messages: Existing conversation history.
        add: Tool names to add at this point.
        remove: Tool names to remove at this point.
        system_text: Optional extra system instruction text.
        position: Insertion index (``-1`` appends).
        deep_copy: Make a deep copy before mutating.

    Returns:
        Updated message list.
    """
    msgs = deepcopy(messages) if deep_copy else list(messages)
    msg = make_tool_change_message(add=add, remove=remove, system_text=system_text)

    if position == -1:
        msgs.append(msg)
    else:
        msgs.insert(position, msg)

    return msgs


# ---------------------------------------------------------------------------
# Mid-conversation effort / thinking adjustment
# ---------------------------------------------------------------------------


def make_effort_hint_message(
    effort: str,
    model_id: str = "",
) -> Dict[str, Any]:
    """Create a system message that hints the model to adjust reasoning effort.

    For Claude models this is a Buddy-level instruction that will be picked
    up by the Claude model implementation to adjust the ``thinking`` param.
    For OpenAI reasoning models the ``reasoning_effort`` param is set at the
    request level, so this message triggers the same update via Buddy's
    model layer.

    Args:
        effort: One of ``"low"``, ``"medium"``, ``"high"``, ``"max"``.
        model_id: Target model ID.

    Returns:
        A system-role message (or user-role fallback) with the effort hint.
    """
    text = f"<buddy:effort_hint level={effort!r}/>"
    return make_system_message(text, model_id=model_id)


def make_thinking_mode_message(
    mode: str,
    budget_tokens: Optional[int] = None,
    model_id: str = "",
) -> Dict[str, Any]:
    """Create a system message instructing the model to change its thinking mode.

    Args:
        mode: ``"adaptive"``, ``"extended"``, or ``"disabled"``.
        budget_tokens: Token budget for extended thinking.
        model_id: Target model ID.

    Returns:
        A system-role (or fallback) message with the thinking-mode hint.
    """
    hint = f"<buddy:thinking_hint mode={mode!r}"
    if budget_tokens is not None:
        hint += f" budget_tokens={budget_tokens}"
    hint += "/>"
    return make_system_message(hint, model_id=model_id)


# ---------------------------------------------------------------------------
# Conversation patch builder — convenience API
# ---------------------------------------------------------------------------


@dataclass
class MidConversationPatch:
    """A set of mid-conversation changes to apply to a message list.

    Build the patch, then call :meth:`apply` to produce the updated message
    list.

    Attributes:
        system_update: New system instruction text to inject.
        tools_to_add: Tool names to surface at this checkpoint.
        tools_to_remove: Tool names to withdraw at this checkpoint.
        effort: New effort level (``"low"`` / ``"medium"`` / ``"high"`` /
            ``"max"``).
        thinking_mode: New thinking mode for Claude.
        thinking_budget: Budget tokens for extended thinking.
        position: Index at which to insert the patch message (``-1`` appends).
    """

    system_update: Optional[str] = None
    tools_to_add: List[str] = field(default_factory=list)
    tools_to_remove: List[str] = field(default_factory=list)
    effort: Optional[str] = None
    thinking_mode: Optional[str] = None
    thinking_budget: Optional[int] = None
    position: int = -1

    def apply(
        self,
        messages: List[Dict[str, Any]],
        model_id: str = "",
        deep_copy: bool = True,
    ) -> List[Dict[str, Any]]:
        """Apply all configured changes to *messages*.

        Returns the updated message list.
        """
        msgs = deepcopy(messages) if deep_copy else list(messages)

        # Build all content blocks that go into a single system message
        content_blocks: List[Any] = []
        system_text_parts: List[str] = []

        # Tool additions/removals
        for name in self.tools_to_add:
            content_blocks.append(make_tool_addition_block(name))
        for name in self.tools_to_remove:
            content_blocks.append(make_tool_removal_block(name))

        # Effort and thinking mode hints
        if self.effort:
            system_text_parts.append(f"<buddy:effort_hint level={self.effort!r}/>")
        if self.thinking_mode:
            hint = f"<buddy:thinking_hint mode={self.thinking_mode!r}"
            if self.thinking_budget:
                hint += f" budget_tokens={self.thinking_budget}"
            hint += "/>"
            system_text_parts.append(hint)

        # System instruction update
        if self.system_update:
            system_text_parts.append(self.system_update)

        combined_text = "\n".join(system_text_parts) if system_text_parts else None

        if not content_blocks and not combined_text:
            return msgs

        if content_blocks:
            # Use structured tool-change message (may include text block)
            if combined_text:
                content_blocks.append({"type": "text", "text": combined_text})
            msg: Dict[str, Any] = {"role": "system", "content": content_blocks}
        else:
            # Pure text system update
            msg = make_system_message(combined_text or "", model_id=model_id)

        if self.position == -1:
            msgs.append(msg)
        else:
            msgs.insert(self.position, msg)

        return msgs

    def required_betas(self, model_id: str) -> List[str]:
        """Return beta headers required for this patch on *model_id*."""
        betas: List[str] = []
        if (self.tools_to_add or self.tools_to_remove) and supports_mid_conversation_tool_changes(model_id):
            betas.append(_MID_CONV_TOOL_CHANGES_BETA)
        return betas
