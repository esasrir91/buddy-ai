"""ToolContextManager – manage tool context to prevent context-window bloat.

Implements the four strategies from the Anthropic "Manage tool context" doc:

1. **Tool search** – keep deferred tools out of the initial prompt; discover
   them on demand via :class:`~buddy.tools.server.ToolSearchTool`.
2. **Programmatic tool calling** – collapse sequences of tool calls into a
   single code block executed by :class:`~buddy.tools.server.CodeExecutionTool`.
3. **Prompt caching** – attach ``cache_control`` breakpoints to stable tool
   definitions so the provider can cache them across requests.
4. **Context editing** – trim stale ``tool_result`` blocks from the message
   history once they are no longer needed.

All strategies are provider-agnostic; provider-specific optimisations (e.g.
Anthropic cache_control) are applied where the model supports them.

Usage::

    from buddy.tools.context_manager import ToolContextManager

    cm = ToolContextManager(
        tools=[lots_of_tools],
        cache_stable_tools=True,
        max_history_tool_results=20,
    )
    # Get the tools to pass to the agent (deferred ones excluded)
    active, deferred = cm.split_tools()
    # Trim stale results from a long conversation
    pruned_messages = cm.trim_tool_results(messages, keep_last=10)
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from buddy.tools.function import Function
from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

ToolLike = Union[Function, Toolkit, callable]
Messages = List[Dict[str, Any]]


def _to_functions(tool: ToolLike) -> List[Function]:
    if isinstance(tool, Toolkit):
        return list(tool.functions.values())
    if isinstance(tool, Function):
        return [tool]
    if callable(tool):
        return [Function.from_callable(tool)]
    return []


# Names that should stay in the active tools array when enforcing limits
# (search itself, plus common agentic control-plane tools).
_PROTECTED_TOOL_NAMES = frozenset(
    {
        "search_tools",
        "get_chat_history",
        "get_tool_call_history",
        "get_previous_sessions_messages",
        "update_memory",
        "update_user_memory",
        "search_knowledge_base",
        "search_knowledge_base_with_agentic_filters",
        "add_to_knowledge",
        "get_member_information",
        "forward_task",
        "transfer_task",
        "run_member_agents",
    }
)


def should_manage_tool_context(
    manage_tool_context: Optional[bool],
    *,
    max_tools: Optional[int],
    active_count: int,
    deferred_count: int,
) -> bool:
    """Decide whether to use deferred loading + ToolSearchTool.

    * ``True`` — always manage when there is anything to defer or overflow.
    * ``False`` — never (legacy truncate / silent drop).
    * ``None`` — auto: manage when deferred tools exist or active tools exceed
      the provider limit.
    """
    if manage_tool_context is False:
        return False
    if manage_tool_context is True:
        return deferred_count > 0 or (max_tools is not None and active_count > max_tools)
    # auto
    if deferred_count > 0:
        return True
    if max_tools is not None and active_count > max_tools:
        return True
    return False


def move_overflow_to_deferred(
    tools_for_model: List[Dict[str, Any]],
    functions_for_model: Dict[str, Function],
    deferred_functions: Dict[str, Function],
    budget: int,
) -> int:
    """Move excess function tools into ``deferred_functions`` to free slots.

    Prefers deferring non-protected tools from the end of the list. Builtin
    dict tools (provider-native) are never deferred. Returns how many were moved.
    """
    if budget < 1 or len(tools_for_model) <= budget:
        return 0

    # Indices we are allowed to defer (function tools, not protected)
    deferrable_idxs: List[int] = []
    for i, tool in enumerate(tools_for_model):
        if not isinstance(tool, dict) or tool.get("type") != "function":
            continue
        name = (tool.get("function") or {}).get("name") or ""
        if name in _PROTECTED_TOOL_NAMES or name.startswith("transfer_task_to_"):
            continue
        if name in functions_for_model:
            deferrable_idxs.append(i)

    need = len(tools_for_model) - budget
    if need <= 0:
        return 0

    # Defer from the end so earlier (often more general) tools stay active
    to_defer = deferrable_idxs[-need:] if len(deferrable_idxs) >= need else deferrable_idxs
    if not to_defer:
        return 0

    moved = 0
    for i in sorted(to_defer, reverse=True):
        tool = tools_for_model.pop(i)
        name = (tool.get("function") or {}).get("name")
        if not name:
            continue
        func = functions_for_model.pop(name, None)
        if func is None:
            continue
        func.defer_loading = True
        deferred_functions[name] = func
        moved += 1

    if moved:
        log = logger.warning if moved >= 5 else logger.debug
        log(
            "Deferred %d tools to stay under provider limit (active=%d, deferred=%d, budget=%d). "
            "Use search_tools to discover and load them.",
            moved,
            len(tools_for_model),
            len(deferred_functions),
            budget,
        )
    return moved


def activate_deferred_tools(
    names: List[str],
    *,
    tools_for_model: List[Dict[str, Any]],
    functions_for_model: Dict[str, Function],
    deferred_functions: Dict[str, Function],
    max_tools: Optional[int] = None,
    deferred_index: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Move named deferred tools into the active model tool lists.

    If ``max_tools`` is reached, non-protected active tools are swapped back
    into the deferred pool to free slots for the requested tools.
    Returns names that were successfully loaded.
    """
    loaded: List[str] = []
    for name in names:
        if name not in deferred_functions:
            continue
        if name in functions_for_model:
            deferred_functions.pop(name, None)
            if deferred_index is not None:
                deferred_index.pop(name, None)
            loaded.append(name)
            continue

        if max_tools is not None and len(tools_for_model) >= max_tools:
            # Free one slot by re-deferring a non-protected active tool
            freed = move_overflow_to_deferred(
                tools_for_model,
                functions_for_model,
                deferred_functions,
                budget=max_tools - 1,
            )
            if deferred_index is not None:
                for n, f in deferred_functions.items():
                    if n not in deferred_index:
                        deferred_index[n] = f.description or ""
            if not freed and len(tools_for_model) >= max_tools:
                logger.warning(
                    "Cannot activate deferred tool %s: already at max_tools=%d "
                    "and no swappable active tools",
                    name,
                    max_tools,
                )
                break

        func = deferred_functions.pop(name)
        func.defer_loading = False
        functions_for_model[name] = func
        tools_for_model.append({"type": "function", "function": func.to_dict()})
        if deferred_index is not None:
            deferred_index.pop(name, None)
        loaded.append(name)
        logger.debug("Activated deferred tool %s", name)
    return loaded


