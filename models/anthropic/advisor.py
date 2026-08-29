"""Anthropic Advisor Tool configuration for the buddy framework.

The advisor tool lets a faster, lower-cost **executor** model (e.g. Claude
Sonnet or Haiku) consult a higher-intelligence **advisor** model (e.g. Claude
Opus) mid-generation for strategic guidance.  The advisor reads the executor's
full conversation transcript and returns a plan; the executor continues with the
task informed by that advice.  All of this happens inside a single API request —
no extra round trips on your side.

Usage::

    from buddy.models.anthropic import Claude, AdvisorConfig
    from buddy.agent import Agent

    agent = Agent(
        model=Claude(
            id="claude-sonnet-5",
            advisor=AdvisorConfig(
                model="claude-opus-5",
                max_tokens=2048,
                caching=True,
            ),
        ),
        instructions="You are a coding assistant.",
    )

See https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool
for full documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Beta header required by the Anthropic API to enable the advisor tool.
ADVISOR_BETA = "advisor-tool-2026-03-01"

# Suggested system-prompt block for coding / agent tasks (Sonnet executor).
# Prepend this to the executor's system prompt for consistent advisor timing
# (~2-3 calls per task).  See the Anthropic docs for executor-specific variants.
ADVISOR_SYSTEM_PROMPT_CODING = """\
You have access to an `advisor` tool backed by a stronger reviewer model. \
It takes NO parameters — when you call advisor(), your entire conversation \
history is automatically forwarded. They see the task, every tool call you've \
made, every result you've seen.

