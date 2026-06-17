# Models

Buddy AI supports **30+ LLM providers** through a unified `Model` interface.

## OpenAI

```python
from buddy.models.openai import OpenAIChat

model = OpenAIChat(id="gpt-4o")
model = OpenAIChat(id="gpt-4o-mini", temperature=0.7, max_tokens=2048)
```

## Anthropic

```python
pip install "buddy-ai[anthropic]"

from buddy.models.anthropic import Claude
model = Claude(id="claude-opus-4-5")
```

## Google Gemini

```python
pip install "buddy-ai[google]"

from buddy.models.google import Gemini
model = Gemini(id="gemini-1.5-pro")
```

## AWS Bedrock

```python
pip install "buddy-ai[aws]"

from buddy.models.aws import AwsBedrock
model = AwsBedrock(id="anthropic.claude-3-sonnet-20240229-v1:0")
```

## Ollama (Local)

```python
from buddy.models.ollama import Ollama
model = Ollama(id="llama3.2")  # Requires ollama server running
```

## All Supported Providers

| Provider | Import | Extra |
|----------|--------|-------|
| OpenAI | `buddy.models.openai` | core |
| Anthropic | `buddy.models.anthropic` | `[anthropic]` |
| Google Gemini | `buddy.models.google` | `[google]` |
| AWS Bedrock | `buddy.models.aws` | `[aws]` |
| Azure OpenAI | `buddy.models.azure` | core |
| Cohere | `buddy.models.cohere` | `[cohere]` |
| Ollama | `buddy.models.ollama` | core |
| Groq | `buddy.models.groq` | core |
| Mistral | `buddy.models.mistral` | core |
| HuggingFace | `buddy.models.huggingface` | core |
| DeepSeek | `buddy.models.deepseek` | core |
| xAI (Grok) | `buddy.models.xai` | core |
| Perplexity | `buddy.models.perplexity` | core |
| Together AI | `buddy.models.together` | core |
| Fireworks | `buddy.models.fireworks` | core |
| LiteLLM | `buddy.models.litellm` | core |

See [Model Providers Overview](../models/overview.md) for the full list.
