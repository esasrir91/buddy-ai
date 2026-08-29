"""Context window management for any LLM provider.

This module tracks context window sizes, detects approaching limits, and
provides context-awareness injection compatible with Anthropic's context-
awareness tags as well as a generic token-budget hint for other providers.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/context-windows
* https://platform.claude.com/docs/en/build-with-claude/context-windows#context-awareness
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Context-window sizes per model (input tokens)
# ---------------------------------------------------------------------------

#: Mapping of model-id prefix → context window size in tokens.
#: Use ``context_window_for_model()`` to look up a value.
_CONTEXT_WINDOWS: Dict[str, int] = {
    # ── Anthropic ────────────────────────────────────────────────────────────
    "claude-mythos-5": 1_000_000,
    "claude-mythos-preview": 1_000_000,
    "claude-fable-5": 1_000_000,
    "claude-opus-5": 1_000_000,
    "claude-opus-4-8": 1_000_000,
    "claude-opus-4-7": 1_000_000,
    "claude-opus-4-6": 1_000_000,
    "claude-sonnet-5": 1_000_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-opus-4-5": 200_000,
    "claude-opus-4-1": 200_000,
    "claude-sonnet-4-5": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-opus-4": 200_000,
    "claude-haiku-4-5": 200_000,
    "claude-haiku-4": 200_000,
    "claude-haiku-3-5": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    # ── OpenAI ───────────────────────────────────────────────────────────────
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "o1": 200_000,
    "o1-mini": 128_000,
    "o1-preview": 128_000,
    "o3": 200_000,
    "o3-mini": 200_000,
    "o4": 200_000,
    "o4-mini": 200_000,
    # ── Google ───────────────────────────────────────────────────────────────
    "gemini-2.0-flash": 1_048_576,
    "gemini-2.0-pro": 2_097_152,
    "gemini-1.5-flash": 1_048_576,
    "gemini-1.5-pro": 2_097_152,
    "gemini-1.0-pro": 32_760,
    # ── Meta Llama ───────────────────────────────────────────────────────────
    "llama-3.3": 128_000,
    "llama-3.2": 128_000,
    "llama-3.1": 128_000,
    "llama-3": 8_192,
    # ── Mistral ──────────────────────────────────────────────────────────────
    "mistral-large": 128_000,
    "mistral-medium": 32_000,
    "mistral-small": 32_000,
    "mistral-7b": 32_768,
    "mixtral-8x7b": 32_768,
    # ── Cohere ───────────────────────────────────────────────────────────────
    "command-r-plus": 128_000,
    "command-r": 128_000,
    "command": 4_096,
    # ── DeepSeek ─────────────────────────────────────────────────────────────
    "deepseek-chat": 128_000,
    "deepseek-coder": 16_000,
    # ── xAI ──────────────────────────────────────────────────────────────────
    "grok-2": 131_072,
    "grok-1": 8_192,
    # ── Groq ─────────────────────────────────────────────────────────────────
    "llama3-70b-8192": 8_192,
    "llama3-8b-8192": 8_192,
    "mixtral-8x7b-32768": 32_768,
    # Fallback for unknown models
    "__default__": 128_000,
}

#: Maximum output tokens per model.  ``None`` means use model default.
_MAX_OUTPUT_TOKENS: Dict[str, int] = {
    "claude-opus-5": 128_000,
    "claude-sonnet-5": 128_000,
    "claude-mythos-5": 128_000,
    "claude-fable-5": 128_000,
    "claude-mythos-preview": 128_000,
    "claude-opus-4-8": 128_000,
    "claude-opus-4-7": 128_000,
    "claude-opus-4-6": 128_000,
    "claude-sonnet-4-6": 128_000,
    "claude-opus-4-5": 16_000,
    "claude-sonnet-4-5": 16_000,
    "claude-haiku-4-5": 16_000,
    "gpt-4o": 16_384,
    "gpt-4o-mini": 16_384,
    "gpt-4-turbo": 4_096,
    "o1": 100_000,
    "o3": 100_000,
    "o4": 100_000,
    "gemini-2.0-flash": 8_192,
    "gemini-1.5-pro": 8_192,
    "__default__": 4_096,
}

#: Models with context-awareness (injected budget tags).
_CONTEXT_AWARE_MODELS = {
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
}


def context_window_for_model(model_id: str) -> int:
    """Return the context window size (input tokens) for *model_id*.

    Performs a longest-prefix match against the known table so that versioned
    model IDs such as ``"claude-opus-5-20261001"`` correctly resolve to
    ``"claude-opus-5"``.

    Falls back to ``128_000`` for unknown models.
    """
    best_prefix = ""
    best_size = _CONTEXT_WINDOWS["__default__"]
    for prefix, size in _CONTEXT_WINDOWS.items():
        if prefix == "__default__":
            continue
        if model_id.startswith(prefix) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_size = size
    return best_size


def max_output_tokens_for_model(model_id: str) -> int:
    """Return the maximum output tokens for *model_id*."""
    best_prefix = ""
    best_tokens = _MAX_OUTPUT_TOKENS["__default__"]
    for prefix, tokens in _MAX_OUTPUT_TOKENS.items():
        if prefix == "__default__":
            continue
        if model_id.startswith(prefix) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_tokens = tokens
    return best_tokens


def is_context_aware(model_id: str) -> bool:
    """Return True when *model_id* receives injected context-awareness tags."""
    for prefix in _CONTEXT_AWARE_MODELS:
        if model_id.startswith(prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# Context usage dataclass
# ---------------------------------------------------------------------------


@dataclass
class ContextUsage:
    """Snapshot of how a request uses the model's context window.

    Attributes:
        model_id: The model being called.
        input_tokens: Tokens consumed by the current input (messages +
            system prompt + tools).  Estimated if not yet sent.
        output_tokens: Tokens generated in the last response (0 before
            the call).
        context_window: Total context window size for the model.
        cache_read_tokens: Input tokens served from cache (Anthropic).
        cache_write_tokens: Input tokens written to cache (Anthropic).
        compaction_tokens: Tokens in a compaction summary block (if any).
    """

    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    context_window: int = field(init=False)
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    compaction_tokens: int = 0

    def __post_init__(self) -> None:
        self.context_window = context_window_for_model(self.model_id)

    # ── Derived helpers ──────────────────────────────────────────────────────

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.context_window - self.total_tokens)

    @property
    def utilization(self) -> float:
        """Fraction of the context window consumed (0.0–1.0)."""
        if self.context_window == 0:
            return 1.0
        return min(1.0, self.total_tokens / self.context_window)

    @property
    def approaching_limit(self) -> bool:
        """True when utilization exceeds 80 %."""
        return self.utilization >= 0.80

    @property
    def near_limit(self) -> bool:
        """True when utilization exceeds 90 %."""
        return self.utilization >= 0.90

    def system_warning(self) -> str:
        """Anthropic-style token-budget warning string."""
        return (
            f"Token usage: {self.input_tokens}/{self.context_window}; "
            f"{self.remaining_tokens} remaining"
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "context_window": self.context_window,
            "remaining_tokens": self.remaining_tokens,
            "utilization_pct": round(self.utilization * 100, 1),
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "compaction_tokens": self.compaction_tokens,
            "approaching_limit": self.approaching_limit,
            "near_limit": self.near_limit,
        }


# ---------------------------------------------------------------------------
# Context-awareness injection
# ---------------------------------------------------------------------------


def build_context_awareness_system_prefix(
    model_id: str,
    context_window: Optional[int] = None,
) -> str:
    """Build Anthropic-style context-awareness XML tags for the system prompt.

    These are the ``<budget:token_budget>`` tags injected by the Anthropic API
    for context-aware models.  Buddy injects equivalent tags itself so the
    feature works the same way for all providers.

    Returns an empty string for models that don't benefit from context
    awareness.
    """
    cw = context_window or context_window_for_model(model_id)
    return f"<budget:token_budget>{cw}</budget:token_budget>\n"


def build_context_warning_block(usage: ContextUsage) -> str:
    """Build the per-turn warning injected after tool calls for context-aware
    models (mirrors the Anthropic API's ``<system_warning>`` injection)."""
    return f"<system_warning>{usage.system_warning()}</system_warning>"


# ---------------------------------------------------------------------------
# Overflow detection
# ---------------------------------------------------------------------------


class ContextWindowOverflow(Exception):
    """Raised when the estimated input already exceeds the context window."""

    def __init__(self, model_id: str, input_tokens: int, context_window: int) -> None:
        self.model_id = model_id
        self.input_tokens = input_tokens
        self.context_window = context_window
        super().__init__(
            f"Input ({input_tokens:,} tokens) already exceeds the context window "
            f"({context_window:,} tokens) for model '{model_id}'. "
            "Truncate the conversation history or enable compaction."
        )


def check_overflow(usage: ContextUsage, raise_on_overflow: bool = False) -> bool:
    """Check whether the request would overflow the context window.

    Args:
        usage: A :class:`ContextUsage` snapshot with ``input_tokens`` filled.
        raise_on_overflow: When ``True``, raise :class:`ContextWindowOverflow`
            instead of returning ``True``.

    Returns:
        ``True`` if the input alone exceeds the context window.
    """
    overflows = usage.input_tokens > usage.context_window
    if overflows and raise_on_overflow:
        raise ContextWindowOverflow(
            usage.model_id, usage.input_tokens, usage.context_window
        )
    return overflows


# ---------------------------------------------------------------------------
# Context-window config for agents / models
# ---------------------------------------------------------------------------


@dataclass
class ContextWindowConfig:
    """Configuration for context-window management on a model/agent.

    Attributes:
        warn_at_pct: Log a warning when utilization exceeds this fraction.
            Default: 0.80 (80 %).
        error_at_pct: Raise :class:`ContextWindowOverflow` when the *input*
            alone would exceed this fraction.  ``None`` disables this.
        inject_awareness: Inject context-awareness budget tags into the system
            prompt.  Defaults to ``True`` for context-aware models.
        inject_per_turn_warning: Inject ``<system_warning>`` after every tool
            call when approaching the limit.  Default: ``True``.
        auto_truncate: Drop oldest non-system messages when approaching the
            limit.  Default: ``False``.
        auto_truncate_at_pct: Fraction at which auto-truncation kicks in.
            Default: 0.90.
    """

    warn_at_pct: float = 0.80
    error_at_pct: Optional[float] = None
    inject_awareness: Optional[bool] = None  # None → auto-detect per model
    inject_per_turn_warning: bool = True
    auto_truncate: bool = False
    auto_truncate_at_pct: float = 0.90

    def should_inject_awareness(self, model_id: str) -> bool:
        if self.inject_awareness is not None:
            return self.inject_awareness
        return is_context_aware(model_id)


# ---------------------------------------------------------------------------
# Helpers used by model implementations
# ---------------------------------------------------------------------------


def update_usage_from_response(
    usage: ContextUsage,
    response: Any,
) -> ContextUsage:
    """Populate *usage* from a provider response object or dict.

    Handles both Anthropic response objects (with ``.usage`` attribute) and
    OpenAI-style response objects.  Also handles plain dicts.
    """
    raw = getattr(response, "usage", None) or {}
    if hasattr(raw, "__dict__"):
        raw = raw.__dict__

    def _get(key: str, *aliases: str) -> int:
        for k in (key, *aliases):
            v = raw.get(k) if isinstance(raw, dict) else getattr(raw, k, None)
            if v is not None:
                return int(v)
        return 0

    usage.input_tokens = _get("input_tokens", "prompt_tokens")
    usage.output_tokens = _get("output_tokens", "completion_tokens")
    usage.cache_read_tokens = _get("cache_read_input_tokens", "cached_tokens")
    usage.cache_write_tokens = _get("cache_creation_input_tokens", "cache_write_tokens")
    return usage


def estimate_messages_tokens(
    messages: List[Dict[str, Any]],
    chars_per_token: float = 4.0,
) -> int:
    """Rough character-based token estimate for a list of provider messages.

    Used as a fast pre-flight check when a proper token-counting endpoint
    is not available.  The default ``chars_per_token=4`` approximates common
    Latin-script tokenizers; adjust for other scripts.

    Args:
        messages: List of ``{"role": ..., "content": ...}`` dicts.
        chars_per_token: Characters per token ratio.

    Returns:
        Estimated total tokens.
    """
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(str(block.get("text", "") or block.get("content", "")))
    # Add ~4 tokens overhead per message for role/separator
    total_chars += len(messages) * 16
    return max(1, math.ceil(total_chars / chars_per_token))
