# Prompt Caching

Prompt caching dramatically reduces cost and latency for agents that reuse the
same large context across multiple turns — a long system prompt, a big tool
list, or a growing conversation history.

Buddy AI builds caching in at the model layer, so you activate it with a
single flag rather than manually inserting provider-specific headers.

---

## Quick start

```python
from buddy.agent import Agent
from buddy.models.anthropic import Claude
from buddy.models.openai import OpenAIChat

# Anthropic — explicit cache breakpoints injected automatically
agent = Agent(
    model=Claude(id="claude-opus-4-5"),
    cache_prompt=True,
)

# OpenAI — server-side automatic caching (no flag needed for caching itself,
# but setting cache_prompt=True surfaces cache hit/miss metrics)
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    cache_prompt=True,
)
```

That's it. No changes to your prompts, tools, or run loop.

---

## How it works by provider

### Anthropic (Claude)

Anthropic's Prompt Caching API lets you mark up to **4 cache breakpoints** per
request. Buddy automatically places them on the segments that change least
often, in priority order:

| Breakpoint | Flag | Default |
|---|---|---|
| System prompt | `cache_system` | ✅ enabled |
| Tools list | `cache_tools` | ✅ enabled |
| Stable conversation history | `cache_history` | ✅ enabled |

A 5-minute **ephemeral** TTL is used by default.  You can extend it to **1 hour**:

```python
from buddy.models.cache import PromptCacheConfig

agent = Agent(
    model=Claude(id="claude-opus-4-5"),
    cache_prompt=True,
    model=Claude(
        id="claude-opus-4-5",
        prompt_cache_config=PromptCacheConfig(
            enabled=True,
            cache_system=True,
            cache_tools=True,
            cache_history=True,
            ttl="1h",          # requires claude-3-5-sonnet-20241022+
        ),
    ),
)
```

> **Minimum cacheable prefix**: 1 024 tokens for Sonnet; 2 048 for Haiku.
> Short prompts won't be cached even with the flag set — Anthropic silently
> ignores breakpoints that fall below the minimum.

#### Cost savings

Anthropic charges **~10 %** of the normal input-token price for a cache hit and
**~125 %** for the one-time cache write.  On a 10 000-token system prompt with
20 turns you save roughly **90 %** of prompt-token costs after the first turn.

### OpenAI (GPT-4o, GPT-4o-mini, o-series)

OpenAI caches the **longest matching prefix** of any repeated request
automatically — no client-side header required.  The minimum cacheable prefix
is **1 024 tokens** and the cache key is based on exact token sequence.

Setting `cache_prompt=True` on an OpenAI agent:

- Does **not** change the API request (no `cache_control` headers are sent).
- Ensures `cached_tokens` from the response usage details are captured in
  `RunResponse.metrics` and `session_metrics`.

Tips for maximising OpenAI cache hits:

- Keep the **system prompt and tool list stable** across turns.
- Use a fixed `seed` value to improve prefix consistency.
- Minimise changes to early messages in the conversation history.

---

## Fine-grained control with `PromptCacheConfig`

For cases where you only want to cache *some* segments, pass a
`PromptCacheConfig` directly to the model:

```python
from buddy.models.cache import PromptCacheConfig
from buddy.models.anthropic import Claude

model = Claude(
    id="claude-3-5-sonnet-20241022",
    prompt_cache_config=PromptCacheConfig(
        enabled=True,
        cache_system=True,   # cache the (often large) system prompt
        cache_tools=False,   # tools change per request — don't cache
        cache_history=True,  # cache stable history prefix
        ttl="ephemeral",     # "ephemeral" (5 min) or "1h"
    ),
)

agent = Agent(model=model, cache_prompt=True)
```

---

## Reading cache metrics

Cache token counts are available in `RunResponse.metrics`:

```python
response = agent.run("Summarise the document.")

metrics = response.metrics
print("Input tokens      :", sum(metrics.get("input_tokens", [])))
print("Cache write tokens:", sum(metrics.get("cache_write_tokens", [])))
print("Cache read tokens :", sum(metrics.get("cached_tokens", [])))
```

Or on the cumulative `session_metrics` after multiple turns:

```python
sm = agent.session_metrics
print(f"Total cached tokens this session: {sm.cached_tokens}")
print(f"Total cache writes this session : {sm.cache_write_tokens}")
```

---

## Example: long multi-turn conversation

```python
from buddy.agent import Agent
from buddy.models.anthropic import Claude

SYSTEM = """
You are an expert legal assistant.  The following is the full text of the
contract you must analyse (50 pages, ~40 000 tokens):

[... full contract text ...]
"""

agent = Agent(
    model=Claude(id="claude-opus-4-5"),
    system_prompt=SYSTEM,
    cache_prompt=True,   # system + tools + history all cached
    add_history_to_messages=True,
    num_history_runs=10,
)

for question in [
    "What are the termination clauses?",
    "Summarise the payment terms.",
    "Are there any non-compete provisions?",
]:
    r = agent.run(question)
    print(r.content)
    # From turn 2 onward the 40 000-token system prompt is served from cache
    # at ~10 % of the normal input price.
```

---

## Compatibility matrix

| Provider | Automatic server-side | Explicit breakpoints | 1-hour TTL |
|---|---|---|---|
| Anthropic (Claude 3+) | ❌ | ✅ | ✅ (Sonnet 20241022+) |
| OpenAI (GPT-4o+) | ✅ | ❌ | N/A |
| AWS Bedrock (Claude) | ❌ | ✅ (inherits) | ✅ |
| Google Gemini | automatic context caching | — | session-based |
| Others | — | — | — |

---

## FAQ

**Does enabling `cache_prompt` change the model's output?**
No. Cache hits return identical outputs to uncached calls — the cache stores
the processed KV representation of the tokens, not a generated response.

**Will it slow down the first request?**
The very first request incurs a small **cache write overhead** (~125 % of normal
input price on Anthropic).  From the second request onward you save ~90 %.

**What happens if the context changes between turns?**
Anthropic matches the longest unchanged prefix.  If you add a new user message,
the system + tools + history before it are still served from cache; only the new
tokens are processed fresh.

**Can I use `cache_prompt` in a streaming response?**
Yes — `invoke_stream` / `ainvoke_stream` apply the same breakpoints.
