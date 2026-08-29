"""Adapt Buddy agents and teams into LangGraph nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

if TYPE_CHECKING:  # pragma: no cover - typing only
    from buddy.agent import Agent
    from buddy.team import Team


class BuddyNode:
    """A LangGraph-compatible node backed by a Buddy ``Agent`` or ``Team``.

    A ``BuddyNode`` is a plain callable ``state -> state_update`` (and an async
    callable), which is exactly LangGraph's node contract. It reads a prompt
    from the graph state, runs the Buddy agent, and writes the result back.

    Input resolution order:
        1. ``state[input_key]`` if present and truthy.
        2. The content of the last entry in ``state["messages"]`` (supports
           LangChain message objects, ``(role, content)`` tuples, and dicts).
        3. The stringified state as a last resort.

    State update written:
        - ``state[output_key]`` = the agent's text response.
        - If ``append_messages`` is True, an assistant message is appended to
          ``state["messages"]`` using LangChain's ``add_messages`` semantics
          when available, otherwise a plain list append.

    Args:
        agent: The Buddy ``Agent`` or ``Team`` to run.
        name: Node name (defaults to the agent's name).
        input_key: State key holding the prompt. Defaults to ``"input"``.
        output_key: State key to write the response to. Defaults to ``"output"``.
        append_messages: Whether to also append to ``state["messages"]``.
    """

    def __init__(
        self,
        agent: Union["Agent", "Team"],
        *,
        name: Optional[str] = None,
        input_key: str = "input",
        output_key: str = "output",
        append_messages: bool = True,
    ) -> None:
        self.agent = agent
        self.name = name or getattr(agent, "name", None) or "buddy_node"
        self.input_key = input_key
        self.output_key = output_key
        self.append_messages = append_messages

    def _resolve_input(self, state: Dict[str, Any]) -> str:
        value = state.get(self.input_key)
        if value:
            return value if isinstance(value, str) else str(value)

        messages = state.get("messages")
        if messages:
            return _message_content(messages[-1])

        return str(state)

    def _build_update(self, state: Dict[str, Any], content: str) -> Dict[str, Any]:
        update: Dict[str, Any] = {self.output_key: content}
        if self.append_messages:
            update["messages"] = _assistant_messages(content)
        return update

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._resolve_input(state)
        response = self.agent.run(prompt)
        return self._build_update(state, _content_of(response))

    async def __acall__(self, state: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        return await self.ainvoke(state)

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._resolve_input(state)
        response = await self.agent.arun(prompt)
        return self._build_update(state, _content_of(response))


def _content_of(response: Any) -> str:
    get_content = getattr(response, "get_content_as_string", None)
    if callable(get_content):
        return get_content()
    return str(getattr(response, "content", response))


def _message_content(message: Any) -> str:
    # LangChain message object
    content = getattr(message, "content", None)
    if content is not None:
        return content if isinstance(content, str) else str(content)
    # (role, content) tuple
    if isinstance(message, (tuple, list)) and len(message) == 2:
        return str(message[1])
    # dict-shaped message
    if isinstance(message, dict):
        return str(message.get("content", message))
    return str(message)


def _assistant_messages(content: str) -> Any:
    """Return an assistant message list suitable for ``add_messages`` reducers."""
    try:
        from langchain_core.messages import AIMessage

        return [AIMessage(content=content)]
    except ImportError:
        return [("assistant", content)]