def inject_tool_search(
    *,
    tools_for_model: List[Dict[str, Any]],
    functions_for_model: Dict[str, Function],
    deferred_functions: Dict[str, Function],
    max_tools: Optional[int],
    activate_callback: Callable[[List[str]], List[str]],
    owner: Any = None,
    tool_hooks: Optional[List[Callable]] = None,
    strict: bool = False,
) -> Any:
    """Inject a :class:`ToolSearchTool` when deferred tools exist.

    Returns the toolkit instance, or ``None`` if nothing was injected.
    """
    if not deferred_functions:
        return None

    # Already have search_tools?
    if "search_tools" in functions_for_model:
        # Refresh index on existing search tool if possible
        existing = functions_for_model["search_tools"]
        toolkit = getattr(existing, "_toolkit", None)
        if toolkit is not None and hasattr(toolkit, "register_deferred"):
            for name, fn in deferred_functions.items():
                toolkit.register_deferred(name, fn.description or "", fn)
        return toolkit

    from buddy.tools.server import ToolSearchTool

    # Need a free slot for search_tools
    if max_tools is not None and len(tools_for_model) >= max_tools:
        move_overflow_to_deferred(
            tools_for_model, functions_for_model, deferred_functions, max_tools - 1
        )

    search = ToolSearchTool(
        deferred_tools={n: (f.description or "") for n, f in deferred_functions.items()},
        deferred_functions=deferred_functions,
        activate_callback=activate_callback,
    )

    for name, func in search.functions.items():
        if name in functions_for_model:
            continue
        if owner is not None:
            func._agent = owner
            if hasattr(owner, "members"):  # Team-ish
                func._team = owner
        func.process_entrypoint(strict=strict)
        if strict and func.strict is None:
            func.strict = True
        if tool_hooks is not None:
            func.tool_hooks = tool_hooks
        functions_for_model[name] = func
        tools_for_model.append({"type": "function", "function": func.to_dict()})
        logger.debug("Injected ToolSearchTool function %s", name)

    return search


