"""Prompt caching configuration and breakpoint utilities shared across providers.

Anthropic and OpenAI use different mechanisms:

* **Anthropic** — explicit ``cache_control`` blocks on system, tools, and/or
  the last stable history message. Buddy sets these breakpoints automatically
  when ``cache_prompt=True`` on the model. As of Anthropic's automatic-caching
  feature (see
  https://platform.claude.com/docs/en/build-with-claude/prompt-caching#automatic-caching),
  the conversation history breakpoint can also be delegated to the API itself
  via a single top-level ``cache_control`` field on the request — the API
  finds the longest matching cached prefix and moves the breakpoint forward
  as the conversation grows, without Buddy needing to compute a message index
  by hand. This is the default (``cache_history_mode="auto"``) since it is
  Anthropic's recommended starting point for multi-turn conversations and
  composes cleanly with the explicit system/tools breakpoints Buddy already
  sets. Set ``cache_history_mode="explicit"`` to fall back to Buddy's
  hand-computed breakpoint (last assistant/tool message) if you need finer
  control (e.g. a different TTL on history vs. system/tools).

* **OpenAI** — automatic server-side caching for repeated prefixes >= 1024
  tokens. No client-side ``cache_control`` is needed; enabling
  ``cache_prompt=True`` just surfaces per-request cache-hit metrics more
  clearly and (optionally) pins the ``seed`` for prefix stability.

Usage example:

    from buddy.models.openai import OpenAIChat
    from buddy.models.anthropic import Claude

    # OpenAI — automatic; cache_prompt surfaces metrics
    agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), cache_prompt=True)

    # Anthropic — explicit breakpoints on system + tools, automatic on history
    agent = Agent(model=Claude(id="claude-opus-4-5"), cache_prompt=True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptCacheConfig:
    """Controls which prompt segments get cache-breakpoints injected.

    All flags are respected by providers that support explicit caching
    (Anthropic). For providers with automatic server-side caching (OpenAI) the
    flags are informational only — the ``enabled`` flag activates metrics
    tracking.

    Attributes:
        enabled: Master switch. ``False`` disables caching entirely.
        cache_system: Cache the system prompt block.
        cache_tools: Cache the tools list (breakpoint on the last tool entry).
        cache_history: Cache the stable conversation history.
        cache_history_mode: How the history breakpoint is placed —
            ``"auto"`` (default) uses Anthropic's automatic caching (a single
            top-level ``cache_control`` field; the API manages the breakpoint
            as the conversation grows). ``"explicit"`` uses Buddy's
            hand-computed breakpoint on the last assistant/tool message
            (``inject_anthropic_cache_breakpoints``).
        ttl: Cache lifetime. ``"ephemeral"`` = 5 minutes (default).
            ``"1h"`` = 1 hour (Anthropic extended cache; only supported on
            ``claude-3-5-sonnet-20241022`` and newer).
    """

    enabled: bool = True
    cache_system: bool = True
    cache_tools: bool = True
    cache_history: bool = True
    cache_history_mode: str = "auto"  # "auto" | "explicit"
    ttl: str = "ephemeral"  # "ephemeral" | "1h"

    @property
    def cache_control(self) -> Dict[str, Any]:
        """Build the Anthropic-style cache_control dict for this config.

        Ephemeral (5 min): {"type": "ephemeral"}
        Extended (1 hour): {"type": "ephemeral", "ttl": "1h"}
        """
        ctrl: Dict[str, Any] = {"type": "ephemeral"}
        if self.ttl == "1h":
            ctrl["ttl"] = "1h"
        return ctrl

    def is_1h(self) -> bool:
        return self.ttl == "1h"


def inject_anthropic_cache_breakpoints(
    messages: List[Dict[str, Any]],
    config: PromptCacheConfig,
) -> List[Dict[str, Any]]:
    """Add Anthropic ``cache_control`` to the last stable history message.

    Anthropic counts up to 4 cache breakpoints per request. We use one for the
    system block (handled in ``_prepare_request_kwargs``), one for the tools
    list (handled in ``_format_tools_for_model``), and one here for the stable
    conversation prefix — the last *non-user* message before the current user
    turn, i.e. the final assistant or tool-result block in the existing history.

    This function is called **after** ``format_messages`` converts the Buddy
    ``Message`` list to Anthropic's chat format, and **before** the API call.
    It mutates a **copy** of ``messages`` and returns it.
    """
    if not config.cache_history or not messages:
        return messages

    messages = [m.copy() for m in messages]

    cache_control = config.cache_control
    target_idx: Optional[int] = None

    # Work backwards from the second-to-last message: skip the last user turn
    # (which is always the current prompt) and find the last assistant or
    # tool-result block to attach the breakpoint to.
    for i in range(len(messages) - 2, -1, -1):
        role = messages[i].get("role", "")
        if role in ("assistant", "tool"):
            target_idx = i
            break

    if target_idx is None:
        return messages

    msg = messages[target_idx]
    content = msg.get("content")

    if isinstance(content, str):
        msg["content"] = [{"type": "text", "text": content, "cache_control": cache_control}]
    elif isinstance(content, list) and content:
        last_block = content[-1]
        if isinstance(last_block, dict) and "cache_control" not in last_block:
            last_block = dict(last_block)
            last_block["cache_control"] = cache_control
            content = list(content[:-1]) + [last_block]
        msg["content"] = content

    return messages
