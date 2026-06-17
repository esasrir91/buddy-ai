# Frequently Asked Questions

## How many LLM providers does Buddy AI support?

30+ providers ship under `buddy.models.*`, including OpenAI, Anthropic, Google
Gemini, AWS Bedrock, Azure OpenAI, Cohere, Ollama, Groq, Mistral, HuggingFace,
DeepSeek, xAI, Perplexity, Together AI, and many more. See
[Model Providers](../models/overview.md).

## Do I need API keys?

For hosted providers, yes — each reads its key from an environment variable
(e.g. `OPENAI_API_KEY`). For local inference with Ollama or a self-hosted vLLM
server, no key is required.

## Can I run models locally / offline?

Yes. Use `Ollama` (`from buddy.models.ollama import Ollama`) or another local
provider. No internet connection or API key is needed once the model is pulled.
Buddy also includes optional training extras (`pip install "buddy-ai[training]"`)
for fine-tuning workflows.

## Can I use multiple providers in one application?

Yes. Each `Agent` has its own `model`, so you can mix providers freely — for
example within a `Team`:

```python
from buddy import Agent, Team
from buddy.models.openai import OpenAIChat
from buddy.models.anthropic import Claude

team = Team(
    members=[
        Agent(model=OpenAIChat(id="gpt-4o")),
        Agent(model=Claude(id="claude-3-5-sonnet-20241022")),
    ],
)
```

!!! note "`Team` uses `members=`"
    The team's participants are passed via the required `members` parameter.

## What is iRAG?

iRAG (`buddy.knowledge.irag`) is Buddy's built-in retrieval engine that combines
spaCy NLP, TF-IDF, and cosine similarity. It needs no external vector database.
If you prefer a vector store, use a knowledge base with a `vector_db` such as
`ChromaDb` — see the [Knowledge API](../api/knowledge-api.md).

## Does memory persist between runs?

In-process memory persists for the life of the agent object. For durability
across restarts, attach storage: `storage=SqliteStorage(...)` persists sessions,
and `memory=Memory(db=SqliteMemoryDb(...))` with `enable_user_memories=True`
persists user memories. Pass a stable `session_id`/`user_id` to resume. See the
[memory example](../examples/basic.md#agent-with-memory).

## How is Buddy AI different from using a provider SDK directly?

A raw SDK (e.g. the `openai` package) gives you one model call. Buddy adds the
agent layer on top: tool calling, memory and sessions, knowledge/RAG, multi-agent
teams, workflows, structured (Pydantic) outputs, streaming, and deployment via
`FastAPIApp` — all behind a consistent API that works across 30+ providers.

## Can I define my own tools?

Yes — any Python function with type hints and a docstring can be passed in
`tools=[...]`, or you can use the `@tool` decorator / build a `Toolkit`. See
[Custom Tools](../tools/custom.md).

## What license is Buddy AI under?

MIT.

## How do I report a bug or get help?

Open a [GitHub Issue](https://github.com/esasrir91/buddy-ai/issues) with a
minimal reproducible example (include `get_version_info()` output), or ask in
[GitHub Discussions](https://github.com/esasrir91/buddy-ai/discussions).
