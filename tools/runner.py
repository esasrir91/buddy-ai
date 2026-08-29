"""ToolRunner – provider-agnostic agentic tool-use loop.

Mirrors the Anthropic SDK's ``beta.messages.tool_runner`` pattern but works
with **any LLM** supported by buddy (Claude, OpenAI, Gemini, Ollama, …).

Typical usage::

    from buddy.tools.runner import ToolRunner
    from buddy.models.anthropic import Claude

    runner = ToolRunner(
        model=Claude(),
        tools=[my_tool_a, my_tool_b],
        messages=[{"role": "user", "content": "What's the weather in Paris?"}],
        max_tokens=1024,
    )

    # Iterate message-by-message (yields one message per model turn)
    for msg in runner:
        print(msg)

    # Or get only the final answer
    final = runner.until_done()
"""

from __future__ import annotations

import asyncio
import json
import logging
from copy import deepcopy
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Union,
)

from buddy.tools.function import Function, FunctionCall, FunctionExecutionResult
from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

ToolLike = Union[Function, Callable, Toolkit, Dict[str, Any]]
Messages = List[Dict[str, Any]]


def _resolve_tools(tools: List[ToolLike]) -> Dict[str, Function]:
    """Flatten Toolkits / callables / dicts into a name→Function registry."""
    registry: Dict[str, Function] = {}
    for t in tools:
        if isinstance(t, Toolkit):
            for fn in t.functions.values():
                registry[fn.name] = fn
        elif isinstance(t, Function):
            registry[t.name] = t
        elif callable(t):
            fn = Function.from_callable(t)
            registry[fn.name] = fn
        elif isinstance(t, dict):
            # Pre-built schema dicts (server-tool stubs)
            name = t.get("name", t.get("type", "unknown"))
            fn = Function(name=name, skip_entrypoint_processing=True, **{
                k: v for k, v in t.items() if k in ("name", "description", "parameters", "strict")
            })
            registry[fn.name] = fn
    return registry


def _tool_schemas(registry: Dict[str, Function]) -> List[Dict[str, Any]]:
    """Return JSON-schema tool definitions for a model call."""
    schemas = []
    for fn in registry.values():
        fn.process_entrypoint()
        schemas.append(fn.to_dict())
    return schemas


def _parse_tool_calls(response: Any) -> List[Dict[str, Any]]:
    """Extract tool-call blocks from a raw model response (duck-typed)."""
    calls: List[Dict[str, Any]] = []

    # Anthropic-style: response.content is a list of blocks
    if hasattr(response, "content") and isinstance(response.content, list):
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                calls.append({
                    "id": getattr(block, "id", None),
                    "name": block.name,
                    "arguments": block.input if isinstance(block.input, dict) else json.loads(block.input),
                })
        return calls

    # OpenAI-style: response.choices[0].message.tool_calls
    if hasattr(response, "choices"):
        msg = response.choices[0].message
        for tc in getattr(msg, "tool_calls", None) or []:
            calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            })
        return calls

    # Buddy RunResponse / dict
    if isinstance(response, dict):
        for block in response.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                calls.append({
                    "id": block.get("id"),
                    "name": block["name"],
                    "arguments": block.get("input", {}),
                })
    return calls


def _get_text(response: Any) -> str:
    """Extract the text content from a model response."""
    if hasattr(response, "content") and isinstance(response.content, list):
        parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        return "\n".join(parts)
    if hasattr(response, "choices"):
        return response.choices[0].message.content or ""
    if isinstance(response, dict):
        parts = [b.get("text", "") for b in response.get("content", []) if b.get("type") == "text"]
        return "\n".join(parts)
    return str(response)


def _stop_reason(response: Any) -> Optional[str]:
    if hasattr(response, "stop_reason"):
        return response.stop_reason
    if hasattr(response, "choices"):
        fr = response.choices[0].finish_reason
        return "tool_use" if fr == "tool_calls" else fr
    return None


# ─────────────────────────────────────────────────────────────────────────────
# RunnerMessage  –  thin wrapper around a model response
# ─────────────────────────────────────────────────────────────────────────────

