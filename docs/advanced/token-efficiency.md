# Token Efficiency

Buddy AI gives you several layered techniques to reduce token usage, API costs,
and latency — from provider-native prompt caching to automatic context
compression.  All techniques compose: you can enable any combination.

---

## Technique 1 — Prompt Caching

The fastest, cheapest win.  See the dedicated [Prompt Caching](prompt-caching.md)
guide.

```python
# Works on both Claude and GPT-4o — one flag
agent = Agent(model=Claude(id="claude-opus-4-5"), cache_prompt=True)
```

---

## Technique 2 — Proxy-Aware Caching

When your company routes LLM traffic through a proxy (LiteLLM, OpenRouter,
Azure AI Gateway), Buddy automatically injects the right cache headers so the
proxy's own caching layer fires too — **even for Claude models served through
an OpenAI-compatible endpoint**.

```python
from buddy.models.openai import OpenAIChat

# Claude behind a LiteLLM proxy
model = OpenAIChat(
    id="anthropic/claude-opus-4-5",
    base_url="http://0.0.0.0:4000/v1",
    api_key="sk-my-litellm-key",
    proxy_type="litellm",   # injects {"cache": {"no-cache": False}}
    cache_prompt=True,
)

# Any model behind OpenRouter
model = OpenAIChat(
    id="anthropic/claude-opus-4-5",
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-...",
    proxy_type="openrouter",  # injects X-OpenRouter-Cache header
    cache_prompt=True,
)

# Azure AI Management
model = OpenAIChat(
    id="gpt-4o",
    base_url="https://my-gateway.azure-api.net/openai",
    proxy_type="azure",     # injects x-ms-cache-enabled header
    cache_prompt=True,
)
```

**Supported `proxy_type` values:**

