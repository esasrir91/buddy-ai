import json
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from os import getenv
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from buddy.exceptions import ModelProviderError, ModelRateLimitError
from buddy.models.base import Model
from buddy.models.message import Citations, DocumentCitation, Message, UrlCitation
from buddy.models.response import ModelResponse
from buddy.utils.log import log_debug, log_error, log_warning
from buddy.models.anthropic.advisor import AdvisorConfig
from buddy.utils.models.claude import MCPServerConfiguration, format_messages

try:
    from anthropic import Anthropic as AnthropicClient
    from anthropic import (
        APIConnectionError,
        APIStatusError,
    )
    from anthropic import AsyncAnthropic as AsyncAnthropicClient
    from anthropic import (
        RateLimitError,
    )
    from anthropic.types import (  # MessageDeltaEvent,  # Currently broken
        CitationPageLocation,
        CitationsWebSearchResultLocation,
        ContentBlockDeltaEvent,
        ContentBlockStartEvent,
        ContentBlockStopEvent,
    )
    from anthropic.types import Message as AnthropicMessage
    from anthropic.types import (  # MessageDeltaEvent,  # Currently broken
        MessageStopEvent,
    )
except ImportError as e:
    raise ImportError("`anthropic` not installed. Please install it with `pip install anthropic`") from e

# Import Beta types
try:
    from anthropic.types.beta import (
        BetaMessage,
        BetaRawContentBlockDeltaEvent,
        BetaTextDelta,
    )
except ImportError as e:
    raise ImportError(
        "`anthropic` not installed or missing beta components. Please install with `pip install anthropic`"
    ) from e


