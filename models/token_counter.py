"""Pre-request token counting for any LLM provider.

Estimates the number of tokens a request will consume **before** it is sent,
enabling:

* Proactive context-window overflow detection.
* Smart model routing based on prompt size.
* Cost estimation and rate-limit management.

Three backends are tried in order of accuracy:

1. **Anthropic token-counting API** (``/v1/messages/count_tokens``): exact
   count for any Claude model.  Requires the ``anthropic`` package and a
   valid API key.
2. **tiktoken**: fast, local, accurate for OpenAI GPT models and anything
   that uses the same tokenizer family (cl100k_base, o200k_base, etc.).
3. **Character heuristic**: ``len(text) / chars_per_token`` — fast, free,
   ~20 % error.  Always available as a last resort.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/token-counting
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Character-heuristic fallback
# ---------------------------------------------------------------------------

_DEFAULT_CHARS_PER_TOKEN = 4.0

# Known tokenizer encoding → model prefixes
_TIKTOKEN_ENCODING_FOR_MODEL = {
    "o200k_base": {
        "gpt-4o", "gpt-4o-mini", "o1", "o3", "o4",
        "o1-mini", "o1-preview", "o3-mini", "o4-mini",
    },
    "cl100k_base": {
        "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5",
        "text-embedding-ada-002", "text-embedding-3",
    },
    "p50k_base": {"text-davinci-003", "text-davinci-002"},
}


def _encoding_for_model(model_id: str) -> Optional[str]:
    """Return the tiktoken encoding name for *model_id*, or ``None``."""
    for encoding, prefixes in _TIKTOKEN_ENCODING_FOR_MODEL.items():
        for prefix in prefixes:
            if model_id.startswith(prefix):
                return encoding
    return None


def _content_to_text(content: Any) -> str:
    """Flatten a message content value to a plain string for counting."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "") or block.get("content", "")))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content or "")


def estimate_tokens_heuristic(
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    chars_per_token: float = _DEFAULT_CHARS_PER_TOKEN,
) -> int:
    """Character-based token estimate.  Fast, always available.

    Args:
        messages: Conversation messages (any provider format).
        system: System prompt text (if separate from messages).
        tools: Tool/function definitions to include in the count.
        chars_per_token: Characters-per-token ratio.

    Returns:
        Estimated total input tokens (integer).
    """
    total_chars = 0

    if system:
        total_chars += len(system)

    for msg in messages:
        total_chars += len(_content_to_text(msg.get("content", "")))
        # ~4 overhead tokens per message (role, separator)
        total_chars += 16

    if tools:
        import json
        total_chars += len(json.dumps(tools))

    return max(1, math.ceil(total_chars / chars_per_token))


# ---------------------------------------------------------------------------
# tiktoken backend
# ---------------------------------------------------------------------------