| Value | Cache mechanism | Reference |
|---|---|---|
| `"litellm"` | Redis / in-memory exact-match cache | [LiteLLM caching docs](https://docs.litellm.ai/docs/proxy/caching) |
| `"openrouter"` | OpenRouter context caching | [OpenRouter docs](https://openrouter.ai/docs/context-caching) |
| `"azure"` | Azure API Management cache policy | Azure APIM |
| `None` (default) | Native OpenAI server-side cache | Automatic |

> **Direct Claude key?** Use the `Claude` model directly — it sends explicit
> `cache_control` blocks to Anthropic and is more efficient than going through
> a proxy.

---

## Technique 3 — Token Budget Manager

Set a hard token ceiling on every request.  Buddy counts tokens *before*
sending, warns you as you approach the limit, and automatically drops the
oldest history turns to keep requests within budget.

```python
from buddy.agent import Agent
from buddy.models.openai import OpenAIChat
from buddy.models.token_budget import TokenBudgetConfig

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    add_history_to_messages=True,
    num_history_runs=20,             # keep lots of history...
    token_budget=TokenBudgetConfig(
        max_input_tokens=100_000,    # ...but never exceed this
        target_input_tokens=80_000,  # trim until we're here (default: 90 %)
        auto_compress=True,          # drop oldest turns automatically
        warn_at=0.85,                # log a warning at 85 % usage
        count_method="approx",       # "approx" (fast) or "tiktoken" (exact)
        max_tool_result_tokens=2_000,# also trim oversized tool outputs
    ),
)
```

### Reading budget metrics

```python
response = agent.run("...")
budget = (response.extra_data or {}).get("token_budget", {})
print("Estimated input tokens:", budget.get("estimated_tokens"))
print("After compression:     ", budget.get("tokens_after"))
print("Turns dropped:         ", budget.get("turns_dropped"))
print("Tokens trimmed:        ", budget.get("tokens_trimmed"))
```

### `TokenBudgetConfig` reference

| Field | Default | Description |
|---|---|---|
| `max_input_tokens` | `100_000` | Hard ceiling on input tokens per request |
| `target_input_tokens` | 90 % of max | Compress history down to this level |
| `auto_compress` | `True` | Drop oldest history turns automatically |
| `warn_at` | `0.85` | Warn fraction (0–1); `None` to silence |
| `count_method` | `"approx"` | `"approx"` (len//4) or `"tiktoken"` |
| `max_tool_result_tokens` | `2_000` | Cap per tool result; `None` to disable |

---

## Technique 4 — Automatic Tool-Result Trimming

Long tool outputs (web search results, file reads, API responses) can cost
thousands of tokens per call.  When a `TokenBudgetConfig` is set, Buddy trims
any tool result that exceeds `max_tool_result_tokens` *before* appending it to
the message list, and adds a brief notice so the model knows the output was cut.

```python
# Aggressive trimming — useful for search/scrape tools
token_budget=TokenBudgetConfig(
    max_input_tokens=128_000,
    max_tool_result_tokens=1_000,   # ~4 KB per tool call
)
```

Tool results that fit under the limit are passed through unchanged.

---

## Technique 5 — History Truncation (`num_history_runs`)

The simplest dial: `num_history_runs` (default `3`) controls how many past
conversation turns are appended to each prompt.  Combine with token budget for
best results:

```python
agent = Agent(
    model=...,
    add_history_to_messages=True,
    num_history_runs=5,              # include last 5 turns
    token_budget=TokenBudgetConfig(
        max_input_tokens=60_000,
        auto_compress=True,          # drop turns if 5 is still too many
    ),
)
```

---

## Technique 6 — Session Summaries (instead of raw history)

For very long sessions, Buddy can summarize past context instead of including
raw messages.  This keeps the history compact while preserving meaning:

```python
agent = Agent(
    model=...,
    enable_session_summaries=True,   # generate a rolling summary
    add_history_to_messages=False,   # don't include raw turns
    add_session_summary_references=True,  # inject the summary instead
)
```

---

## Combining all techniques

```python
from buddy.agent import Agent
from buddy.models.anthropic import Claude
from buddy.models.token_budget import TokenBudgetConfig

agent = Agent(
    model=Claude(id="claude-opus-4-5"),

    # --- Prompt caching (saves ~90 % on repeated system/tool prefix) ---
    cache_prompt=True,

    # --- History ---
    add_history_to_messages=True,
    num_history_runs=10,

    # --- Token budget (auto-compress + tool trimming) ---
    token_budget=TokenBudgetConfig(
        max_input_tokens=180_000,    # Claude's 200k window - output reserve
        target_input_tokens=140_000,
        auto_compress=True,
        warn_at=0.80,
        max_tool_result_tokens=1_500,
    ),
)
```

---

## Proxy + Caching decision tree

```
Using Claude?
├── Direct Anthropic key
│   └── Use Claude model + cache_prompt=True  ← BEST: explicit cache_control
└── Through a proxy
    ├── LiteLLM  → OpenAIChat(proxy_type="litellm", cache_prompt=True)
    ├── OpenRouter → OpenAIChat(proxy_type="openrouter", cache_prompt=True)
    └── Azure    → OpenAIChat(proxy_type="azure", cache_prompt=True)

Using GPT-4o?
└── OpenAI server-side auto-caching (no flag needed)
    └── cache_prompt=True surfaces metrics in RunResponse
```

---

## Cost impact at a glance

| Technique | Typical saving | Best for |
|---|---|---|
| Prompt caching (Anthropic) | 60–90 % of prompt cost | Long system prompts, big tool lists |
| Prompt caching (OpenAI auto) | 50 % of cached prefix | Repeated prompts / same user |
| Proxy caching | Full response reuse | Identical queries |
| Token budget compression | Prevents runaway costs | Long multi-turn sessions |
| Tool-result trimming | 30–80 % of tool tokens | Search, scraping, large API responses |
| Session summaries | 70–95 % of history tokens | Very long (50+ turn) sessions |
