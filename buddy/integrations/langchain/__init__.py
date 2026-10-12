"""LangChain interoperability for Buddy AI.

Use Buddy's unified model layer, agents, and tools from within the LangChain
ecosystem — and bring LangChain tools into Buddy.

Public API:

- :class:`BuddyChatModel` — wrap any ``buddy.models`` model as a LangChain
  ``BaseChatModel`` so Buddy's 30+ providers work in LangChain chains.
- :class:`BuddyAgentTool` — expose a Buddy ``Agent`` or ``Team`` as a LangChain
  ``BaseTool`` that other LangChain agents can call.
- :func:`to_langchain_tool` / :func:`from_langchain_tool` — convert tools in
  either direction between Buddy ``Function`` and LangChain ``BaseTool``.
- :func:`to_buddy_messages` / :func:`from_buddy_message` — convert message
  objects between the two frameworks.

All LangChain imports are lazy; ``import buddy.integrations.langchain`` works
without LangChain installed and only raises when an adapter is actually used.
"""

from __future__ import annotations

__all__ = [
    "BuddyChatModel",
    "BuddyAgentTool",
    "to_langchain_tool",
    "from_langchain_tool",
    "to_buddy_messages",
    "from_buddy_message",
]


def __getattr__(name: str):  # pragma: no cover - thin lazy import shim
    if name == "BuddyChatModel":
        from buddy.integrations.langchain.chat_model import BuddyChatModel

        globals()[name] = BuddyChatModel
        return BuddyChatModel
    if name in {"from_buddy_message", "to_buddy_messages"}:
        from buddy.integrations.langchain import messages

        value = getattr(messages, name)
        globals()[name] = value
        return value
    if name in {"BuddyAgentTool", "from_langchain_tool", "to_langchain_tool"}:
        from buddy.integrations.langchain import tools

        value = getattr(tools, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
