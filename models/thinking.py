"""Unified thinking configuration for all LLM providers.

This module provides a provider-agnostic interface for reasoning / thinking
features so the same ``ThinkingConfig`` works across Claude, OpenAI o-models,
Google Gemini, and any future model that exposes an internal reasoning step.

Claude specifics
----------------
* **Adaptive** (current): ``thinking: {type: "adaptive", display: "..."}``
  Claude decides whether and how deeply to think.  Controlled via ``effort``.
* **Extended** (legacy, budget_tokens): ``thinking: {type: "enabled", budget_tokens: N}``
  Explicit token budget.  Deprecated on Claude 4.6 models; rejected on 4.7+.

OpenAI reasoning models (o1, o3, o4)
--------------------------------------
Thinking is always on.  Control depth via ``reasoning_effort`` ("low" /
"medium" / "high") or via :class:`EffortConfig`.

Other models
------------
When ``inject_prompt=True``, a chain-of-thought instruction is prepended to
the system prompt to encourage visible step-by-step reasoning.

Streaming
---------
When streaming is enabled and ``display != "omitted"``, the provider emits
``thinking_delta`` events.  Buddy's streaming handlers accumulate these
automatically.

Error handling
--------------
``ThinkingConfig`` raises :class:`ThinkingConfigError` with actionable
messages for common mis-configurations (wrong type for model, disabled on
always-on models, etc.).  See :func:`validate_for_model`.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/thinking
* https://platform.claude.com/docs/en/build-with-claude/extended-thinking
* https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting
* https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost
* https://platform.claude.com/docs/en/build-with-claude/thinking-tool-workflows
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

# ── Type aliases ─────────────────────────────────────────────────────────────

ThinkingMode = Literal["adaptive", "extended", "disabled"]
ThinkingDisplay = Literal["summarized", "omitted"]

# ── Model capability tables ──────────────────────────────────────────────────

# Claude models that are always-on (cannot disable thinking).
_CLAUDE_ALWAYS_ON = {
    "claude-fable-5",
    "claude-mythos-5",
}

# Claude models that default to on but can be disabled.
_CLAUDE_ON_BY_DEFAULT = {
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-mythos-preview",
}

# Claude models that support adaptive thinking.
_CLAUDE_ADAPTIVE_SUPPORT = {
    "claude-fable-5", "claude-mythos-5", "claude-mythos-preview",
    "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7",
    "claude-sonnet-5", "claude-opus-4-6", "claude-sonnet-4-6",
}

# Claude models that support extended (budget_tokens) thinking only.
_CLAUDE_EXTENDED_ONLY = {
    "claude-opus-4-5", "claude-haiku-4-5", "claude-sonnet-4-5",
    "claude-opus-4-1", "claude-sonnet-4", "claude-opus-4",
    "claude-haiku-3-5",
}

# OpenAI reasoning models.
_OPENAI_REASONING_MODELS = {
    "o1", "o1-mini", "o1-preview",
    "o3", "o3-mini",
    "o4", "o4-mini",
}

# Chain-of-thought prompt for non-native models
_COT_PROMPT = (
    "Think step by step before answering. "
    "Reason through the problem carefully, consider alternatives, "
    "then provide your final answer."
)


class ThinkingConfigError(ValueError):
    """Raised when a ThinkingConfig is incompatible with a target model."""


@dataclass
class ThinkingConfig:
    """Provider-agnostic thinking/reasoning configuration.

    Attributes:
        mode: ``"adaptive"`` (let the model decide), ``"extended"`` (use
            explicit ``budget_tokens``; Claude legacy only), or
            ``"disabled"`` (turn thinking off where supported).
        display: ``"summarized"`` returns a text summary of the reasoning
            chain in the response; ``"omitted"`` returns the thinking block
            with an empty ``thinking`` field (still billed, still passed back
            in multi-turn).  Defaults to ``"omitted"`` on newest Claude models.
        budget_tokens: Token budget for extended thinking (``mode="extended"``
            only).  Ignored in adaptive mode.
        inject_prompt: When ``True`` and the model has no native thinking
            support, prepend a chain-of-thought instruction to the system
            prompt.
        preserve_blocks: When ``True`` (default), thinking/redacted-thinking
            blocks in assistant messages are preserved verbatim when building
            multi-turn requests.  Setting this to ``False`` drops them, which
            saves tokens but breaks multi-turn integrity on Claude.
    """

    mode: ThinkingMode = "adaptive"
    display: ThinkingDisplay = "summarized"
    budget_tokens: Optional[int] = None
    inject_prompt: bool = True
    preserve_blocks: bool = True

    def __post_init__(self) -> None:
        if self.mode == "extended" and self.budget_tokens is None:
            self.budget_tokens = 10_000
        if self.mode == "extended" and self.budget_tokens is not None:
            if self.budget_tokens < 1024:
                raise ThinkingConfigError(
                    f"budget_tokens must be at least 1024; got {self.budget_tokens}"
                )

    # ── Claude helpers ────────────────────────────────────────────────────────

    def to_claude_param(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Return the ``thinking`` parameter dict for the Anthropic API.

        Returns ``None`` when no ``thinking`` key should be sent (e.g. for
        always-on models where omitting the key is correct, or when the model
        doesn't support thinking at all).
        """
        prefix = self._claude_prefix(model_id)

        if self.mode == "disabled":
            if prefix in _CLAUDE_ALWAYS_ON:
                raise ThinkingConfigError(
                    f"Model {model_id!r} always has thinking on; "
                    "you cannot set mode='disabled'. "
                    "Use display='omitted' to hide the thinking text instead."
                )
            # For models that default on, explicitly disable
            if prefix in _CLAUDE_ON_BY_DEFAULT:
                return {"type": "disabled"}
            # For models where thinking is off by default, just omit
            return None

        if self.mode == "extended":
            if prefix in _CLAUDE_ADAPTIVE_SUPPORT and prefix not in _CLAUDE_EXTENDED_ONLY:
                # Adaptive-only models reject extended → migrate automatically
                return self._adaptive_dict()
            if prefix in _CLAUDE_EXTENDED_ONLY:
                return {
                    "type": "enabled",
                    "budget_tokens": self.budget_tokens or 10_000,
                }
            return {
                "type": "enabled",
                "budget_tokens": self.budget_tokens or 10_000,
            }

        # mode == "adaptive" (default)
        if prefix in _CLAUDE_EXTENDED_ONLY:
            # Extended-only models reject adaptive → fall back to extended
            return {
                "type": "enabled",
                "budget_tokens": self.budget_tokens or 10_000,
            }
        if prefix is None:
            # Unknown model; return None (don't break the request)
            return None
        return self._adaptive_dict()

    def _adaptive_dict(self) -> Dict[str, Any]:
        return {"type": "adaptive", "display": self.display}

    def to_prompt_hint(self) -> str:
        """Chain-of-thought hint for models without native thinking support."""
        if self.mode == "disabled":
            return ""
        return _COT_PROMPT

    def validate_for_model(self, model_id: str, provider: str = "") -> None:
        """Raise :class:`ThinkingConfigError` if this config is incompatible
        with *model_id*.  Call before building request parameters."""
        provider_lc = provider.lower()
        if "openai" in provider_lc or model_id.startswith(("gpt-", "o1", "o3", "o4")):
            if self.mode == "extended":
                raise ThinkingConfigError(
                    f"OpenAI model {model_id!r} does not support extended thinking "
                    "with budget_tokens.  Use mode='adaptive' or control depth "
                    "via EffortConfig.level."
                )
        prefix = self._claude_prefix(model_id)
        if prefix is None:
            return  # non-Claude; skip validation
        if self.mode == "disabled" and prefix in _CLAUDE_ALWAYS_ON:
            raise ThinkingConfigError(
                f"Model {model_id!r} always has thinking on and cannot be disabled. "
                "Use display='omitted' to suppress the thinking text in the response."
            )

    # ── Streaming helpers ─────────────────────────────────────────────────────

    @property
    def streams_thinking(self) -> bool:
        """Return True when the config will produce thinking_delta events."""
        return self.mode != "disabled" and self.display == "summarized"

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _claude_prefix(model_id: str) -> Optional[str]:
        all_known = (
            _CLAUDE_ALWAYS_ON
            | _CLAUDE_ON_BY_DEFAULT
            | _CLAUDE_ADAPTIVE_SUPPORT
            | _CLAUDE_EXTENDED_ONLY
        )
        for prefix in all_known:
            if model_id.startswith(prefix):
                return prefix
        return None


# ── Convenience constructors ──────────────────────────────────────────────────

def adaptive(display: ThinkingDisplay = "summarized") -> ThinkingConfig:
    """Adaptive thinking: Claude decides when and how deeply to think."""
    return ThinkingConfig(mode="adaptive", display=display)


def extended(budget_tokens: int = 10_000, display: ThinkingDisplay = "summarized") -> ThinkingConfig:
    """Extended thinking with an explicit token budget (legacy Claude 4.5 style)."""
    return ThinkingConfig(mode="extended", budget_tokens=budget_tokens, display=display)


def disabled() -> ThinkingConfig:
    """Disable thinking where supported."""
    return ThinkingConfig(mode="disabled", inject_prompt=False)


def omitted() -> ThinkingConfig:
    """Adaptive thinking with omitted display (thinking runs but text is hidden)."""
    return ThinkingConfig(mode="adaptive", display="omitted")
