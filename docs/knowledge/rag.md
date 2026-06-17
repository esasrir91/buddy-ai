# RAG Implementation

Retrieval-Augmented Generation grounds an agent's answers in your own documents.
buddy-ai supports two retrieval styles, both driven by parameters on `Agent`
(and `Team`).

## Two retrieval modes

| Mode | Parameter | When retrieval happens |
|------|-----------|------------------------|
| **Agentic RAG** | `search_knowledge=True` (default) | The model calls a search tool *on demand* during its reasoning |
| **Traditional RAG** | `add_references=True` | Retrieval runs *before* the model, injecting context into the prompt |

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat

# Agentic: the model decides when to search
agent = Agent(model=OpenAIChat(id="gpt-4o"), knowledge=knowledge, search_knowledge=True)

# Traditional: always prepend retrieved references
agent = Agent(model=OpenAIChat(id="gpt-4o"), knowledge=knowledge, add_references=True)
```

The relevant `Agent` parameters (from `buddy/agent/agent.py`) are:

- `knowledge` — the `AgentKnowledge` instance.
- `search_knowledge` (default `True`) — register the knowledge-search tool.
- `add_references` (default `False`) — inject retrieved passages into the prompt.
- `knowledge_filters` — metadata filters applied to every search.
- `enable_agentic_knowledge_filters` — let the model choose filters itself.
- `retriever` — a custom callable that replaces the default search.
- `references_format` — `"json"` (default) or `"yaml"`.

## Retrieval flow

1. A query is produced — either the model's tool call (agentic) or the user
   message (traditional).
2. `AgentKnowledge.search(query, num_documents, filters)` runs.
3. That calls `vector_db.search(query, limit, filters)`, returning the top
   `num_documents` (default `5`) `Document`s.
4. The passages are returned to the model — as a tool result or as references in
   the prompt, formatted per `references_format`.

## Knowledge filters

Filters narrow retrieval to documents whose metadata matches. Pass them once on
the agent, or per call to `run()`.

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    knowledge_filters={"department": "engineering"},
)

# Or per-run:
agent.print_response("What is the on-call policy?",
                     knowledge_filters={"team": "platform"})
```

Metadata keys become valid filters as documents are loaded; `AgentKnowledge`
tracks them and validates filter keys via `validate_filters()`.

## Custom retriever

Supply a `retriever` callable to bypass the built-in search entirely — useful for
hybrid search, reranking, or an external service.

```python
def my_retriever(agent, query, num_documents=5, **kwargs):
    docs = my_search_service(query, k=num_documents)
    return [{"content": d.text, "meta_data": d.meta} for d in docs]

agent = Agent(model=OpenAIChat(id="gpt-4o"), knowledge=knowledge, retriever=my_retriever)
```

## iRAG: the built-in lightweight RAG

`iRAG` (`buddy.knowledge.irag`) is a self-contained knowledge base that needs **no
external vector database**. It stores documents in **SQLite** and retrieves with
a blend of TF-IDF cosine similarity, NLP ontology matching (via spaCy, if
installed), and basic/fuzzy text search.

```python
from buddy.knowledge import irag

kb = irag(file_path="support_docs.txt", strict_kb_mode=True)
kb.load()

results = kb.search("login error timeout")
```

!!! note "What iRAG is good for — and its trade-offs"
    iRAG is convenient for local files and logs because it has no infrastructure
    dependency and ingests directories directly (`dir_path=...`). It is **not** a
    dense-vector semantic engine: ranking is lexical/TF-IDF based, and its
    defaults favor recall (broad results) over precision. spaCy ontology features
    require `en_core_web_sm`. The class is exported lowercase as `irag`, and it
    also offers helpers like `search_comprehensive()`, `create_agent()` and
    `get_database_info()`.

For semantic retrieval at scale, prefer a standard `AgentKnowledge` subclass with
a [vector database](vectordb.md).
