"""Context compaction for long-running agent conversations.

Compaction extends the effective context length by automatically summarizing
older messages when the agent's conversation history approaches the model's
context-window limit.

Two strategies are supported:

* **Anthropic server-side compaction** (``compact_20260112``): passes a
  ``context_management`` edit in the Messages API request.  The server
  summarizes older context into a ``compaction`` block and the conversation
  continues.  Only works with supported Claude models.

* **Generic client-side summarization**: uses any LLM callable to summarize
  the earliest messages and replaces them with a summary message.  Works
  with every provider.

Both strategies are exposed through :class:`CompactionConfig` so you can
enable compaction on an agent with a single line::

    from buddy.agent.compaction import auto_compact

    agent = Agent(
        model=Claude(id="claude-opus-5"),
        compaction=auto_compact(),
    )

References
----------
* https://platform.claude.com/docs/en/build-with-claude/compaction
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Supported Claude models for server-side compaction
# ---------------------------------------------------------------------------

_COMPACTION_SUPPORTED_MODELS = {
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
}

_COMPACTION_BETA_HEADER = "compact-2026-01-12"
_COMPACTION_EDIT_TYPE = "compact_20260112"


def supports_server_compaction(model_id: str) -> bool:
    """Return ``True`` when *model_id* supports Anthropic server-side compaction."""
    for prefix in _COMPACTION_SUPPORTED_MODELS:
        if model_id.startswith(prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# Strategy enum
# ---------------------------------------------------------------------------


class CompactionStrategy(str, Enum):
    """Compaction strategy.

    * ``server``: Anthropic server-side compaction via ``compact_20260112``.
      Falls back to ``client`` if the model doesn't support it.
    * ``client``: Client-side summarization using any LLM callable.
    * ``auto``: Use ``server`` when available, fall back to ``client``.
    * ``disabled``: No compaction.
    """

    server = "server"
    client = "client"
    auto = "auto"
    disabled = "disabled"


# ---------------------------------------------------------------------------
# CompactionConfig
# ---------------------------------------------------------------------------


@dataclass
class CompactionConfig:
    """Configuration for context compaction on an agent.

    Attributes:
        strategy: Which compaction strategy to use (default: ``"auto"``).
        trigger_at_pct: Compact when context utilization reaches this
            fraction.  Default: ``0.75`` (75 %).
        min_messages_to_keep: Minimum number of recent messages to always
            keep verbatim after compaction.  Default: ``4``.
        summarization_prompt: System prompt used by the client-side
            summarizer.  ``None`` uses a sensible built-in default.
        summary_max_tokens: Maximum tokens the summarizer may produce.
            Default: ``2048``.
        include_tool_results: Include tool-result messages in the summary.
            Default: ``False``.
    """

    strategy: CompactionStrategy = CompactionStrategy.auto
    trigger_at_pct: float = 0.75
    min_messages_to_keep: int = 4
    summarization_prompt: Optional[str] = None
    summary_max_tokens: int = 2_048
    include_tool_results: bool = False

    # ── Anthropic server-side helpers ────────────────────────────────────────

    def anthropic_context_management_edit(self) -> Dict[str, Any]:
        """Return the ``context_management`` edit dict for the Anthropic API."""
        return {"type": _COMPACTION_EDIT_TYPE}

    def anthropic_betas(self) -> List[str]:
        """Return the beta header list required for server-side compaction."""
        return [_COMPACTION_BETA_HEADER]

    def effective_strategy(self, model_id: str) -> CompactionStrategy:
        """Resolve the effective strategy for *model_id*."""
        if self.strategy == CompactionStrategy.disabled:
            return CompactionStrategy.disabled
        if self.strategy == CompactionStrategy.server:
            return (
                CompactionStrategy.server
                if supports_server_compaction(model_id)
                else CompactionStrategy.client
            )
        if self.strategy == CompactionStrategy.auto:
            return (
                CompactionStrategy.server
                if supports_server_compaction(model_id)
                else CompactionStrategy.client
            )
        return CompactionStrategy.client


# ---------------------------------------------------------------------------
# Compaction result
# ---------------------------------------------------------------------------


@dataclass
class CompactionResult:
    """Result of a compaction operation.

    Attributes:
        compacted: Whether compaction actually occurred.
        strategy_used: The strategy that was applied.
        messages_before: Number of messages before compaction.
        messages_after: Number of messages after compaction.
        summary: The generated summary text (client-side) or extracted
            compaction summary (server-side).
        tokens_saved_estimate: Rough estimate of tokens saved.
    """

    compacted: bool = False
    strategy_used: CompactionStrategy = CompactionStrategy.disabled
    messages_before: int = 0
    messages_after: int = 0
    summary: str = ""
    tokens_saved_estimate: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "compacted": self.compacted,
            "strategy_used": self.strategy_used.value,
            "messages_before": self.messages_before,
            "messages_after": self.messages_after,
            "summary_length": len(self.summary),
            "tokens_saved_estimate": self.tokens_saved_estimate,
        }


# ---------------------------------------------------------------------------
# Client-side helpers
# ---------------------------------------------------------------------------

_DEFAULT_SUMMARIZATION_PROMPT = (
    "You are a context-management assistant. "
    "Your job is to produce a concise, faithful summary of the conversation "
    "history below.  The summary will replace the original history so that the "
    "conversation can continue without exceeding the model's context window. "
    "Preserve: key decisions, important facts, unresolved questions, and the "
    "current state of any in-progress tasks. "
    "Omit: redundant chitchat, verbatim code that can be reconstructed, and "
    "tool results that are no longer relevant. "
    "Write the summary in the third person and in plain prose."
)


def build_summarization_messages(
    messages: List[Dict[str, Any]],
    min_messages_to_keep: int = 4,
    include_tool_results: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split *messages* into ``(to_summarize, to_keep)``."""
    if len(messages) <= min_messages_to_keep:
        return [], messages

    split_point = max(0, len(messages) - min_messages_to_keep)
    to_summarize = messages[:split_point]
    to_keep = messages[split_point:]

    if not include_tool_results:
        to_summarize = [
            m
            for m in to_summarize
            if m.get("role") not in ("tool",)
            and not (
                isinstance(m.get("content"), list)
                and any(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in m.get("content", [])
                )
            )
        ]

    return to_summarize, to_keep