def estimate_tokens_tiktoken(
    messages: List[Dict[str, Any]],
    model_id: str,
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Optional[int]:
    """Count tokens using tiktoken (OpenAI tokenizer library).

    Returns ``None`` when tiktoken is not installed or the model encoding is
    unknown.
    """
    try:
        import tiktoken
    except ImportError:
        return None

    encoding_name = _encoding_for_model(model_id)
    if encoding_name is None:
        # Try tiktoken's own model lookup
        try:
            enc = tiktoken.encoding_for_model(model_id)
        except KeyError:
            return None
    else:
        enc = tiktoken.get_encoding(encoding_name)

    import json
    total = 0

    if system:
        total += len(enc.encode(system)) + 4  # role overhead

    for msg in messages:
        content_text = _content_to_text(msg.get("content", ""))
        total += len(enc.encode(content_text))
        total += 4  # per-message overhead (role, separator tokens)

    if tools:
        total += len(enc.encode(json.dumps(tools)))

    total += 2  # reply primer
    return total


# ---------------------------------------------------------------------------
# Anthropic token-counting API backend
# ---------------------------------------------------------------------------


def count_tokens_anthropic(
    messages: List[Dict[str, Any]],
    model_id: str,
    system: Optional[Union[str, List[Dict[str, Any]]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
) -> Optional[int]:
    """Call the Anthropic ``/v1/messages/count_tokens`` endpoint.

    Returns the exact ``input_tokens`` count, or ``None`` if the call fails
    (missing package, network error, etc.).

    Args:
        messages: Messages in Anthropic format.
        model_id: Claude model ID.
        system: System prompt (string or list of content blocks).
        tools: Tool definitions.
        api_key: Anthropic API key.  Falls back to the ``ANTHROPIC_API_KEY``
            environment variable.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    try:
        import os
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return None

        client = Anthropic(api_key=key)

        kwargs: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
        }
        if system is not None:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = client.messages.count_tokens(**kwargs)
        return getattr(response, "input_tokens", None)
    except Exception:
        return None


async def count_tokens_anthropic_async(
    messages: List[Dict[str, Any]],
    model_id: str,
    system: Optional[Union[str, List[Dict[str, Any]]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
) -> Optional[int]:
    """Async variant of :func:`count_tokens_anthropic`."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return None

    try:
        import os
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return None

        client = AsyncAnthropic(api_key=key)

        kwargs: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
        }
        if system is not None:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = await client.messages.count_tokens(**kwargs)
        return getattr(response, "input_tokens", None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Unified token counter
# ---------------------------------------------------------------------------


@dataclass
class TokenCountResult:
    """Result of a token count operation.

    Attributes:
        token_count: Estimated / exact token count.
        backend: Which backend produced the count
            (``"anthropic_api"``, ``"tiktoken"``, ``"heuristic"``).
        is_exact: ``True`` only for Anthropic API counts.
        model_id: The model the count is for.
    """

    token_count: int
    backend: str
    is_exact: bool
    model_id: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "token_count": self.token_count,
            "backend": self.backend,
            "is_exact": self.is_exact,
            "model_id": self.model_id,
        }


def count_tokens(
    messages: List[Dict[str, Any]],
    model_id: str,
    system: Optional[Union[str, List[Dict[str, Any]]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    prefer_api: bool = True,
    chars_per_token: float = _DEFAULT_CHARS_PER_TOKEN,
) -> TokenCountResult:
    """Count input tokens using the best available backend.

    Backend priority:
    1. Anthropic API (exact, only for Claude models when ``prefer_api=True``)
    2. tiktoken (fast, accurate for OpenAI family)
    3. Character heuristic (always available)

    Args:
        messages: Conversation messages.
        model_id: Target model ID.
        system: System prompt.
        tools: Tool definitions.
        api_key: API key for provider-side counting.
        prefer_api: When ``True``, attempt the Anthropic API first for Claude
            models.
        chars_per_token: Fallback heuristic ratio.

    Returns:
        :class:`TokenCountResult` with the count and backend info.
    """
    # 1. Anthropic API for Claude models
    if prefer_api and model_id.startswith("claude"):
        n = count_tokens_anthropic(
            messages=messages,
            model_id=model_id,
            system=system,
            tools=tools,
            api_key=api_key,
        )
        if n is not None:
            return TokenCountResult(
                token_count=n,
                backend="anthropic_api",
                is_exact=True,
                model_id=model_id,
            )

    # 2. tiktoken for OpenAI-family models
    n = estimate_tokens_tiktoken(
        messages=messages,
        model_id=model_id,
        system=system,
        tools=tools,
    )
    if n is not None:
        return TokenCountResult(
            token_count=n,
            backend="tiktoken",
            is_exact=False,
            model_id=model_id,
        )

    # 3. Heuristic fallback
    system_text = system if isinstance(system, str) else None
    n = estimate_tokens_heuristic(
        messages=messages,
        system=system_text,
        tools=tools,
        chars_per_token=chars_per_token,
    )
    return TokenCountResult(
        token_count=n,
        backend="heuristic",
        is_exact=False,
        model_id=model_id,
    )


async def count_tokens_async(
    messages: List[Dict[str, Any]],
    model_id: str,
    system: Optional[Union[str, List[Dict[str, Any]]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    prefer_api: bool = True,
    chars_per_token: float = _DEFAULT_CHARS_PER_TOKEN,
) -> TokenCountResult:
    """Async variant of :func:`count_tokens`."""
    if prefer_api and model_id.startswith("claude"):
        n = await count_tokens_anthropic_async(
            messages=messages,
            model_id=model_id,
            system=system,
            tools=tools,
            api_key=api_key,
        )
        if n is not None:
            return TokenCountResult(
                token_count=n,
                backend="anthropic_api",
                is_exact=True,
                model_id=model_id,
            )

    n = estimate_tokens_tiktoken(
        messages=messages,
        model_id=model_id,
        system=system,
        tools=tools,
    )
    if n is not None:
        return TokenCountResult(
            token_count=n,
            backend="tiktoken",
            is_exact=False,
            model_id=model_id,
        )

    system_text = system if isinstance(system, str) else None
    n = estimate_tokens_heuristic(
        messages=messages,
        system=system_text,
        tools=tools,
        chars_per_token=chars_per_token,
    )
    return TokenCountResult(
        token_count=n,
        backend="heuristic",
        is_exact=False,
        model_id=model_id,
    )


# ---------------------------------------------------------------------------
# Convenience: fits_in_context
# ---------------------------------------------------------------------------


def fits_in_context(
    messages: List[Dict[str, Any]],
    model_id: str,
    max_output_tokens: int = 4_096,
    system: Optional[Union[str, List[Dict[str, Any]]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    context_window: Optional[int] = None,
) -> bool:
    """Return ``True`` when the request is estimated to fit in the context window.

    Args:
        messages: Conversation messages.
        model_id: Target model ID.
        max_output_tokens: Expected maximum output tokens (subtracted from the
            available window).
        system: System prompt.
        tools: Tool definitions.
        api_key: API key for Anthropic exact counting.
        context_window: Override the context window size.  When ``None``,
            the known size for *model_id* is used.

    Returns:
        ``True`` when the estimated input + output fits within the window.
    """
    from buddy.models.context_window import context_window_for_model

    cw = context_window or context_window_for_model(model_id)
    result = count_tokens(
        messages=messages,
        model_id=model_id,
        system=system,
        tools=tools,
        api_key=api_key,
    )
    return (result.token_count + max_output_tokens) <= cw
