"""Cache diagnostics for prompt caching across LLM providers.

Analyses per-request cache hit/miss data returned by the API and surfaces
actionable recommendations to improve cache efficiency.

Supported providers
-------------------
* **Anthropic**: ``cache_read_input_tokens``, ``cache_creation_input_tokens``
  in the ``usage`` block.  Cache savings are clearly separated from billed
  input tokens.
* **OpenAI**: ``prompt_tokens_details.cached_tokens`` in the ``usage``
  object.  Cache is automatic for requests ≥ 1024 tokens that share a prefix.
* **Generic**: Falls back to zero cache tokens when the provider doesn't
  report caching metrics.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/cache-diagnostics
* https://platform.claude.com/docs/en/build-with-claude/prompt-caching
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Per-request cache metrics
# ---------------------------------------------------------------------------


@dataclass
class CacheMetrics:
    """Token-level cache metrics for a single API request.

    Attributes:
        model_id: The model that handled the request.
        input_tokens: Total input tokens billed (does **not** include cache
            reads that are billed at the discounted rate on Anthropic).
        output_tokens: Output tokens generated.
        cache_read_tokens: Input tokens served from the prompt cache
            (Anthropic ``cache_read_input_tokens``; OpenAI cached portion
            of ``prompt_tokens``).
        cache_write_tokens: Input tokens written to the cache this request
            (Anthropic ``cache_creation_input_tokens``).
        cache_hit: ``True`` when at least one token was served from cache.
        latency_ms: Round-trip latency in milliseconds (optional).
        timestamp: Unix time when the request completed.
    """

    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: Optional[float] = None
    timestamp: float = field(default_factory=time.time)

    # ── Derived helpers ──────────────────────────────────────────────────────

    @property
    def cache_hit(self) -> bool:
        return self.cache_read_tokens > 0

    @property
    def total_input_tokens(self) -> int:
        """All input tokens including cache reads and cache writes."""
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    @property
    def cache_hit_rate(self) -> float:
        """Fraction of input tokens served from cache (0.0–1.0)."""
        total = self.total_input_tokens
        if total == 0:
            return 0.0
        return min(1.0, self.cache_read_tokens / total)

    @property
    def effective_input_tokens(self) -> int:
        """Tokens actually fetched (not from cache), i.e. cache misses."""
        return self.input_tokens + self.cache_write_tokens

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "total_input_tokens": self.total_input_tokens,
            "cache_hit": self.cache_hit,
            "cache_hit_rate_pct": round(self.cache_hit_rate * 100, 1),
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def extract_cache_metrics_anthropic(
    response: Any,
    model_id: str = "",
    latency_ms: Optional[float] = None,
) -> CacheMetrics:
    """Extract cache metrics from an Anthropic API response object or dict."""
    usage = getattr(response, "usage", None) or {}
    if hasattr(usage, "__dict__"):
        usage = {k: v for k, v in vars(usage).items() if v is not None}

    def _get(key: str) -> int:
        if isinstance(usage, dict):
            return int(usage.get(key) or 0)
        return int(getattr(usage, key, 0) or 0)

    return CacheMetrics(
        model_id=model_id or (getattr(response, "model", "") or ""),
        input_tokens=_get("input_tokens"),
        output_tokens=_get("output_tokens"),
        cache_read_tokens=_get("cache_read_input_tokens"),
        cache_write_tokens=_get("cache_creation_input_tokens"),
        latency_ms=latency_ms,
    )


def extract_cache_metrics_openai(
    response: Any,
    model_id: str = "",
    latency_ms: Optional[float] = None,
) -> CacheMetrics:
    """Extract cache metrics from an OpenAI API response object or dict."""
    usage = getattr(response, "usage", None) or {}
    if hasattr(usage, "__dict__"):
        usage_dict = {k: v for k, v in vars(usage).items() if v is not None}
    elif isinstance(usage, dict):
        usage_dict = usage
    else:
        usage_dict = {}

    def _get(key: str) -> int:
        return int(usage_dict.get(key) or 0)

    # OpenAI nests cached_tokens under prompt_tokens_details
    details = usage_dict.get("prompt_tokens_details") or {}
    if hasattr(details, "__dict__"):
        details = vars(details)
    cached = int((details.get("cached_tokens") if isinstance(details, dict) else
                  getattr(details, "cached_tokens", 0)) or 0)

    prompt_tokens = _get("prompt_tokens")
    return CacheMetrics(
        model_id=model_id or (getattr(response, "model", "") or ""),
        input_tokens=prompt_tokens - cached,
        output_tokens=_get("completion_tokens"),
        cache_read_tokens=cached,
        cache_write_tokens=0,  # OpenAI does not report write tokens separately
        latency_ms=latency_ms,
    )


def extract_cache_metrics_generic(
    response: Any,
    model_id: str = "",
    latency_ms: Optional[float] = None,
) -> CacheMetrics:
    """Best-effort cache metric extraction for unknown providers."""
    usage = getattr(response, "usage", None) or {}
    if hasattr(usage, "__dict__"):
        usage = vars(usage)

    def _get(*keys: str) -> int:
        for k in keys:
            v = usage.get(k) if isinstance(usage, dict) else getattr(usage, k, None)
            if v is not None:
                return int(v)
        return 0

    return CacheMetrics(
        model_id=model_id or (getattr(response, "model", "") or ""),
        input_tokens=_get("input_tokens", "prompt_tokens"),
        output_tokens=_get("output_tokens", "completion_tokens"),
        cache_read_tokens=_get(
            "cache_read_input_tokens", "cached_tokens", "cache_hit_tokens"
        ),
        cache_write_tokens=_get("cache_creation_input_tokens", "cache_write_tokens"),
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Session-level diagnostics aggregator
# ---------------------------------------------------------------------------


@dataclass
class CacheDiagnostics:
    """Aggregated cache statistics across multiple requests.

    Use :meth:`record` to add a :class:`CacheMetrics` snapshot after each
    request, then call :meth:`report` to get a summary dict.

    Attributes:
        requests: All recorded CacheMetrics snapshots.
    """

    requests: List[CacheMetrics] = field(default_factory=list)

    def record(self, metrics: CacheMetrics) -> None:
        """Append *metrics* to the session history."""
        self.requests.append(metrics)

    # ── Aggregated stats ─────────────────────────────────────────────────────

    @property
    def total_requests(self) -> int:
        return len(self.requests)

    @property
    def cache_hits(self) -> int:
        return sum(1 for m in self.requests if m.cache_hit)

    @property
    def cache_misses(self) -> int:
        return self.total_requests - self.cache_hits

    @property
    def session_hit_rate(self) -> float:
        if not self.requests:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def total_input_tokens(self) -> int:
        return sum(m.total_input_tokens for m in self.requests)

    @property
    def total_cache_read_tokens(self) -> int:
        return sum(m.cache_read_tokens for m in self.requests)

    @property
    def total_cache_write_tokens(self) -> int:
        return sum(m.cache_write_tokens for m in self.requests)

    @property
    def token_cache_hit_rate(self) -> float:
        """Fraction of total input tokens served from cache."""
        if self.total_input_tokens == 0:
            return 0.0
        return min(1.0, self.total_cache_read_tokens / self.total_input_tokens)

    # ── Recommendations ──────────────────────────────────────────────────────

    def recommendations(self) -> List[str]:
        """Return a list of actionable cache improvement recommendations."""
        recs: List[str] = []

        if not self.requests:
            return ["No requests recorded yet."]

        hit_rate = self.session_hit_rate
        token_hit_rate = self.token_cache_hit_rate

        if hit_rate < 0.3:
            recs.append(
                f"Cache hit rate is low ({hit_rate:.0%}). "
                "Ensure the system prompt and tool definitions are placed before "
                "frequently-changing content, and that repeated requests share "
                "a stable prefix (≥ 1024 tokens for OpenAI, ≥ 1024 for Anthropic)."
            )

        if self.total_cache_write_tokens > 0 and self.total_cache_read_tokens == 0:
            recs.append(
                "Cache writes are happening but no reads have occurred. "
                "This is expected on the first request.  If it persists across "
                "multiple requests, check that the prefix being cached is "
                "identical across calls (same system prompt text, same order)."
            )

        if token_hit_rate < 0.5 and self.total_requests > 3:
            recs.append(
                f"Token cache hit rate is {token_hit_rate:.0%}. "
                "Move large, stable content (system prompt, tool schemas, "
                "document context) to the beginning of the request so it "
                "forms a long cacheable prefix."
            )

        # Check for models that need explicit cache_control
        anthropic_models = [m for m in self.requests if "claude" in m.model_id.lower()]
        if anthropic_models and all(m.cache_write_tokens == 0 for m in anthropic_models):
            recs.append(
                "No Anthropic cache writes detected.  Set ``cache_prompt=True`` "
                "on the Claude model (or attach a PromptCacheConfig) to enable "
                "explicit prompt caching."
            )

        if not recs:
            recs.append(
                f"Cache looks healthy: session hit rate {hit_rate:.0%}, "
                f"token hit rate {token_hit_rate:.0%}."
            )

        return recs

    def report(self) -> Dict[str, Any]:
        """Return a comprehensive diagnostics report dict."""
        avg_latency = None
        latencies = [m.latency_ms for m in self.requests if m.latency_ms is not None]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)

        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "session_hit_rate_pct": round(self.session_hit_rate * 100, 1),
            "total_input_tokens": self.total_input_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "token_cache_hit_rate_pct": round(self.token_cache_hit_rate * 100, 1),
            "avg_latency_ms": round(avg_latency, 1) if avg_latency else None,
            "recommendations": self.recommendations(),
        }

    def print_report(self) -> None:
        """Print a human-readable cache diagnostics report."""
        r = self.report()
        print("─" * 60)
        print("Cache Diagnostics Report")
        print("─" * 60)
        print(f"  Requests         : {r['total_requests']}")
        print(f"  Cache hits       : {r['cache_hits']} ({r['session_hit_rate_pct']}%)")
        print(f"  Cache misses     : {r['cache_misses']}")
        print(f"  Total input toks : {r['total_input_tokens']:,}")
        print(f"  Cache read toks  : {r['total_cache_read_tokens']:,}")
        print(f"  Cache write toks : {r['total_cache_write_tokens']:,}")
        print(f"  Token hit rate   : {r['token_cache_hit_rate_pct']}%")
        if r["avg_latency_ms"] is not None:
            print(f"  Avg latency      : {r['avg_latency_ms']} ms")
        print()
        print("Recommendations:")
        for rec in r["recommendations"]:
            print(f"  • {rec}")
        print("─" * 60)