@dataclass
class Claude(Model):
    """
    A class representing Anthropic Claude model.

    For more information, see: https://docs.anthropic.com/en/api/messages

    New features (all model-agnostic via base.Model fields):
    ---------------------------------------------------------
    * ``effort``          – EffortConfig: map to output_config.effort (low/medium/high/xhigh/max).
    * ``thinking_config`` – ThinkingConfig: adaptive/extended/disabled with display control.
    * ``fast_mode``       – FastModeConfig: up to 2.5× OTPS on claude-opus-5 / claude-opus-4-8.
    * ``multilingual``    – MultilingualConfig: enforce a response language.
    * ``citation_config`` – CitationConfig: enable native citation support.

    Legacy thinking shortcut
    ------------------------
    ``thinking`` (Dict) is the old low-level way to pass the ``thinking``
    param.  It is still respected.  Prefer ``thinking_config`` for new code.
    """

    id: str = "claude-3-5-sonnet-20241022"
    name: str = "Claude"
    provider: str = "Anthropic"

    # Automatic prompt caching is on by default for all Claude models.
    # Set cache_prompt=False to disable it (e.g. for short one-shot calls
    # where the cache-write overhead is not worth it).
    cache_prompt: bool = True

    # Request parameters
    max_tokens: Optional[int] = 4096
    thinking: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    cache_system_prompt: Optional[bool] = False
    extended_cache_time: Optional[bool] = False
    cache_tools: Optional[bool] = False  # add cache_control to last tool entry
    request_params: Optional[Dict[str, Any]] = None
    mcp_servers: Optional[List[MCPServerConfiguration]] = None

    # --- Streaming refusal handling ---
    # When True, detect stop_reason="refusal" in streaming responses and reset
    # the conversation context automatically.
    handle_streaming_refusals: bool = True
    # When set, retry refused requests on this fallback model ID.
    refusal_fallback_model: Optional[str] = None

    # Advisor tool: pair this executor model with a higher-intelligence advisor.
    # Example: advisor=AdvisorConfig(model="claude-opus-5", max_tokens=2048)
    # The advisor's system-prompt guidance is automatically prepended to the
    # executor's system prompt; set advisor.system_prompt="" to opt out.
    advisor: Optional[AdvisorConfig] = None

    # Client parameters
    api_key: Optional[str] = None
    default_headers: Optional[Dict[str, Any]] = None
    client_params: Optional[Dict[str, Any]] = None

    # Anthropic clients
    client: Optional[AnthropicClient] = None
    async_client: Optional[AsyncAnthropicClient] = None

    # Sampling params Anthropic rejects on Claude 4.7+ / Claude 5 / Mythos.
    # See: https://platform.claude.com/docs/en/build-with-claude/working-with-messages
    _DEPRECATED_SAMPLING_KEYS = ("temperature", "top_p", "top_k")

    @staticmethod
    def supports_temperature(model_id: str) -> bool:
        """Return whether Anthropic still accepts sampling params for this model.

        Anthropic deprecated ``temperature``, ``top_p``, and ``top_k`` on
        Claude 4.7+ and Claude 5 / Mythos.  Non-default values return HTTP 400
        (``temperature is deprecated for this model``).  Match as a substring
        so Bedrock / OpenRouter / dated IDs (``anthropic.claude-opus-5-…``,
        ``claude-opus-5-2026…``) are covered too.
        """
        return Claude.supports_sampling_params(model_id)

    @staticmethod
    def supports_sampling_params(model_id: str) -> bool:
        """Return whether ``temperature`` / ``top_p`` / ``top_k`` are accepted."""
        mid = (model_id or "").lower()
        # Tokens that identify models which reject sampling controls.
        # Order longer tokens first so "claude-opus-4-8" matches before a
        # hypothetical shorter sibling.
        blocked_tokens = (
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-fable-5",
            "claude-mythos-5",
            "claude-mythos-preview",
            "claude-opus-4-8",
            "claude-opus-4-7",
            # Sonnet 4.7+ if/when released under the same numbering scheme
            "claude-sonnet-4-7",
            "claude-sonnet-4-8",
        )
        return not any(tok in mid for tok in blocked_tokens)

    def _thinking_is_active(self) -> bool:
        """True when this request will enable Anthropic thinking.

        Thinking requires temperature to be unset (or 1).  Safer to omit all
        sampling params whenever thinking is on.
        """
        if self.thinking:
            t = self.thinking.get("type") if isinstance(self.thinking, dict) else None
            return t not in (None, "disabled")
        if self.thinking_config is not None:
            mode = getattr(self.thinking_config, "mode", None)
            return mode not in (None, "disabled")
        return False

    def _sampling_params_allowed(self) -> bool:
        """Sampling params are forbidden on Claude 4.7+ and whenever thinking is on."""
        if not self.supports_sampling_params(self.id):
            return False
        if self._thinking_is_active():
            return False
        return True

    def _strip_sampling_params(
        self, params: Dict[str, Any], *, warn: bool = False
    ) -> Dict[str, Any]:
        """Remove deprecated sampling keys from a request-params dict in place."""
        removed = [k for k in self._DEPRECATED_SAMPLING_KEYS if k in params]
        for k in removed:
            params.pop(k, None)
        if warn and removed:
            log_warning(
                f"Omitting deprecated sampling params {removed} for {self.id!r}; "
                "Anthropic rejects these on Claude 4.7+/5 and whenever thinking is enabled."
            )
        return params

    def __post_init__(self):
        super().__post_init__()
        # Sanitize typed fields + request_params escape hatch at construction.
        if not self.supports_sampling_params(self.id):
            dirty = (
                self.temperature is not None
                or self.top_p is not None
                or self.top_k is not None
                or (
                    self.request_params
                    and any(k in self.request_params for k in self._DEPRECATED_SAMPLING_KEYS)
                )
            )
            if dirty:
                log_warning(
                    f"Ignoring deprecated sampling params for {self.id!r}; "
                    "Anthropic no longer accepts temperature/top_p/top_k on this model."
                )
            self.temperature = None
            self.top_p = None
            self.top_k = None
            if self.request_params:
                self.request_params = dict(self.request_params)
                self._strip_sampling_params(self.request_params)
        # Propagate cache_prompt=True to the legacy per-segment flags so existing
        # code paths that check cache_system_prompt / cache_tools still fire.
        if self.cache_prompt and self.prompt_cache_config is not None:
            cfg = self.prompt_cache_config
            if cfg.cache_system:
                self.cache_system_prompt = True
            if cfg.ttl == "1h":
                self.extended_cache_time = True
            if cfg.cache_tools:
                self.cache_tools = True
        # Validate thinking_config for this model
        if self.thinking_config is not None:
            try:
                self.thinking_config.validate_for_model(self.id, provider="Anthropic")
            except Exception as e:
                log_warning(f"ThinkingConfig validation warning for {self.id!r}: {e}")

    def _get_client_params(self) -> Dict[str, Any]:
        client_params: Dict[str, Any] = {}

        self.api_key = self.api_key or getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            log_error("ANTHROPIC_API_KEY not set. Please set the ANTHROPIC_API_KEY environment variable.")

        # Add API key to client parameters
        client_params["api_key"] = self.api_key

        # Add additional client parameters
        if self.client_params is not None:
            client_params.update(self.client_params)
        if self.default_headers is not None:
            client_params["default_headers"] = self.default_headers
        return client_params

    def get_client(self) -> AnthropicClient:
        """
        Returns an instance of the Anthropic client.
        """
        if self.client and not self.client.is_closed():
            return self.client

        _client_params = self._get_client_params()
        self.client = AnthropicClient(**_client_params)
        return self.client

    def get_async_client(self) -> AsyncAnthropicClient:
        """
        Returns an instance of the async Anthropic client.
        """
        if self.async_client:
            return self.async_client

        _client_params = self._get_client_params()
        self.async_client = AsyncAnthropicClient(**_client_params)
        return self.async_client

    def get_request_params(self) -> Dict[str, Any]:
        """
        Generate keyword arguments for API requests.

        Resolution order for ``thinking``:
        1. The legacy ``self.thinking`` dict (set explicitly on the model).
        2. ``self.thinking_config`` (ThinkingConfig object, new API).
        3. Neither → no ``thinking`` key in the request.

        Resolution order for ``output_config.effort``:
        1. ``self.effort`` (EffortConfig object).
        2. Not set → ``output_config`` key is omitted.
        """
        _request_params: Dict[str, Any] = {}
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens

        # --- Thinking: legacy dict takes priority over thinking_config ---
        if self.thinking:
            _request_params["thinking"] = self.thinking
        elif self.thinking_config is not None:
            thinking_param = self.thinking_config.to_claude_param(self.id)
            if thinking_param is not None:
                _request_params["thinking"] = thinking_param

        allow_sampling = self._sampling_params_allowed()
        if allow_sampling and self.temperature is not None:
            _request_params["temperature"] = self.temperature
        if self.stop_sequences:
            _request_params["stop_sequences"] = self.stop_sequences
        if allow_sampling and self.top_p is not None:
            _request_params["top_p"] = self.top_p
        if allow_sampling and self.top_k is not None:
            _request_params["top_k"] = self.top_k
        if self.mcp_servers:
            _request_params["mcp_servers"] = [
                {k: v for k, v in asdict(server).items() if v is not None} for server in self.mcp_servers
            ]

        # --- Effort → output_config ---
        if self.effort is not None:
            output_config = self.effort.to_claude_output_config(self.id)
            if output_config:
                _request_params["output_config"] = output_config

        # --- Fast mode → speed param (merged into request_params later via _get_betas) ---
        if self.fast_mode is not None:
            fast_params = self.fast_mode.to_request_params(self.id)
            _request_params.update(fast_params)

        if self.request_params:
            _request_params.update(self.request_params)

        # Final defensive filter: request_params may be mutated after model
        # construction, but deprecated fields must never reach Anthropic.
        if not allow_sampling:
            self._strip_sampling_params(_request_params)

        return _request_params

    @staticmethod
    def _uses_advisor_tool(tools: Optional[List[Dict[str, Any]]]) -> bool:
        if not tools:
            return False
        return any(tool.get("type") == "advisor_20260301" for tool in tools)

    def _uses_beta_messages_api(self, tools: Optional[List[Dict[str, Any]]]) -> bool:
        return (
            self.mcp_servers is not None
            or self._uses_advisor_tool(tools)
            or self._uses_fast_mode()
        )

    def _uses_fast_mode(self) -> bool:
        """True when fast mode is enabled and the model supports it."""
        return (
            self.fast_mode is not None
            and self.fast_mode.enabled
            and self.fast_mode.is_supported(self.id)
        )

    def _get_betas(self, tools: Optional[List[Dict[str, Any]]]) -> List[str]:
        """Collect all Anthropic beta feature headers needed for this request."""
        betas: List[str] = []
        if self._uses_advisor_tool(tools):
            betas.extend(AdvisorConfig.get_betas())
        if self._uses_fast_mode() and self.fast_mode is not None:
            betas.extend(self.fast_mode.get_betas(self.id))
        return betas

    def _inject_advisor_tool(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Prepend the advisor tool dict when ``self.advisor`` is configured.

        If the caller already included an ``advisor_20260301`` entry in their
        own tools list we leave it untouched (their explicit config wins).
        """
        if self.advisor is None:
            return tools
        if self._uses_advisor_tool(tools):
            return tools
        advisor_dict = self.advisor.to_tool_dict()
        return [advisor_dict] + list(tools or [])

    def _requires_streaming(self, max_tokens: Optional[int] = None) -> bool:
        """True when the Anthropic SDK will reject a non-streaming ``.create()``.

        Mirrors ``Anthropic._calculate_nonstreaming_timeout``: streaming is
        required when the request may take longer than ~10 minutes, or when
        ``max_tokens`` exceeds the per-model ``MODEL_NONSTREAMING_TOKENS`` cap.
        """
        tokens = max_tokens if max_tokens is not None else (self.max_tokens or 0)
        if not tokens:
            return False
        # expected_time = 3600 * max_tokens / 128_000; require stream if > 600s
        if 3600 * tokens / 128_000 > 600:
            return True
        try:
            from anthropic._constants import MODEL_NONSTREAMING_TOKENS

            limit = MODEL_NONSTREAMING_TOKENS.get(self.id)
            if limit is not None and tokens > limit:
                return True
        except ImportError:
            pass
        return False

    def _create_message_response(
        self,
        *,
        client: Any,
        chat_messages: List[Any],
        request_kwargs: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]],
        async_client: bool = False,
    ) -> Union[AnthropicMessage, BetaMessage]:
        """Create a message, resuming automatically on advisor pause_turn."""
        use_beta = self._uses_beta_messages_api(tools)
        betas = self._get_betas(tools)

        while True:
            if use_beta:
                create = client.beta.messages.create
                kwargs = dict(request_kwargs, betas=betas) if betas else dict(request_kwargs)
            else:
                create = client.messages.create
                kwargs = dict(request_kwargs)
            # Belt-and-suspenders: never let sampling params reach Anthropic on
            # models / thinking modes that reject them (HTTP 400).
            if not self._sampling_params_allowed():
                self._strip_sampling_params(kwargs)

            response = create(
                model=self.id,
                messages=chat_messages,  # type: ignore
                **kwargs,
            )
            if getattr(response, "stop_reason", None) != "pause_turn":
                return response
            chat_messages.append({"role": "assistant", "content": response.content})

    def _collect_streaming_response(
        self,
        chat_messages: List[Any],
        request_kwargs: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]],
    ) -> Union[AnthropicMessage, BetaMessage]:
        """Stream and collect the final message object.

        Used when Anthropic requires streaming (high ``max_tokens``, long-running
        tool calls, etc.). Resumes automatically on advisor ``pause_turn``.
        """
        use_beta = self._uses_beta_messages_api(tools)
        betas = self._get_betas(tools)
        client = self.get_client()

        stream_api = client.beta.messages.stream if use_beta else client.messages.stream
        kwargs = dict(request_kwargs, betas=betas) if (use_beta and betas) else dict(request_kwargs)
        if not self._sampling_params_allowed():
            self._strip_sampling_params(kwargs)

        while True:
            with stream_api(
                model=self.id,
                messages=chat_messages,  # type: ignore
                **kwargs,
            ) as stream:
                response = stream.get_final_message()
            if getattr(response, "stop_reason", None) != "pause_turn":
                return response
            chat_messages.append({"role": "assistant", "content": response.content})

    async def _acollect_streaming_response(
        self,
        chat_messages: List[Any],
        request_kwargs: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]],
    ) -> Union[AnthropicMessage, BetaMessage]:
        """Async version of :meth:`_collect_streaming_response`."""
        use_beta = self._uses_beta_messages_api(tools)
        betas = self._get_betas(tools)
        client = self.get_async_client()

        stream_api = client.beta.messages.stream if use_beta else client.messages.stream
        kwargs = dict(request_kwargs, betas=betas) if (use_beta and betas) else dict(request_kwargs)
        if not self._sampling_params_allowed():
            self._strip_sampling_params(kwargs)

        while True:
            async with stream_api(
                model=self.id,
                messages=chat_messages,  # type: ignore
                **kwargs,
            ) as stream:
                response = await stream.get_final_message()
            if getattr(response, "stop_reason", None) != "pause_turn":
                return response
            chat_messages.append({"role": "assistant", "content": response.content})

    def _uses_automatic_history_cache(self) -> bool:
        """True when history caching should use Anthropic's automatic caching
        (a single top-level ``cache_control`` field) rather than Buddy's
        hand-computed breakpoint. See ``PromptCacheConfig.cache_history_mode``.
        """
        cfg = self.prompt_cache_config
        return bool(
            cfg and cfg.enabled and cfg.cache_history and cfg.cache_history_mode != "explicit"
        )

    def _prepare_request_kwargs(
        self, system_message: str, tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Prepare the request keyword arguments for the API call.

        Args:
            system_message (str): The concatenated system messages.
            tools: Tool definitions (advisor tool will be injected if configured).

        Returns:
            Dict[str, Any]: The request keyword arguments.
        """
        # Prepend the advisor system-prompt block when an advisor is configured.
        if self.advisor is not None:
            advisor_sp = self.advisor.get_system_prompt()
            if advisor_sp:
                system_message = (advisor_sp + "\n\n" + system_message).strip()

        # Inject model-level system-prompt fragments (multilingual, effort, thinking, citations).
        # For Claude, thinking and effort use native API params — only inject prompts for
        # models/features that don't have a native parameter.
        model_fragments = []
        multilingual_hint = self._get_multilingual_system_prompt()
        if multilingual_hint:
            model_fragments.append(multilingual_hint)
        # Effort: only inject prompt hint if effort is not natively supported
        if self.effort is not None and not self.effort.is_default():
            if self.effort.to_claude_output_config(self.id) is None and self.effort.inject_prompt:
                hint = self.effort.to_prompt_hint()
                if hint:
                    model_fragments.append(hint)
        # Thinking: only inject prompt hint if thinking_config is set but not natively applied
        if self.thinking_config is not None and self.thinking is None:
            tc_param = self.thinking_config.to_claude_param(self.id)
            if tc_param is None and self.thinking_config.inject_prompt:
                hint = self.thinking_config.to_prompt_hint()
                if hint:
                    model_fragments.append(hint)
        # Citation prompt hint (for non-native citation scenarios)
        citation_hint = self._get_citation_system_prompt()
        if citation_hint:
            model_fragments.append(citation_hint)

        if model_fragments:
            prefix = "\n\n".join(model_fragments)
            system_message = (prefix + "\n\n" + system_message).strip() if system_message else prefix

        request_kwargs = self.get_request_params().copy()
        if self._uses_automatic_history_cache():
            # Anthropic automatic caching: a single top-level cache_control
            # field. The API applies the breakpoint to the last cacheable
            # block and moves it forward on its own as messages accumulate —
            # no need to walk the message list ourselves. Composes with the
            # explicit system/tools breakpoints below (uses one of the
            # remaining cache-breakpoint slots).
            request_kwargs["cache_control"] = self.prompt_cache_config.cache_control
        if system_message:
            should_cache_system = self.cache_system_prompt or (
                self.prompt_cache_config
                and self.prompt_cache_config.enabled
                and self.prompt_cache_config.cache_system
            )
            if should_cache_system:
                cache_ctrl = (
                    self.prompt_cache_config.cache_control
                    if self.prompt_cache_config
                    else ({"type": "ephemeral", "ttl": "1h"} if self.extended_cache_time else {"type": "ephemeral"})
                )
                request_kwargs["system"] = [{"text": system_message, "type": "text", "cache_control": cache_ctrl}]
            else:
                request_kwargs["system"] = [{"text": system_message, "type": "text"}]

        if tools:
            formatted_tools = self._format_tools_for_model(tools)
            # When caching is enabled, attach cache_control to the last tool
            # entry so Anthropic caches the entire tools prefix in one breakpoint.
            if formatted_tools and (self.cache_tools or (self.prompt_cache_config and self.prompt_cache_config.cache_tools)):
                cache_ctrl = (
                    self.prompt_cache_config.cache_control
                    if self.prompt_cache_config
                    else ({"type": "ephemeral", "ttl": "1h"} if self.extended_cache_time else {"type": "ephemeral"})
                )
                formatted_tools[-1] = dict(formatted_tools[-1])
                formatted_tools[-1]["cache_control"] = cache_ctrl
            request_kwargs["tools"] = formatted_tools

        # Last-line defense: sampling params must never leave this method for
        # models / thinking modes that Anthropic rejects them on.
        if not self._sampling_params_allowed():
            self._strip_sampling_params(request_kwargs, warn=True)

        if request_kwargs:
            log_debug(f"Calling {self.provider} with request parameters: {request_kwargs}", log_level=2)
        return request_kwargs

    def _apply_history_cache(self, chat_messages: List[Any]) -> List[Any]:
        """Inject a history cache breakpoint when prompt caching is enabled.

        No-op when history caching is on "auto" mode — the top-level
        ``cache_control`` field added in ``_prepare_request_kwargs`` already
        tells Anthropic to manage the breakpoint automatically, so hand-
        computing one here would just waste one of the 4 available slots.
        """
        cfg = self.prompt_cache_config
        if not cfg or not cfg.enabled or not cfg.cache_history:
            return chat_messages
        if self._uses_automatic_history_cache():
            return chat_messages
        from buddy.models.cache import inject_anthropic_cache_breakpoints

        return inject_anthropic_cache_breakpoints(chat_messages, cfg)

    def _sanitize_json_schema(self, schema: Any) -> Dict[str, Any]:
        """Normalize a JSON schema for Anthropic tool ``input_schema`` (draft 2020-12).

        Fixes common Buddy/OpenAI schema issues that Claude rejects:
        empty ``type`` strings, arrays without ``items``, bare ``**kwargs``
        properties, and unresolved ``$ref``/``$defs`` leftovers.
        """
        if not isinstance(schema, dict):
            return {"type": "object", "properties": {}}

        out: Dict[str, Any] = {}

        # Copy scalar / simple keys Anthropic accepts
        for key in (
            "type",
            "description",
            "enum",
            "const",
            "default",
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "minLength",
            "maxLength",
            "pattern",
            "format",
            "minItems",
            "maxItems",
            "uniqueItems",
            "title",
        ):
            if key in schema and schema[key] != "":
                out[key] = schema[key]

        # Empty type string is invalid — drop it
        if out.get("type") == "":
            out.pop("type", None)

        for key in ("anyOf", "oneOf", "allOf"):
            if key in schema and isinstance(schema[key], list):
                cleaned = [
                    self._sanitize_json_schema(sub) for sub in schema[key] if isinstance(sub, dict)
                ]
                if cleaned:
                    out[key] = cleaned

        if "additionalProperties" in schema:
            ap = schema["additionalProperties"]
            if isinstance(ap, bool):
                out["additionalProperties"] = ap
            elif isinstance(ap, dict):
                out["additionalProperties"] = self._sanitize_json_schema(ap)

        if "properties" in schema and isinstance(schema["properties"], dict):
            props: Dict[str, Any] = {}
            for name, prop in schema["properties"].items():
                if not isinstance(prop, dict):
                    continue
                cleaned = self._sanitize_json_schema(prop)
                # Drop useless props (e.g. **kwargs → {})
                meaningful = set(cleaned.keys()) - {"description"}
                if not meaningful:
                    continue
                if "type" not in cleaned and "anyOf" not in cleaned and "oneOf" not in cleaned and "enum" not in cleaned:
                    if "properties" in cleaned or "additionalProperties" in cleaned:
                        cleaned["type"] = "object"
                    else:
                        cleaned["type"] = "string"
                props[name] = cleaned
            out["properties"] = props

        if "items" in schema:
            items = schema["items"]
            if isinstance(items, dict):
                out["items"] = self._sanitize_json_schema(items)
            elif isinstance(items, list) and items:
                # draft-04 tuple → use first schema as items
                out["items"] = self._sanitize_json_schema(items[0])
            else:
                out["items"] = {"type": "string"}

        # Arrays must declare items (draft 2020-12)
        if out.get("type") == "array" and "items" not in out:
            out["items"] = {"type": "string"}

        if "required" in schema and isinstance(schema["required"], list):
            props = out.get("properties") or {}
            out["required"] = [r for r in schema["required"] if isinstance(r, str) and r in props]

        # Object schemas need a type
        if "properties" in out and "type" not in out and "anyOf" not in out and "oneOf" not in out:
            out["type"] = "object"

        return out

    def _format_tools_for_model(self, tools: Optional[List[Dict[str, Any]]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Transforms function definitions into a format accepted by the Anthropic API.
        """
        if not tools:
            return None

        parsed_tools: List[Dict[str, Any]] = []
        for tool_def in tools:
            if tool_def.get("type", "") != "function":
                # Pass through provider built-in / server tools as-is
                parsed_tools.append(tool_def)
                continue

            func_def = tool_def.get("function", {}) or {}
            parameters: Dict[str, Any] = func_def.get("parameters") or {
                "type": "object",
                "properties": {},
            }
            input_schema = self._sanitize_json_schema(parameters)
            if input_schema.get("type") not in (None, "object") and "properties" in input_schema:
                input_schema["type"] = "object"
            if "type" not in input_schema:
                input_schema["type"] = "object"
            if "properties" not in input_schema:
                input_schema["properties"] = {}

            name = func_def.get("name") or ""
            description = (func_def.get("description") or "").strip() or name
            tool = {
                "name": name,
                "description": description,
                "input_schema": input_schema,
            }
            parsed_tools.append(tool)
        return parsed_tools

    def invoke(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Union[AnthropicMessage, BetaMessage]:
        """
        Send a request to the Anthropic API to generate a response.
        """
        chat_messages: List[Any] = []
        request_kwargs: Dict[str, Any] = {}
        try:
            tools = self._inject_advisor_tool(tools)
            chat_messages, system_message = format_messages(messages)
            request_kwargs = self._prepare_request_kwargs(system_message, tools)
            chat_messages = self._apply_history_cache(chat_messages)

            # High max_tokens: Anthropic SDK rejects non-streaming create(); use
            # stream + get_final_message up front to avoid the fallback warning.
            if self._requires_streaming(request_kwargs.get("max_tokens")):
                return self._collect_streaming_response(
                    chat_messages=chat_messages,
                    request_kwargs=request_kwargs,
                    tools=tools,
                )

            return self._create_message_response(
                client=self.get_client(),
                chat_messages=chat_messages,
                request_kwargs=request_kwargs,
                tools=tools,
            )
        except APIConnectionError as e:
            log_error(f"Connection error while calling Claude API: {str(e)}")
            raise ModelProviderError(message=e.message, model_name=self.name, model_id=self.id) from e
        except RateLimitError as e:
            log_warning(f"Rate limit exceeded: {str(e)}")
            raise ModelRateLimitError(message=e.message, model_name=self.name, model_id=self.id) from e
        except APIStatusError as e:
            # Safety net: SDK/API may still require streaming in edge cases.
            if "Streaming is required" in (getattr(e, "message", None) or str(e)):
                log_debug(
                    "Anthropic requires streaming for this operation. "
                    "Automatically falling back to streaming mode."
                )
                try:
                    return self._collect_streaming_response(
                        chat_messages=chat_messages,
                        request_kwargs=request_kwargs,
                        tools=tools,
                    )
                except Exception as stream_exc:
                    log_error(f"Streaming fallback also failed: {stream_exc}")
                    raise ModelProviderError(message=str(stream_exc), model_name=self.name, model_id=self.id) from stream_exc
            log_error(f"Claude API error (status {e.status_code}): {str(e)}")
            raise ModelProviderError(
                message=e.message, status_code=e.status_code, model_name=self.name, model_id=self.id
            ) from e
        except Exception as e:
            # Anthropic may raise a non-APIStatusError when streaming is required
            # (e.g. from newer SDK versions or beta endpoints).  Handle it here too.
            if "Streaming is required" in str(e):
                log_debug(
                    "Anthropic requires streaming for this operation. "
                    "Automatically falling back to streaming mode."
                )
                try:
                    return self._collect_streaming_response(
                        chat_messages=chat_messages,
                        request_kwargs=request_kwargs,
                        tools=tools,
                    )
                except Exception as stream_exc:
                    log_error(f"Streaming fallback also failed: {stream_exc}")
                    raise ModelProviderError(message=str(stream_exc), model_name=self.name, model_id=self.id) from stream_exc
            log_error(f"Unexpected error calling Claude API: {str(e)}")
            raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e

    def invoke_stream(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Any:
        """
        Stream a response from the Anthropic API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Any: The streamed response from the model.

        Raises:
            APIConnectionError: If there are network connectivity issues
            RateLimitError: If the API rate limit is exceeded
            APIStatusError: For other API-related errors
        """
        tools = self._inject_advisor_tool(tools)
        chat_messages, system_message = format_messages(messages)
        request_kwargs = self._prepare_request_kwargs(system_message, tools)
        chat_messages = self._apply_history_cache(chat_messages)
        betas = self._get_betas(tools)

        try:
            use_beta = self._uses_beta_messages_api(tools)
            stream_api = (
                self.get_client().beta.messages.stream
                if use_beta
                else self.get_client().messages.stream
            )
            kwargs = dict(request_kwargs, betas=betas) if (use_beta and betas) else dict(request_kwargs)
            if not self._sampling_params_allowed():
                self._strip_sampling_params(kwargs)
            return stream_api(
                model=self.id,
                messages=chat_messages,  # type: ignore
                **kwargs,
            ).__enter__()
        except APIConnectionError as e:
            log_error(f"Connection error while calling Claude API: {str(e)}")
            raise ModelProviderError(message=e.message, model_name=self.name, model_id=self.id) from e
        except RateLimitError as e:
            log_warning(f"Rate limit exceeded: {str(e)}")
            raise ModelRateLimitError(message=e.message, model_name=self.name, model_id=self.id) from e
        except APIStatusError as e:
            log_error(f"Claude API error (status {e.status_code}): {str(e)}")
            raise ModelProviderError(
                message=e.message, status_code=e.status_code, model_name=self.name, model_id=self.id
            ) from e
        except Exception as e:
            log_error(f"Unexpected error calling Claude API: {str(e)}")
            raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e

    async def ainvoke(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Union[AnthropicMessage, BetaMessage]:
        """
        Send an asynchronous request to the Anthropic API to generate a response.
        """
        chat_messages: List[Any] = []
        request_kwargs: Dict[str, Any] = {}
        try:
            tools = self._inject_advisor_tool(tools)
            chat_messages, system_message = format_messages(messages)
            request_kwargs = self._prepare_request_kwargs(system_message, tools)
            chat_messages = self._apply_history_cache(chat_messages)

            # High max_tokens: Anthropic SDK rejects non-streaming create(); use
            # stream + get_final_message up front to avoid the fallback warning.
            if self._requires_streaming(request_kwargs.get("max_tokens")):
                return await self._acollect_streaming_response(
                    chat_messages=chat_messages,
                    request_kwargs=request_kwargs,
                    tools=tools,
                )

            client = self.get_async_client()
            use_beta = self._uses_beta_messages_api(tools)
            betas = self._get_betas(tools)
            while True:
                create = client.beta.messages.create if use_beta else client.messages.create
                kwargs = dict(request_kwargs, betas=betas) if (use_beta and betas) else dict(request_kwargs)
                if not self._sampling_params_allowed():
                    self._strip_sampling_params(kwargs)
                response = await create(
                    model=self.id,
                    messages=chat_messages,  # type: ignore
                    **kwargs,
                )
                if getattr(response, "stop_reason", None) != "pause_turn":
                    return response
                chat_messages.append({"role": "assistant", "content": response.content})
        except APIConnectionError as e:
            log_error(f"Connection error while calling Claude API: {str(e)}")
            raise ModelProviderError(message=e.message, model_name=self.name, model_id=self.id) from e
        except RateLimitError as e:
            log_warning(f"Rate limit exceeded: {str(e)}")
            raise ModelRateLimitError(message=e.message, model_name=self.name, model_id=self.id) from e
        except APIStatusError as e:
            # Safety net: SDK/API may still require streaming in edge cases.
            if "Streaming is required" in (getattr(e, "message", None) or str(e)):
                log_debug(
                    "Anthropic requires streaming for this operation. "
                    "Automatically falling back to streaming mode."
                )
                try:
                    return await self._acollect_streaming_response(
                        chat_messages=chat_messages,
                        request_kwargs=request_kwargs,
                        tools=tools,
                    )
                except Exception as stream_exc:
                    log_error(f"Streaming fallback also failed: {stream_exc}")
                    raise ModelProviderError(message=str(stream_exc), model_name=self.name, model_id=self.id) from stream_exc
            log_error(f"Claude API error (status {e.status_code}): {str(e)}")
            raise ModelProviderError(
                message=e.message, status_code=e.status_code, model_name=self.name, model_id=self.id
            ) from e
        except Exception as e:
            # Anthropic may raise a non-APIStatusError when streaming is required
            # (e.g. from newer SDK versions or beta endpoints).  Handle it here too.
            if "Streaming is required" in str(e):
                log_debug(
                    "Anthropic requires streaming for this operation. "
                    "Automatically falling back to streaming mode."
                )
                try:
                    return await self._acollect_streaming_response(
                        chat_messages=chat_messages,
                        request_kwargs=request_kwargs,
                        tools=tools,
                    )
                except Exception as stream_exc:
                    log_error(f"Streaming fallback also failed: {stream_exc}")
                    raise ModelProviderError(message=str(stream_exc), model_name=self.name, model_id=self.id) from stream_exc
            log_error(f"Unexpected error calling Claude API: {str(e)}")
            raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e

    async def ainvoke_stream(
        self,
        messages: List[Message],
        response_format: Optional[Union[Dict, Type[BaseModel]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> AsyncIterator[Any]:
        """
        Stream an asynchronous response from the Anthropic API.

        Args:
            messages (List[Message]): A list of messages to send to the model.

        Returns:
            Any: The streamed response from the model.

        Raises:
            APIConnectionError: If there are network connectivity issues
            RateLimitError: If the API rate limit is exceeded
            APIStatusError: For other API-related errors
        """
        try:
            tools = self._inject_advisor_tool(tools)
            chat_messages, system_message = format_messages(messages)
            request_kwargs = self._prepare_request_kwargs(system_message, tools)
            chat_messages = self._apply_history_cache(chat_messages)
            betas = self._get_betas(tools)

            use_beta = self._uses_beta_messages_api(tools)
            stream_api = (
                self.get_async_client().beta.messages.stream
                if use_beta
                else self.get_async_client().messages.stream
            )
            kwargs = dict(request_kwargs, betas=betas) if (use_beta and betas) else dict(request_kwargs)
            if not self._sampling_params_allowed():
                self._strip_sampling_params(kwargs)
            async with stream_api(
                model=self.id,
                messages=chat_messages,  # type: ignore
                **kwargs,
            ) as stream:
                async for chunk in stream:  # type: ignore
                    yield chunk
        except APIConnectionError as e:
            log_error(f"Connection error while calling Claude API: {str(e)}")
            raise ModelProviderError(message=e.message, model_name=self.name, model_id=self.id) from e
        except RateLimitError as e:
            log_warning(f"Rate limit exceeded: {str(e)}")
            raise ModelRateLimitError(message=e.message, model_name=self.name, model_id=self.id) from e
        except APIStatusError as e:
            log_error(f"Claude API error (status {e.status_code}): {str(e)}")
            raise ModelProviderError(
                message=e.message, status_code=e.status_code, model_name=self.name, model_id=self.id
            ) from e
        except Exception as e:
            log_error(f"Unexpected error calling Claude API: {str(e)}")
            raise ModelProviderError(message=str(e), model_name=self.name, model_id=self.id) from e

    def format_function_call_results(self, messages: List[Message], function_call_results: List[Message]) -> None:
        """
        Handle the results of function calls.

        Formats Claude ``tool_result`` blocks per
        https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls :
        ``tool_use_id``, ``content``, and ``is_error`` when execution failed.
        All tool_result blocks are placed in a single user message that
        immediately follows the assistant tool_use turn.

        Args:
            messages (List[Message]): The list of conversation messages.
            function_call_results (List[Message]): The results of the function calls.
        """
        if len(function_call_results) > 0:
            if self.token_budget is not None:
                function_call_results = self._trim_tool_results(function_call_results)
            fc_responses: List = []
            for _fc_message in function_call_results:
                block: Dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": _fc_message.tool_call_id,
                    "content": str(_fc_message.content) if _fc_message.content is not None else "",
                }
                # Signal errors so Claude can recover / retry (docs: is_error)
                if _fc_message.tool_call_error:
                    block["is_error"] = True
                fc_responses.append(block)
            messages.append(Message(role="user", content=fc_responses))

    def get_system_message_for_model(self, tools: Optional[List[Any]] = None) -> Optional[str]:
        if tools is not None and len(tools) > 0:
            tool_call_prompt = "Do not reflect on the quality of the returned search results in your response\n\n"
            return tool_call_prompt
        return None

    def parse_provider_response(self, response: AnthropicMessage, **kwargs) -> ModelResponse:
        """
        Parse the Claude response into a ModelResponse.

        Args:
            response: Raw response from Anthropic

        Returns:
            ModelResponse: Parsed response data
        """
        model_response = ModelResponse()

        # Add role (Claude always uses 'assistant')
        model_response.role = response.role or "assistant"

        if response.content:
            for block in response.content:
                if block.type == "text":
                    if model_response.content is None:
                        model_response.content = block.text
                    else:
                        model_response.content += block.text

                    # Capture citations from the response
                    if block.citations is not None:
                        if model_response.citations is None:
                            model_response.citations = Citations(raw=[], urls=[], documents=[])
                        for citation in block.citations:
                            model_response.citations.raw.append(citation.model_dump())  # type: ignore
                            # Web search citations
                            if isinstance(citation, CitationsWebSearchResultLocation):
                                model_response.citations.urls.append(  # type: ignore
                                    UrlCitation(url=citation.url, title=citation.cited_text)
                                )
                            # Document citations
                            elif isinstance(citation, CitationPageLocation):
                                model_response.citations.documents.append(  # type: ignore
                                    DocumentCitation(
                                        document_title=citation.document_title,
                                        cited_text=citation.cited_text,
                                    )
                                )
                elif block.type == "thinking":
                    model_response.thinking = block.thinking
                    model_response.provider_data = {
                        "signature": block.signature,
                    }
                elif block.type == "redacted_thinking":
                    model_response.redacted_thinking = block.data

        # Extract tool calls from the response
        if response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    function_def = {"name": tool_name}
                    if tool_input:
                        function_def["arguments"] = json.dumps(tool_input)

                    model_response.extra = model_response.extra or {}
                    model_response.tool_calls.append(
                        {
                            "id": block.id,
                            "type": "function",
                            "function": function_def,
                        }
                    )

        # --- Streaming / streaming-classifier refusal handling ---
        # When stop_reason="refusal" the model declined the request due to a
        # policy violation detected by streaming classifiers.  We surface this
        # via model_response.stop_reason so callers can detect and handle it.
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            stop_details = getattr(response, "stop_details", None)
            category = getattr(stop_details, "category", None) if stop_details else None
            explanation = getattr(stop_details, "explanation", None) if stop_details else None
            model_response.extra = model_response.extra or {}
            model_response.extra["refusal"] = {
                "stop_reason": "refusal",
                "category": category,
                "explanation": explanation,
            }
            if self.handle_streaming_refusals:
                log_warning(
                    f"Claude refusal detected (category={category!r}): {explanation or 'No explanation provided'}. "
                    "Reset conversation context before retrying."
                )

        # Add usage metrics
        if response.usage is not None:
            usage_dict = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

            if hasattr(response.usage, "cache_creation_input_tokens") and response.usage.cache_creation_input_tokens:
                usage_dict["cache_write_tokens"] = response.usage.cache_creation_input_tokens

            if hasattr(response.usage, "cache_read_input_tokens") and response.usage.cache_read_input_tokens:
                usage_dict["cached_tokens"] = response.usage.cache_read_input_tokens

            model_response.response_usage = usage_dict

        return model_response

    def parse_provider_response_delta(
        self, response: Union[ContentBlockStartEvent, ContentBlockDeltaEvent, ContentBlockStopEvent, MessageStopEvent]
    ) -> ModelResponse:
        """
        Parse the Claude streaming response into ModelProviderResponse objects.

        Handles both stable ``messages.stream`` events and beta
        ``beta.messages.stream`` events (advisor / MCP). Beta stop events are
        different classes (``ParsedBetaContentBlockStopEvent`` etc.), so tool_use
        must be detected via duck-typing on ``content_block``.
        """
        model_response = ModelResponse()
        content_block = getattr(response, "content_block", None)
        delta = getattr(response, "delta", None)
        cls_name = type(response).__name__
        is_block_start = isinstance(response, ContentBlockStartEvent) or "ContentBlockStart" in cls_name
        is_block_stop = isinstance(response, ContentBlockStopEvent) or "ContentBlockStop" in cls_name
        is_message_stop = isinstance(response, MessageStopEvent) or cls_name.endswith("MessageStopEvent")

        if is_block_start and content_block is not None:
            if getattr(content_block, "type", None) == "redacted_thinking":
                model_response.redacted_thinking = getattr(content_block, "data", None)

        # content_block_delta (stable types OR beta via attributes)
        if delta is not None:
            dtype = getattr(delta, "type", None)
            if dtype == "text_delta":
                text = getattr(delta, "text", None)
                if text is not None:
                    model_response.content = text
            elif dtype == "thinking_delta":
                thinking = getattr(delta, "thinking", None)
                if thinking is not None:
                    model_response.thinking = thinking
            elif dtype == "signature_delta":
                signature = getattr(delta, "signature", None)
                if signature is not None:
                    model_response.provider_data = {"signature": signature}

        # Only finalize tool_use / thinking on STOP — start events also carry
        # type=tool_use with empty input and would duplicate the call.
        if is_block_stop and content_block is not None:
            block_type = getattr(content_block, "type", None)
            if block_type == "thinking":
                thinking = getattr(content_block, "thinking", None)
                if thinking is not None:
                    model_response.thinking = thinking
                if hasattr(content_block, "signature") and content_block.signature:
                    model_response.provider_data = {"signature": content_block.signature}
            elif block_type == "tool_use":
                tool_name = getattr(content_block, "name", None)
                tool_input = getattr(content_block, "input", None) or {}
                tool_id = getattr(content_block, "id", None)
                if tool_name and tool_id:
                    function_def: Dict[str, Any] = {"name": tool_name}
                    function_def["arguments"] = json.dumps(tool_input) if tool_input else "{}"
                    model_response.extra = model_response.extra or {}
                    model_response.tool_calls = [
                        {
                            "id": tool_id,
                            "type": "function",
                            "function": function_def,
                        }
                    ]

        # Citations from final message_stop (stable or beta)
        message = getattr(response, "message", None)
        if is_message_stop and message is not None:
            model_response.content = model_response.content or ""
            model_response.citations = Citations(raw=[], urls=[], documents=[])
            for block in getattr(message, "content", None) or []:
                citations = getattr(block, "citations", None)
                if not citations:
                    continue
                for citation in citations:
                    model_response.citations.raw.append(citation.model_dump())  # type: ignore
                    if isinstance(citation, CitationsWebSearchResultLocation):
                        model_response.citations.urls.append(UrlCitation(url=citation.url, title=citation.cited_text))  # type: ignore
                    elif isinstance(citation, CitationPageLocation):
                        model_response.citations.documents.append(  # type: ignore
                            DocumentCitation(document_title=citation.document_title, cited_text=citation.cited_text)
                        )

        if hasattr(response, "usage") and response.usage is not None:
            usage_dict = {
                "input_tokens": response.usage.input_tokens or 0,
                "output_tokens": response.usage.output_tokens or 0,
            }

            if hasattr(response.usage, "cache_creation_input_tokens") and response.usage.cache_creation_input_tokens:
                usage_dict["cache_write_tokens"] = response.usage.cache_creation_input_tokens

            if hasattr(response.usage, "cache_read_input_tokens") and response.usage.cache_read_input_tokens:
                usage_dict["cached_tokens"] = response.usage.cache_read_input_tokens

            model_response.response_usage = usage_dict

        # --- Streaming refusal detection on message_delta events ---
        # Starting with Claude 4 models, stop_reason="refusal" can arrive on
        # message_delta events during streaming.  Capture it so the agent layer
        # can reset conversation context.
        if delta is not None:
            stream_stop_reason = getattr(delta, "stop_reason", None)
            if stream_stop_reason == "refusal" and self.handle_streaming_refusals:
                stop_details = getattr(delta, "stop_details", None)
                category = getattr(stop_details, "category", None) if stop_details else None
                explanation = getattr(stop_details, "explanation", None) if stop_details else None
                model_response.extra = model_response.extra or {}
                model_response.extra["refusal"] = {
                    "stop_reason": "refusal",
                    "category": category,
                    "explanation": explanation,
                }
                log_warning(
                    f"Streaming refusal detected (category={category!r}): "
                    f"{explanation or 'No explanation provided'}. "
                    "Reset conversation context before retrying."
                )

        # Beta text deltas (advisor / MCP stream) — keep legacy path as fallback
        try:
            if (
                isinstance(response, BetaRawContentBlockDeltaEvent)
                and isinstance(response.delta, BetaTextDelta)
                and response.delta.text is not None
                and not model_response.content
            ):
                model_response.content = response.delta.text
        except Exception as e:
            log_error(f"Error parsing Beta response: {e}")

        return model_response