def build_summary_message(summary_text: str) -> Dict[str, Any]:
    """Wrap *summary_text* in a user message that prefixes the compacted history."""
    return {
        "role": "user",
        "content": (
            "[Conversation history has been compacted.]\n\n"
            f"Summary of earlier conversation:\n{summary_text}"
        ),
    }


def extract_compaction_summary(response_content: List[Dict[str, Any]]) -> Optional[str]:
    """Extract the summary from an Anthropic compaction block in *response_content*."""
    for block in response_content:
        if isinstance(block, dict) and block.get("type") == "compaction":
            return block.get("summary", "")
        if hasattr(block, "type") and getattr(block, "type", None) == "compaction":
            return getattr(block, "summary", "")
    return None


async def compact_messages_async(
    messages: List[Dict[str, Any]],
    config: CompactionConfig,
    summarizer: Callable[[List[Dict[str, Any]], str, int], Coroutine[Any, Any, str]],
    model_id: str = "",
    current_token_usage: int = 0,
    context_window: int = 128_000,
) -> Tuple[List[Dict[str, Any]], CompactionResult]:
    """Compact *messages* using client-side async summarization."""
    result = CompactionResult(
        strategy_used=CompactionStrategy.client,
        messages_before=len(messages),
    )

    to_summarize, to_keep = build_summarization_messages(
        messages,
        min_messages_to_keep=config.min_messages_to_keep,
        include_tool_results=config.include_tool_results,
    )

    if not to_summarize:
        result.messages_after = len(messages)
        return messages, result

    system_prompt = config.summarization_prompt or _DEFAULT_SUMMARIZATION_PROMPT
    summary = await summarizer(to_summarize, system_prompt, config.summary_max_tokens)

    summary_msg = build_summary_message(summary)
    new_messages = [summary_msg] + list(to_keep)

    removed_chars = sum(len(str(m.get("content", ""))) for m in to_summarize)
    tokens_saved = max(0, (removed_chars - len(summary)) // 4)

    result.compacted = True
    result.summary = summary
    result.messages_after = len(new_messages)
    result.tokens_saved_estimate = tokens_saved

    return new_messages, result


def compact_messages_sync(
    messages: List[Dict[str, Any]],
    config: CompactionConfig,
    summarizer: Callable[[List[Dict[str, Any]], str, int], str],
    model_id: str = "",
    current_token_usage: int = 0,
    context_window: int = 128_000,
) -> Tuple[List[Dict[str, Any]], CompactionResult]:
    """Compact *messages* using client-side synchronous summarization."""
    result = CompactionResult(
        strategy_used=CompactionStrategy.client,
        messages_before=len(messages),
    )

    to_summarize, to_keep = build_summarization_messages(
        messages,
        min_messages_to_keep=config.min_messages_to_keep,
        include_tool_results=config.include_tool_results,
    )

    if not to_summarize:
        result.messages_after = len(messages)
        return messages, result

    system_prompt = config.summarization_prompt or _DEFAULT_SUMMARIZATION_PROMPT
    summary = summarizer(to_summarize, system_prompt, config.summary_max_tokens)

    summary_msg = build_summary_message(summary)
    new_messages = [summary_msg] + list(to_keep)

    removed_chars = sum(len(str(m.get("content", ""))) for m in to_summarize)
    tokens_saved = max(0, (removed_chars - len(summary)) // 4)

    result.compacted = True
    result.summary = summary
    result.messages_after = len(new_messages)
    result.tokens_saved_estimate = tokens_saved

    return new_messages, result


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def auto_compact(
    trigger_at_pct: float = 0.75,
    min_messages_to_keep: int = 4,
    summary_max_tokens: int = 2_048,
) -> CompactionConfig:
    """Create a :class:`CompactionConfig` using the ``auto`` strategy."""
    return CompactionConfig(
        strategy=CompactionStrategy.auto,
        trigger_at_pct=trigger_at_pct,
        min_messages_to_keep=min_messages_to_keep,
        summary_max_tokens=summary_max_tokens,
    )


def server_compact(trigger_at_pct: float = 0.75) -> CompactionConfig:
    """Create a :class:`CompactionConfig` using Anthropic server-side compaction."""
    return CompactionConfig(
        strategy=CompactionStrategy.server,
        trigger_at_pct=trigger_at_pct,
    )


def client_compact(
    trigger_at_pct: float = 0.75,
    min_messages_to_keep: int = 4,
    summarization_prompt: Optional[str] = None,
    summary_max_tokens: int = 2_048,
) -> CompactionConfig:
    """Create a :class:`CompactionConfig` using client-side summarization."""
    return CompactionConfig(
        strategy=CompactionStrategy.client,
        trigger_at_pct=trigger_at_pct,
        min_messages_to_keep=min_messages_to_keep,
        summarization_prompt=summarization_prompt,
        summary_max_tokens=summary_max_tokens,
    )
