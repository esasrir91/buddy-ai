# Common Issues

Fixes for the problems you are most likely to hit when installing and running
Buddy AI. See also [Debugging](debugging.md) and the [FAQ](faq.md).

## Installation & extras

Buddy keeps optional dependencies out of the base install. If a provider, tool,
or feature reports a missing module, install the matching extra.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: No module named 'anthropic'` | Anthropic provider not installed | `pip install "buddy-ai[anthropic]"` |
| `ImportError: ... 'google.generativeai'` | Google provider missing | `pip install "buddy-ai[google]"` |
| `ImportError: No module named 'boto3'` | AWS Bedrock missing | `pip install "buddy-ai[aws]"` |
| `ImportError: No module named 'torch'` | Training extras missing | `pip install "buddy-ai[training]"` |
| `ImportError: No module named 'PIL'` / `cv2` | Multimodal extras missing | `pip install "buddy-ai[multimodal]"` |
| `ImportError: The 'chromadb' package is not installed` | Vector DB missing | `pip install chromadb` |

!!! tip "Install everything"
    To pull in all common providers and features at once:
    ```bash
    pip install "buddy-ai[all]"
    ```
    Available extras include `openai`, `anthropic`, `google`, `cohere`, `aws`,
    `azure`, `irag`, `multimodal`, `training`, `tools`, and `all`.

## Missing API keys

Most providers read their key from an environment variable. A missing key
usually surfaces as an authentication error from the provider SDK.

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=AIza...
export TAVILY_API_KEY=tvly-...   # for TavilyTools
```

Verify a key is visible to your process:

```bash
echo $OPENAI_API_KEY
```

!!! note "Local models need no key"
    Providers like `Ollama` (`from buddy.models.ollama import Ollama`) run
    locally and require no API key.

## Wrong model id

Each provider validates the `id` you pass. A typo or an id your account cannot
access raises a provider error. Double-check the id against your provider's
catalog:

```python
from buddy.models.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o-mini"))  # not "gpt4o-mini"
```

## Agent returns an empty response

1. Confirm the API key is set (see above).
2. Turn on debug logging to see the raw request/response:
   ```python
   agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), debug_mode=True)
   ```
3. Inspect the returned object directly: `print(agent.run("hi").to_dict())`.

## Rate-limit / transient errors

Add retries at the model level, or per run:

```python
from buddy.models.openai import OpenAIChat

agent = Agent(model=OpenAIChat(id="gpt-4o-mini", max_retries=3))
# or bound retries on a single call:
agent.run("Summarize this.", retries=2)
```

The agent also supports `retries`, `delay_between_retries`, and
`exponential_backoff` constructor parameters.

## Memory not persisting between runs

Pass a stable `session_id` (and `user_id`) across calls, and configure a
backend so state survives process restarts:

```python
agent.run("Hello", session_id="my-session", user_id="user-123")
agent.run("Remember me?", session_id="my-session", user_id="user-123")
```

For durable storage use `storage=SqliteStorage(...)` for sessions and
`memory=Memory(db=SqliteMemoryDb(...))` for user memories — see the
[memory example](../examples/basic.md#agent-with-memory).

## Optional feature not available

If a feature like planning or PULSE seems missing, its extra may not be
installed. Check at runtime:

```python
from buddy import get_available_features, check_feature

print(get_available_features())   # e.g. ["reasoning", "pulse", "core"]
print(check_feature("planning"))  # False if its deps are missing
```
