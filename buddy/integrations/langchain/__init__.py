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

from buddy.integrations.langchain.chat_model import BuddyChatModel
from buddy.integrations.langchain.messages import from_buddy_message, to_buddy_messages
from buddy.integrations.langchain.tools import (
    BuddyAgentTool,
    from_langchain_tool,
    to_langchain_tool,
)

__all__ = [
    "BuddyChatModel",
    "BuddyAgentTool",
    "to_langchain_tool",
    "from_langchain_tool",
    "to_buddy_messages",
    "from_buddy_message",
]
