# Frequently Asked Questions

## What LLM providers does Buddy AI support?

35+ providers including OpenAI, Anthropic, Google Gemini, AWS Bedrock, Azure OpenAI, Cohere,
Ollama, Groq, Mistral, HuggingFace, DeepSeek, xAI, Perplexity, Together AI, and more.
See [Model Providers](../models/overview.md).

## Do I need an internet connection?

Not if you use a local provider like Ollama or a self-hosted vLLM server.

## How is Buddy AI different from LangChain?

Buddy AI focuses on **production-grade agents** with a simpler, Pydantic-first API.
It ships iRAG (no external vector DB needed), built-in personality and evolution engines,
and a hosted Playground UI out of the box — without the complexity of LangChain's chain abstractions.

## What is iRAG?

iRAG is Buddy AI's custom RAG engine that uses spaCy NLP, TF-IDF, and cosine similarity.
It requires no external vector database and is included in the base install. See [Knowledge](../core/knowledge.md).

## Can I use multiple LLM providers in one application?

Yes. Each `Agent` has its own `model`. Mix providers freely:

```python
team = Team(
    agents=[
        Agent(model=OpenAIChat(id="gpt-4o")),
        Agent(model=Claude(id="claude-opus-4-5")),
    ]
)
```

## Is Buddy AI production-ready?

Yes. v2.0.0 ships with Docker support, PostgreSQL/Redis storage backends, streaming,
session management, security hardening, and a full test suite.

## How do I report a bug?

Open a [GitHub Issue](https://github.com/esasrir91/buddy-ai/issues) with a minimal reproducible example.

## Where can I get help?

[GitHub Discussions](https://github.com/esasrir91/buddy-ai/discussions) or open an issue.
