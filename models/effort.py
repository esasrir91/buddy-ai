"""Effort control for LLM requests.

The effort parameter lets you trade off between response quality and token
efficiency. This module defines effort levels and provides model-agnostic
utilities to apply them.

**Claude** maps effort to ``output_config.effort`` (low/medium/high/xhigh/max).
**OpenAI reasoning models** (o1, o3, o4) map effort to ``reasoning_effort``.
**Other models** receive a prompt-based hint when ``inject_prompt=True``.

Usage::

    from buddy.models.effort import EffortConfig

    model = Claude(effort=EffortConfig(level="medium"))
    model = OpenAIChat(id="o3", effort=EffortConfig(level="high"))

    # Dynamic effort (e.g. low for subagents, high for main tasks)
    config = EffortConfig(level="low", inject_prompt=True)

Effort levels
-------------
* ``max``    – Unconstrained. Best results, highest token cost.
* ``xhigh``  – Extended capability for long-horizon / agentic work.
* ``high``   – Default. Complex reasoning, difficult coding, agentic tasks.
* ``medium`` – Balanced: moderate savings with solid performance.
* ``low``    – Most efficient. Significant savings; best for simple tasks.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/effort
* https://platform.openai.com/docs/guides/reasoning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

# Valid effort values (ordered weakest → strongest)
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]

# ── Model-specific effort mappings ──────────────────────────────────────────

# Claude models that support each effort level
_CLAUDE_EFFORT_SUPPORT: Dict[str, tuple] = {
    # model-id prefix → supported levels
    "claude-fable-5":         ("low", "medium", "high", "xhigh", "max"),
    "claude-mythos-5":        ("low", "medium", "high", "xhigh", "max"),
    "claude-mythos-preview":  ("low", "medium", "high", "xhigh", "max"),
    "claude-opus-5":          ("low", "medium", "high", "xhigh", "max"),
    "claude-opus-4-8":        ("low", "medium", "high", "xhigh", "max"),
    "claude-opus-4-7":        ("low", "medium", "high", "xhigh", "max"),
    "claude-sonnet-5":        ("low", "medium", "high", "xhigh", "max"),
    "claude-opus-4-6":        ("low", "medium", "high", "max"),
    "claude-sonnet-4-6":      ("low", "medium", "high", "max"),
    "claude-opus-4-5":        ("low", "medium", "high", "max"),
}

# OpenAI reasoning models and their effort param mapping
_OPENAI_REASONING_MODELS = {
    "o1", "o1-mini", "o1-preview",
    "o3", "o3-mini",
    "o4", "o4-mini",
}

# Prompt hints for models without native effort support
_EFFORT_PROMPTS: Dict[str, str] = {
    "low":    "Be concise and direct. Use the minimum tokens needed for a correct answer.",
    "medium": "Balance thoroughness and conciseness. Cover the key points without over-elaborating.",
    "high":   "Be thorough and comprehensive in your response. Reason carefully before answering.",
    "xhigh":  "Apply deep reasoning and extended analysis. Explore multiple approaches before settling on an answer.",
    "max":    "Apply maximum reasoning depth. Be exhaustive, check your work, and provide the most complete answer possible.",
}


@dataclass
class EffortConfig:
    """Configure how much work the model should put into each response.

    Attributes:
        level: One of ``"low"``, ``"medium"``, ``"high"``, ``"xhigh"``,
            ``"max"``.  Defaults to ``"high"`` (the API default).
        inject_prompt: When ``True``, prepend an effort hint to the system
            prompt for models that don't support a native effort parameter.
            Has no effect on Claude and OpenAI reasoning models, which use
            their provider-native parameters.
    """

    level: EffortLevel = "high"
    inject_prompt: bool = True

    def __post_init__(self) -> None:
        if self.level not in EFFORT_LEVELS:
            raise ValueError(
                f"Invalid effort level {self.level!r}. "
                f"Choose from: {', '.join(EFFORT_LEVELS)}"
            )

    # ── Provider-specific helpers ────────────────────────────────────────────

    def to_claude_output_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Return ``output_config`` dict for the Anthropic API, or ``None``
        if the model does not support this effort level."""
        # Skip default "high" to avoid cache invalidation
        if self.level == "high":
            return None
        model_prefix = self._claude_prefix(model_id)
        if model_prefix is None:
            return None
        supported = _CLAUDE_EFFORT_SUPPORT.get(model_prefix, ())
        if not supported or self.level not in supported:
            return None
        return {"effort": self.level}

    def to_openai_reasoning_effort(self, model_id: str) -> Optional[str]:
        """Return the ``reasoning_effort`` value for OpenAI o-models, or
        ``None`` for non-reasoning models or the default effort level."""
        if not self._is_openai_reasoning_model(model_id):
            return None
        # Map xhigh → high (OpenAI uses low/medium/high)
        mapping = {"low": "low", "medium": "medium", "high": "high",
                   "xhigh": "high", "max": "high"}
        return mapping.get(self.level)

    def to_prompt_hint(self) -> str:
        """Return a system-prompt string that communicates effort level to
        any model without native effort support."""
        return _EFFORT_PROMPTS.get(self.level, "")

    def is_default(self) -> bool:
        """Return True when this config is equivalent to the API default and
        can be safely omitted to preserve prompt-cache hits."""
        return self.level == "high"

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _claude_prefix(model_id: str) -> Optional[str]:
        for prefix in _CLAUDE_EFFORT_SUPPORT:
            if model_id.startswith(prefix):
                return prefix
        return None

    @staticmethod
    def _is_openai_reasoning_model(model_id: str) -> bool:
        return any(model_id.startswith(m) for m in _OPENAI_REASONING_MODELS)
