"""Tool conversion between LangChain and Buddy, plus agent-as-tool wrapping."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from buddy.tools.function import Function

if TYPE_CHECKING:  # pragma: no cover - typing only
    from langchain_core.tools import BaseTool

    from buddy.agent import Agent
    from buddy.team import Team


def to_langchain_tool(tool: Union[Function, Callable]) -> "BaseTool":
    """Convert a Buddy ``Function`` (or plain callable) to a LangChain tool.

    Args:
        tool: A Buddy ``Function`` produced by the ``@tool`` decorator, or any
            plain callable with type hints and a docstring.

    Returns:
        A LangChain ``StructuredTool`` that invokes the underlying entrypoint.
    """
    from langchain_core.tools import StructuredTool

    if isinstance(tool, Function):
        fn = tool
    else:
        fn = Function.from_callable(tool)

    entrypoint = fn.entrypoint
    if entrypoint is None:
        raise ValueError(f"Buddy Function '{fn.name}' has no entrypoint and cannot be converted to a LangChain tool.")

    return StructuredTool.from_function(
        func=entrypoint,
        name=fn.name,
        description=fn.description or fn.name,
    )


def from_langchain_tool(tool: "BaseTool") -> Function:
    """Convert a LangChain ``BaseTool`` into a Buddy ``Function``.

    The resulting ``Function`` can be passed directly in an ``Agent(tools=[...])``
    list. Invocation is delegated to the LangChain tool's ``run`` method.
    """
    from langchain_core.tools import BaseTool

    if not isinstance(tool, BaseTool):
        raise TypeError(f"Expected a LangChain BaseTool, got {type(tool).__name__}.")

    def _entrypoint(**kwargs: Any) -> Any:
        return tool.run(kwargs)

    _entrypoint.__name__ = tool.name
    _entrypoint.__doc__ = tool.description or tool.name

    parameters = _langchain_args_schema_to_json(tool)

    return Function(
        name=tool.name,
        description=tool.description or tool.name,
        parameters=parameters,
        entrypoint=_entrypoint,
        skip_entrypoint_processing=True,
        sanitize_arguments=False,
    )


def _langchain_args_schema_to_json(tool: "BaseTool") -> dict:
    """Best-effort extraction of a JSON-schema parameter spec from a tool."""
    default = {"type": "object", "properties": {}, "required": []}

    args_schema = getattr(tool, "args_schema", None)
    if args_schema is None:
        return default

    # pydantic v2
    if hasattr(args_schema, "model_json_schema"):
        try:
            schema = args_schema.model_json_schema()
            return _clean_schema(schema)
        except Exception:  # pragma: no cover - defensive
            return default

    # pydantic v1
    if hasattr(args_schema, "schema"):
        try:
            schema = args_schema.schema()
            return _clean_schema(schema)
        except Exception:  # pragma: no cover - defensive
            return default

    return default


def _clean_schema(schema: dict) -> dict:
    """Keep only the fields Buddy's tool layer expects from a JSON schema."""
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }


class BuddyAgentTool:
    """Expose a Buddy ``Agent`` or ``Team`` as a LangChain ``BaseTool``.

    This lets a LangChain (or LangGraph) agent delegate a subtask to a fully
    featured Buddy agent — with its own model, tools, memory, and knowledge.

    Example:
        >>> from buddy import Agent
        >>> from buddy.models.openai import OpenAIChat
        >>> from buddy.integrations.langchain import BuddyAgentTool
        >>> researcher = Agent(name="researcher", model=OpenAIChat(id="gpt-4o-mini"))
        >>> lc_tool = BuddyAgentTool(researcher, name="research",
        ...                         description="Research a topic in depth").as_tool()
    """

    def __init__(
        self,
        agent: Union["Agent", "Team"],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        self.agent = agent
        self.name = name or getattr(agent, "name", None) or "buddy_agent"
        self.description = (
            description
            or getattr(agent, "description", None)
            or getattr(agent, "role", None)
            or f"Delegate a task to the Buddy agent '{self.name}'."
        )

    def _run_agent(self, query: str) -> str:
        response = self.agent.run(query)
        get_content = getattr(response, "get_content_as_string", None)
        if callable(get_content):
            return get_content()
        return str(getattr(response, "content", response))

    async def _arun_agent(self, query: str) -> str:
        response = await self.agent.arun(query)
        get_content = getattr(response, "get_content_as_string", None)
        if callable(get_content):
            return get_content()
        return str(getattr(response, "content", response))

    def as_tool(self) -> "BaseTool":
        """Build the LangChain ``StructuredTool`` for this Buddy agent."""
        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            func=self._run_agent,
            coroutine=self._arun_agent,
            name=self.name,
            description=self.description,
        )