class ToolContextManager:
    """Manage tool context to keep the model's context window lean.

    Parameters
    ----------
    tools:
        All tools the agent has access to (mix of Function, Toolkit,
        callables).
    cache_stable_tools:
        If ``True``, attach ``cache_control: {"type": "ephemeral"}`` to the
        last non-deferred tool definition so providers that support prompt
        caching (e.g. Anthropic) can cache the entire tools prefix.
    max_history_tool_results:
        Maximum number of ``tool_result`` blocks to keep in the message
        history.  Older ones are removed by :meth:`trim_tool_results`.
        ``None`` means no limit.
    deferred_threshold:
        Minimum number of tools before automatically enabling deferred loading
        for tools that have ``defer_loading=True``.
    """

    def __init__(
        self,
        tools: Optional[List[ToolLike]] = None,
        cache_stable_tools: bool = True,
        max_history_tool_results: Optional[int] = 50,
        deferred_threshold: int = 10,
    ):
        self._all_functions: List[Function] = []
        for t in tools or []:
            self._all_functions.extend(_to_functions(t))

        self._cache_stable = cache_stable_tools
        self._max_results = max_history_tool_results
        self._threshold = deferred_threshold

    # ── tool splitting ────────────────────────────────────────────────────────

    def split_tools(self) -> Tuple[List[Function], List[Function]]:
        """Split tools into *active* (loaded immediately) and *deferred*.

        Returns
        -------
        active:
            Tools that go into the initial system prompt / tools array.
        deferred:
            Tools marked with ``defer_loading=True``; should be registered
            with a :class:`~buddy.tools.server.ToolSearchTool`.
        """
        total = len(self._all_functions)
        active, deferred = [], []
        for fn in self._all_functions:
            if fn.defer_loading and total >= self._threshold:
                deferred.append(fn)
            else:
                active.append(fn)

        if self._cache_stable and active:
            # Attach ephemeral cache_control to the last stable tool
            last = active[-1]
            if last.cache_control is None:
                last.cache_control = {"type": "ephemeral"}

        return active, deferred

    def get_active_schemas(self) -> List[Dict[str, Any]]:
        """Return JSON-schema dicts for non-deferred tools (ready to pass to model)."""
        active, _ = self.split_tools()
        schemas = []
        for fn in active:
            fn.process_entrypoint()
            schemas.append(fn.to_dict())
        return schemas

    def enforce_max_tools(self, max_tools: int = 128, reserve_for_search: int = 1) -> Tuple[List[Function], List[Function]]:
        """Force-defer tools that would exceed a provider limit (e.g. OpenAI's 128).

        Keeps the first ``max_tools - reserve_for_search`` non-deferred tools
        active and marks the overflow with ``defer_loading=True`` so they can
        be discovered via :class:`~buddy.tools.server.ToolSearchTool`.

        Parameters
        ----------
        max_tools:
            Hard provider limit (OpenAI = 128).
        reserve_for_search:
            Slots to leave free for a ToolSearchTool (default 1).

        Returns
        -------
        active, deferred
        """
        active, deferred = self.split_tools()
        budget = max(1, max_tools - reserve_for_search)
        if len(active) <= budget:
            return active, deferred

        overflow = active[budget:]
        active = active[:budget]
        for fn in overflow:
            fn.defer_loading = True
            deferred.append(fn)
        logger.warning(
            "enforce_max_tools: deferred %d tools to stay under provider limit of %d "
            "(active=%d, deferred=%d). Register deferred tools with ToolSearchTool.",
            len(overflow),
            max_tools,
            len(active),
            len(deferred),
        )
        return active, deferred

    def get_deferred_index(self) -> Dict[str, str]:
        """Return a name→description mapping of deferred tools for ToolSearchTool."""
        _, deferred = self.split_tools()
        return {fn.name: fn.description or "" for fn in deferred}

    # ── context editing ───────────────────────────────────────────────────────

    def trim_tool_results(
        self,
        messages: Messages,
        keep_last: int = 20,
        preserve_ids: Optional[List[str]] = None,
    ) -> Messages:
        """Remove old ``tool_result`` blocks from the message history.

        Keeps the most recent ``keep_last`` tool-result blocks and removes
        the rest, shrinking the context window for long-running conversations.
        Tool-use blocks in assistant messages are kept intact (only their
        result counterparts in user messages are pruned).

        Parameters
        ----------
        messages:
            The full conversation history.
        keep_last:
            Number of most-recent tool results to preserve.
        preserve_ids:
            Optional list of ``tool_use_id`` values that must never be removed.

        Returns
        -------
        Messages
            A new message list with stale tool results removed.
        """
        preserve_ids = set(preserve_ids or [])

        # Collect all tool_result positions
        result_locations: List[Tuple[int, int]] = []  # (msg_idx, content_idx)
        for mi, msg in enumerate(messages):
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for ci, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tid = block.get("tool_use_id", "")
                    if tid not in preserve_ids:
                        result_locations.append((mi, ci))

        # Determine which ones to drop (all but the last keep_last)
        to_drop: set = set()
        if len(result_locations) > keep_last:
            excess = result_locations[: len(result_locations) - keep_last]
            to_drop = {(mi, ci) for mi, ci in excess}

        if not to_drop:
            return messages

        pruned = deepcopy(messages)
        for mi, ci in sorted(to_drop, reverse=True):
            content = pruned[mi].get("content", [])
            if isinstance(content, list) and ci < len(content):
                # Replace with a stub instead of removing (keeps message structure valid)
                content[ci] = {
                    "type": "tool_result",
                    "tool_use_id": messages[mi]["content"][ci].get("tool_use_id", ""),
                    "content": "[result trimmed to save context]",
                }
        return pruned

    def compact_assistant_messages(self, messages: Messages, keep_text: bool = True) -> Messages:
        """Summarise old assistant turns to reduce context size.

        Replaces long assistant messages that contain only text with a
        truncated version, keeping the most recent ``keep_text`` turns
        intact.

        Parameters
        ----------
        messages:
            Full conversation history.
        keep_text:
            If ``True``, keep the first 200 chars of each compacted turn.

        Returns
        -------
        Messages
            Compacted message list.
        """
        compacted = deepcopy(messages)
        assistant_idxs = [i for i, m in enumerate(compacted) if m.get("role") == "assistant"]
        # Leave the last two assistant turns untouched
        to_compact = assistant_idxs[:-2] if len(assistant_idxs) > 2 else []

        for idx in to_compact:
            msg = compacted[idx]
            content = msg.get("content")
            if isinstance(content, str) and len(content) > 400:
                compacted[idx]["content"] = content[:200] + " … [compacted]"
            elif isinstance(content, list):
                new_content = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if len(text) > 400 and keep_text:
                            block = dict(block)
                            block["text"] = text[:200] + " … [compacted]"
                    new_content.append(block)
                compacted[idx]["content"] = new_content
        return compacted

    # ── cache control helpers ─────────────────────────────────────────────────

    @staticmethod
    def add_cache_breakpoints(
        tool_schemas: List[Dict[str, Any]],
        ttl: str = "ephemeral",
    ) -> List[Dict[str, Any]]:
        """Attach a cache_control breakpoint to the last tool schema.

        This tells Anthropic's API to cache the entire tools prefix up to
        this point.  Has no effect on other providers (the field is ignored).

        Parameters
        ----------
        tool_schemas:
            List of tool definition dicts (as passed to the model API).
        ttl:
            Cache TTL type: ``"ephemeral"`` (5 min) or ``"1h"``.

        Returns
        -------
        List[Dict[str, Any]]
            Modified tool schemas list.
        """
        if not tool_schemas:
            return tool_schemas
        schemas = deepcopy(tool_schemas)
        schemas[-1]["cache_control"] = {"type": ttl}
        return schemas

    @staticmethod
    def add_result_cache_control(
        tool_results: List[Dict[str, Any]],
        ttl: str = "ephemeral",
    ) -> List[Dict[str, Any]]:
        """Attach cache_control to tool result content blocks.

        Useful for caching large tool results (e.g. document search outputs)
        across subsequent API calls.

        Parameters
        ----------
        tool_results:
            List of ``tool_result`` dicts in the user message.
        ttl:
            Cache TTL: ``"ephemeral"`` (5 min) or ``"1h"``.

        Returns
        -------
        List[Dict[str, Any]]
            Modified tool results.
        """
        results = deepcopy(tool_results)
        for block in results:
            if block.get("type") == "tool_result":
                content = block.get("content")
                if isinstance(content, str):
                    block["content"] = [{"type": "text", "text": content, "cache_control": {"type": ttl}}]
                elif isinstance(content, list):
                    for cb in content:
                        if isinstance(cb, dict) and "cache_control" not in cb:
                            cb["cache_control"] = {"type": ttl}
        return results

    # ── usage reporting ───────────────────────────────────────────────────────

    def context_report(self, messages: Messages) -> Dict[str, Any]:
        """Return a summary of context usage in the given message history.

        Counts messages, tool calls, and tool results to help decide when to
        apply context-management strategies.
        """
        tool_calls = 0
        tool_results = 0
        text_chars = 0

        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, str):
                text_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "tool_use":
                        tool_calls += 1
                    elif btype == "tool_result":
                        tool_results += 1
                        c = block.get("content", "")
                        text_chars += len(str(c))
                    elif btype == "text":
                        text_chars += len(block.get("text", ""))

        return {
            "message_count": len(messages),
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "approx_text_chars": text_chars,
            "active_tools": len([f for f in self._all_functions if not f.defer_loading]),
            "deferred_tools": len([f for f in self._all_functions if f.defer_loading]),
        }
