"""Message conversion between LangChain and Buddy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from buddy.models.message import Message

if TYPE_CHECKING:  # pragma: no cover - typing only
    from langchain_core.messages import BaseMessage


def to_buddy_messages(messages: List["BaseMessage"]) -> List[Message]:
    """Convert a list of LangChain ``BaseMessage`` objects to Buddy ``Message``.

    Role mapping:
        - ``HumanMessage`` -> ``"user"``
        - ``AIMessage`` -> ``"assistant"``
        - ``SystemMessage`` -> ``"system"``
        - ``ToolMessage`` -> ``"tool"`` (preserves ``tool_call_id``)
        - anything else -> falls back to the message ``type`` or ``"user"``
    """
    role_by_type = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
        "tool": "tool",
        "function": "tool",
    }

    converted: List[Message] = []
    for msg in messages:
        msg_type = getattr(msg, "type", None) or "user"
        role = role_by_type.get(msg_type, msg_type)

        content = getattr(msg, "content", "")
        if not isinstance(content, (str, list)):
            content = str(content)

        buddy_msg = Message(role=role, content=content)

        tool_call_id = getattr(msg, "tool_call_id", None)
        if tool_call_id:
            buddy_msg.tool_call_id = tool_call_id

        name = getattr(msg, "name", None)
        if name:
            buddy_msg.name = name

        converted.append(buddy_msg)

    return converted


def from_buddy_message(message: Message) -> "BaseMessage":
    """Convert a single Buddy ``Message`` into the matching LangChain message."""
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    content: Any = message.get_content_string()

    if message.role == "assistant":
        return AIMessage(content=content)
    if message.role == "system":
        return SystemMessage(content=content)
    if message.role == "tool":
        return ToolMessage(content=content, tool_call_id=message.tool_call_id or "")
    return HumanMessage(content=content)