class RunnerMessage:
    """Wraps a raw model response returned by a single ToolRunner iteration."""

    def __init__(self, raw: Any, tool_calls: List[Dict[str, Any]], tool_results: Optional[List[Dict[str, Any]]] = None):
        self.raw = raw
        self.tool_calls: List[Dict[str, Any]] = tool_calls
        self.tool_results: Optional[List[Dict[str, Any]]] = tool_results
        self.text: str = _get_text(raw)
        self.stop_reason: Optional[str] = _stop_reason(raw)

    def __repr__(self) -> str:
        snippet = self.text[:80].replace("\n", " ")
        return f"RunnerMessage(stop_reason={self.stop_reason!r}, text={snippet!r})"


# ─────────────────────────────────────────────────────────────────────────────
# ToolRunner
# ─────────────────────────────────────────────────────────────────────────────

class ToolRunner:
    """Model-agnostic agentic tool-use loop.

    Parameters
    ----------
    model:
        Any buddy ``Model`` instance (Claude, OpenAI, Gemini, …).
        If *None*, you must supply a ``call_model`` callable instead.
    tools:
        List of ``Function``, ``Toolkit``, plain callables, or raw tool-schema
        dicts.
    messages:
        Initial conversation history (list of ``{"role": …, "content": …}``).
    max_tokens:
        Maximum tokens per model call.
    max_iterations:
        Hard cap on the number of model turns before the loop exits.
    stream:
        If ``True``, each turn is streamed; ``__iter__`` yields
        ``RunnerMessage`` objects whose ``raw`` is a stream object.
    call_model:
        Optional override for the model invocation.  Signature::

            call_model(messages, tools_schema, **kwargs) -> raw_response

    **kwargs:
        Extra keyword arguments forwarded to every model call.
    """

    def __init__(
        self,
        model: Any = None,
        tools: Optional[List[ToolLike]] = None,
        messages: Optional[Messages] = None,
        max_tokens: int = 4096,
        max_iterations: int = 20,
        stream: bool = False,
        call_model: Optional[Callable] = None,
        **kwargs: Any,
    ):
        self._model = model
        self._registry: Dict[str, Function] = _resolve_tools(tools or [])
        self._messages: Messages = deepcopy(messages or [])
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._stream = stream
        self._call_model = call_model
        self._extra_kwargs = kwargs

        # Tracks whether caller modified history inside the loop body
        self._history_modified = False
        # The last tool-result message (for generate_tool_call_response)
        self._pending_tool_result: Optional[Dict[str, Any]] = None

    # ── public API ──────────────────────────────────────────────────────────

    @property
    def messages(self) -> Messages:
        """Current conversation history (mutable)."""
        return self._messages

    def append_messages(self, *msgs: Any) -> None:
        """Append one or more messages and flag that the caller owns history."""
        for m in msgs:
            if isinstance(m, dict):
                self._messages.append(m)
            elif isinstance(m, RunnerMessage):
                self._messages.append(self._runner_msg_to_assistant_dict(m))
        self._history_modified = True

    def set_messages_params(self, updater: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Update extra model-call params without touching message history.

        The *updater* receives the current params dict and must return the
        new one.  Unlike ``append_messages`` this does **not** suppress the
        runner's automatic append.
        """
        self._extra_kwargs = updater(self._extra_kwargs)

    def generate_tool_call_response(self) -> Optional[Dict[str, Any]]:
        """Return the tool-result message for the current turn *without* sending it.

        Returns ``None`` if the last message had no tool calls.  Calling this
        method also flags the runner to skip its automatic append so the caller
        can modify and re-append the result manually.
        """
        if self._pending_tool_result is None:
            return None
        self._history_modified = True
        return deepcopy(self._pending_tool_result)

    def until_done(self) -> RunnerMessage:
        """Run the loop to completion and return the last ``RunnerMessage``."""
        last: Optional[RunnerMessage] = None
        for msg in self:
            last = msg
        if last is None:
            raise RuntimeError("ToolRunner produced no messages.")
        return last

    run_to_completion = until_done  # alias

    # ── iteration ───────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[RunnerMessage]:
        return self._sync_loop()

    def _sync_loop(self) -> Iterator[RunnerMessage]:
        iteration = 0
        while iteration < self._max_iterations:
            iteration += 1
            self._history_modified = False
            self._pending_tool_result = None

            # ── call the model ────────────────────────────────────────────
            raw = self._invoke_model()
            tool_calls = _parse_tool_calls(raw)

            # ── execute tools ─────────────────────────────────────────────
            tool_results: List[Dict[str, Any]] = []
            if tool_calls:
                tool_results = self._execute_tool_calls(tool_calls)
                self._pending_tool_result = {
                    "role": "user",
                    "content": tool_results,
                }

            msg = RunnerMessage(raw, tool_calls, tool_results or None)
            yield msg

            # ── manage history ────────────────────────────────────────────
            if not self._history_modified:
                # Auto-append assistant turn
                self._messages.append(self._runner_msg_to_assistant_dict(msg))
                if tool_results:
                    self._messages.append({"role": "user", "content": tool_results})

            # ── stop condition ────────────────────────────────────────────
            if not tool_calls:
                break  # model is done calling tools

    # ── async iteration ──────────────────────────────────────────────────────

    def __aiter__(self) -> AsyncIterator[RunnerMessage]:
        return self._async_generator()

    async def _async_generator(self) -> AsyncIterator[RunnerMessage]:
        iteration = 0
        while iteration < self._max_iterations:
            iteration += 1
            self._history_modified = False
            self._pending_tool_result = None

            raw = await self._ainvoke_model()
            tool_calls = _parse_tool_calls(raw)

            tool_results: List[Dict[str, Any]] = []
            if tool_calls:
                tool_results = await self._aexecute_tool_calls(tool_calls)
                self._pending_tool_result = {
                    "role": "user",
                    "content": tool_results,
                }

            msg = RunnerMessage(raw, tool_calls, tool_results or None)
            yield msg

            if not self._history_modified:
                self._messages.append(self._runner_msg_to_assistant_dict(msg))
                if tool_results:
                    self._messages.append({"role": "user", "content": tool_results})

            if not tool_calls:
                break

    async def auntil_done(self) -> RunnerMessage:
        """Async version of :meth:`until_done`."""
        last: Optional[RunnerMessage] = None
        async for msg in self:
            last = msg
        if last is None:
            raise RuntimeError("ToolRunner produced no messages.")
        return last

    # ── model invocation ─────────────────────────────────────────────────────

    def _tool_schemas(self) -> List[Dict[str, Any]]:
        return _tool_schemas(self._registry)

    def _invoke_model(self) -> Any:
        if self._call_model is not None:
            return self._call_model(self._messages, self._tool_schemas(), **self._extra_kwargs)
        if self._model is None:
            raise RuntimeError("ToolRunner requires either `model` or `call_model`.")
        return self._call_buddy_model(self._model, self._messages, self._tool_schemas())

    async def _ainvoke_model(self) -> Any:
        if self._call_model is not None:
            result = self._call_model(self._messages, self._tool_schemas(), **self._extra_kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        if self._model is None:
            raise RuntimeError("ToolRunner requires either `model` or `call_model`.")
        return await self._acall_buddy_model(self._model, self._messages, self._tool_schemas())

    def _call_buddy_model(self, model: Any, messages: Messages, tool_schemas: List[Dict[str, Any]]) -> Any:
        """Invoke a buddy Model object synchronously."""
        try:
            return model.invoke(
                messages=messages,
                tools=tool_schemas,
                max_tokens=self._max_tokens,
                **self._extra_kwargs,
            )
        except TypeError:
            # Fallback for models that don't accept tools kwarg directly
            return model.invoke(messages=messages, max_tokens=self._max_tokens, **self._extra_kwargs)

    async def _acall_buddy_model(self, model: Any, messages: Messages, tool_schemas: List[Dict[str, Any]]) -> Any:
        """Invoke a buddy Model object asynchronously."""
        try:
            coro = model.ainvoke(
                messages=messages,
                tools=tool_schemas,
                max_tokens=self._max_tokens,
                **self._extra_kwargs,
            )
            return await coro
        except TypeError:
            coro = model.ainvoke(messages=messages, max_tokens=self._max_tokens, **self._extra_kwargs)
            return await coro

    # ── tool execution ───────────────────────────────────────────────────────

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute all tool calls and return tool-result blocks."""
        results = []
        for tc in tool_calls:
            result_content, is_error = self._run_single_tool(tc)
            block: Dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": tc.get("id", tc["name"]),
                "content": result_content,
            }
            if is_error:
                block["is_error"] = True
            results.append(block)
        return results

    async def _aexecute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Async version of _execute_tool_calls (runs in parallel)."""
        coros = [self._arun_single_tool(tc) for tc in tool_calls]
        outcomes = await asyncio.gather(*coros, return_exceptions=True)
        results = []
        for tc, outcome in zip(tool_calls, outcomes):
            if isinstance(outcome, Exception):
                result_content, is_error = str(outcome), True
            else:
                result_content, is_error = outcome  # type: ignore[misc]
            block: Dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": tc.get("id", tc["name"]),
                "content": result_content,
            }
            if is_error:
                block["is_error"] = True
            results.append(block)
        return results

    def _run_single_tool(self, tc: Dict[str, Any]):
        name = tc["name"]
        arguments = tc.get("arguments", {})
        fn = self._registry.get(name)
        if fn is None:
            return f"Error: unknown tool '{name}'", True
        try:
            fn.process_entrypoint()
            fc = FunctionCall(function=fn, arguments=arguments, call_id=tc.get("id"))
            res: FunctionExecutionResult = fc.execute()
            if res.status == "failure":
                return res.error or "Tool execution failed", True
            return self._serialize_result(res.result), False
        except Exception as exc:
            logger.exception("Tool '%s' raised: %s", name, exc)
            return f"{type(exc).__name__}: {exc}", True

    async def _arun_single_tool(self, tc: Dict[str, Any]):
        name = tc["name"]
        arguments = tc.get("arguments", {})
        fn = self._registry.get(name)
        if fn is None:
            return f"Error: unknown tool '{name}'", True
        try:
            fn.process_entrypoint()
            fc = FunctionCall(function=fn, arguments=arguments, call_id=tc.get("id"))
            res: FunctionExecutionResult = await fc.aexecute()
            if res.status == "failure":
                return res.error or "Tool execution failed", True
            return self._serialize_result(res.result), False
        except Exception as exc:
            logger.exception("Tool '%s' raised: %s", name, exc)
            return f"{type(exc).__name__}: {exc}", True

    @staticmethod
    def _serialize_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, default=str)
        except Exception:
            return str(result)

    @staticmethod
    def _runner_msg_to_assistant_dict(msg: RunnerMessage) -> Dict[str, Any]:
        """Convert a RunnerMessage back to an assistant message dict."""
        raw = msg.raw
        # Anthropic-style
        if hasattr(raw, "content") and isinstance(raw.content, list):
            content = []
            for block in raw.content:
                btype = getattr(block, "type", None)
                if btype == "text":
                    content.append({"type": "text", "text": block.text})
                elif btype == "tool_use":
                    content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                else:
                    content.append({"type": btype or "text", "text": str(block)})
            return {"role": "assistant", "content": content}
        # OpenAI-style
        if hasattr(raw, "choices"):
            m = raw.choices[0].message
            return {"role": "assistant", "content": m.content or "", "tool_calls": getattr(m, "tool_calls", None)}
        # Fallback
        return {"role": "assistant", "content": msg.text}


# ─────────────────────────────────────────────────────────────────────────────
# Convenience factory
# ─────────────────────────────────────────────────────────────────────────────

def tool_runner(
    model: Any = None,
    tools: Optional[List[ToolLike]] = None,
    messages: Optional[Messages] = None,
    *,
    max_tokens: int = 4096,
    max_iterations: int = 20,
    stream: bool = False,
    call_model: Optional[Callable] = None,
    **kwargs: Any,
) -> ToolRunner:
    """Shorthand constructor for :class:`ToolRunner`.

    Example::

        runner = tool_runner(
            model=Claude(),
            tools=[search, calculate],
            messages=[{"role": "user", "content": "What is 42 + 8?"}],
        )
        print(runner.until_done().text)
    """
    return ToolRunner(
        model=model,
        tools=tools,
        messages=messages,
        max_tokens=max_tokens,
        max_iterations=max_iterations,
        stream=stream,
        call_model=call_model,
        **kwargs,
    )