Call advisor BEFORE substantive work — before writing, before committing to an \
interpretation, before building on an assumption. If the task requires \
orientation first (finding files, fetching a source, seeing what's there), do \
that, then call advisor. Orientation is not substantive work. Writing, editing, \
and declaring an answer are.

Also call advisor:
- When you believe the task is complete. BEFORE this call, make your deliverable \
durable: write the file, save the result, commit the change. The advisor call \
takes time; if the session ends during it, a durable result persists and an \
unwritten one doesn't.
- When stuck — errors recurring, approach not converging, results that don't fit.
- When considering a change of approach.

On tasks longer than a few steps, call advisor at least once before committing \
to an approach and once before declaring done. On short reactive tasks where the \
next action is dictated by tool output you just read, you don't need to keep \
calling — the advisor adds most of its value on the first call, before the \
approach crystallizes.

Give the advice serious weight. If you follow a step and it fails empirically, \
or you have primary-source evidence that contradicts a specific claim (the file \
says X, the paper states Y), adapt. A passing self-test is not evidence the \
advice is wrong — it's evidence your test doesn't check what the advice is \
checking.

If you've already retrieved data pointing one way and the advisor points \
another: don't silently switch. Surface the conflict in one more advisor call — \
"I found X, you suggest Y, which constraint breaks the tie?" The advisor saw \
your evidence but may have underweighted it; a reconcile call is cheaper than \
committing to the wrong branch.\
"""

# Alternative system-prompt block tuned for Claude Haiku 4.5 on coding tasks.
ADVISOR_SYSTEM_PROMPT_HAIKU = """\
Consult a stronger reviewer who sees your full conversation transcript.

No parameters. When you call advisor(), your entire history — task, every tool \
call and result, your reasoning — is automatically forwarded. The advisor sees \
exactly what you've done.

Call advisor BEFORE substantive work — before writing, before committing to an \
interpretation, before building on an assumption. If the task requires \
orientation first (finding files, fetching a source, seeing what's there), do \
that, then call advisor. Orientation is not substantive work. Writing, editing, \
and declaring an answer are.

Also call advisor:
- When you believe the task is complete. BEFORE this call, make your deliverable \
durable: write the file, save the result, commit the change.
- When stuck — errors recurring, approach not converging, results that don't fit.
- When considering a change of approach.

On tasks longer than a few steps, call advisor at least once before committing \
to an approach and once before declaring done.

Give the advice serious weight. If you follow a step and it fails empirically, \
or you have primary-source evidence that contradicts a specific claim, adapt.

If you've already retrieved data pointing one way and the advisor points \
another: don't silently switch. Surface the conflict in one more advisor call.

Call advisor for design, architecture, and risk questions where you won't touch \
a file. If your response would be analysis or a recommendation with no other \
tool calls, call advisor first.

Hard rule: your first write_file, edit_file, or state-changing bash call on a \
task must be preceded by an advisor call in the same or an earlier turn. \
Read-only orientation commands (ls, cat, grep, find) are not state-changing. \
This is a checkpoint, not a difficulty judgment. It applies to one-line edits too.\
"""

# Nudge message injected as a user message when the executor has not yet called
# the advisor by the configured nudge turn.  Effective for Haiku executors;
# has no measurable effect on Sonnet; slightly lowers quality on Opus.
ADVISOR_NUDGE_TEXT = (
    "You have not consulted the advisor yet. If the task has a non-obvious "
    "design decision or a failure mode you haven't ruled out, call advisor "
    "now before committing to an approach."
)


@dataclass
class AdvisorConfig:
    """Configuration for Anthropic's advisor tool.

    Pair a faster **executor** model (set as ``Claude.id``) with a
    higher-intelligence **advisor** model to get close to advisor-quality
    output while most token generation runs at the cheaper executor rate.

    Parameters
    ----------
    model:
        Advisor model ID, e.g. ``"claude-opus-5"``.  Must form a valid
        executor/advisor pair — see the compatibility table in the Anthropic
        docs.  The advisor model must be at least as capable as the executor.
    max_uses:
        Per-request cap on advisor calls.  Once the executor reaches this cap,
        further advisor calls return an error and the executor continues without
        advice.  ``None`` = unlimited (default).
    max_tokens:
        Cap the advisor's total output (thinking + text) per call.  Minimum
        1 024.  Recommended starting point: 2 048 — reduces mean output ~7x
        with near-zero truncation.  ``None`` = advisor model's own output cap.
    caching:
        Enable prompt caching for the advisor's own transcript across calls
        within the same conversation.  Breaks even at ~3 advisor calls per
        conversation; beneficial for long agent loops.  Pass ``True`` for 5-min
        TTL (ephemeral), ``"1h"`` for 1-hour TTL, or ``False`` / ``None`` to
        disable.
    system_prompt:
        Optional system-prompt text to prepend to the executor's system prompt
        to improve advisor call timing and advice-following.  Use
        ``ADVISOR_SYSTEM_PROMPT_CODING`` (default for Sonnet/Opus executors) or
        ``ADVISOR_SYSTEM_PROMPT_HAIKU`` for Haiku executors.  Set to ``""`` to
        skip the injection entirely.
    nudge_turn:
        Inject a reminder user message before this assistant turn (1-indexed)
        if the advisor has not been called yet.  Effective for Haiku executors
        (raises pass rates ~7pp).  Set to ``None`` to disable.  Recommended
        default: ``2`` for Haiku, ``None`` for Sonnet/Opus.
    """

    model: str
    max_uses: Optional[int] = None
    max_tokens: Optional[int] = None
    caching: Any = None  # True | False | None | "1h"
    system_prompt: Optional[str] = None  # None = use ADVISOR_SYSTEM_PROMPT_CODING
    nudge_turn: Optional[int] = None

    def to_tool_dict(self) -> Dict[str, Any]:
        """Return the ``advisor_20260301`` tool definition dict for the API."""
        d: Dict[str, Any] = {
            "type": "advisor_20260301",
            "name": "advisor",
            "model": self.model,
        }
        if self.max_uses is not None:
            d["max_uses"] = self.max_uses
        if self.max_tokens is not None:
            d["max_tokens"] = self.max_tokens
        if self.caching:
            ttl = "1h" if self.caching == "1h" else "5m"
            d["caching"] = {"type": "ephemeral", "ttl": ttl}
        return d

    def get_system_prompt(self) -> str:
        """Return the system-prompt block to prepend to the executor's prompt.

        Returns an empty string when ``system_prompt=""`` was set explicitly
        (opt-out).  Falls back to ``ADVISOR_SYSTEM_PROMPT_CODING`` when
        ``system_prompt`` is ``None`` (the default).
        """
        if self.system_prompt is None:
            return ADVISOR_SYSTEM_PROMPT_CODING
        return self.system_prompt

    @staticmethod
    def get_betas() -> List[str]:
        """Beta header(s) required for the advisor tool."""
        return [ADVISOR_BETA]
