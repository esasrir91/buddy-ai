"""Fast mode configuration for Claude Opus models.

Fast mode delivers up to **2.5× higher output tokens per second** from
Claude Opus 5 and Claude Opus 4.8 via a premium-priced inference path.
It is a research preview feature requiring the ``fast-mode-2026-02-01``
beta header.

For other providers, ``FastModeConfig`` acts as a no-op (the ``speed``
param is simply not added to non-Claude requests).

Usage::

    from buddy.models.fast_mode import FastModeConfig
    from buddy.models.anthropic import Claude

    model = Claude(
        id="claude-opus-5",
        fast_mode=FastModeConfig(enabled=True, fallback_on_rate_limit=True),
    )

Pricing
-------
* Input:  $10 / MTok   (vs $5 standard)
* Output: $50 / MTok   (vs $25 standard)
* Stacks with prompt caching and data residency multipliers.

Limitations
-----------
* Only Claude Opus 5 and Claude Opus 4.8 support fast mode.
* Not available on Batch API, Priority Tier, or AWS/GCP/Azure deployments.
* Cache prefixes are NOT shared between fast and standard speed requests.
* Time-to-first-token (TTFT) improvement is minimal; gains are in OTPS.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/fast-mode
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Models that support fast mode
_FAST_MODE_SUPPORTED_MODELS = {
    "claude-opus-5",
    "claude-opus-4-8",
}

# Beta header required for fast mode
FAST_MODE_BETA = "fast-mode-2026-02-01"


@dataclass
class FastModeConfig:
    """Configure fast-mode inference for supported Claude Opus models.

    Attributes:
        enabled: Enable fast mode.  Only takes effect on
            ``claude-opus-5`` and ``claude-opus-4-8``.
        fallback_on_rate_limit: When ``True`` and the fast-mode rate limit
            is exceeded (HTTP 429), the request is automatically retried at
            standard speed instead of raising an error.  Note that a
            fallback request will incur a prompt-cache miss.
        max_retries_before_fallback: Number of retry attempts on transient
            errors (5xx, connection errors) before giving up.  Does not
            apply to the rate-limit fallback path.
    """

    enabled: bool = True
    fallback_on_rate_limit: bool = True
    max_retries_before_fallback: int = 2

    def is_supported(self, model_id: str) -> bool:
        """Return True when the model supports fast mode."""
        return any(model_id.startswith(m) for m in _FAST_MODE_SUPPORTED_MODELS)

    def get_speed_param(self, model_id: str) -> Optional[str]:
        """Return ``"fast"`` when fast mode should be requested, else ``None``."""
        if self.enabled and self.is_supported(model_id):
            return "fast"
        return None

    def get_betas(self, model_id: str) -> List[str]:
        """Return the list of beta headers needed for this request."""
        if self.enabled and self.is_supported(model_id):
            return [FAST_MODE_BETA]
        return []

    def to_request_params(self, model_id: str) -> Dict[str, Any]:
        """Return additional request parameters to inject for fast mode."""
        params: Dict[str, Any] = {}
        speed = self.get_speed_param(model_id)
        if speed:
            params["speed"] = speed
        return params
