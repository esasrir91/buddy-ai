"""Token budget management and pre-invoke token estimation.

Buddy estimates the token cost of every request *before* it is sent so it can:

* Warn when a request is approaching the model's context limit.
* Automatically drop the oldest history turns to bring the count back under
  budget (``auto_compress=True``).
* Report how many tokens were trimmed in ``RunResponse.metrics``.

Usage on a model::

    from buddy.models.openai import OpenAIChat
    from buddy.models.token_budget import TokenBudgetConfig

    model = OpenAIChat(
        id="gpt-4o",
        token_budget=TokenBudgetConfig(
            max_input_tokens=100_000,
            target_input_tokens=80_000,   # trim history until we're here
            auto_compress=True,
            warn_at=0.90,                 # warn at 90 % of max
        ),
    )

Usage on an agent (propagated to the model automatically)::

    agent = Agent(
        model=...,
        token_budget=TokenBudgetConfig(max_input_tokens=100_000, auto_compress=True),
    )
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from buddy.models.message import Message


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class TokenBudgetConfig:
    """Configuration for the TokenBudgetManager attached to a Model.

    Attributes:
        max_input_tokens: Hard ceiling on input tokens per request.  Set to the
            model's context window minus a comfortable output reserve.
        target_input_tokens: After auto-compression the manager trims history
            until the estimated input is at or below this value.  Defaults to
            90 % of ``max_input_tokens``.
        auto_compress: When ``True``, drop the oldest history ``Message``
            pairs (user + assistant) until the count is under budget instead
            of raising an error.
        warn_at: Fraction of ``max_input_tokens`` at which a warning is logged
            (0–1).  Set to ``None`` to silence warnings.
        count_method: Token counting strategy.
            ``"tiktoken"`` — uses the tiktoken library when available.
            ``"approx"``   — fast character-count approximation (len // 4).
        tokens_trimmed: Accumulated token count removed from history across all
            requests in this session.  Updated in-place by the manager.
    """

    max_input_tokens: int = 100_000
    target_input_tokens: Optional[int] = None
    auto_compress: bool = True
    warn_at: Optional[float] = 0.85
    count_method: str = "approx"   # "tiktoken" | "approx"
    # Cap individual tool-result messages at this many tokens.  Set to None to
    # disable tool-result trimming even when the budget is active.
    max_tool_result_tokens: Optional[int] = 2_000
    tokens_trimmed: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.target_input_tokens is None:
            self.target_input_tokens = int(self.max_input_tokens * 0.90)


# ---------------------------------------------------------------------------
# Token counting helpers
# ---------------------------------------------------------------------------

def _approx_tokens(text: str) -> int:
    """Approximate token count: 1 token ≈ 4 characters (English prose)."""
    return max(1, len(text) // 4)


def _tiktoken_tokens(text: str, model: str = "gpt-4o") -> int:
    """Exact token count via tiktoken (falls back to approx if unavailable)."""
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return _approx_tokens(text)


def count_message_tokens(message: "Message", method: str = "approx", model_id: str = "gpt-4o") -> int:
    """Estimate the token cost of a single ``Message``."""
    content = message.get_content_string() if hasattr(message, "get_content_string") else (
        message.content if isinstance(message.content, str) else str(message.content or "")
    )

    # Tool call JSON contributes tokens too
    extra = ""
    if message.tool_calls:
        import json
        extra = json.dumps(message.tool_calls)
    if message.tool_call_id:
        extra += message.tool_call_id

    text = content + extra
    if not text:
        return 4  # empty messages still cost a few overhead tokens

    if method == "tiktoken":
        return _tiktoken_tokens(text, model_id) + 4  # +4 for role/overhead per message
    return _approx_tokens(text) + 4


def estimate_messages_tokens(
    messages: List["Message"],
    method: str = "approx",
    model_id: str = "gpt-4o",
) -> int:
    """Estimate total token cost for a list of messages."""
    return sum(count_message_tokens(m, method, model_id) for m in messages) + 3  # +3 reply primer


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class TokenBudgetManager:
    """Checks and enforces token budgets before each model invocation.

    Attach an instance to ``Model.token_budget_manager`` or create one from a
    ``TokenBudgetConfig`` via ``TokenBudgetManager.from_config()``.
    """

    def __init__(self, config: TokenBudgetConfig, model_id: str = "gpt-4o") -> None:
        self.config = config
        self.model_id = model_id

    @classmethod
    def from_config(cls, config: TokenBudgetConfig, model_id: str = "gpt-4o") -> "TokenBudgetManager":
        return cls(config, model_id)

    def estimate(self, messages: List["Message"]) -> int:
        """Return estimated token count for ``messages``."""
        return estimate_messages_tokens(messages, self.config.count_method, self.model_id)

    def check_and_compress(self, messages: List["Message"]) -> Dict[str, Any]:
        """Enforce the budget.  Returns a report dict with keys:

        * ``estimated_tokens`` — token count before any trimming.
        * ``tokens_after`` — token count after trimming (same if no trim needed).
        * ``turns_dropped`` — number of (user, assistant) pairs removed.
        * ``tokens_trimmed`` — tokens removed.
        * ``warning`` — non-empty string if usage is high.
        """
        from buddy.utils.log import log_warning

        cfg = self.config
        estimated = self.estimate(messages)
        report: Dict[str, Any] = {
            "estimated_tokens": estimated,
            "tokens_after": estimated,
            "turns_dropped": 0,
            "tokens_trimmed": 0,
            "warning": "",
        }

        # Warn if approaching the limit
        if cfg.warn_at is not None and estimated >= int(cfg.max_input_tokens * cfg.warn_at):
            pct = estimated / cfg.max_input_tokens * 100
            msg = (
                f"Token budget warning: ~{estimated:,} / {cfg.max_input_tokens:,} tokens "
                f"({pct:.0f}%).  Consider enabling auto_compress or reducing history."
            )
            log_warning(msg)
            report["warning"] = msg

        # Auto-compress if over the hard limit
        if cfg.auto_compress and estimated > cfg.max_input_tokens:
            estimated, trimmed_count, trimmed_tokens = self._compress(messages, estimated)
            cfg.tokens_trimmed += trimmed_tokens
            report["tokens_after"] = estimated
            report["turns_dropped"] = trimmed_count
            report["tokens_trimmed"] = trimmed_tokens
            if trimmed_count:
                from buddy.utils.log import log_info
                log_info(
                    f"TokenBudget: dropped {trimmed_count} history turn(s) "
                    f"(~{trimmed_tokens:,} tokens) to fit context window."
                )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compress(
        self,
        messages: List["Message"],
        current_estimate: int,
    ) -> tuple[int, int, int]:
        """Remove the oldest history turns until ``current_estimate`` is under
        ``target_input_tokens``.  History messages are identified by
        ``message.from_history == True``.

        Returns ``(new_estimate, turns_dropped, tokens_trimmed)``.
        """
        target = self.config.target_input_tokens or int(self.config.max_input_tokens * 0.90)
        history_indices = [
            i for i, m in enumerate(messages)
            if getattr(m, "from_history", False)
        ]

        turns_dropped = 0
        tokens_trimmed = 0

        # Remove from the oldest (lowest index) history messages in pairs
        i = 0
        while current_estimate > target and i < len(history_indices):
            idx = history_indices[i]
            msg = messages[idx]
            cost = count_message_tokens(msg, self.config.count_method, self.model_id)
            messages.pop(idx)
            # Adjust remaining indices
            history_indices = [j - 1 if j > idx else j for j in history_indices]
            current_estimate -= cost
            tokens_trimmed += cost
            turns_dropped += 1
            # Don't re-increment i; we re-check the same slot

        return current_estimate, turns_dropped, tokens_trimmed
